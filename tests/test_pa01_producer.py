from __future__ import annotations

import copy
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from sochron1k.chart import ChartSettings
from sochron1k.telemetry import DemoIdentity
from sochron_worker.pa01_cli import main as pa01_main
from sochron_worker.pa01_config import (
    PA01ConfigInvalid,
    PA01ProducerConfig,
    load_pa01_config,
)
from sochron_worker.pa01_driver import (
    PA01DestinationConflict,
    PA01DestinationUnavailable,
    PA01ProducerDriver,
)
from sochron_worker.pa01_envelope import PA01DecisionEnvelope
from sochron_worker.pa01_http import PA01SupabaseDestination
from sochron_worker.pa01_journal import PA01JournalUnavailable, PA01ProducerJournal
from sochron_worker.pa01_source import (
    PA01DecisionSource,
    PA01SourceUnavailable,
    PolicyFileSource,
)
from test_pa01_envelope import CODE_HASH, native_m1, policy

OWNER = UUID("90000000-0000-4000-8000-000000000001")
ORIGIN = "http://127.0.0.1:54321"


@dataclass
class Clock:
    utc: datetime

    def now(self) -> datetime:
        return self.utc


class FakeArchive:
    def __init__(self, directory: Path, rows) -> None:
        self.directory = directory
        self.archive_id = str(rows[0].archive_id)
        self.binding_json = json.dumps(
            {
                "identity": {
                    "executor_id": "fixture-executor",
                    "account_ref": "fixture-demo",
                    "server": "Fixture-Demo",
                    "currency": "USD",
                    "margin_mode": "retail_hedging",
                    "symbol": rows[0].symbol,
                },
                "offset": rows[0].broker_utc_offset_seconds,
                "chart": {
                    "offset_valid_from_server_s": rows[0].offset_valid_from_server_s,
                    "offset_valid_until_server_s": rows[0].offset_valid_until_server_s,
                },
            },
            sort_keys=True,
        )
        self.rows = rows
        self.calls = []

    def read_pa01(self, cutoff):
        self.calls.append(cutoff)
        return self.rows


@pytest.fixture(scope="module")
def rows():
    return tuple(native_m1(index) for index in range(720))


@pytest.fixture
def producer(tmp_path, rows):
    source_dir = (tmp_path / "archive").resolve()
    state_dir = (tmp_path / "producer").resolve()
    source_dir.mkdir(mode=0o700)
    state_dir.mkdir(mode=0o700)
    archive = FakeArchive(source_dir, rows)
    from sochron_worker.pa01_aggregation import aggregate_native_m1

    aggregation = aggregate_native_m1(rows, cutoff_utc=max(row.available_at_utc for row in rows))
    evidence = policy(aggregation)
    policy_path = (tmp_path / "policy.json").resolve()
    policy_path.write_text(evidence.model_dump_json())
    policy_path.chmod(0o600)
    clock = Clock(evidence.cutoff_utc)
    source = PA01DecisionSource(
        archive, PolicyFileSource(policy_path), CODE_HASH, utc_now=clock.now
    )
    return clock, source, state_dir


def receiver_record(envelope: PA01DecisionEnvelope, created_at: datetime) -> dict:
    snapshot = envelope.snapshot.model_dump(mode="json")
    signal = envelope.signal.model_dump(mode="json")
    for name in ("event_time", "received_at", "available_at"):
        snapshot[name] = snapshot[name].replace("Z", "+00:00")
    for name in ("formed_at", "confirmed_at", "expires_at"):
        signal[name] = signal[name].replace("Z", "+00:00")
    snapshot.update(row_id=101, created_at=created_at.isoformat())
    signal.update(row_id=202, created_at=created_at.isoformat())
    return {
        "protocol": envelope.protocol,
        "found": True,
        "owner_id": str(OWNER),
        "strategy_version_id": 11,
        "experiment_id": 22,
        "producer_revision": envelope.producer_revision,
        "decision_fingerprint": envelope.decision_fingerprint,
        "snapshot": snapshot,
        "signal": signal,
    }


