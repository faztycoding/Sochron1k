from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError
from sochron_worker.pa01_aggregation import NativeM1Evidence, aggregate_native_m1
from sochron_worker.pa01_envelope import (
    EnvelopeUnavailable,
    PA01PolicyEvidence,
    PA01PolicyObservations,
    PA01StoredPolicyContext,
    PolicyObservation,
    build_pa01_decision_envelope,
)

D = Decimal
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
SERVER_BASE = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
ARCHIVE_ID = UUID("22222222-3333-4444-8555-666666666666")
VALID_FROM = SERVER_BASE - 3_600
VALID_UNTIL = SERVER_BASE + 800 * 60
CODE_HASH = "a" * 64


def native_m1(index: int) -> NativeM1Evidence:
    time_server_s = SERVER_BASE + index * 60
    opened = EPOCH + timedelta(seconds=time_server_s - 7_200)
    confirmed_at = opened + timedelta(seconds=60)
    price = D("2500.00") + D(index) / D("100")
    return NativeM1Evidence(
        archive_id=ARCHIVE_ID,
        symbol="XAUUSD.fixture",
        time_server_s=time_server_s,
        broker_utc_offset_seconds=7_200,
        offset_valid_from_server_s=VALID_FROM,
        offset_valid_until_server_s=VALID_UNTIL,
        open_time_utc=opened,
        confirmed_by_server_s=time_server_s + 60,
        source_observed_at_utc=confirmed_at,
        first_received_at_utc=confirmed_at + timedelta(seconds=1),
        available_at_utc=confirmed_at + timedelta(seconds=2),
        first_receipt=index + 1,
        terminal_build=5_550,
        open=price,
        high=price + D("0.05"),
        low=price - D("0.05"),
        close=price + D("0.01"),
        tick_volume=100 + index,
        spread_points=12,
        tick_size=D("0.01"),
        digits=2,
    )


@pytest.fixture(scope="module")
def aggregation():
    rows = tuple(native_m1(index) for index in range(720))
    cutoff = max(row.available_at_utc for row in rows)
    return aggregate_native_m1(rows, cutoff_utc=cutoff)


def policy(aggregation, **changes) -> PA01PolicyEvidence:
    cutoff = aggregation.cutoff_utc
    values = dict(
        cutoff_utc=cutoff,
        symbol=aggregation.symbol,
        feed_id=aggregation.feed_id,
        spread_price=D("0.01"),
        market_open=True,
        price_stale=False,
        news_blocked=False,
        has_exposure=False,
        has_pending=False,
        observations=PA01PolicyObservations(
            quote=PolicyObservation(
                evidence_id="quote:XAUUSD.fixture:2026-01-01T10:00:02Z",
                observed_at_utc=cutoff,
            ),
            market=PolicyObservation(
                evidence_id="market-session:XAUUSD.fixture:2026-01-01",
                observed_at_utc=cutoff - timedelta(seconds=1),
            ),
            news=PolicyObservation(
                evidence_id="news-window:XAUUSD.fixture:2026-01-01T10:00Z",
                observed_at_utc=cutoff - timedelta(seconds=2),
            ),
            account=PolicyObservation(
                evidence_id="account-state:demo-fixture:0001",
                observed_at_utc=cutoff - timedelta(seconds=1),
            ),
        ),
    )
    values.update(changes)
    return PA01PolicyEvidence(**values)


def test_envelope_is_deterministic_complete_and_receiver_shaped(aggregation):
    first = build_pa01_decision_envelope(aggregation, policy(aggregation), code_hash=CODE_HASH)
    repeated = build_pa01_decision_envelope(aggregation, policy(aggregation), code_hash=CODE_HASH)

    assert first == repeated
    payload = first.model_dump(mode="json")
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")) == json.dumps(
        repeated.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    assert payload["protocol"] == "sochron.pa01.decision.v2"
    assert payload["producer_revision"] == ("PA01-v1.0.1/native-pa01-aggregation-v1")
    assert payload["snapshot"]["values"]["schema"] == "sochron.pa01.features.v1"
    assert payload["snapshot"]["decision_protocol"] == payload["protocol"]
    assert payload["snapshot"]["policy_context"]["schema"] == ("sochron.pa01.policy-context.v1")
    assert payload["snapshot"]["values"]["data_cutoff_utc"] == (payload["snapshot"]["available_at"])
    assert payload["signal"]["confirmed_at"] == payload["snapshot"]["available_at"]
    assert first.snapshot.policy_context.evidence_id in first.signal.evidence_ids
    assert first.snapshot.policy_context.kernel_decision_id.startswith("decision-")
    assert first.snapshot.policy_context.market_data_cutoff_utc <= (
        first.snapshot.policy_context.cutoff_utc
    )
    assert first.snapshot.values.action == "wait"
    assert first.snapshot.values.reason_code == "STRUCTURE_INCOMPLETE"
    assert first.snapshot.values.execution_parameters.order_created is False
    assert first.snapshot.values.execution_parameters.risk_admitted is False

    features = payload["snapshot"]["values"]["features"]
    decimal_values = [
        features[name]
        for name in (
            "ema20",
            "ema50",
            "previous_ema20",
            "atr14",
            "adx14",
            "spread_cap",
            "proposed_stop",
            "stop_distance_at_close",
            "stop_distance_atr",
        )
        if features[name] is not None
    ]
    decimal_values.extend(
        pivot["price"]
        for name in ("latest_swing_highs", "latest_swing_lows")
        for pivot in features[name]
    )
    assert decimal_values
    assert all(len(value) <= 40 for value in decimal_values)
    assert all(not ("." in value and value.endswith("0")) for value in decimal_values)


