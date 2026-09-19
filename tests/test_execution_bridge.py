from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.execution_bridge import (
    ExecutionBridgeDenied,
    ExecutionBridgeSettings,
    ExecutionInventoryFrame,
    ExecutionOutcomeFrame,
    ExecutionPollingBridge,
    UncertainEvidence,
    load_execution_bridge_settings,
)
from sochron1k.executor import ExecutorInventory, ExecutorRejected
from sochron1k.journal import Journal
from sochron1k.main import create_app
from sochron1k.models import (
    AccountSnapshot,
    BrokerDeal,
    BrokerSnapshot,
    ExecutorRejection,
    ManagementIntent,
    ManagementOperation,
    RiskState,
    TradeMode,
)
from sochron1k.service import ExecutionService
from sochron1k.telemetry import BridgeSettings, DemoIdentity

TOKEN = "e" * 48


def settings(*, timeout=Decimal("0.20")):
    return ExecutionBridgeSettings(
        identity=DemoIdentity(
            executor_id="mt5-demo-executor-1",
            account_ref="demo-account-1",
            server="Demo-Server",
            currency="THB",
            margin_mode="retail_hedging",
            symbol="XAUUSD",
        ),
        token=SecretStr(TOKEN),
        magic_number=910001,
        response_timeout_seconds=timeout,
    )


def account(observed_at):
    return AccountSnapshot(
        account_ref="demo-account-1",
        server="Demo-Server",
        currency="THB",
        margin_mode="retail_hedging",
        trade_mode=TradeMode.DEMO,
        can_trade=True,
        equity=Decimal("100000"),
        checked_at=observed_at,
    )


def inventory_frame(bridge, observed_at, *, sequence=1, generation="terminal-a"):
    return ExecutionInventoryFrame(
        protocol="sochron.execution.inventory.v1",
        boot_id=bridge.boot_id,
        sequence=sequence,
        identity=bridge.settings.identity,
        trade_mode="demo",
        terminal_build=5320,
        terminal_connected=True,
        account_trade_allowed=True,
        algo_trading_allowed=True,
        magic_number=bridge.settings.magic_number,
        observed_at=observed_at,
        inventory=ExecutorInventory(
            executor_id=bridge.settings.identity.executor_id,
            generation=generation,
            account=account(observed_at),
            symbol="XAUUSD",
            observed_at=observed_at,
            complete=True,
            foreign_orders=0,
            foreign_positions=0,
            snapshots=(),
        ),
    )


def wait_for_command(bridge):
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        command = bridge.next_command()
        if command is not None:
            return command
        time.sleep(0.002)
    raise AssertionError("dispatch was not exposed")


def filled_snapshot(intent, volume):
    return BrokerSnapshot(
        command_id=intent.command_id,
        order_ticket="order-1",
        position_id="position-1",
        requested_volume=volume,
        filled_volume=volume,
        remaining_volume=Decimal("0"),
        deals=(BrokerDeal(deal_ticket="deal-1", volume=volume, price=intent.requested_entry),),
        stop_loss_confirmed=True,
    )


def snapshot_outcome(bridge, command, snapshot, observed_at):
    return ExecutionOutcomeFrame(
        protocol="sochron.execution.outcome.v1",
        boot_id=bridge.boot_id,
        dispatch_sequence=command.dispatch_sequence,
        attempt_id=command.attempt_id,
        generation=command.generation,
        command_id=command.command_id,
        target_command_id=command.target_command_id,
        operation=command.operation,
        observed_at=observed_at,
        status="snapshot",
        snapshot=snapshot,
    )


def test_settings_default_disabled_and_private_file(monkeypatch, tmp_path):
    monkeypatch.delenv("SOCHRON_EXECUTION_BRIDGE_CONFIG_FILE", raising=False)
    assert load_execution_bridge_settings() is None
    path = tmp_path / "execution.json"
    payload = settings().model_dump(mode="json")
    payload["token"] = TOKEN
    path.write_text(json.dumps(payload))
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_EXECUTION_BRIDGE_CONFIG_FILE", str(path))
    assert load_execution_bridge_settings().magic_number == 910001
    path.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private execution bridge configuration"):
        load_execution_bridge_settings()
    path.chmod(0o600)
    link = tmp_path / "execution-link.json"
    link.symlink_to(path)
    monkeypatch.setenv("SOCHRON_EXECUTION_BRIDGE_CONFIG_FILE", str(link))
    with pytest.raises(RuntimeError, match="Invalid private execution bridge configuration"):
        load_execution_bridge_settings()