class FakeDestination:
    owner_id = str(OWNER)
    strategy_version_id = 11
    experiment_id = 22
    origin = ORIGIN

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.stores = 0
        self.reads = 0
        self.saved = None
        self.lose_after_commit = False
        self.missing = False
        self.conflict = False
        self.on_store = None

    def store(self, envelope):
        self.stores += 1
        if self.on_store:
            self.on_store(envelope)
        if self.conflict:
            raise PA01DestinationConflict()
        self.saved = receiver_record(envelope, self.clock.utc)
        if self.lose_after_commit:
            raise PA01DestinationUnavailable()

    def read(self, envelope):
        self.reads += 1
        if self.missing or self.saved is None:
            return {
                "protocol": "sochron.pa01.decision.v1",
                "found": False,
                "owner_id": self.owner_id,
                "signal_id": envelope.signal.signal_id,
            }
        return copy.deepcopy(self.saved)


def open_journal(producer, *, create=False):
    clock, source, state_dir = producer
    return PA01ProducerJournal(
        state_dir,
        source,
        OWNER,
        11,
        22,
        ORIGIN,
        create=create,
        utc_now=clock.now,
    )


def test_source_builds_one_exact_decision_per_new_m5_and_denies_stale_policy(producer):
    clock, source, _ = producer
    envelope = source.next(None)
    assert envelope is not None
    assert envelope.protocol == "sochron.pa01.decision.v2"
    assert source.next(envelope.signal.formed_at) is None
    assert source.archive.calls == [envelope.signal.confirmed_at, envelope.signal.confirmed_at]

    clock.utc += timedelta(seconds=31)
    with pytest.raises(PA01SourceUnavailable, match=r"^PA01_SOURCE_UNAVAILABLE$"):
        source.next(None)


def test_journal_is_unknown_before_send_and_lost_response_reconciles_without_resend(producer):
    clock, _, state_dir = producer
    destination = FakeDestination(clock)
    destination.lose_after_commit = True
    with open_journal(producer, create=True) as journal:

        def inspect(envelope):
            with sqlite3.connect(state_dir / "pa01.sqlite3") as db:
                row = db.execute(
                    "SELECT state,attempts,payload FROM decisions WHERE signal_id=?",
                    (envelope.signal.signal_id,),
                ).fetchone()
            assert row[:2] == ("UNKNOWN", 1)
            assert json.loads(row[2])["decision_fingerprint"] == envelope.decision_fingerprint

        destination.on_store = inspect
        assert PA01ProducerDriver(journal, destination).step() == "UNKNOWN"
        assert journal.status().pending.state == "UNKNOWN"
        assert journal.status().last_formed_at is None

    destination.lose_after_commit = False
    with open_journal(producer) as restarted:
        driver = PA01ProducerDriver(restarted, destination)
        assert driver.step() == "VERIFIED"
        assert destination.stores == 1 and destination.reads == 1
        assert restarted.status().pending is None
        assert restarted.status().last_formed_at is not None
        assert driver.step() == "IDLE"


def test_unknown_missing_readback_requires_later_step_before_resend(producer):
    clock, _, _ = producer
    destination = FakeDestination(clock)
    destination.lose_after_commit = True
    with open_journal(producer, create=True) as journal:
        driver = PA01ProducerDriver(journal, destination)
        assert driver.step() == "UNKNOWN" and destination.stores == 1
        destination.saved = None
        destination.lose_after_commit = False
        assert driver.step() == "PREPARED"
        assert destination.stores == 1
        assert driver.step() == "VERIFIED"
        assert destination.stores == 2


@pytest.mark.parametrize("kind", ["foreign", "changed", "shape", "confirmed"])
def test_confirmed_or_readback_conflicts_quarantine_persistently(producer, kind):
    clock, _, _ = producer
    destination = FakeDestination(clock)
    with open_journal(producer, create=True) as journal:
        if kind == "confirmed":
            destination.conflict = True
            assert PA01ProducerDriver(journal, destination).step() == "QUARANTINED"
        else:
            destination.lose_after_commit = True
            driver = PA01ProducerDriver(journal, destination)
            assert driver.step() == "UNKNOWN"
            destination.lose_after_commit = False
            if kind == "foreign":
                destination.saved["owner_id"] = str(UUID(int=2))
            elif kind == "changed":
                destination.saved["signal"]["action"] = "buy"
            else:
                destination.saved["extra"] = True
            assert driver.step() == "QUARANTINED"
        calls = (destination.stores, destination.reads)
        assert PA01ProducerDriver(journal, destination).step() == "QUARANTINED"
        assert (destination.stores, destination.reads) == calls


