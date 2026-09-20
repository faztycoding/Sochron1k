"""Query-only admission of normalized target evidence; never release authority."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StrictInt, field_validator, model_validator

from .models import StrictModel

MAX_CONFIG_BYTES = 16_384
MAX_MANIFEST_BYTES = 32_768
MAX_REPORT_BYTES = 65_536
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
SourceRevision = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
SafeText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"),
]
TargetGateId = Literal["target_artifact", "broker_round_trip", "recovery_observability"]
ReportOutcome = Literal["PASS", "FAIL", "NOT_RUN"]
CheckState = Literal["PASS", "FAIL", "NOT_RUN"]
TargetEvidenceState = Literal[
    "disabled",
    "awaiting_snapshot",
    "awaiting_evidence",
    "partial",
    "admitted",
    "failed",
    "stale",
    "degraded",
]
TargetGateState = Literal["not_run", "evidence_admitted", "evidence_failed", "stale", "degraded"]

TARGET_GATES: tuple[TargetGateId, ...] = (
    "target_artifact",
    "broker_round_trip",
    "recovery_observability",
)
TARGET_CHECKS: dict[TargetGateId, tuple[str, ...]] = {
    "target_artifact": (
        "metaeditor_compile",
        "artifact_identity",
        "target_identity",
        "demo_only_preflight",
    ),
    "broker_round_trip": (
        "command_journaled",
        "order_confirmed",
        "deal_confirmed",
        "position_confirmed",
        "broker_sl_confirmed",
        "close_confirmed",
        "no_mismatch",
    ),
    "recovery_observability": (
        "restart_reconcile",
        "network_loss_reconcile",
        "stale_feed_entry_lock",
        "sl_rejection_emergency",
        "risk_halt_restart",
        "journal_failure_entry_lock",
        "alert_delivery",
        "backup_restore",
        "no_unknown_position",
        "latency_report",
        "burn_in",
    ),
}


class _InvalidTargetEvidence(RuntimeError):
    pass


class _MissingTargetSnapshot(FileNotFoundError):
    pass


def _directory_identity(path: Path) -> tuple[int, int, int, int]:
    try:
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise _InvalidTargetEvidence()
        info = path.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise _InvalidTargetEvidence()
        return info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode)
    except OSError, ValueError, TypeError:
        raise _InvalidTargetEvidence() from None


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _private_bytes(
    path: Path,
    limit: int,
    *,
    missing_allowed: bool = False,
) -> bytes:
    parent = _directory_identity(path.parent)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if missing_allowed:
            raise _MissingTargetSnapshot() from None
        raise _InvalidTargetEvidence() from None
    except OSError:
        raise _InvalidTargetEvidence() from None
    try:
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
                or before.st_size > limit
            ):
                raise _InvalidTargetEvidence()
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        current = path.lstat()
        if (
            len(raw) > limit
            or _file_identity(before) != _file_identity(after)
            or _file_identity(after) != _file_identity(current)
            or _directory_identity(path.parent) != parent
        ):
            raise _InvalidTargetEvidence()
        return raw
    except OSError, ValueError, TypeError:
        raise _InvalidTargetEvidence() from None


def _json(raw: bytes) -> dict[str, object]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


class TargetEvidenceSettings(StrictModel):
    snapshot_file: Path
    source_revision: SourceRevision
    target_sha256: Sha256
    decision_revision: SafeText
    decision_recorded_at_utc: AwareDatetime
    max_age_seconds: StrictInt = Field(ge=60, le=604_800)

    @field_validator("snapshot_file", mode="before")
    @classmethod
    def canonical_snapshot(cls, value: object) -> Path:
        if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
            raise ValueError("canonical snapshot path required")
        path = Path(value)
        if not path.is_absolute() or path.resolve() != path or str(path) != str(value):
            raise ValueError("canonical snapshot path required")
        return path

    @field_validator("decision_recorded_at_utc")
    @classmethod
    def utc_decision(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class TargetEvidenceManifestEntry(StrictModel):
    id: TargetGateId
    report_file: str = Field(
        min_length=6,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_.-]*\.json$",
    )
    report_bytes: StrictInt = Field(gt=0, le=MAX_REPORT_BYTES)
    report_sha256: Sha256


class TargetEvidenceManifest(StrictModel):
    protocol: Literal["sochron.target-evidence-manifest.v1"]
    source_revision: SourceRevision
    target_sha256: Sha256
    decision_revision: SafeText
    produced_at_utc: AwareDatetime
    reports: tuple[TargetEvidenceManifestEntry, ...]

    @field_validator("produced_at_utc")
    @classmethod
    def utc_produced(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def exact_reports(self) -> Self:
        if tuple(report.id for report in self.reports) != TARGET_GATES:
            raise ValueError("fixed ordered target reports required")
        if len({report.report_file for report in self.reports}) != len(self.reports):
            raise ValueError("duplicate target report file")
        return self


class TargetEvidenceCheck(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    state: CheckState
    evidence_sha256: Sha256 | None = None

    @model_validator(mode="after")
    def evidence_matches_state(self) -> Self:
        if (self.state == "NOT_RUN") != (self.evidence_sha256 is None):
            raise ValueError("incoherent target check evidence")
        return self


class TargetGateReport(StrictModel):
    protocol: Literal["sochron.target-gate-report.v1"]
    gate: TargetGateId
    outcome: ReportOutcome
    source_revision: SourceRevision
    target_sha256: Sha256
    decision_revision: SafeText
    verifier_sha256: Sha256 | None = None
    started_at_utc: AwareDatetime | None = None
    finished_at_utc: AwareDatetime | None = None
    checks: tuple[TargetEvidenceCheck, ...]

    @field_validator("started_at_utc", "finished_at_utc")
    @classmethod
    def utc_optional(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def coherent_report(self) -> Self:
        expected = TARGET_CHECKS[self.gate]
        if tuple(check.id for check in self.checks) != expected:
            raise ValueError("fixed ordered target checks required")
        states = tuple(check.state for check in self.checks)
        completed = (
            self.verifier_sha256 is not None
            and self.started_at_utc is not None
            and self.finished_at_utc is not None
        )
        if self.outcome == "NOT_RUN":
            if completed or any(state != "NOT_RUN" for state in states):
                raise ValueError("not-run report cannot claim evidence")
        else:
            if not completed or any(state == "NOT_RUN" for state in states):
                raise ValueError("completed report requires complete checks")
            if self.started_at_utc > self.finished_at_utc:
                raise ValueError("invalid target report time")
            if self.outcome == "PASS" and any(state != "PASS" for state in states):
                raise ValueError("pass requires every target check")
            if self.outcome == "FAIL" and "FAIL" not in states:
                raise ValueError("fail requires a failed target check")
        return self


class TargetEvidenceGateView(StrictModel):
    id: TargetGateId
    state: TargetGateState
    report_ref: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    finished_at_utc: AwareDatetime | None = None

    @field_validator("finished_at_utc")
    @classmethod
    def utc_finished(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def coherent_gate(self) -> Self:
        has_report = self.report_ref is not None and self.finished_at_utc is not None
        if self.state == "not_run" and (
            self.report_ref is not None or self.finished_at_utc is not None
        ):
            raise ValueError("not-run gate cannot claim evidence")
        if self.state in {"evidence_admitted", "evidence_failed", "stale"} and not has_report:
            raise ValueError("target gate evidence required")
        if self.state == "degraded" and (
            self.report_ref is not None or self.finished_at_utc is not None
        ):
            raise ValueError("degraded gate cannot expose untrusted evidence")
        return self


class TargetEvidenceView(StrictModel):
    protocol: Literal["sochron.target-evidence-view.v1"] = "sochron.target-evidence-view.v1"
    trading_mode: Literal["demo"] = "demo"
    read_only: Literal[True] = True
    auto_trading_enabled: Literal[False] = False
    release_ready: Literal[False] = False
    round_trip_authorized: Literal[False] = False
    unattended_demo_ready: Literal[False] = False
    state: TargetEvidenceState
    configured: bool
    source_revision: SourceRevision | None = None
    target_ref: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    decision_ref: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    produced_at_utc: AwareDatetime | None = None
    gates: tuple[TargetEvidenceGateView, ...]

    @field_validator("produced_at_utc")
    @classmethod
    def utc_produced_optional(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def coherent_view(self) -> Self:
        if tuple(gate.id for gate in self.gates) != TARGET_GATES:
            raise ValueError("fixed ordered target gates required")
        gate_states = tuple(gate.state for gate in self.gates)
        if (self.state == "disabled") != (not self.configured):
            raise ValueError("incoherent target evidence configuration")
        ref_values = (
            self.source_revision is not None,
            self.target_ref is not None,
            self.decision_ref is not None,
        )
        if self.configured != all(ref_values) or (
            not self.configured and any(ref_values)
        ):
            raise ValueError("incoherent target evidence references")
        if (
            self.state in {"disabled", "awaiting_snapshot", "degraded"}
            and self.produced_at_utc is not None
        ):
            raise ValueError("untrusted target production time")
        if (
            self.state not in {"disabled", "awaiting_snapshot", "degraded"}
            and self.produced_at_utc is None
        ):
            raise ValueError("target production time required")
        if self.state in {"disabled", "awaiting_snapshot", "awaiting_evidence"}:
            coherent_states = all(state == "not_run" for state in gate_states)
        elif self.state == "degraded":
            coherent_states = all(state == "degraded" for state in gate_states)
        elif self.state == "partial":
            coherent_states = (
                "evidence_admitted" in gate_states
                and set(gate_states) <= {"evidence_admitted", "not_run"}
            )
        elif self.state == "admitted":
            coherent_states = all(state == "evidence_admitted" for state in gate_states)
        elif self.state == "failed":
            coherent_states = (
                "evidence_failed" in gate_states
                and set(gate_states)
                <= {"evidence_admitted", "evidence_failed", "not_run"}
            )
        else:
            coherent_states = set(gate_states) <= {"stale", "not_run"}
        if not coherent_states:
            raise ValueError("incoherent target evidence gate states")
        return self


def _empty_gates(
    state: Literal["not_run", "degraded"] = "not_run",
) -> tuple[TargetEvidenceGateView, ...]:
    return tuple(TargetEvidenceGateView(id=gate, state=state) for gate in TARGET_GATES)


def load_target_evidence_settings() -> TargetEvidenceSettings | None:
    selected = os.environ.get("SOCHRON_TARGET_EVIDENCE_CONFIG_FILE")
    if not selected:
        return None
    try:
        path = Path(selected)
        if not path.is_absolute() or path.resolve() != path or str(path) != selected:
            raise _InvalidTargetEvidence()
        data = _json(_private_bytes(path, MAX_CONFIG_BYTES))
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        expected = set(TargetEvidenceSettings.model_fields) | {"enabled"}
        if set(data) != expected or data.pop("enabled", None) is not True:
            raise _InvalidTargetEvidence()
        settings = TargetEvidenceSettings.model_validate(data)
        if settings.snapshot_file == path:
            raise _InvalidTargetEvidence()
        _directory_identity(settings.snapshot_file.parent)
        return settings
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        _InvalidTargetEvidence,
    ):
        raise RuntimeError(
            "Invalid private target evidence configuration; source not started"
        ) from None


class TargetEvidenceReader:
    def __init__(
        self,
        settings: TargetEvidenceSettings | None,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = settings
        self._utc_now = utc_now
        if settings is not None:
            try:
                self._parent_identity = _directory_identity(settings.snapshot_file.parent)
            except _InvalidTargetEvidence:
                raise RuntimeError(
                    "Invalid private target evidence configuration; source not started"
                ) from None

    def _refs(self) -> tuple[str | None, str | None, str | None]:
        if self.settings is None:
            return None, None, None
        return (
            self.settings.source_revision,
            self.settings.target_sha256[:16],
            hashlib.sha256(self.settings.decision_revision.encode()).hexdigest()[:16],
        )

    def _base(
        self,
        state: Literal["disabled", "awaiting_snapshot", "degraded"],
    ) -> TargetEvidenceView:
        source, target, decision = self._refs()
        return TargetEvidenceView(
            state=state,
            configured=self.settings is not None,
            source_revision=source,
            target_ref=target,
            decision_ref=decision,
            gates=_empty_gates("degraded" if state == "degraded" else "not_run"),
        )

    def _read(self) -> tuple[TargetEvidenceManifest, tuple[TargetGateReport, ...]]:
        settings = self.settings
        if settings is None:
            raise _InvalidTargetEvidence()
        if _directory_identity(settings.snapshot_file.parent) != self._parent_identity:
            raise _InvalidTargetEvidence()
        manifest_raw = _private_bytes(
            settings.snapshot_file,
            MAX_MANIFEST_BYTES,
            missing_allowed=True,
        )
        manifest = TargetEvidenceManifest.model_validate(_json(manifest_raw))
        if (
            manifest.source_revision != settings.source_revision
            or manifest.target_sha256 != settings.target_sha256
            or manifest.decision_revision != settings.decision_revision
            or manifest.produced_at_utc < settings.decision_recorded_at_utc
        ):
            raise _InvalidTargetEvidence()
        reports: list[TargetGateReport] = []
        for entry in manifest.reports:
            path = settings.snapshot_file.parent / entry.report_file
            if path.parent != settings.snapshot_file.parent:
                raise _InvalidTargetEvidence()
            raw = _private_bytes(path, MAX_REPORT_BYTES)
            if (
                len(raw) != entry.report_bytes
                or hashlib.sha256(raw).hexdigest() != entry.report_sha256
            ):
                raise _InvalidTargetEvidence()
            report = TargetGateReport.model_validate(_json(raw))
            if (
                report.gate != entry.id
                or report.source_revision != settings.source_revision
                or report.target_sha256 != settings.target_sha256
                or report.decision_revision != settings.decision_revision
            ):
                raise _InvalidTargetEvidence()
            if report.outcome != "NOT_RUN" and (
                report.started_at_utc < settings.decision_recorded_at_utc
                or report.finished_at_utc > manifest.produced_at_utc
            ):
                raise _InvalidTargetEvidence()
            reports.append(report)
        if _directory_identity(settings.snapshot_file.parent) != self._parent_identity:
            raise _InvalidTargetEvidence()
        return manifest, tuple(reports)

    def view(self, now: datetime | None = None) -> TargetEvidenceView:
        if self.settings is None:
            return self._base("disabled")
        try:
            observed = now or self._utc_now()
            if observed.tzinfo is None or observed.utcoffset() is None:
                raise _InvalidTargetEvidence()
            current = observed.astimezone(UTC)
            manifest, reports = self._read()
            if manifest.produced_at_utc > current:
                raise _InvalidTargetEvidence()
            expired = (
                current - manifest.produced_at_utc
            ).total_seconds() > self.settings.max_age_seconds
            gates: list[TargetEvidenceGateView] = []
            for entry, report in zip(manifest.reports, reports, strict=True):
                if report.outcome == "NOT_RUN":
                    gates.append(TargetEvidenceGateView(id=report.gate, state="not_run"))
                    continue
                state: TargetGateState = (
                    "stale"
                    if expired
                    else "evidence_admitted"
                    if report.outcome == "PASS"
                    else "evidence_failed"
                )
                gates.append(
                    TargetEvidenceGateView(
                        id=report.gate,
                        state=state,
                        report_ref=entry.report_sha256[:16],
                        finished_at_utc=report.finished_at_utc,
                    )
                )
            outcomes = tuple(report.outcome for report in reports)
            if expired:
                state: TargetEvidenceState = "stale"
            elif "FAIL" in outcomes:
                state = "failed"
            elif all(outcome == "PASS" for outcome in outcomes):
                state = "admitted"
            elif "PASS" in outcomes:
                state = "partial"
            else:
                state = "awaiting_evidence"
            source, target, decision = self._refs()
            return TargetEvidenceView(
                state=state,
                configured=True,
                source_revision=source,
                target_ref=target,
                decision_ref=decision,
                produced_at_utc=manifest.produced_at_utc,
                gates=tuple(gates),
            )
        except _MissingTargetSnapshot:
            return self._base("awaiting_snapshot")
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RecursionError,
            _InvalidTargetEvidence,
        ):
            return self._base("degraded")


def load_target_evidence_reader() -> TargetEvidenceReader:
    return TargetEvidenceReader(load_target_evidence_settings())
