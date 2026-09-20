from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from sochron_worker.research_evaluation import (
    ResearchBundle,
    ResearchEvaluationInvalid,
    bundle_dict,
    decode_envelope,
    evaluate_bundle,
    load_bundle,
)
from sochron_worker.research_evaluation_cli import main
from sochron_worker.research_evaluation_config import (
    ResearchEvaluationConfig,
    ResearchEvaluationConfigInvalid,
    load_research_evaluation_config,
)
from sochron_worker.research_evaluation_driver import (
    ResearchEvaluationDestinationConflict,
    ResearchEvaluationDestinationUnavailable,
    ResearchEvaluationDriver,
    ResearchEvaluationSendBudgetExhausted,
)
from sochron_worker.research_evaluation_http import ResearchEvaluationSupabaseDestination
from sochron_worker.research_evaluation_journal import (
    ENVELOPE_READ_PROTOCOL,
    ResearchEvaluationJournal,
    ResearchEvaluationJournalUnavailable,
)
from sochron_worker.sync_journal import canonical

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
NOW = datetime(2026, 2, 1, tzinfo=UTC)


def record_base(index: int, *, record_type: str = "closed_trade") -> dict:
    hour = index * 3
    return {
        "type": record_type,
        "setup_id": f"setup-{index}",
        "evidence_ids": [f"evidence-{index}"],
        "formed_at_utc": f"2026-01-02T{hour:02d}:00:00Z",
        "decision_available_at_utc": f"2026-01-02T{hour:02d}:01:00Z",
        "decision_at_utc": f"2026-01-02T{hour:02d}:01:00Z",
        "label_horizon_end_utc": f"2026-01-02T{hour + 1:02d}:00:00Z",
        "outcome_available_at_utc": f"2026-01-02T{hour + 1:02d}:00:00Z",
    }


def closed_trade(index: int, gross: str, label: str) -> dict:
    value = record_base(index)
    hour = index * 3
    value.update(
        label=label,
        entry_at_utc=f"2026-01-02T{hour:02d}:02:00Z",
        exit_at_utc=f"2026-01-02T{hour:02d}:30:00Z",
        filled_volume_lots="1",
        point_value_per_lot="1",
        initial_risk="10",
        gross_pnl=gross,
        swap_cost="0",
        partial_deal_count=index + 1,
    )
    return value


def excluded(index: int, record_type: str) -> dict:
    value = record_base(index, record_type=record_type)
    value["reason_code"] = record_type.upper()
    return value


