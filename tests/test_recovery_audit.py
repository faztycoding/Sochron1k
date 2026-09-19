import hashlib
import json
import socket
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sochron1k.bar_history import BarHistory
from sochron1k.journal import Journal
from sochron1k.models import (
    BrokerDeal,
    BrokerSnapshot,
    CommandState,
    ExecutorRejection,
    ManagementIntent,
    ManagementOperation,
    ManagementSnapshot,
    RiskState,
)
from sochron1k.sqlite_snapshot import (
    SnapshotUnavailable,
    create_snapshot,
    materialize_snapshot,
    verify_snapshot,
)
from sochron_worker import recovery_audit as audit
from sochron_worker.sync_journal import SyncJournal, canonical
from test_bar_history import accept, attach
from test_bar_history import archive as archive
from test_chart import packet
from test_chart import setup_chart as setup_chart
from test_native_source import record_packet, source, tamper
from test_sync_driver import ORIGIN, OWNER


@pytest.fixture
def recovery_case(tmp_path, setup_chart, archive, intent):
    attach(setup_chart, archive)
    accept(setup_chart)
    directory = tmp_path.resolve() / "worker"
    directory.mkdir(mode=0o700)
    reader = source(setup_chart, archive)
    commands_path = tmp_path.resolve() / "commands.sqlite3"
    commands_path.touch(mode=0o600)
    commands = Journal(commands_path)
    intent = intent.model_copy(
        update={
            "account_ref": reader_identity(setup_chart).account_ref,
            "symbol": reader_identity(setup_chart).symbol,
        }
    )
    commands.save_risk_state(
        RiskState(
            account_ref=intent.account_ref,
            experiment_id=intent.experiment_id,
            bangkok_day="2026-09-17",
            daily_baseline=Decimal("100000"),
            experiment_baseline=Decimal("100000"),
            daily_halt=True,
            total_halt=True,
            updated_at=setup_chart[0].now(),
        )
    )
    commands.reserve(intent, Decimal("0.1"), Decimal("100"))
    commands.begin_dispatch(intent.command_id, "fixture-attempt")
    commands.transition(intent.command_id, CommandState.UNKNOWN)
    with SyncJournal(
        directory, reader, OWNER, ORIGIN, create=True, utc_now=setup_chart[0].now
    ) as sync:
        pending = sync.prepare(reader.read())
        sync.begin_send(pending.batch_id)
        binding = audit.RecoveryBinding(
            identity=reader_identity(setup_chart),
            active_experiment_id=intent.experiment_id,
            archive_id=UUID(archive.archive_id),
            owner_id=OWNER,
            source_directory=str(archive.directory),
            destination=ORIGIN,
            offset_seconds=7200,
            chart=setup_chart[2].settings,
        )
        yield dict(
            commands=commands,
            sync=sync,
            archive=archive,
            binding=binding,
            intent=intent,
            root=tmp_path.resolve(),
            pending=pending,
        )


def reader_identity(setup_chart):
    return setup_chart[1].settings.identity


def take(case):
    output = case["root"] / str(uuid4())
    output.mkdir(mode=0o700)
    paths = {}
    for role in ("commands", "sync", "archive"):
        paths[role] = output / role
        create_snapshot(case[role].path, paths[role])
    return paths


def inspect(case, paths=None, **changes):
    paths = paths or take(case)
    args = dict(now=datetime.now(UTC), max_age_seconds=3600, max_span_seconds=60)
    args.update(changes)
    return audit.audit_recovery_set(**paths, binding=case["binding"], **args)


def sql(path, statement, args=()):
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        db.execute(statement, args)


def fingerprint(paths):
    return {
        str(file): hashlib.sha256(file.read_bytes()).hexdigest()
        for path in paths.values()
        for file in path.iterdir()
    }


