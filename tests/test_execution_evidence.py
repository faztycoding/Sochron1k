from __future__ import annotations

import gc
import hashlib
import sqlite3
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.execution_evidence import (
    MAX_COMMANDS,
    ExecutionEvidenceReader,
    load_execution_evidence_reader,
)
from sochron1k.journal import Journal
from sochron1k.main import create_app
from sochron1k.models import ManagementIntent, ManagementOperation, RiskState
from sochron1k.owner_auth import OwnerAuthDenied, OwnerAuthSettings
from sochron1k.service import ExecutionService
from sochron1k.simulator import SimulatorAdapter, SimulatorBehavior

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class VerifiedOwner:
    async def verify(self, authorization):
        if authorization != ["Bearer owner-fixture"]:
            raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        return OWNER


def private_journal(tmp_path: Path) -> tuple[Journal, Path]:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    path = directory / "commands.sqlite3"
    journal = Journal(path)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.chmod(0o600)
    return journal, path


def secure_journal_files(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.chmod(0o600)


def owner_settings() -> OwnerAuthSettings:
    return OwnerAuthSettings(
        supabase_url="https://auth.fixture.invalid",
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )


def authorized_app(reader: ExecutionEvidenceReader | None):
    app = create_app(owner_auth_settings=owner_settings(), execution_evidence=reader)
    app.state.owner_verifier = VerifiedOwner()
    return app


async def owner_read(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        return await client.get(
            "/owner/execution", headers={"Authorization": "Bearer owner-fixture"}
        )


def populate_fill(
    journal, policy, account, contract, market, intent, risk, observed_at, *, behavior=None
):
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
    adapter = SimulatorAdapter(
        behavior=behavior or SimulatorBehavior.FILL,
        account=account,
        symbol=contract.symbol,
    )
    service = ExecutionService(journal, adapter)
    service.startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=adapter.executor_id,
        now=observed_at,
    )
    return service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )


@pytest.mark.anyio
async def test_ac01_ac02_owner_route_is_authenticated_read_only_and_disabled() -> None:
    app = authorized_app(None)
    response = await owner_read(app)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "trading_mode": "demo",
        "read_only": True,
        "source": "local-execution-journal",
        "status": {
            "state": "disabled",
            "reason": "not_configured",
            "total_commands": 0,
            "truncated": False,
            "auto_trading_enabled": False,
            "execution_ready": False,
        },
        "commands": [],
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        assert (await client.get("/owner/execution")).status_code == 401
        assert (
            await client.post(
                "/owner/execution", headers={"Authorization": "Bearer owner-fixture"}
            )
        ).status_code == 405


@pytest.mark.anyio
async def test_ac04_ac05_confirmed_fill_projection_excludes_private_fields(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal, path = private_journal(tmp_path)
    result = populate_fill(journal, policy, account, contract, market, intent, risk, observed_at)
    secure_journal_files(path)
    reader = ExecutionEvidenceReader(path)

    response = await owner_read(authorized_app(reader))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == {
        "state": "available",
        "reason": None,
        "total_commands": 1,
        "truncated": False,
        "auto_trading_enabled": False,
        "execution_ready": False,
    }
    command = body["commands"][0]
    assert command["command_id"] == intent.command_id
    assert command["symbol"] == contract.symbol
    assert command["side"] == intent.side.value
    assert command["state"] == result.state.value == "filled"
    assert command["requested_volume"] == str(result.volume)
    assert command["order"]["order_ticket"]
    assert command["order"]["position_id"]
    assert command["order"]["filled_volume"] == str(result.volume)
    assert command["order"]["stop_loss_confirmed"] is True
    assert len(command["order"]["deals"]) == 1
    assert command["created_at_utc"].endswith(("Z", "+00:00"))
    assert command["updated_at_utc"].endswith(("Z", "+00:00"))
    for private in (intent.account_ref, intent.idempotency_key, str(path), "payload_json"):
        assert private not in response.text


@pytest.mark.parametrize(
    "behavior,expected_state,has_rejection",
    [
        (SimulatorBehavior.ACCEPT_THEN_TIMEOUT, "unknown", False),
        (SimulatorBehavior.REJECT, "rejected", True),
    ],
)
def test_ac05_ac06_unknown_and_confirmed_rejection_remain_distinct(
    tmp_path, policy, account, contract, market, intent, risk, observed_at,
    behavior, expected_state, has_rejection,
) -> None:
    journal, path = private_journal(tmp_path)
    populate_fill(
        journal,
        policy,
        account,
        contract,
        market,
        intent,
        risk,
        observed_at,
        behavior=behavior,
    )
    secure_journal_files(path)

    command = ExecutionEvidenceReader(path).view().commands[0]

    assert command.state.value == expected_state
    assert command.order is None
    assert (command.rejection is not None) is has_rejection
    if command.rejection is not None:
        assert command.rejection.operation == "open"
        assert command.rejection.retcode == 10006


def test_ac06_management_outcome_is_bound_to_parent(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal, path = private_journal(tmp_path)
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
    adapter = SimulatorAdapter(account=account, symbol=contract.symbol)
    service = ExecutionService(journal, adapter)
    service.startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=adapter.executor_id,
        now=observed_at,
    )
    opened = service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )
    close = ManagementIntent(
        command_id="owner-view-close",
        idempotency_key="owner-view-close",
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        target_command_id=intent.command_id,
        symbol=intent.symbol,
        operation=ManagementOperation.CLOSE,
        reason="strategy_exit",
        expires_at=observed_at + timedelta(seconds=30),
    )
    closed = service.manage(policy=policy, account=account, intent=close, now=observed_at)
    secure_journal_files(path)

    command = ExecutionEvidenceReader(path).view().commands[0]

    assert opened.state.value == "filled" and closed.state.value == "closed"
    assert command.state.value == "closed"
    assert command.order is not None and command.order.closed_volume == opened.volume
    assert len(command.management) == 1
    management = command.management[0]
    assert management.command_id == close.command_id
    assert management.operation is ManagementOperation.CLOSE
    assert management.state.value == "closed"
    assert management.outcome is not None
    assert management.outcome.completed_volume == opened.volume
    assert len(management.outcome.deals) == 1