def bundle_data() -> dict:
    value = {
        "protocol": "sochron.research-bundle.v1",
        "strategy_version": "PA01-v1",
        "strategy_code_hash": "a" * 64,
        "split": "walk_forward",
        "data_cutoff_utc": "2026-01-03T00:00:00Z",
        "evaluation_window": {
            "start_utc": "2026-01-02T00:00:00Z",
            "end_utc": "2026-01-03T00:00:00Z",
            "prior_development_cutoff_utc": "2026-01-01T00:00:00Z",
            "embargo_seconds": 3600,
        },
        "cost_assumptions": {
            "spread_points": "1",
            "slippage_points": "1",
            "commission_per_lot": "2",
            "swap_included": True,
            "operating_cost_per_trade": "1",
            "currency": "USD",
        },
        "bootstrap": {"seed": 17, "samples": 1000, "block_length": 2},
        "initial_equity": "1000",
        "equity_basis": "mark_to_market_including_open_exposure",
        "records": [
            closed_trade(0, "25", "TP_FIRST"),
            closed_trade(1, "-5", "SL_FIRST"),
            closed_trade(2, "5", "TIME_EXIT"),
            excluded(3, "wait"),
            excluded(4, "rejected"),
            excluded(5, "counterfactual"),
            excluded(6, "ambiguous"),
        ],
        "equity_samples": [
            {
                "event_time_utc": "2026-01-02T00:00:00Z",
                "available_at_utc": "2026-01-02T00:00:00Z",
                "equity": "1000",
                "open_setup_ids": [],
            },
            {
                "event_time_utc": "2026-01-02T00:10:00Z",
                "available_at_utc": "2026-01-02T00:10:00Z",
                "equity": "995",
                "open_setup_ids": ["setup-0"],
            },
            {
                "event_time_utc": "2026-01-02T01:10:00Z",
                "available_at_utc": "2026-01-02T01:10:00Z",
                "equity": "1020",
                "open_setup_ids": [],
            },
            {
                "event_time_utc": "2026-01-02T03:10:00Z",
                "available_at_utc": "2026-01-02T03:10:00Z",
                "equity": "1000",
                "open_setup_ids": ["setup-1"],
            },
            {
                "event_time_utc": "2026-01-02T04:10:00Z",
                "available_at_utc": "2026-01-02T04:10:00Z",
                "equity": "1010",
                "open_setup_ids": [],
            },
            {
                "event_time_utc": "2026-01-02T06:10:00Z",
                "available_at_utc": "2026-01-02T06:10:00Z",
                "equity": "1008",
                "open_setup_ids": ["setup-2"],
            },
            {
                "event_time_utc": "2026-01-03T00:00:00Z",
                "available_at_utc": "2026-01-03T00:00:00Z",
                "equity": "1010",
                "open_setup_ids": [],
            },
        ],
    }
    value["dataset_hash"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    return value


def bundle() -> ResearchBundle:
    value = bundle_data()
    return ResearchBundle.model_validate(bundle_dict(canonical(value)))


def private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path.resolve()


def private_file(path: Path, value: str) -> Path:
    path.write_text(value)
    os.chmod(path, 0o600)
    return path.resolve()


def snapshot(envelope, *, found: bool = True) -> dict:
    if not found:
        return {
            "protocol": ENVELOPE_READ_PROTOCOL,
            "found": False,
            "owner_id": str(OWNER),
            "evaluation_fingerprint": envelope.evaluation_fingerprint,
        }
    return {
        "protocol": ENVELOPE_READ_PROTOCOL,
        "found": True,
        "owner_id": str(OWNER),
        "strategy_version_id": 7,
        "experiment_id": 9,
        "evaluation": envelope.model_dump(mode="json"),
    }


def test_metrics_are_derived_deterministically_and_exclusions_are_retained():
    evaluation = evaluate_bundle(bundle())
    repeated = evaluate_bundle(bundle())
    assert evaluation == repeated
    assert evaluation.metrics.model_dump(mode="json") == {
        "sample_size": 3,
        "wins": 1,
        "losses": 1,
        "breakeven": 1,
        "net_return_pct": "1",
        "expectancy_r": "0.33333333",
        "expectancy_r_ci95_low": "-0.66666667",
        "expectancy_r_ci95_high": "1.33333333",
        "max_drawdown_pct": "1.96078431",
        "profit_factor": "2",
    }
    assert evaluation.evidence_manifest.record_counts.model_dump() == {
        "closed_trade": 3,
        "wait": 1,
        "rejected": 1,
        "counterfactual": 1,
        "ambiguous": 1,
    }
    assert decode_envelope(canonical(evaluation.model_dump(mode="json"))) == evaluation
    assert evaluation.evaluation_fingerprint == (
        "0b2b2d2b7f920d30d39c8c4b0b92710124c328bc3d07652f8031e310b71564e5"
    )


def test_future_append_changes_new_hash_without_changing_prior_evaluation():
    original = bundle_data()
    before = evaluate_bundle(ResearchBundle.model_validate(bundle_dict(canonical(original))))
    later = deepcopy(original)
    later.pop("dataset_hash")
    later["records"].append(excluded(7, "wait"))
    later["dataset_hash"] = hashlib.sha256(canonical(later).encode()).hexdigest()
    after = evaluate_bundle(ResearchBundle.model_validate(bundle_dict(canonical(later))))
    assert before.dataset_hash != after.dataset_hash
    assert before.metrics == after.metrics
    assert before.evaluation_fingerprint != after.evaluation_fingerprint
    assert (
        evaluate_bundle(ResearchBundle.model_validate(bundle_dict(canonical(original))))
        == before
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["records"].append(deepcopy(value["records"][0])),
        lambda value: value["records"][0].update(type="ambiguous", reason_code="AMBIGUOUS"),
        lambda value: value["records"][0].update(decision_at_utc="2026-01-01T23:59:00Z"),
        lambda value: value["records"][0].update(outcome_available_at_utc="2026-01-04T00:00:00Z"),
        lambda value: value["evaluation_window"].update(
            prior_development_cutoff_utc="2026-01-01T23:30:01Z"
        ),
        lambda value: value["equity_samples"][1].update(open_setup_ids=[]),
        lambda value: value["equity_samples"][-1].update(equity="1011"),
        lambda value: (
            value["cost_assumptions"].update(swap_included=False),
            value["records"][0].update(swap_cost="1"),
        ),
        lambda value: value["records"][0].update(swap_cost="1"),
        lambda value: value["bootstrap"].update(block_length=4),
    ],
)
def test_invalid_or_misleading_bundle_fails_closed(mutate):
    value = bundle_data()
    value.pop("dataset_hash")
    mutate(value)
    value["dataset_hash"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    with pytest.raises((ValueError, ResearchEvaluationInvalid)):
        checked = ResearchBundle.model_validate(bundle_dict(canonical(value)))
        evaluate_bundle(checked)


def test_bundle_requires_canonical_exact_json_and_verified_hash(tmp_path):
    directory = private_directory(tmp_path / "private")
    value = bundle_data()
    raw = canonical(value)
    path = private_file(directory / "bundle.json", raw)
    assert load_bundle(path) == bundle()
    with pytest.raises(ResearchEvaluationInvalid):
        load_bundle(private_file(directory / "pretty.json", json.dumps(value, indent=2)))
    changed = deepcopy(value)
    changed["bootstrap"]["seed"] = 18
    with pytest.raises(ResearchEvaluationInvalid):
        load_bundle(private_file(directory / "wrong-hash.json", canonical(changed)))
    floating = raw.replace('"gross_pnl":"25"', '"gross_pnl":25.0')
    with pytest.raises(ResearchEvaluationInvalid):
        load_bundle(private_file(directory / "float.json", floating))
    integer = raw.replace('"gross_pnl":"25"', '"gross_pnl":25')
    with pytest.raises(ResearchEvaluationInvalid):
        load_bundle(private_file(directory / "integer.json", integer))


def journal_case(tmp_path, *, now=lambda: NOW):
    source = private_directory(tmp_path / "source")
    state = private_directory(tmp_path / "state")
    input_file = private_file(source / "bundle.json", canonical(bundle_data()))
    envelope = evaluate_bundle(load_bundle(input_file))
    journal = ResearchEvaluationJournal(
        state,
        envelope,
        input_file,
        OWNER,
        7,
        9,
        "https://fixture.invalid",
        create=True,
        utc_now=now,
    )
    return journal, envelope, input_file, state


class Destination:
    owner_id = str(OWNER)
    strategy_version_id = 7
    experiment_id = 9
    origin = "https://fixture.invalid"

    def __init__(self, journal, *, accept_then_timeout=False, conflict=False):
        self.journal = journal
        self.accept_then_timeout = accept_then_timeout
        self.conflict = conflict
        self.stored = None
        self.sends = 0

    def store(self, envelope):
        assert self.journal.status().pending.state == "UNKNOWN"
        self.sends += 1
        if self.conflict:
            raise ResearchEvaluationDestinationConflict()
        if self.accept_then_timeout:
            self.stored = envelope
            raise ResearchEvaluationDestinationUnavailable()
        self.stored = envelope

    def read(self, envelope):
        return snapshot(envelope, found=self.stored is not None)


def test_journal_is_prepared_before_send_and_lost_response_reconciles(tmp_path):
    journal, envelope, _, _ = journal_case(tmp_path)
    try:
        assert journal.status().pending.state == "PREPARED"
        destination = Destination(journal, accept_then_timeout=True)
        driver = ResearchEvaluationDriver(journal, destination)
        assert driver.step() == "UNKNOWN"
        assert destination.sends == 1
        assert journal.status().pending.attempts == 1
        assert driver.step() == "VERIFIED"
        assert destination.sends == 1
        assert journal.status().pending.envelope == envelope
    finally:
        journal.close()


def test_absent_readback_returns_to_prepared_before_bounded_resend(tmp_path):
    journal, _, _, _ = journal_case(tmp_path)
    try:
        destination = Destination(journal)
        driver = ResearchEvaluationDriver(journal, destination, max_sends=1)
        journal.begin_send(journal.status().pending.fingerprint)
        assert driver.step() == "PREPARED"
        with pytest.raises(ResearchEvaluationSendBudgetExhausted):
            driver.step()
        assert destination.sends == 0
    finally:
        journal.close()


def test_conflict_quarantines_and_target_binding_is_fixed(tmp_path):
    journal, _, _, _ = journal_case(tmp_path)
    try:
        assert ResearchEvaluationDriver(journal, Destination(journal, conflict=True)).step() == (
            "QUARANTINED"
        )
    finally:
        journal.close()

    other = deepcopy(bundle_data())
    other.pop("dataset_hash")
    other["bootstrap"]["seed"] = 23
    other["dataset_hash"] = hashlib.sha256(canonical(other).encode()).hexdigest()
    source = private_directory(tmp_path / "other-source")
    path = private_file(source / "bundle.json", canonical(other))
    with pytest.raises(ResearchEvaluationJournalUnavailable):
        ResearchEvaluationJournal(
            (tmp_path / "state").resolve(),
            evaluate_bundle(load_bundle(path)),
            path,
            OWNER,
            7,
            9,
            "https://fixture.invalid",
        )


def test_journal_rejects_lock_contention_corruption_and_future_cutoff(tmp_path):
    journal, envelope, input_file, state = journal_case(tmp_path)
    try:
        with pytest.raises(ResearchEvaluationJournalUnavailable):
            ResearchEvaluationJournal(
                state, envelope, input_file, OWNER, 7, 9, "https://fixture.invalid"
            )
    finally:
        journal.close()
    with sqlite3.connect(state / "research-evaluation.sqlite3") as db:
        db.execute("DROP TRIGGER immutable_research_evaluation")
    with pytest.raises(ResearchEvaluationJournalUnavailable):
        ResearchEvaluationJournal(
            state, envelope, input_file, OWNER, 7, 9, "https://fixture.invalid"
        )

    future_state = private_directory(tmp_path / "future-state")
    with pytest.raises(ResearchEvaluationJournalUnavailable):
        ResearchEvaluationJournal(
            future_state,
            envelope,
            input_file,
            OWNER,
            7,
            9,
            "https://fixture.invalid",
            create=True,
            utc_now=lambda: datetime(2025, 1, 1, tzinfo=UTC),
        )


def config(tmp_path) -> ResearchEvaluationConfig:
    source = private_directory(tmp_path / "config-source")
    state = private_directory(tmp_path / "config-state")
    input_file = private_file(source / "bundle.json", canonical(bundle_data()))
    key_file = private_file(source / "service.key", "sb_secret_" + "a" * 32)
    return ResearchEvaluationConfig(
        input_file, state, OWNER, 7, 9, "https://fixture.invalid", key_file
    )


def test_http_transport_is_bounded_pinned_and_uses_backend_key(tmp_path):
    settings = config(tmp_path)
    envelope = evaluate_bundle(load_bundle(settings.input_file))
    calls = []

    def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "POST"
        assert request.url.host == "fixture.invalid"
        assert request.headers["apikey"].startswith("sb_secret_")
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        body = json.loads(request.content)
        if request.url.path.endswith("sochron_store_research_evaluation"):
            assert body["p_evaluation"]["evaluation_fingerprint"] == (
                envelope.evaluation_fingerprint
            )
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                stream=httpx.ByteStream(json.dumps(snapshot(envelope)).encode()),
            )
        assert request.url.path.endswith("sochron_read_research_evaluation")
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=httpx.ByteStream(json.dumps(snapshot(envelope)).encode()),
        )

    destination = ResearchEvaluationSupabaseDestination(
        settings, transport=httpx.MockTransport(upstream)
    )
    destination.store(envelope)
    assert destination.read(envelope) == snapshot(envelope)
    assert len(calls) == 2


