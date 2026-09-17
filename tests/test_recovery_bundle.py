import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from sochron_worker import recovery_bundle as bundle
from test_bar_history import archive as archive
from test_chart import setup_chart as setup_chart
from test_recovery_audit import recovery_case as recovery_case


@pytest.fixture
def configured(recovery_case):
    case = recovery_case
    config = case["root"] / "recovery.json"
    config.touch(mode=0o600)
    config.write_text(
        json.dumps(
            dict(
                binding=case["binding"].model_dump(mode="json"),
                command_database=str(case["commands"].path),
                sync_database=str(case["sync"].path),
                archive_database=str(case["archive"].path),
                max_age_seconds=3600,
                max_span_seconds=60,
                operator_provenance_claims=dict(source_revision="0" * 40, artifact_sha256="a" * 64),
            )
        )
    )
    return case, config, case["root"] / "backup", case["root"] / "inspection"


def invoke(configured, *args, code=None):
    case, _, _, _ = configured
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": os.pathsep.join(
            str(Path(p).resolve()) for p in ("services/api/src", "services/worker/src")
        ),
    }
    command = (
        [sys.executable, "-c", code]
        if code
        else [sys.executable, "-m", "sochron_worker.recovery_cli"]
    )
    return subprocess.run(
        [*command, *map(str, args)],
        cwd=case["root"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_full_bundle_roundtrip_and_preserved_state(configured):
    case, config, backup, inspection = configured
    captured = bundle.backup_bundle(config, backup)
    original = {p.relative_to(backup): p.read_bytes() for p in backup.rglob("*") if p.is_file()}
    verified = bundle.verify_bundle(config, backup)
    restored = bundle.restore_bundle(config, backup, inspection)
    assert verified["bundle_sha256"] == captured["bundle_sha256"]
    assert restored["manifest"]["parent_bundle_sha256"] == captured["bundle_sha256"]
    assert restored["manifest"]["evidence"] == captured["manifest"]["evidence"]
    assert restored["manifest"]["capture_start"] == captured["manifest"]["capture_start"]
    assert restored["manifest"]["capture_end"] == captured["manifest"]["capture_end"]
    assert restored["manifest"]["kind"] == "inspection"
    assert restored["audit"]["commands"]["total_halts"] == 1
    assert restored["audit"]["sync"]["pending"]["state"] == "UNKNOWN"
    assert restored["audit"]["sync"]["pending"]["attempts"] == 1
    assert captured["manifest"]["duration_seconds"] > 0
    assert restored["manifest"]["duration_seconds"] > 0
    assert not restored["manifest"]["execution_ready"]
    assert restored["manifest"]["operator_provenance_claims"]["source_revision"] == "0" * 40
    assert all(
        p.stat().st_mode & 0o777 == (0o700 if p.is_dir() else 0o600) for p in inspection.rglob("*")
    )
    assert {
        p.relative_to(backup): p.read_bytes() for p in backup.rglob("*") if p.is_file()
    } == original
    assert case["binding"].source_directory not in json.dumps(captured["manifest"])


@pytest.mark.parametrize("action", ["backup", "restore"])
def test_existing_output_never_overwritten(configured, action):
    _, config, backup, inspection = configured
    bundle.backup_bundle(config, backup)
    inspection.mkdir(mode=0o700)
    marker = inspection / "preserve"
    marker.write_text("owner fixture")
    with pytest.raises(bundle.BundleUnavailable):
        if action == "backup":
            bundle.backup_bundle(config, inspection)
        else:
            bundle.restore_bundle(config, backup, inspection)
    assert marker.read_text() == "owner fixture" and list(inspection.iterdir()) == [marker]


def test_nested_restore_does_not_invalidate_source(configured):
    _, config, backup, _ = configured
    original = bundle.backup_bundle(config, backup)
    for output in (backup, backup / "child"):
        with pytest.raises(bundle.BundleUnavailable):
            bundle.restore_bundle(config, backup, output)
        assert bundle.verify_bundle(config, backup)["bundle_sha256"] == original["bundle_sha256"]


@pytest.mark.parametrize(
    "kind",
    ["extra", "missing", "manifest", "mode", "symlink", "code", "evidence", "config", "member"],
)
def test_tampered_bundle_is_not_restored(configured, kind):
    _, config, backup, inspection = configured
    bundle.backup_bundle(config, backup)
    manifest_path = backup / "bundle.json"
    if kind == "extra":
        (backup / "extra").touch(mode=0o600)
    elif kind == "missing":
        (backup / "commands/manifest.json").unlink()
    elif kind == "manifest":
        manifest_path.write_text("{}")
    elif kind == "mode":
        manifest_path.chmod(0o644)
    elif kind == "symlink":
        original = backup.parent / "moved-manifest"
        manifest_path.rename(original)
        manifest_path.symlink_to(original)
    elif kind == "config":
        config.write_text(config.read_text() + " ")
    elif kind == "member":
        path = backup / "sync/manifest.json"
        path.write_text(path.read_text() + " ")
    else:
        data = json.loads(manifest_path.read_text())
        if kind == "code":
            name = next(iter(data["producer"]["modules"]))
            data["producer"]["modules"][name] = "0" * 64
        else:
            data["evidence"]["sync"]["pending"]["state"] = "VERIFIED"
        manifest_path.write_text(json.dumps(data))
    with pytest.raises(bundle.BundleUnavailable, match=r"^RECOVERY_BUNDLE_UNAVAILABLE$"):
        bundle.restore_bundle(config, backup, inspection)
    assert not inspection.exists()


@pytest.mark.parametrize(
    "kind",
    [
        "config-mode",
        "extra-key",
        "source-mode",
        "missing-risk",
        "deadline",
        "fsync",
        "config-drift",
    ],
)
def test_failure_never_publishes_accepted_bundle(configured, monkeypatch, kind):
    case, config, backup, _ = configured
    if kind == "config-mode":
        config.chmod(0o644)
    elif kind == "extra-key":
        raw = json.loads(config.read_text())
        raw["api_key"] = "not-a-real-key"
        config.write_text(json.dumps(raw))
    elif kind == "source-mode":
        case["commands"].path.chmod(0o644)
    elif kind == "missing-risk":
        with case["commands"]._connect() as db:
            db.execute("DELETE FROM risk_state")
    elif kind == "deadline":
        monkeypatch.setattr(bundle, "MAX_SECONDS", -1)
    elif kind == "fsync":

        def fail(*args, **kwargs):
            raise OSError("fixture fsync failed")

        monkeypatch.setattr(bundle, "_sync", fail)
    else:
        original = bundle.create_snapshot

        def changed(*args):
            result = original(*args)
            config.write_text(config.read_text() + " ")
            return result

        monkeypatch.setattr(bundle, "create_snapshot", changed)
    with pytest.raises(bundle.BundleUnavailable):
        bundle.backup_bundle(config, backup)
    if backup.exists():
        assert (backup / "INCOMPLETE").exists()
    with pytest.raises(bundle.BundleUnavailable):
        bundle.verify_bundle(config, backup)


@pytest.mark.parametrize("signal", ["term", "kill-before-publication"])
def test_process_interruption_is_not_success(configured, signal):
    _, config, backup, _ = configured
    code = """
import os, signal
from sochron_worker import recovery_bundle as b, recovery_cli as c
def interrupted(*args):
    INTERRUPT
b._publish = interrupted
raise SystemExit(c.cli())
""".replace(
        "INTERRUPT", "os.kill(os.getpid(), signal.SIGTERM)" if signal == "term" else "os._exit(73)"
    )
    result = invoke(configured, "backup", "--config", config, "--output", backup, code=code)
    assert result.returncode == (130 if signal == "term" else 73)
    assert not result.stderr
    if signal == "term":
        assert json.loads(result.stdout)["state"] == "STOPPED"
        assert (backup / "INCOMPLETE").exists()
    else:
        assert result.stdout == ""
    assert not (backup / "bundle.json").exists()
    with pytest.raises(bundle.BundleUnavailable):
        bundle.verify_bundle(config, backup)


def test_cli_commands_and_redacted_failure(configured):
    _, config, backup, inspection = configured
    for action, args, state in (
        ("backup", ["--output", backup], "BACKUP_CREATED"),
        ("verify", ["--bundle", backup], "BUNDLE_VERIFIED"),
        ("restore", ["--bundle", backup, "--output", inspection], "INSPECTION_CREATED"),
    ):
        result = invoke(configured, action, "--config", config, *args)
        assert result.returncode == 0 and not result.stderr
        data = json.loads(result.stdout)
        assert data["state"] == state
        assert data["execution_ready"] is data["auto_trading_enabled"] is False
        assert data["command_unknown"] == data["total_halts"] == 1
        assert data["elapsed_seconds"] > 0 and data["capture_age_seconds"] >= 0
        assert str(config) not in result.stdout
    invalid = "sb_secret_" + secrets.token_urlsafe(32)
    result = invoke(configured, invalid)
    assert result.returncode == 2 and not result.stderr
    assert invalid not in result.stdout
    assert json.loads(result.stdout)["state"] == "RECOVERY_BUNDLE_UNAVAILABLE"
    assert invoke(configured).returncode == 2
    assert invoke(configured, "--help").returncode == 0


def test_restore_without_original_sources(configured):
    case, config, backup, inspection = configured
    original = bundle.backup_bundle(config, backup)
    # Fixture databases only: make all original sources unavailable, leaving config/bundle.
    for role in bundle.ROLES:
        path = case[role].path
        path.rename(path.with_suffix(".hidden"))
    restored = bundle.restore_bundle(config, backup, inspection)
    assert restored["manifest"]["evidence"] == original["manifest"]["evidence"]
    assert all(not case[role].path.exists() for role in bundle.ROLES)


def test_mixed_members_are_denied(configured):
    _, config, backup, inspection = configured
    bundle.backup_bundle(config, backup)
    second = backup.parent / "second"
    bundle.backup_bundle(config, second)
    shutil.copyfile(second / "commands/manifest.json", backup / "commands/manifest.json")
    with pytest.raises(bundle.BundleUnavailable):
        bundle.restore_bundle(config, backup, inspection)
    assert not inspection.exists()


def test_member_lineage_must_match_bundle_kind(configured):
    _, config, backup, inspection = configured
    bundle.backup_bundle(config, backup)
    member = backup / "commands/manifest.json"
    raw = json.loads(member.read_text())
    raw["parent_database_sha256"] = raw["database_sha256"]
    member.write_text(json.dumps(raw))
    root = backup / "bundle.json"
    manifest = json.loads(root.read_text())
    manifest["member_manifest_sha256"]["commands"] = bundle.digest(member.read_bytes())
    root.write_text(json.dumps(manifest))
    with pytest.raises(bundle.BundleUnavailable):
        bundle.restore_bundle(config, backup, inspection)
    assert not inspection.exists()