def test_reconcile_action_never_prepares_or_sends(producer):
    clock, _, _ = producer
    destination = FakeDestination(clock)
    with open_journal(producer, create=True) as journal:
        driver = PA01ProducerDriver(journal, destination)
        assert driver.reconcile_pending() == "NO_PENDING"
        pending = journal.prepare(journal.source.next(None))
        assert pending.state == "PREPARED"
        assert driver.reconcile_pending() == "REVIEW_REQUIRED"
        assert destination.stores == destination.reads == 0


def test_binding_replacement_and_tamper_fail_closed(producer):
    _, source, state_dir = producer
    with open_journal(producer, create=True) as journal:
        journal.prepare(source.next(None))
    with sqlite3.connect(state_dir / "pa01.sqlite3") as db:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("DROP TRIGGER retain_pa01_decision")
    with pytest.raises(PA01JournalUnavailable):
        open_journal(producer)


def http_response(data, *, status=200):
    return httpx.Response(
        status,
        headers={"content-type": "application/json"},
        stream=httpx.ByteStream(json.dumps(data).encode()),
    )


def test_http_uses_two_fixed_rpcs_and_ignores_store_ack(producer, tmp_path):
    clock, source, _ = producer
    key = (tmp_path / "service-key").resolve()
    key.write_text("sb_secret_" + "a" * 32)
    key.chmod(0o600)
    binding = json.loads(source.archive.binding_json)
    config = PA01ProducerConfig(
        source.archive.directory,
        (tmp_path / "unused-state").resolve(),
        source.policy.path,
        UUID(source.archive.archive_id),
        DemoIdentity.model_validate(binding["identity"]),
        binding["offset"],
        ChartSettings.model_validate(binding["chart"]),
        OWNER,
        11,
        22,
        CODE_HASH,
        ORIGIN,
        key,
    )
    envelope = source.next(None)
    record = receiver_record(envelope, clock.utc)
    calls = []

    def handle(request):
        calls.append(request)
        assert request.method == "POST"
        assert request.headers["apikey"] == key.read_text()
        assert request.headers["accept-encoding"] == "identity"
        arguments = json.loads(request.content)
        if request.url.path.endswith("sochron_store_pa01_decision"):
            assert arguments["p_decision"] == envelope.model_dump(mode="json")
            assert arguments["p_strategy_version_id"] == 11
            assert arguments["p_experiment_id"] == 22
            return http_response({"untrusted_ack": True})
        assert request.url.path.endswith("sochron_read_pa01_decision")
        assert arguments == {
            "p_owner_id": str(OWNER),
            "p_signal_id": envelope.signal.signal_id,
        }
        return http_response(record)

    destination = PA01SupabaseDestination(config, transport=httpx.MockTransport(handle))
    destination.store(envelope)
    assert destination.read(envelope) == record
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (409, {"code": "23505", "message": "PA01_DECISION_CONFLICT"}),
        (400, {"code": "23514", "message": "PA01_STRATEGY_DENIED"}),
        (400, {"code": "23514", "message": "PA01_EXPERIMENT_DENIED"}),
        (400, {"code": "23514", "message": "PA01_FEATURES_INVALID"}),
        (400, {"code": "23514", "message": "PA01_POLICY_CONTEXT_INVALID"}),
        (400, {"code": "22023", "message": "PA01_DECISION_INVALID"}),
        (400, {"code": "22023", "message": "PA01_READ_INVALID"}),
    ],
)
def test_http_confirmed_receiver_denials_are_conflicts(producer, tmp_path, status, error):
    _, source, _ = producer
    key = (tmp_path / "service-key").resolve()
    key.write_text("sb_secret_" + "b" * 32)
    key.chmod(0o600)
    binding = json.loads(source.archive.binding_json)
    config = PA01ProducerConfig(
        source.archive.directory,
        (tmp_path / "unused-state").resolve(),
        source.policy.path,
        UUID(source.archive.archive_id),
        DemoIdentity.model_validate(binding["identity"]),
        binding["offset"],
        ChartSettings.model_validate(binding["chart"]),
        OWNER,
        11,
        22,
        CODE_HASH,
        ORIGIN,
        key,
    )
    destination = PA01SupabaseDestination(
        config, transport=httpx.MockTransport(lambda request: http_response(error, status=status))
    )
    with pytest.raises(PA01DestinationConflict):
        destination.store(source.next(None))