def test_compatible_unknown_halts_and_isolated_copies_without_authority(recovery_case, monkeypatch):
    case = recovery_case
    paths = take(case)
    original = fingerprint(paths)
    copies = {}
    for role, path in paths.items():
        copies[role] = path.parent / (role + "-inspection")
        materialize_snapshot(path, copies[role])

    def forbidden(*args, **kwargs):
        raise AssertionError("writer/network authority must not be used")

    for cls in (Journal, BarHistory, SyncJournal):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result = inspect(case, paths)
    copied = inspect(case, copies)
    assert result["execution_ready"] is False
    assert result["consistency"] == "causal-prefix-not-atomic"
    assert result["commands"]["unknown"] == result["commands"]["total_halts"] == 1
    assert result["commands"]["daily_halts"] == result["commands"]["exposure"] == 1
    assert result["sync"]["pending"] == dict(
        state="UNKNOWN", attempts=1, send_budget_exhausted=False
    )
    assert result["sync"]["cursor_receipt"] == 0
    assert result["archive"]["bars"] == dict(M1=2, M5=0, M15=0, H1=0)
    assert result["commands"] == copied["commands"]
    assert result["sync"] == copied["sync"]
    assert result["snapshots"] == copied["snapshots"]
    assert fingerprint(paths) == original
    assert str(case["archive"].directory) not in json.dumps(result)
    assert case["binding"].identity.account_ref not in json.dumps(result)
    assert result["broker_reconciliation"] == result["destination_reconciliation"] == "NOT_RUN"


@pytest.mark.parametrize("state", ["PREPARED", "VERIFIED", "QUARANTINED", "exhausted"])
def test_sync_states_and_budget_are_preserved(recovery_case, state):
    case, journal = recovery_case, recovery_case["sync"]
    batch = case["pending"].batch
    if state == "VERIFIED":
        journal.reconcile(
            case["pending"].batch_id,
            dict(
                archive_id=batch.archive_id,
                binding=json.loads(batch.binding_json),
                rows=batch.wire_rows(),
            ),
        )
    elif state == "QUARANTINED":
        journal.quarantine(case["pending"].batch_id)
    else:
        missing = dict(archive_id=batch.archive_id, binding=None, rows=[])
        journal.reconcile(case["pending"].batch_id, missing)
        if state == "exhausted":
            for _ in range(4):
                journal.begin_send(case["pending"].batch_id)
                journal.reconcile(case["pending"].batch_id, missing)
    before = journal.status()
    result = inspect(case)
    assert journal.status() == before
    if state == "VERIFIED":
        assert result["sync"]["pending"] is None
        assert result["sync"]["cursor_receipt"] == 1
    else:
        pending = result["sync"]["pending"]
        assert pending["state"] == ("PREPARED" if state == "exhausted" else state)
        assert pending["attempts"] == (5 if state == "exhausted" else 1)
        assert pending["send_budget_exhausted"] == (state == "exhausted")


@pytest.mark.parametrize("state", ["filled", "partial", "unprotected", "rejected"])
def test_command_broker_relationships(recovery_case, state):
    case = recovery_case
    filled = (
        Decimal("0")
        if state == "rejected"
        else Decimal("0.04")
        if state == "partial"
        else Decimal("0.1")
    )
    case["commands"].apply_broker_snapshot(
        BrokerSnapshot(
            command_id=case["intent"].command_id,
            order_ticket="order-fixture",
            position_id=None if state == "rejected" else "position-fixture",
            requested_volume=Decimal("0.1"),
            filled_volume=filled,
            remaining_volume=Decimal("0.1") - filled,
            deals=(BrokerDeal(deal_ticket="deal-fixture", volume=filled, price=Decimal("2500.2")),)
            if filled
            else (),
            stop_loss_confirmed=state in {"filled", "partial"},
            terminal_state=CommandState.REJECTED if state == "rejected" else None,
        )
    )
    result = inspect(case)
    assert result["commands"]["orders"] == 1
    assert result["commands"]["deals"] == int(bool(filled))
    assert result["commands"]["exposure"] == int(state != "rejected")
    assert result["execution_ready"] is False