def test_ac03_read_does_not_change_database_or_sidecars(tmp_path) -> None:
    _, path = private_journal(tmp_path)
    gc.collect()

    def evidence():
        result = {}
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(path) + suffix)
            if candidate.exists():
                info = candidate.stat()
                result[suffix] = (
                    info.st_dev,
                    info.st_ino,
                    info.st_size,
                    info.st_mtime_ns,
                    hashlib.sha256(candidate.read_bytes()).hexdigest(),
                )
        return result

    before = evidence()
    assert set(before) == {""}
    reader = ExecutionEvidenceReader(path)
    assert reader.view().status.state == "available"
    assert evidence() == before


def test_ac03_live_wal_read_does_not_checkpoint_database(tmp_path, intent) -> None:
    _, path = private_journal(tmp_path)
    gc.collect()
    with sqlite3.connect(path) as writer:
        writer.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        writer.execute(
            """
            INSERT INTO commands(
                command_id,scope,idempotency_key,fingerprint,account_ref,experiment_id,
                payload_json,volume,reserved_loss,state,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                intent.command_id,
                intent.idempotency_scope,
                intent.idempotency_key,
                intent.canonical_fingerprint(),
                intent.account_ref,
                intent.experiment_id,
                intent.model_dump_json(),
                "0.01",
                "1",
                "queued",
                "2026-09-20T00:00:00+00:00",
                "2026-09-20T00:00:00+00:00",
            ),
        )
    wal = Path(str(path) + "-wal")
    assert wal.stat().st_size > 0
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).chmod(0o600)

    def durable_evidence():
        return {
            suffix: (
                Path(str(path) + suffix).stat().st_size,
                Path(str(path) + suffix).stat().st_mtime_ns,
                hashlib.sha256(Path(str(path) + suffix).read_bytes()).hexdigest(),
            )
            for suffix in ("", "-wal")
        }

    before = durable_evidence()
    view = ExecutionEvidenceReader(path).view()
    assert view.status.state == "available" and len(view.commands) == 1
    assert durable_evidence() == before


def test_ac02_configuration_is_explicit_and_private(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SOCHRON_EXECUTION_JOURNAL_PATH", raising=False)
    assert load_execution_evidence_reader() is None
    _, path = private_journal(tmp_path)
    monkeypatch.setenv("SOCHRON_EXECUTION_JOURNAL_PATH", str(path))
    assert load_execution_evidence_reader().path == path

    path.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private execution journal"):
        load_execution_evidence_reader()
    path.chmod(0o600)
    alias = path.parent / "alias.sqlite3"
    alias.symlink_to(path)
    monkeypatch.setenv("SOCHRON_EXECUTION_JOURNAL_PATH", str(alias))
    with pytest.raises(RuntimeError, match="Invalid private execution journal"):
        load_execution_evidence_reader()


def test_ac03_replaced_or_malformed_source_is_redacted(tmp_path) -> None:
    _, path = private_journal(tmp_path)
    reader = ExecutionEvidenceReader(path)
    moved = path.with_suffix(".old")
    path.rename(moved)
    Journal(path)
    secure_journal_files(path)
    unavailable = reader.view()
    assert unavailable.status.state == "unavailable"
    assert unavailable.status.reason == "source_unavailable"
    assert unavailable.commands == ()
    assert reader.runtime_state() == "degraded"

    fresh = ExecutionEvidenceReader(path)
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE executor_rejections")
    assert fresh.view().status.state == "unavailable"


def test_ac04_latest_commands_are_bounded_and_deterministic(tmp_path, intent) -> None:
    journal, path = private_journal(tmp_path)
    for index in range(MAX_COMMANDS + 1):
        candidate = intent.model_copy(
            update={
                "command_id": f"command-{index:03d}",
                "idempotency_key": f"idempotency-{index:03d}",
                "account_ref": f"demo-{index:03d}",
            }
        )
        journal.reserve(candidate, volume=Decimal("0.01"), reserved_loss=Decimal("0.01"))
    secure_journal_files(path)

    view = ExecutionEvidenceReader(path).view()

    assert view.status.state == "available"
    assert view.status.total_commands == MAX_COMMANDS + 1
    assert view.status.truncated is True
    assert len(view.commands) == MAX_COMMANDS
    assert [item.command_id for item in view.commands] == sorted(
        (item.command_id for item in view.commands), reverse=True
    )