def test_full_policy_context_changes_identity_and_recomputes_block(aggregation):
    admitted = build_pa01_decision_envelope(aggregation, policy(aggregation), code_hash=CODE_HASH)
    closed = build_pa01_decision_envelope(
        aggregation,
        policy(aggregation, market_open=False),
        code_hash=CODE_HASH,
    )
    changed_code = build_pa01_decision_envelope(
        aggregation,
        policy(aggregation),
        code_hash="b" * 64,
    )

    assert (closed.signal.action, closed.signal.blocked_reason) == (
        "block",
        "MARKET_CLOSED",
    )
    assert (
        len(
            {
                admitted.decision_fingerprint,
                closed.decision_fingerprint,
                changed_code.decision_fingerprint,
            }
        )
        == 3
    )
    assert admitted.signal.signal_id != closed.signal.signal_id
    assert admitted.snapshot.policy_context.context_hash != (
        closed.snapshot.policy_context.context_hash
    )


def test_forged_or_mixed_aggregation_fails_closed(aggregation):
    forged = aggregation.model_copy(update={"aggregation_hash": "0" * 64})
    with pytest.raises(EnvelopeUnavailable, match="PA01_ENVELOPE_UNAVAILABLE"):
        build_pa01_decision_envelope(forged, policy(aggregation), code_hash=CODE_HASH)

    with pytest.raises(EnvelopeUnavailable):
        build_pa01_decision_envelope(
            aggregation,
            policy(aggregation, feed_id="mt5-copyrates:00000000-0000-4000-8000-000000000000"),
            code_hash=CODE_HASH,
        )
    with pytest.raises(EnvelopeUnavailable):
        build_pa01_decision_envelope(aggregation, policy(aggregation), code_hash="A" * 64)


def test_policy_observations_are_unique_causal_and_fresh_when_claimed(aggregation):
    base = policy(aggregation)
    observations = base.observations
    with pytest.raises(ValidationError):
        policy(
            aggregation,
            observations=observations.model_copy(
                update={
                    "news": observations.news.model_copy(
                        update={"evidence_id": observations.quote.evidence_id}
                    )
                }
            ),
        )
    with pytest.raises(ValidationError):
        policy(
            aggregation,
            observations=observations.model_copy(
                update={
                    "account": observations.account.model_copy(
                        update={
                            "observed_at_utc": aggregation.cutoff_utc + timedelta(microseconds=1)
                        }
                    )
                }
            ),
        )
    with pytest.raises(ValidationError):
        policy(
            aggregation,
            observations=observations.model_copy(
                update={
                    "quote": observations.quote.model_copy(
                        update={"observed_at_utc": aggregation.cutoff_utc - timedelta(seconds=6)}
                    )
                }
            ),
        )

    stale = policy(
        aggregation,
        price_stale=True,
        observations=observations.model_copy(
            update={
                "quote": observations.quote.model_copy(
                    update={"observed_at_utc": aggregation.cutoff_utc - timedelta(seconds=60)}
                )
            }
        ),
    )
    result = build_pa01_decision_envelope(aggregation, stale, code_hash=CODE_HASH)
    assert (result.signal.action, result.signal.blocked_reason) == (
        "block",
        "STALE_PRICE",
    )


def test_stored_context_detects_hash_or_identity_tampering(aggregation):
    result = build_pa01_decision_envelope(aggregation, policy(aggregation), code_hash=CODE_HASH)
    raw = result.snapshot.policy_context.model_dump()
    raw["context_hash"] = "0" * 64
    with pytest.raises(ValidationError):
        PA01StoredPolicyContext(**raw)

    raw = result.snapshot.policy_context.model_dump()
    raw["evidence_id"] = "pa01-policy:" + "0" * 32
    with pytest.raises(ValidationError):
        PA01StoredPolicyContext(**raw)


def test_envelope_module_has_no_io_risk_or_execution_authority():
    source = Path("services/worker/src/sochron_worker/pa01_envelope.py").read_text()
    for forbidden in (
        "import httpx",
        "import requests",
        "import sqlite3",
        "import os",
        "datetime.now",
        "supabase",
        "OrderSend",
        "ExecutionService",
        "service_role",
        "open(",
        "create_command",
        "risk_engine",
    ):
        assert forbidden not in source
