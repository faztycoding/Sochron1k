"""Redacted Demo admission inventory; never execution authorization."""

from __future__ import annotations

import os
import stat
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from .models import StrictModel

MAX_DECISION_CONFIG_BYTES = 16_384
SafeText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"),
]
GateId = Literal[
    "owner_decisions",
    "owner_auth",
    "market_data",
    "execution_bridge",
    "policy_research",
    "target_artifact",
    "broker_round_trip",
    "recovery_observability",
    "operational_authorization",
]
GateState = Literal[
    "missing",
    "recorded",
    "configured",
    "awaiting_source",
    "connected",
    "degraded",
    "not_run",
    "not_authorized",
]
OverallState = Literal[
    "awaiting_owner_inputs",
    "awaiting_runtime",
    "awaiting_target_evidence",
    "degraded",
]
NextAction = Literal[
    "record_owner_decisions",
    "configure_owner_auth",
    "connect_mt5_market_data",
    "connect_demo_executor",
    "connect_policy_research_sources",
    "compile_and_attest_ea",
    "run_bounded_demo_round_trip",
    "verify_target_recovery",
    "grant_explicit_demo_authorization",
]


class DemoOwnerDecisions(StrictModel):
    """Owner choices only. Secrets and account references are intentionally absent."""

    protocol: Literal["sochron.demo-owner-decisions.v1"]
    decision_revision: SafeText
    recorded_at_utc: AwareDatetime
    owner_approved: StrictBool
    broker_name: SafeText
    demo_server: SafeText
    account_currency: str = Field(pattern=r"^[A-Z]{3,8}$")
    starting_capital: Decimal = Field(gt=0, allow_inf_nan=False, max_digits=18, decimal_places=2)
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s\x00-\x1f\x7f]+$")
    account_mode: Literal["retail_netting", "retail_hedging"]
    trading_hours_policy_ref: SafeText
    overnight_policy: Literal["flat", "allowed_by_versioned_policy"]
    target_executor: Literal["hostinger_wine", "windows_executor"]
    target_region: SafeText
    monthly_budget_thb: Decimal = Field(
        gt=0, allow_inf_nan=False, max_digits=12, decimal_places=2
    )
    alert_destination_ref: SafeText
    halt_release_authority_ref: SafeText
    approved_secret_channel_ref: SafeText
    rpo_seconds: StrictInt = Field(ge=0, le=86_400)
    rto_seconds: StrictInt = Field(gt=0, le=604_800)
    magic_number: StrictInt = Field(gt=0, le=2_147_483_647)

    @field_validator("recorded_at_utc")
    @classmethod
    def normalize_recorded_at(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def explicit_owner_approval(self) -> Self:
        if self.owner_approved is not True:
            raise ValueError("explicit owner decision approval required")
        return self


def load_demo_owner_decisions() -> DemoOwnerDecisions | None:
    configured = os.environ.get("SOCHRON_DEMO_READINESS_CONFIG_FILE")
    if not configured:
        return None
    try:
        path = Path(configured)
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise ValueError("canonical absolute configuration path required")
        parent = path.parent.stat()
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) & 0o077
        ):
            raise ValueError("private configuration directory required")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(path, flags), "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
            ):
                raise ValueError("private configuration required")
            raw = stream.read(MAX_DECISION_CONFIG_BYTES + 1)
        if len(raw) > MAX_DECISION_CONFIG_BYTES:
            raise ValueError("configuration too large")
        return DemoOwnerDecisions.model_validate_json(raw)
    except OSError, ValueError, RuntimeError:
        raise RuntimeError(
            "Invalid private Demo readiness configuration; API not started"
        ) from None


class DemoReadinessGate(StrictModel):
    id: GateId
    state: GateState
    api_routes: tuple[str, ...]
    sources: tuple[str, ...]
    next_action: NextAction


class DemoReadiness(StrictModel):
    protocol: Literal["sochron.demo-readiness.v1"] = "sochron.demo-readiness.v1"
    state: OverallState
    demo_only: Literal[True] = True
    auto_trading_enabled: Literal[False] = False
    release_ready: Literal[False] = False
    round_trip_authorized: Literal[False] = False
    unattended_demo_ready: Literal[False] = False
    gates: tuple[DemoReadinessGate, ...]


def _market_state(
    telemetry_state: str,
    *,
    chart_enabled: bool,
    chart_states: tuple[str, ...],
    history_configured: bool,
) -> GateState:
    if telemetry_state in {"stale", "rejected"} or any(
        state in {"stale", "rejected"} for state in chart_states
    ):
        return "degraded"
    if (
        telemetry_state == "connected"
        and chart_enabled
        and bool(chart_states)
        and all(state == "ready" for state in chart_states)
        and history_configured
    ):
        return "connected"
    if telemetry_state != "disabled" or chart_enabled or history_configured:
        return "awaiting_source"
    return "missing"