def test_default_cli_is_inert_and_config_is_private(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("SOCHRON_RESEARCH_EVALUATION_CONFIG_FILE", raising=False)
    assert main(["status"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "DISABLED",
        "statistics_source_ready": False,
        "promotion_decided": False,
        "execution_ready": False,
        "auto_trading_enabled": False,
    }

    directory = private_directory(tmp_path / "config")
    source = private_directory(tmp_path / "private-source")
    state = private_directory(tmp_path / "private-state")
    input_file = private_file(source / "bundle.json", canonical(bundle_data()))
    service_key = private_file(source / "service.key", "sb_secret_" + "a" * 32)
    config_path = private_file(
        directory / "producer.json",
        canonical(
            {
                "enabled": True,
                "input_file": str(input_file),
                "state_directory": str(state),
                "owner_id": str(OWNER),
                "strategy_version_id": 7,
                "experiment_id": 9,
                "origin": "https://fixture.invalid",
                "service_key_file": str(service_key),
            }
        ),
    )
    monkeypatch.setenv("SOCHRON_RESEARCH_EVALUATION_CONFIG_FILE", str(config_path))
    assert load_research_evaluation_config() == ResearchEvaluationConfig(
        input_file, state, OWNER, 7, 9, "https://fixture.invalid", service_key
    )
    os.chmod(config_path, 0o644)
    with pytest.raises(ResearchEvaluationConfigInvalid):
        load_research_evaluation_config()