def test_execution_credential_cannot_reuse_telemetry_credential():
    execution = settings()
    telemetry = BridgeSettings(
        identity=execution.identity,
        token=SecretStr(TOKEN),
        broker_utc_offset_seconds=0,
    )
    with pytest.raises(RuntimeError, match="require separate credentials"):
        create_app(bridge_settings=telemetry, execution_bridge_settings=execution)


@pytest.mark.anyio
async def test_http_boundary_is_authenticated_bounded_and_disabled_by_default():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()), base_url="http://fixture"
    ) as client:
        assert (await client.get("/executor/v1/status")).json()["state"] == "disabled"
        assert (await client.get("/executor/v1/challenge")).status_code == 503
        assert (await client.get("/executor/v1/commands/next")).status_code == 503

    configured = create_app(execution_bridge_settings=settings())
    bridge = configured.state.execution_bridge
    auth = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=configured), base_url="http://fixture"
    ) as client:
        assert (await client.get("/executor/v1/challenge")).status_code == 401
        challenge = (await client.get("/executor/v1/challenge", headers=auth)).json()
        assert challenge["boot_id"] == str(bridge.boot_id)
        payload = inventory_frame(bridge, datetime.now(UTC)).model_dump(mode="json")
        assert (await client.post("/executor/v1/inventory", json=payload)).status_code == 401
        accepted = await client.post("/executor/v1/inventory", headers=auth, json=payload)
        assert accepted.status_code == 200 and accepted.json()["duplicate"] is False
        response = await client.get("/executor/v1/commands/next", headers=auth)
        assert response.status_code == 204 and response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_duplicate_json_and_oversize_latch_redacted_rejection(observed_at):
    app = create_app(execution_bridge_settings=settings())
    bridge = app.state.execution_bridge
    auth = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = inventory_frame(bridge, observed_at).model_dump(mode="json")
    body = json.dumps(payload)
    ambiguous = body[:-1] + ',"sequence":1}'
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        assert (
            await client.post("/executor/v1/inventory", headers=auth, content=ambiguous)
        ).status_code == 422
        assert (await client.get("/executor/v1/status")).json()["state"] == "rejected"
        huge = b"{" + b'"x":0,' * 50_000 + b'"z":0}'
        assert (
            await client.post("/executor/v1/inventory", headers=auth, content=huge)
        ).status_code == 413


@pytest.mark.anyio
async def test_http_poll_and_outcome_complete_one_adapter_wait(intent):
    app = create_app(execution_bridge_settings=settings())
    bridge = app.state.execution_bridge
    auth = {"Authorization": f"Bearer {TOKEN}"}
    observed = datetime.now(UTC)
    request = intent.model_copy(update={"expires_at": observed + timedelta(seconds=30)})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        inventory = inventory_frame(bridge, observed).model_dump(mode="json")
        assert (
            await client.post("/executor/v1/inventory", headers=auth, json=inventory)
        ).status_code == 200
        with ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(bridge.send, request, Decimal("0.10"), "attempt-http")
            response = None
            for _ in range(100):
                response = await client.get("/executor/v1/commands/next", headers=auth)
                if response.status_code == 200:
                    break
                await asyncio.sleep(0.002)
            assert response is not None and response.status_code == 200
            command = response.json()
            outcome = ExecutionOutcomeFrame(
                protocol="sochron.execution.outcome.v1",
                boot_id=bridge.boot_id,
                dispatch_sequence=command["dispatch_sequence"],
                attempt_id=command["attempt_id"],
                generation=command["generation"],
                command_id=command["command_id"],
                operation="open",
                observed_at=datetime.now(UTC),
                status="snapshot",
                snapshot=filled_snapshot(request, Decimal("0.10")),
            )
            accepted = await client.post(
                "/executor/v1/outcomes",
                headers=auth,
                json=outcome.model_dump(mode="json"),
            )
            assert accepted.status_code == 200
            assert waiting.result(timeout=1) == outcome.snapshot