def _execution_state(bridge_state: str, evidence_state: str) -> GateState:
    if bridge_state in {"stale", "rejected"} or evidence_state == "degraded":
        return "degraded"
    if bridge_state == "connected" and evidence_state == "connected":
        return "connected"
    if bridge_state != "disabled" or evidence_state != "awaiting_configuration":
        return "awaiting_source"
    return "missing"


def _policy_state(
    writer_state: str, *, signal_configured: bool, statistics_configured: bool
) -> GateState:
    if writer_state == "degraded":
        return "degraded"
    if writer_state != "disabled" or signal_configured or statistics_configured:
        # Reader construction is configuration, not proof that either remote
        # source returned current evidence.
        return "awaiting_source"
    return "missing"


def build_demo_readiness(
    *,
    owner_decisions_recorded: bool,
    owner_auth_configured: bool,
    telemetry_state: str,
    chart_enabled: bool,
    chart_states: tuple[str, ...],
    history_configured: bool,
    execution_state: str,
    execution_evidence_state: str,
    signal_configured: bool,
    policy_state: str,
    statistics_configured: bool,
) -> DemoReadiness:
    gates = (
        DemoReadinessGate(
            id="owner_decisions",
            state="recorded" if owner_decisions_recorded else "missing",
            api_routes=("/api/ui/demo-readiness",),
            sources=("owner_private_decision_record",),
            next_action="record_owner_decisions",
        ),
        DemoReadinessGate(
            id="owner_auth",
            state="configured" if owner_auth_configured else "missing",
            api_routes=("/api/auth/config", "/api/owner/session"),
            sources=("supabase_auth",),
            next_action="configure_owner_auth",
        ),
        DemoReadinessGate(
            id="market_data",
            state=_market_state(
                telemetry_state,
                chart_enabled=chart_enabled,
                chart_states=chart_states,
                history_configured=history_configured,
            ),
            api_routes=(
                "/api/owner/telemetry",
                "/api/owner/chart/{timeframe}",
                "/api/owner/history/{timeframe}",
            ),
            sources=("mt5_telemetry", "mt5_copyrates", "local_bar_archive"),
            next_action="connect_mt5_market_data",
        ),
        DemoReadinessGate(
            id="execution_bridge",
            state=_execution_state(execution_state, execution_evidence_state),
            api_routes=("/api/executor/v1/status", "/api/owner/execution"),
            sources=("mt5_execution", "local_execution_journal"),
            next_action="connect_demo_executor",
        ),
        DemoReadinessGate(
            id="policy_research",
            state=_policy_state(
                policy_state,
                signal_configured=signal_configured,
                statistics_configured=statistics_configured,
            ),
            api_routes=(
                "/api/policy/v1/status",
                "/api/owner/signals",
                "/api/owner/statistics",
            ),
            sources=("news_gate", "supabase_signals", "supabase_evaluations"),
            next_action="connect_policy_research_sources",
        ),
        DemoReadinessGate(
            id="target_artifact",
            state="not_run",
            api_routes=("/api/ui/demo-readiness",),
            sources=("metaeditor_build_evidence", "target_artifact_identity"),
            next_action="compile_and_attest_ea",
        ),
        DemoReadinessGate(
            id="broker_round_trip",
            state="not_run",
            api_routes=("/api/owner/execution",),
            sources=("mt5_orders_deals_positions", "broker_side_sl"),
            next_action="run_bounded_demo_round_trip",
        ),
        DemoReadinessGate(
            id="recovery_observability",
            state="not_run",
            api_routes=("/api/ui/demo-readiness",),
            sources=("target_fault_evidence", "alerts", "backup_restore"),
            next_action="verify_target_recovery",
        ),
        DemoReadinessGate(
            id="operational_authorization",
            state="not_authorized",
            api_routes=("/api/ui/demo-readiness",),
            sources=("explicit_owner_authorization",),
            next_action="grant_explicit_demo_authorization",
        ),
    )
    if any(gate.state == "degraded" for gate in gates):
        state: OverallState = "degraded"
    elif not owner_decisions_recorded:
        state = "awaiting_owner_inputs"
    elif (
        not owner_auth_configured
        or gates[2].state != "connected"
        or gates[3].state != "connected"
        or gates[4].state != "connected"
    ):
        state = "awaiting_runtime"
    else:
        state = "awaiting_target_evidence"
    return DemoReadiness(state=state, gates=gates)