def test_confirmed_rejection_without_fake_ticket_is_recovery_admitted(recovery_case):
    case = recovery_case
    case["commands"].apply_executor_rejection(
        ExecutorRejection(
            command_id=case["intent"].command_id,
            operation="open",
            retcode=10006,
            retcode_external=0,
            request_id=19,
            observed_at=case["commands"]
            .risk_state(case["intent"].account_ref, case["intent"].experiment_id)
            .updated_at,
        )
    )
    result = inspect(case)
    assert result["commands"]["executor_rejections"] == 1
    assert result["commands"]["orders"] == result["commands"]["exposure"] == 0

    sql(case["commands"].path, "UPDATE executor_rejections SET retcode=10012")
    paths = take(case)
    assert verify_snapshot(paths["commands"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(case, paths)


def close_fixture(case):
    risk = case["commands"].risk_state(case["intent"].account_ref, case["intent"].experiment_id)
    now = risk.updated_at
    case["commands"].apply_broker_snapshot(
        BrokerSnapshot(
            command_id=case["intent"].command_id,
            order_ticket="entry-order",
            position_id="position",
            requested_volume=Decimal("0.1"),
            filled_volume=Decimal("0.1"),
            remaining_volume=Decimal("0"),
            deals=(
                BrokerDeal(
                    deal_ticket="entry-deal",
                    volume=Decimal("0.1"),
                    price=Decimal("2500.2"),
                    commission=Decimal("-1"),
                    occurred_at=now,
                ),
            ),
            stop_loss_confirmed=True,
        )
    )
    intent = ManagementIntent(
        command_id="management-close",
        idempotency_key="management-close",
        account_ref=case["intent"].account_ref,
        experiment_id=case["intent"].experiment_id,
        target_command_id=case["intent"].command_id,
        symbol=case["intent"].symbol,
        operation=ManagementOperation.CLOSE,
        reason="risk_halt",
        expires_at=now + timedelta(seconds=30),
    )
    reservation = case["commands"].reserve_management(intent, expected_risk=risk)
    case["commands"].begin_management_dispatch(
        reservation.command_id, "management-attempt", expected_risk=risk
    )
    target = case["commands"].broker_snapshot(case["intent"].command_id)
    deal = BrokerDeal(
        deal_ticket="exit-deal",
        volume=target.open_position_volume,
        price=Decimal("2501.2"),
        profit=Decimal("10"),
        commission=Decimal("-1"),
        occurred_at=now,
    )
    case["commands"].apply_management_snapshot(
        ManagementSnapshot(
            command_id=intent.command_id,
            target_command_id=intent.target_command_id,
            operation=intent.operation,
            broker_order_ticket="exit-order",
            position_id=target.position_id,
            requested_volume=target.open_position_volume,
            completed_volume=target.open_position_volume,
            remaining_volume=Decimal("0"),
            deals=(deal,),
            terminal_state=CommandState.CLOSED,
            target=target.model_copy(
                update={
                    "closed_volume": target.filled_volume,
                    "stop_loss_confirmed": False,
                    "terminal_state": CommandState.CLOSED,
                }
            ),
            observed_at=now,
        )
    )


def test_management_close_and_financials_are_recovery_admitted(recovery_case):
    close_fixture(recovery_case)
    result = inspect(recovery_case)
    assert result["commands"]["management_commands"] == 1
    assert result["commands"]["management_attempts"] == 1
    assert result["commands"]["management_deals"] == 1
    assert result["commands"]["management_unresolved"] == 0
    assert result["commands"]["exposure"] == result["commands"]["unresolved"] == 0
    audit = recovery_case["commands"].final_trade_audit(recovery_case["intent"].command_id)
    assert audit.net_pnl == Decimal("8") and audit.close_reason == "risk_halt"


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE management_deals SET profit='NaN'",
        "UPDATE management_outcomes SET position_id='foreign-position'",
        "UPDATE management_outcomes SET observed_at='2099-01-01T00:00:00+00:00'",
    ],
)
def test_corrupt_management_evidence_is_denied(recovery_case, statement):
    close_fixture(recovery_case)
    assert inspect(recovery_case)["commands"]["management_deals"] == 1
    sql(recovery_case["commands"].path, statement)
    paths = take(recovery_case)
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM risk_state",
        "UPDATE risk_state SET daily_baseline='NaN'",
        "UPDATE risk_state SET total_halt=2",
        "UPDATE risk_state SET updated_at='2099-01-01T00:00:00+00:00'",
        "UPDATE commands SET fingerprint='invalid'",
        "UPDATE commands SET protected=1",
        "UPDATE commands SET state='filled'",
        "UPDATE commands SET volume='0'",
        "UPDATE exposure_slots SET reserved_loss='0.01'",
        "DELETE FROM exposure_slots",
        "DELETE FROM dispatch_attempts",
        "UPDATE command_transitions SET from_state='unknown' WHERE transition_id=2",
        "DELETE FROM command_transitions WHERE transition_id=2",
        "UPDATE sqlite_sequence SET seq=99",
        "PRAGMA user_version=99",
        "CREATE TABLE unexpected(id INTEGER)",
    ],
)
def test_command_domain_corruption_denied_after_generic_snapshot_passes(recovery_case, statement):
    sql(recovery_case["commands"].path, statement)
    paths = take(recovery_case)
    assert verify_snapshot(paths["commands"])
    before = fingerprint(paths)
    with pytest.raises(audit.RecoveryUnavailable, match=r"^RECOVERY_SET_UNAVAILABLE$"):
        inspect(recovery_case, paths)
    assert fingerprint(paths) == before