def test_inventory_replay_and_generation_fencing(observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    frame = inventory_frame(bridge, observed_at)
    assert bridge.accept_inventory(frame).duplicate is False
    assert bridge.accept_inventory(frame).duplicate is True
    with pytest.raises(ExecutionBridgeDenied, match="SEQUENCE_CONFLICT"):
        bridge.accept_inventory(frame.model_copy(update={"terminal_build": 5321}))
    assert bridge.status().state == "rejected"
    with pytest.raises(ConnectionError, match="inventory is unavailable"):
        bridge.inventory()
    recovery = inventory_frame(bridge, observed_at, sequence=2)
    assert bridge.accept_inventory(recovery).duplicate is False
    assert bridge.status().state == "connected"


def test_entry_poll_round_trip_and_exact_outcome_replay(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    volume = Decimal("0.10")
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.send, intent, volume, "attempt-entry-1")
        command = wait_for_command(bridge)
        assert command.operation == "open"
        assert command.volume == volume
        assert command.fingerprint == intent.canonical_fingerprint()
        assert command.stop_loss == intent.stop_loss
        outcome = snapshot_outcome(bridge, command, filled_snapshot(intent, volume), observed_at)
        assert bridge.accept_outcome(outcome).duplicate is False
        assert waiting.result(timeout=1) == outcome.snapshot
    assert bridge.accept_outcome(outcome).duplicate is True
    with pytest.raises(ExecutionBridgeDenied, match="OUTCOME_CONFLICT"):
        bridge.accept_outcome(
            outcome.model_copy(update={"observed_at": observed_at + timedelta(milliseconds=1)})
        )


def test_bound_outcome_cannot_clear_an_inventory_protocol_rejection(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    original = inventory_frame(bridge, observed_at)
    bridge.accept_inventory(original)
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.send, intent, Decimal("0.10"), "attempt-latched")
        command = wait_for_command(bridge)
        with pytest.raises(ExecutionBridgeDenied, match="SEQUENCE_CONFLICT"):
            bridge.accept_inventory(original.model_copy(update={"terminal_build": 5321}))
        bridge.accept_outcome(
            snapshot_outcome(
                bridge,
                command,
                filled_snapshot(intent, Decimal("0.10")),
                observed_at,
            )
        )
        assert waiting.result(timeout=1).command_id == intent.command_id

    assert bridge.status().state == "rejected"
    with pytest.raises(ConnectionError, match="inventory is unavailable"):
        bridge.inventory()
    bridge.accept_inventory(inventory_frame(bridge, observed_at, sequence=2))
    assert bridge.status().state == "connected"


def test_unclaimed_timeout_withdraws_dispatch(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(timeout=Decimal("0.01")), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    with pytest.raises(TimeoutError):
        bridge.send(intent, Decimal("0.10"), "attempt-unclaimed")
    assert bridge.next_command() is None
    assert bridge.query(intent.command_id) is None


def test_adapter_refuses_foreign_identity_and_management_target(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    with pytest.raises(RuntimeError, match="EXECUTOR_DISPATCH_IDENTITY_MISMATCH"):
        bridge.send(
            intent.model_copy(update={"account_ref": "another-account"}),
            Decimal("0.10"),
            "attempt-foreign",
        )
    close = ManagementIntent(
        command_id="manage-wrong-target",
        idempotency_key="manage-wrong-target",
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        target_command_id=intent.command_id,
        symbol=intent.symbol,
        operation=ManagementOperation.CLOSE,
        reason="owner_request",
        expires_at=observed_at + timedelta(seconds=30),
    )
    with pytest.raises(RuntimeError, match="EXECUTOR_TARGET_MISMATCH"):
        bridge.manage(
            close,
            filled_snapshot(intent, Decimal("0.10")).model_copy(
                update={"command_id": "another-command"}
            ),
            "attempt-wrong-target",
        )
    assert bridge.next_command() is None


def test_claimed_timeout_retains_same_dispatch_for_late_reconciliation(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(timeout=Decimal("0.03")), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.send, intent, Decimal("0.10"), "attempt-claimed")
        command = wait_for_command(bridge)
        with pytest.raises(TimeoutError):
            waiting.result(timeout=1)
    assert bridge.next_command() == command
    snapshot = filled_snapshot(intent, Decimal("0.10"))
    bridge.accept_outcome(snapshot_outcome(bridge, command, snapshot, observed_at))
    assert bridge.query(intent.command_id) == snapshot
    bridge.accept_inventory(inventory_frame(bridge, observed_at, sequence=2))
    assert bridge.query(intent.command_id) is None


def test_uncertain_result_never_becomes_rejection(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.send, intent, Decimal("0.10"), "attempt-unknown")
        command = wait_for_command(bridge)
        bridge.accept_outcome(
            ExecutionOutcomeFrame(
                protocol="sochron.execution.outcome.v1",
                boot_id=bridge.boot_id,
                dispatch_sequence=command.dispatch_sequence,
                attempt_id=command.attempt_id,
                generation=command.generation,
                command_id=command.command_id,
                operation="open",
                observed_at=observed_at,
                status="uncertain",
                uncertain=UncertainEvidence(retcode=10012, retcode_external=0, request_id=11),
            )
        )
        with pytest.raises(TimeoutError, match="EXECUTOR_OUTCOME_UNCERTAIN"):
            waiting.result(timeout=1)
    assert bridge.query(intent.command_id) is None


def test_management_dispatch_uses_confirmed_target_and_typed_rejection(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    target = filled_snapshot(intent, Decimal("0.10"))
    close = ManagementIntent(
        command_id="manage-close-bridge",
        idempotency_key="manage-close-bridge",
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        target_command_id=intent.command_id,
        symbol=intent.symbol,
        operation=ManagementOperation.CLOSE,
        reason="owner_request",
        expires_at=observed_at + timedelta(seconds=30),
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.manage, close, target, "attempt-close")
        command = wait_for_command(bridge)
        assert command.operation == "close"
        assert command.volume == target.open_position_volume
        assert command.position_id == target.position_id
        assert command.broker_order_ticket == target.order_ticket
        evidence = ExecutorRejection(
            command_id=close.command_id,
            target_command_id=intent.command_id,
            operation="close",
            retcode=10006,
            retcode_external=0,
            request_id=12,
            observed_at=observed_at,
        )
        bridge.accept_outcome(
            ExecutionOutcomeFrame(
                protocol="sochron.execution.outcome.v1",
                boot_id=bridge.boot_id,
                dispatch_sequence=command.dispatch_sequence,
                attempt_id=command.attempt_id,
                generation=command.generation,
                command_id=command.command_id,
                target_command_id=command.target_command_id,
                operation="close",
                observed_at=observed_at,
                status="rejected",
                rejection=evidence,
            )
        )
        with pytest.raises(ExecutorRejected) as rejected:
            waiting.result(timeout=1)
    assert rejected.value.evidence == evidence
    assert bridge.query_management(close.command_id) == evidence


def test_generation_change_is_denied_while_dispatch_is_active(intent, observed_at):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.send, intent, Decimal("0.10"), "attempt-active")
        wait_for_command(bridge)
        with pytest.raises(ExecutionBridgeDenied, match="GENERATION_CHANGED_WITH_ACTIVE_COMMAND"):
            bridge.accept_inventory(
                inventory_frame(
                    bridge,
                    observed_at + timedelta(milliseconds=1),
                    sequence=2,
                    generation="terminal-b",
                )
            )
        with pytest.raises(TimeoutError):
            waiting.result(timeout=1)


def test_unclaimed_dispatch_is_not_exposed_after_inventory_becomes_unsafe(
    intent, observed_at
):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(bridge.send, intent, Decimal("0.10"), "attempt-disabled")
        deadline = time.monotonic() + 1
        while not bridge.status().active_command and time.monotonic() < deadline:
            time.sleep(0.002)
        assert bridge.status().active_command
        bridge.accept_inventory(
            inventory_frame(bridge, observed_at, sequence=2).model_copy(
                update={"algo_trading_allowed": False}
            )
        )
        assert bridge.next_command() is None
        with pytest.raises(ConnectionError, match="INVENTORY_UNAVAILABLE_BEFORE_CLAIM"):
            waiting.result(timeout=1)


def test_execution_service_journals_before_poll_and_applies_returned_snapshot(
    tmp_path, policy, contract, market, intent, risk, observed_at
):
    bridge = ExecutionPollingBridge(settings(), utc_now=lambda: observed_at)
    bridge.accept_inventory(inventory_frame(bridge, observed_at))
    journal = Journal(tmp_path / "bridge-service.sqlite3")
    journal.save_risk_state(
        RiskState(
            account_ref=intent.account_ref,
            experiment_id=intent.experiment_id,
            bangkok_day=observed_at.date(),
            daily_baseline=risk.daily_baseline,
            experiment_baseline=risk.experiment_baseline,
            updated_at=observed_at,
        )
    )
    service = ExecutionService(journal, bridge)
    bound_policy = replace(policy, margin_mode="retail_hedging")
    bound_account = account(observed_at)
    service.startup(
        policy=bound_policy,
        experiment_id=intent.experiment_id,
        executor_id=settings().identity.executor_id,
        now=observed_at,
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        waiting = pool.submit(
            service.submit,
            policy=bound_policy,
            account=bound_account,
            contract=contract,
            market=market,
            intent=intent,
            risk=risk,
            now=observed_at,
        )
        command = wait_for_command(bridge)
        assert journal.counts()["dispatch_attempts"] == 1
        assert journal.command(intent.command_id)["state"] == "sent"
        snapshot = filled_snapshot(intent, command.volume)
        bridge.accept_outcome(snapshot_outcome(bridge, command, snapshot, observed_at))
        result = waiting.result(timeout=1)
    assert result.state.value == "filled" and result.protected
    assert journal.broker_snapshot(intent.command_id) == snapshot