def test_policy_file_rejects_public_symlink_and_replacement_race(producer, monkeypatch):
    _, source, _ = producer
    path = source.policy.path
    original = path.read_bytes()
    path.chmod(0o644)
    with pytest.raises(PA01SourceUnavailable):
        source.policy.read()
    path.chmod(0o600)
    alias = path.with_name("policy-alias.json")
    alias.symlink_to(path)
    with pytest.raises(PA01SourceUnavailable):
        PolicyFileSource(alias).read()
    path.write_bytes(original)
    path.chmod(0o600)
    real_fstat = os.fstat
    calls = 0

    def changed(descriptor):
        nonlocal calls
        calls += 1
        result = real_fstat(descriptor)
        if calls == 2:
            path.write_bytes(original + b" ")
        return result

    monkeypatch.setattr(os, "fstat", changed)
    with pytest.raises(PA01SourceUnavailable):
        source.policy.read()


def config_payload(producer, key):
    _, source, state_dir = producer
    binding = json.loads(source.archive.binding_json)
    return {
        "enabled": True,
        "source_directory": str(source.archive.directory),
        "state_directory": str(state_dir),
        "policy_file": str(source.policy.path),
        "archive_id": source.archive.archive_id,
        "identity": binding["identity"],
        "offset_seconds": binding["offset"],
        "chart": binding["chart"],
        "owner_id": str(OWNER),
        "strategy_version_id": 11,
        "experiment_id": 22,
        "code_hash": CODE_HASH,
        "origin": ORIGIN,
        "service_key_file": str(key),
    }


def write_config(tmp_path, monkeypatch, data):
    path = (tmp_path / "pa01-config.json").resolve()
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_PA01_CONFIG_FILE", str(path))
    return path


def test_private_config_roundtrip_disabled_and_cli_default(producer, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SOCHRON_PA01_CONFIG_FILE", raising=False)
    assert load_pa01_config() is None
    assert pa01_main(["run", "--once"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "DISABLED",
        "execution_ready": False,
        "auto_trading_enabled": False,
    }

    key = (tmp_path / "key").resolve()
    key.write_text("sb_secret_" + "c" * 32)
    key.chmod(0o600)
    expected = config_payload(producer, key)
    write_config(tmp_path, monkeypatch, expected)
    observed = load_pa01_config()
    assert observed.owner_id == OWNER
    assert observed.strategy_version_id == 11 and observed.experiment_id == 22
    assert observed.code_hash == CODE_HASH and observed.origin == ORIGIN

    write_config(tmp_path, monkeypatch, {"enabled": False})
    assert load_pa01_config() is None


@pytest.mark.parametrize(
    "change",
    [
        {"strategy_version_id": True},
        {"experiment_id": 0},
        {"code_hash": "A" * 64},
        {"origin": "https://example.test/path"},
        {"owner_id": "not-a-uuid"},
        {"unexpected": "never print me"},
    ],
)
def test_config_denials_are_redacted(producer, tmp_path, monkeypatch, change):
    key = (tmp_path / "key").resolve()
    key.write_text("sb_secret_" + "d" * 32)
    key.chmod(0o600)
    data = config_payload(producer, key)
    data.update(change)
    write_config(tmp_path, monkeypatch, data)
    with pytest.raises(PA01ConfigInvalid, match=r"^PA01_CONFIG_INVALID$"):
        load_pa01_config()
