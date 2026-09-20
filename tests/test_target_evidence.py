from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sochron1k.demo_readiness import DemoOwnerDecisions, build_demo_readiness
from sochron1k.main import create_app
from sochron1k.owner_auth import OwnerAuthDenied, OwnerAuthSettings
from sochron1k.target_evidence import (
    TARGET_CHECKS,
    TARGET_GATES,
    TargetEvidenceGateView,
    TargetEvidenceReader,
    TargetEvidenceSettings,
    TargetEvidenceView,
    TargetGateReport,
    load_target_evidence_settings,
)

NOW = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
DECISION_TIME = NOW - timedelta(hours=2)
SOURCE_REVISION = "1" * 40
TARGET_SHA256 = "2" * 64
DECISION_REVISION = "owner-demo-plan-2026-09"
OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class VerifiedOwner:
    async def verify(self, authorization):
        if authorization != ["Bearer owner-fixture"]:
            raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        return OWNER


def private_directory(tmp_path: Path, name: str = "target") -> Path:
    directory = (tmp_path / name).resolve()
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    return directory


def private_file(directory: Path, name: str, raw: bytes) -> Path:
    path = directory / name
    path.write_bytes(raw)
    path.chmod(0o600)
    return path.resolve()


def canonical(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def settings(snapshot_file: Path, *, max_age_seconds: int = 3600) -> TargetEvidenceSettings:
    return TargetEvidenceSettings(
        snapshot_file=snapshot_file,
        source_revision=SOURCE_REVISION,
        target_sha256=TARGET_SHA256,
        decision_revision=DECISION_REVISION,
        decision_recorded_at_utc=DECISION_TIME,
        max_age_seconds=max_age_seconds,
    )


def report(gate: str, outcome: str, *, failed_check: str | None = None) -> dict[str, object]:
    completed = outcome != "NOT_RUN"
    checks = []
    for check_id in TARGET_CHECKS[gate]:
        state = "NOT_RUN" if not completed else "FAIL" if check_id == failed_check else "PASS"
        checks.append(
            {
                "id": check_id,
                "state": state,
                "evidence_sha256": (
                    None
                    if state == "NOT_RUN"
                    else hashlib.sha256(f"{gate}:{check_id}".encode()).hexdigest()
                ),
            }
        )
    return {
        "protocol": "sochron.target-gate-report.v1",
        "gate": gate,
        "outcome": outcome,
        "source_revision": SOURCE_REVISION,
        "target_sha256": TARGET_SHA256,
        "decision_revision": DECISION_REVISION,
        "verifier_sha256": "3" * 64 if completed else None,
        "started_at_utc": (NOW - timedelta(minutes=2)).isoformat() if completed else None,
        "finished_at_utc": (NOW - timedelta(minutes=1)).isoformat() if completed else None,
        "checks": checks,
    }


def write_bundle(
    directory: Path,
    outcomes: tuple[str, str, str] = ("PASS", "PASS", "PASS"),
    *,
    produced_at: datetime = NOW,
    failed_gate: str | None = None,
) -> Path:
    entries = []
    for gate, outcome in zip(TARGET_GATES, outcomes, strict=True):
        body = report(
            gate,
            outcome,
            failed_check=TARGET_CHECKS[gate][0] if gate == failed_gate else None,
        )
        raw = canonical(body)
        name = f"{gate}.json"
        private_file(directory, name, raw)
        entries.append(
            {
                "id": gate,
                "report_file": name,
                "report_bytes": len(raw),
                "report_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    manifest = {
        "protocol": "sochron.target-evidence-manifest.v1",
        "source_revision": SOURCE_REVISION,
        "target_sha256": TARGET_SHA256,
        "decision_revision": DECISION_REVISION,
        "produced_at_utc": produced_at.isoformat(),
        "reports": entries,
    }
    return private_file(directory, "manifest.json", canonical(manifest))


def decisions() -> DemoOwnerDecisions:
    return DemoOwnerDecisions(
        protocol="sochron.demo-owner-decisions.v1",
        decision_revision=DECISION_REVISION,
        recorded_at_utc=DECISION_TIME,
        owner_approved=True,
        broker_name="Fixture Broker",
        demo_server="Fixture-Demo",
        account_currency="USD",
        starting_capital="10000.00",
        symbol="XAUUSD.fixture",
        account_mode="retail_hedging",
        trading_hours_policy_ref="hours-policy-v1",
        overnight_policy="flat",
        target_executor="hostinger_wine",
        target_region="fixture-region",
        monthly_budget_thb="1000.00",
        alert_destination_ref="owner-alert-route",
        halt_release_authority_ref="named-owner",
        approved_secret_channel_ref="private-channel-record",
        rpo_seconds=300,
        rto_seconds=1800,
        magic_number=910001,
    )


def build(target_view):
    return build_demo_readiness(
        owner_decisions_recorded=True,
        owner_auth_configured=True,
        telemetry_state="connected",
        chart_enabled=True,
        chart_states=("ready",) * 4,
        history_configured=True,
        execution_state="connected",
        execution_evidence_state="connected",
        signal_configured=True,
        policy_state="ready",
        statistics_configured=True,
        target_evidence=target_view,
    )


def test_scn036_disabled_missing_and_exact_admission_states(tmp_path: Path) -> None:
    disabled = TargetEvidenceReader(None).view(NOW)
    assert disabled.state == "disabled" and disabled.configured is False
    assert [gate.state for gate in disabled.gates] == ["not_run"] * 3

    directory = private_directory(tmp_path)
    manifest = directory / "manifest.json"
    reader = TargetEvidenceReader(settings(manifest), utc_now=lambda: NOW)
    assert reader.view(NOW).state == "awaiting_snapshot"

    write_bundle(directory)
    admitted = reader.view(NOW)
    assert admitted.state == "admitted"
    assert [gate.state for gate in admitted.gates] == ["evidence_admitted"] * 3
    assert admitted.target_ref == TARGET_SHA256[:16]
    assert admitted.source_revision == SOURCE_REVISION
    serialized = admitted.model_dump_json()
    assert str(directory) not in serialized
    assert DECISION_REVISION not in serialized
    assert "metaeditor_compile" not in serialized

    write_bundle(directory, ("PASS", "NOT_RUN", "NOT_RUN"))
    partial = reader.view(NOW)
    assert partial.state == "partial"
    assert [gate.state for gate in partial.gates] == [
        "evidence_admitted",
        "not_run",
        "not_run",
    ]

    write_bundle(directory, ("PASS", "FAIL", "PASS"), failed_gate="broker_round_trip")
    failed = reader.view(NOW)
    assert failed.state == "failed"
    assert failed.gates[1].state == "evidence_failed"


def test_scn036_stale_future_and_tampering_fail_closed(tmp_path: Path) -> None:
    directory = private_directory(tmp_path)
    manifest = write_bundle(directory)
    reader = TargetEvidenceReader(settings(manifest, max_age_seconds=60))
    stale = reader.view(NOW + timedelta(seconds=61))
    assert stale.state == "stale"
    assert [gate.state for gate in stale.gates] == ["stale"] * 3

    write_bundle(directory, produced_at=NOW + timedelta(seconds=1))
    assert reader.view(NOW).state == "degraded"

    write_bundle(directory)
    report_path = directory / "target_artifact.json"
    report_path.write_text("{}", encoding="utf-8")
    report_path.chmod(0o600)
    assert reader.view(NOW).state == "degraded"

    write_bundle(directory)
    report_path.chmod(0o644)
    assert reader.view(NOW).state == "degraded"
    report_path.chmod(0o600)

    alias = directory / "target-artifact-alias.json"
    os.link(report_path, alias)
    assert reader.view(NOW).state == "degraded"
    alias.unlink()

    write_bundle(directory)
    manifest.write_text('{"protocol":"a","protocol":"b"}', encoding="utf-8")
    manifest.chmod(0o600)
    assert reader.view(NOW).state == "degraded"

    write_bundle(directory)
    manifest.chmod(0o644)
    assert reader.view(NOW).state == "degraded"
    manifest.chmod(0o600)

    manifest_alias = directory / "manifest-alias.json"
    os.link(manifest, manifest_alias)
    assert reader.view(NOW).state == "degraded"
    manifest_alias.unlink()

    write_bundle(directory)
    report_path = directory / "target_artifact.json"
    report_raw = report_path.read_bytes()
    report_path.unlink()
    actual = private_file(directory, "target-artifact-actual.json", report_raw)
    report_path.symlink_to(actual)
    assert reader.view(NOW).state == "degraded"
    report_path.unlink()

    write_bundle(directory)
    report_path.write_bytes(b"x" * 65_537)
    report_path.chmod(0o600)
    assert reader.view(NOW).state == "degraded"

    write_bundle(directory)
    assert reader.view(datetime(2026, 9, 20, 9, 0)).state == "degraded"


def test_scn036_config_is_private_exact_and_decision_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SOCHRON_TARGET_EVIDENCE_CONFIG_FILE", raising=False)
    assert load_target_evidence_settings() is None
    directory = private_directory(tmp_path)
    manifest = directory / "manifest.json"
    config = private_file(
        directory,
        "target-config.json",
        canonical(
            {
                "enabled": True,
                "snapshot_file": str(manifest),
                "source_revision": SOURCE_REVISION,
                "target_sha256": TARGET_SHA256,
                "decision_revision": DECISION_REVISION,
                "decision_recorded_at_utc": DECISION_TIME.isoformat(),
                "max_age_seconds": 3600,
            }
        ),
    )
    monkeypatch.setenv("SOCHRON_TARGET_EVIDENCE_CONFIG_FILE", str(config))
    loaded = load_target_evidence_settings()
    assert loaded is not None and loaded.snapshot_file == manifest

    with pytest.raises(RuntimeError, match="matching owner decision"):
        create_app(target_evidence=TargetEvidenceReader(loaded))
    create_app(demo_owner_decisions=decisions(), target_evidence=TargetEvidenceReader(loaded))

    config.write_bytes(canonical({"enabled": False}))
    config.chmod(0o600)
    assert load_target_evidence_settings() is None

    valid_config = canonical(
        {
            "enabled": True,
            "snapshot_file": str(manifest),
            "source_revision": SOURCE_REVISION,
            "target_sha256": TARGET_SHA256,
            "decision_revision": DECISION_REVISION,
            "decision_recorded_at_utc": DECISION_TIME.isoformat(),
            "max_age_seconds": 3600,
        }
    )
    config.write_bytes(valid_config)
    config.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private target evidence"):
        load_target_evidence_settings()
    config.chmod(0o600)

    config_alias = directory / "target-config-alias.json"
    os.link(config, config_alias)
    with pytest.raises(RuntimeError, match="Invalid private target evidence"):
        load_target_evidence_settings()
    config_alias.unlink()

    selected_symlink = directory / "selected-config.json"
    selected_symlink.symlink_to(config)
    monkeypatch.setenv("SOCHRON_TARGET_EVIDENCE_CONFIG_FILE", str(selected_symlink))
    with pytest.raises(RuntimeError, match="Invalid private target evidence"):
        load_target_evidence_settings()
    monkeypatch.setenv("SOCHRON_TARGET_EVIDENCE_CONFIG_FILE", str(config))

    config.write_text('{"enabled":true,"enabled":false}', encoding="utf-8")
    config.chmod(0o600)
    with pytest.raises(RuntimeError, match="Invalid private target evidence"):
        load_target_evidence_settings()

    config.write_bytes(b"x" * 16_385)
    config.chmod(0o600)
    with pytest.raises(RuntimeError, match="Invalid private target evidence"):
        load_target_evidence_settings()


def test_scn036_report_schema_rejects_incomplete_pass_and_route_projects_gate(
    tmp_path: Path,
) -> None:
    directory = private_directory(tmp_path)
    manifest = write_bundle(directory)
    body = report("target_artifact", "PASS")
    body["checks"][0]["state"] = "NOT_RUN"
    body["checks"][0]["evidence_sha256"] = None
    raw = canonical(body)
    private_file(directory, "target_artifact.json", raw)
    manifest_body = json.loads(manifest.read_text())
    manifest_body["reports"][0]["report_bytes"] = len(raw)
    manifest_body["reports"][0]["report_sha256"] = hashlib.sha256(raw).hexdigest()
    manifest.write_bytes(canonical(manifest_body))
    manifest.chmod(0o600)
    reader = TargetEvidenceReader(settings(manifest), utc_now=lambda: NOW)
    assert reader.view(NOW).state == "degraded"

    write_bundle(directory)
    readiness = build(reader.view(NOW))
    assert [gate.state for gate in readiness.gates[5:8]] == ["evidence_admitted"] * 3
    assert readiness.release_ready is False
    assert readiness.round_trip_authorized is False
    assert readiness.unattended_demo_ready is False


def test_scn036_binding_and_time_drift_fail_closed(tmp_path: Path) -> None:
    directory = private_directory(tmp_path)
    manifest = write_bundle(directory)
    reader = TargetEvidenceReader(settings(manifest), utc_now=lambda: NOW)

    def replace_artifact(**updates: object) -> None:
        body = report("target_artifact", "PASS")
        body.update(updates)
        raw = canonical(body)
        private_file(directory, "target_artifact.json", raw)
        manifest_body = json.loads(manifest.read_text())
        manifest_body["reports"][0]["report_bytes"] = len(raw)
        manifest_body["reports"][0]["report_sha256"] = hashlib.sha256(raw).hexdigest()
        manifest.write_bytes(canonical(manifest_body))
        manifest.chmod(0o600)

    replace_artifact(source_revision="4" * 40)
    assert reader.view().state == "degraded"

    write_bundle(directory)
    replace_artifact(started_at_utc=(DECISION_TIME - timedelta(seconds=1)).isoformat())
    assert reader.view().state == "degraded"

    write_bundle(directory)
    replace_artifact(finished_at_utc=(NOW + timedelta(seconds=1)).isoformat())
    assert reader.view().state == "degraded"

    write_bundle(directory)
    manifest_body = json.loads(manifest.read_text())
    manifest_body["target_sha256"] = "5" * 64
    manifest.write_bytes(canonical(manifest_body))
    manifest.chmod(0o600)
    assert reader.view().state == "degraded"


@pytest.mark.anyio
async def test_scn036_owner_route_requires_auth_and_redacts_private_evidence(
    tmp_path: Path,
) -> None:
    directory = private_directory(tmp_path)
    manifest = write_bundle(directory)
    reader = TargetEvidenceReader(settings(manifest), utc_now=lambda: NOW)
    auth = OwnerAuthSettings(
        supabase_url="https://auth.fixture.invalid",
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )
    app = create_app(
        owner_auth_settings=auth,
        demo_owner_decisions=decisions(),
        target_evidence=reader,
    )
    app.state.owner_verifier = VerifiedOwner()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        denied = await client.get("/owner/target-evidence")
        response = await client.get(
            "/owner/target-evidence",
            headers={"Authorization": "Bearer owner-fixture"},
        )
        readiness = await client.get("/ui/demo-readiness")
    assert denied.status_code == 401
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.json()["state"] == "admitted"
    assert [gate["state"] for gate in readiness.json()["gates"][5:8]] == ["evidence_admitted"] * 3
    for forbidden in (
        str(directory),
        "target_artifact.json",
        DECISION_REVISION,
        "metaeditor_compile",
        "fixture broker",
    ):
        assert forbidden.lower() not in response.text.lower()


def test_scn036_symlink_snapshot_and_invalid_report_shape_are_rejected(
    tmp_path: Path,
) -> None:
    directory = private_directory(tmp_path)
    manifest = write_bundle(directory)
    alias = directory / "alias.json"
    alias.symlink_to(manifest)
    with pytest.raises(ValidationError):
        settings(alias)

    body = report("target_artifact", "FAIL", failed_check=None)
    with pytest.raises(ValidationError):
        TargetGateReport.model_validate(body)

    with pytest.raises(ValidationError):
        TargetEvidenceView(
            state="disabled",
            configured=False,
            source_revision=SOURCE_REVISION,
            gates=tuple(TargetEvidenceGateView(id=gate, state="not_run") for gate in TARGET_GATES),
        )

    with pytest.raises(ValidationError):
        TargetEvidenceView(
            state="admitted",
            configured=True,
            source_revision=SOURCE_REVISION,
            target_ref=TARGET_SHA256[:16],
            decision_ref="6" * 16,
            produced_at_utc=NOW,
            gates=tuple(TargetEvidenceGateView(id=gate, state="not_run") for gate in TARGET_GATES),
        )


def test_scn036_snapshot_directory_replacement_fails_closed(tmp_path: Path) -> None:
    directory = private_directory(tmp_path)
    manifest = write_bundle(directory)
    reader = TargetEvidenceReader(settings(manifest), utc_now=lambda: NOW)
    assert reader.view().state == "admitted"

    original = directory.with_name("target-original")
    directory.rename(original)
    replacement = private_directory(tmp_path)
    write_bundle(replacement)
    assert reader.view().state == "degraded"