@pytest.mark.parametrize(
    "change",
    [
        {"first_received_at": "2000-01-01T00:00:00Z"},
        {"broker_utc_offset_seconds": 0},
        {"tick_size": "0.3"},
        {"confirmed_by_server_s": 60},
        {"terminal_build": 2**53},
        {"open": 2500},
    ],
)
def test_archive_semantic_corruption_with_updated_digest(recovery_case, change):
    tamper(recovery_case["archive"], change)
    paths = take(recovery_case)
    assert verify_snapshot(paths["archive"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner_id", UUID("20000000-0000-0000-0000-000000000002")),
        ("archive_id", UUID("20000000-0000-0000-0000-000000000002")),
        ("source_directory", "/different/original/path"),
        ("destination", "https://different.example.com"),
        ("active_experiment_id", "missing"),
        ("offset_seconds", 0),
    ],
)
def test_wrong_expected_binding_denied(recovery_case, field, value):
    recovery_case["binding"] = recovery_case["binding"].model_copy(update={field: value})
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE meta SET receipt=1,time_server_s=60",
        "UPDATE meta SET last_clock='2000-01-01T00:00:00+00:00'",
        "UPDATE batches SET attempts=0",
        "UPDATE batches SET attempts=6",
        "UPDATE batches SET updated_at='2099-01-01T00:00:00+00:00'",
        "UPDATE batches SET state='VERIFIED'",
        "DROP TRIGGER immutable_batch",
    ],
)
def test_sync_corruption_denied(recovery_case, statement):
    sql(recovery_case["sync"].path, statement)
    paths = take(recovery_case)
    assert verify_snapshot(paths["sync"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


def test_skipped_prefix_row_denied_even_when_every_remaining_payload_exists(recovery_case):
    path = recovery_case["sync"].path
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        raw = json.loads(db.execute("SELECT payload FROM batches").fetchone()[0])
        raw["rows"] = raw["rows"][1:]
        payload = canonical(raw)
        trigger = db.execute(
            "SELECT sql FROM sqlite_schema WHERE name='immutable_batch'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER immutable_batch")
        db.execute(
            "UPDATE batches SET payload=?,digest=?",
            (payload, hashlib.sha256(payload.encode()).hexdigest()),
        )
        db.execute(trigger)
    paths = take(recovery_case)
    assert verify_snapshot(paths["sync"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


def test_later_archive_suffix_and_all_timeframes_are_admitted(recovery_case, setup_chart):
    for sequence, timeframe in enumerate(("M5", "M15", "H1"), 2):
        record_packet(
            setup_chart, recovery_case["archive"], packet(setup_chart, timeframe, sequence)
        )
    setup_chart[0].advance(60)
    accept(setup_chart, sequence=5)
    result = inspect(recovery_case)
    assert result["archive"]["bars"] == dict(M1=3, M5=2, M15=2, H1=2)
    assert result["sync"]["pending"]["state"] == "UNKNOWN"


@pytest.mark.parametrize("which", ["age", "future", "span", "order", "naive", "bool"])
def test_snapshot_time_admission(recovery_case, which):
    paths = take(recovery_case)
    options = {}
    if which == "age":
        options["now"] = datetime.now(UTC) + timedelta(days=2)
    elif which == "future":
        options["now"] = datetime(2000, 1, 1, tzinfo=UTC)
    elif which == "naive":
        options["now"] = datetime(2026, 9, 17)
    elif which == "bool":
        options["max_age_seconds"] = True
    else:
        path = paths["commands" if which == "span" else "sync"] / "manifest.json"
        raw = json.loads(path.read_text())
        delta = timedelta(seconds=-120 if which == "span" else 1)
        for key in ("started_at", "completed_at"):
            raw[key] = (datetime.fromisoformat(raw[key]) + delta).isoformat()
        path.write_text(json.dumps(raw))
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths, **options)


def test_deadline_and_row_limit_denied(recovery_case, monkeypatch):
    paths = take(recovery_case)
    monkeypatch.setattr(audit, "AUDIT_SECONDS", -1)
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)
    monkeypatch.setattr(audit, "AUDIT_SECONDS", 30)
    monkeypatch.setattr(audit, "MAX_ROWS", 1)
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


def test_final_snapshot_reverification_is_required(recovery_case, monkeypatch):
    paths = take(recovery_case)
    original = audit._sync

    def change_after_audit(*args):
        result = original(*args)
        (paths["commands"] / "INCOMPLETE").touch(mode=0o600)
        return result

    monkeypatch.setattr(audit, "_sync", change_after_audit)
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


def verified_first_batch(case):
    batch = case["pending"].batch
    case["sync"].reconcile(
        case["pending"].batch_id,
        dict(
            archive_id=batch.archive_id,
            binding=json.loads(batch.binding_json),
            rows=batch.wire_rows(),
        ),
    )


def test_older_archive_content_denied_even_with_new_capture_time(recovery_case, setup_chart):
    case = recovery_case
    older = take(case)["archive"]
    verified_first_batch(case)
    setup_chart[0].advance(60)
    accept(setup_chart, sequence=2)
    pending = case["sync"].prepare(case["sync"].source.read(case["sync"].status().cursor))
    case["sync"].begin_send(pending.batch_id)
    assert inspect(case)["sync"]["batches"] == 2
    paths = take(case)
    stale = paths["archive"].parent / "stale-archive"
    create_snapshot(older / "snapshot.sqlite3", stale)
    paths["archive"] = stale
    assert verify_snapshot(stale)
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(case, paths)


@pytest.mark.parametrize("kind", ["payload", "sequence", "time", "missing", "boot"])
def test_archive_projection_and_receipts_denied(recovery_case, kind):
    path = recovery_case["archive"].path
    if kind == "payload":
        sql(path, "UPDATE latest_frames SET payload='{}'")
    elif kind == "missing":
        sql(path, "DELETE FROM latest_frames")
    else:
        with closing(sqlite3.connect(path, isolation_level=None)) as db:
            trigger = db.execute(
                "SELECT sql FROM sqlite_schema WHERE name='immutable_receipts_update'"
            ).fetchone()[0]
            db.execute("DROP TRIGGER immutable_receipts_update")
            statement = {
                "sequence": "UPDATE receipts SET sequence=0",
                "time": "UPDATE receipts SET received_at='2099-01-01T00:00:00+00:00'",
                "boot": "UPDATE receipts SET boot_id='invalid'",
            }[kind]
            db.execute(statement)
            db.execute(trigger)
    paths = take(recovery_case)
    assert verify_snapshot(paths["archive"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case, paths)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE broker_orders SET filled_volume='0.01'",
        "UPDATE broker_orders SET position_id=NULL",
        "UPDATE broker_orders SET sl_confirmed=0",
        "UPDATE broker_orders SET requested_volume='1'",
        "UPDATE broker_deals SET volume='0.01'",
        "UPDATE broker_deals SET price='NaN'",
        "DELETE FROM broker_deal_financials",
        "DELETE FROM broker_deals",
    ],
)
def test_corrupt_broker_evidence_denied(recovery_case, statement):
    case = recovery_case
    case["commands"].apply_broker_snapshot(
        BrokerSnapshot(
            command_id=case["intent"].command_id,
            order_ticket="order",
            position_id="position",
            requested_volume=Decimal("0.1"),
            filled_volume=Decimal("0.1"),
            remaining_volume=Decimal(0),
            deals=(BrokerDeal(deal_ticket="deal", volume=Decimal("0.1"), price=Decimal("2500.2")),),
            stop_loss_confirmed=True,
        )
    )
    assert inspect(case)["commands"]["deals"] == 1
    sql(case["commands"].path, statement)
    if statement == "DELETE FROM broker_deals":
        with pytest.raises(SnapshotUnavailable):
            take(case)
        return
    paths = take(case)
    assert verify_snapshot(paths["commands"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(case, paths)


def test_new_empty_journals_require_risk_but_allow_unsynced_archive(recovery_case, setup_chart):
    case = recovery_case
    state = case["commands"].risk_state(case["intent"].account_ref, case["intent"].experiment_id)
    empty_path = case["root"] / "empty-commands.sqlite3"
    empty_path.touch(mode=0o600)
    case["commands"] = Journal(empty_path)
    case["commands"].save_risk_state(state)
    directory = case["root"] / "empty-sync"
    directory.mkdir(mode=0o700)
    with SyncJournal(
        directory, case["sync"].source, OWNER, ORIGIN, create=True, utc_now=setup_chart[0].now
    ) as sync:
        case["sync"] = sync
        result = inspect(case)
    assert result["commands"]["commands"] == result["sync"]["batches"] == 0
    assert result["sync"]["pending"] is None
    assert result["archive"]["bars"]["M1"] == 2
    assert result["commands"]["total_halts"] == 1


def test_original_binding_is_data_not_source_access(recovery_case, monkeypatch):
    paths = take(recovery_case)
    original = sqlite3.connect

    def snapshot_only(path, *args, **kwargs):
        assert str(path).endswith("/snapshot.sqlite3?mode=ro")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", snapshot_only)
    assert inspect(recovery_case, paths)["execution_ready"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_directory", "/old/../different"),
        ("source_directory", "relative"),
        ("destination", "http://unexpected.example.com"),
        ("offset_seconds", True),
        ("offset_seconds", 61),
        ("active_experiment_id", ""),
    ],
)
def test_invalid_expected_configuration(recovery_case, field, value):
    recovery_case["binding"] = recovery_case["binding"].model_copy(update={field: value})
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(recovery_case)


@pytest.mark.parametrize(
    "target", [CommandState.CREATED, CommandState.VALIDATED, CommandState.QUEUED]
)
def test_transition_cannot_rewind_dispatched_command(recovery_case, target):
    case = recovery_case
    case["commands"].transition(case["intent"].command_id, target)
    paths = take(case)
    assert verify_snapshot(paths["commands"])
    with pytest.raises(audit.RecoveryUnavailable):
        inspect(case, paths)
