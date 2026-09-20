#!/usr/bin/env python3
"""Build and verify an isolated internal worker artifact, never a hosted service."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import tomllib
import zipfile
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
CHECKS: list[str] = []


class VerificationFailure(RuntimeError):
    pass


def require(condition, stage):
    if not condition:
        raise VerificationFailure(stage)


def check(stage):
    CHECKS.append(stage)
    print("PASS " + stage, flush=True)


def run(args, *, cwd=ROOT, env=None, expected=0):
    reply = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    require(reply.returncode == expected, "subprocess failed; output suppressed")
    return reply


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exercise_startup(python, directory):
    from dataclasses import asdict

    import conftest as fixtures

    observed = fixtures.observed_at.__wrapped__()
    data = {
        name: getattr(fixtures, name).__wrapped__(observed).model_dump(mode="json")
        for name in ("account", "market", "intent")
    }
    data.update(
        {
            name: getattr(fixtures, name).__wrapped__().model_dump(mode="json")
            for name in ("contract", "risk")
        }
    )
    data.update(policy=asdict(fixtures.policy.__wrapped__()), now=observed.isoformat())
    path = directory / "startup-fixture.json"
    path.touch(mode=0o600)
    path.write_text(json.dumps(data))
    probe = run(
        [str(python), "-I", str(ROOT / "tests/fixtures/execution_startup_probe.py"), str(path)],
        cwd=directory,
        env={"PATH": os.defpath},
    )
    require(not probe.stderr, "installed startup probe stderr")
    result = json.loads(probe.stdout)
    require(
        result
        == dict(
            result="PASS",
            scope="installed-simulator",
            sends=1,
            attempts=1,
            deals=1,
            management_sends=1,
            management_attempts=1,
            management_deals=1,
            final_net_pnl="0",
            halts_preserved=True,
            execution_ready=False,
            auto_trading_enabled=False,
        ),
        "installed startup admission",
    )
    check(
        "installed execution startup, missing baseline, UNKNOWN recovery, "
        "generation and halt denial, UNKNOWN close query reconciliation"
    )
    return result


def exercise_recovery(command, python, directory, sync_config, wheel_hash, invoke_sync):
    from decimal import Decimal

    from conftest import intent, observed_at
    from sochron1k.journal import Journal
    from sochron1k.models import BrokerDeal, BrokerSnapshot, CommandState, RiskState

    raw = json.loads(sync_config.read_text())
    command_path = directory / "commands" / "journal.sqlite3"
    command_path.parent.mkdir(mode=0o700)
    command_path.touch(mode=0o600)
    journal = Journal(command_path)
    request = intent.__wrapped__(observed_at.__wrapped__()).model_copy(
        update={"account_ref": raw["identity"]["account_ref"], "symbol": raw["identity"]["symbol"]}
    )
    journal.save_risk_state(
        RiskState(
            account_ref=request.account_ref,
            experiment_id=request.experiment_id,
            bangkok_day="2026-09-17",
            daily_baseline=Decimal("100000"),
            experiment_baseline=Decimal("100000"),
            daily_halt=True,
            total_halt=True,
            updated_at=observed_at.__wrapped__(),
        )
    )
    journal.reserve(request, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(request.command_id, "recovery-fixture-attempt")
    journal.transition(request.command_id, CommandState.UNKNOWN)
    broker_file = directory / "synthetic-broker-snapshot.json"
    broker_file.touch(mode=0o600)
    broker_file.write_text(
        BrokerSnapshot(
            command_id=request.command_id,
            order_ticket="fixture-order",
            position_id="fixture-position",
            requested_volume=Decimal("0.1"),
            filled_volume=Decimal("0.1"),
            remaining_volume=Decimal("0"),
            stop_loss_confirmed=True,
            deals=(
                BrokerDeal(
                    deal_ticket="fixture-deal", volume=Decimal("0.1"), price=request.requested_entry
                ),
            ),
        ).model_dump_json()
    )
    config = directory / "recovery-config.json"
    config.touch(mode=0o600)
    config.write_text(
        json.dumps(
            dict(
                binding=dict(
                    identity=raw["identity"],
                    active_experiment_id=request.experiment_id,
                    archive_id=raw["archive_id"],
                    owner_id=raw["owner_id"],
                    source_directory=raw["source_directory"],
                    destination=raw["origin"],
                    offset_seconds=raw["offset_seconds"],
                    chart=raw["chart"],
                ),
                command_database=str(command_path),
                sync_database=str(Path(raw["state_directory"]) / "sync.sqlite3"),
                archive_database=str(Path(raw["source_directory"]) / "bars.sqlite3"),
                max_age_seconds=3600,
                max_span_seconds=60,
                operator_provenance_claims=dict(
                    source_revision=run(["git", "rev-parse", "HEAD"]).stdout.strip(),
                    artifact_sha256=wheel_hash,
                ),
            )
        )
    )
    backup, inspection = directory / "recovery-backup", directory / "recovery-inspection"
    env = {"PATH": os.defpath, "LANG": "C.UTF-8"}
    measurements = {}

    def invoke(action, *args, module=False):
        executable = (
            [str(python), "-I", "-m", "sochron_worker.recovery_cli"] if module else [str(command)]
        )
        start = time.monotonic()
        reply = run(
            [*executable, action, "--config", str(config), *map(str, args)], cwd=directory, env=env
        )
        measurements[action + "_process_seconds"] = time.monotonic() - start
        require(not reply.stderr and str(directory) not in reply.stdout, "recovery CLI disclosure")
        status = json.loads(reply.stdout)
        require(
            status["execution_ready"] is False and status["auto_trading_enabled"] is False,
            "recovery enabled execution",
        )
        require(status["command_unknown"] == status["total_halts"] == 1, "recovery risk state")
        require(
            status["sync_pending"]
            == dict(state="UNKNOWN", attempts=1, send_budget_exhausted=False),
            "recovery pending state",
        )
        measurements[action + "_reported_seconds"] = status["elapsed_seconds"]
        return status

    captured = invoke("backup", "--output", backup)
    require(captured["state"] == "BACKUP_CREATED", "installed recovery backup")
    original = (backup / "bundle.json").read_bytes()
    unavailable = run(
        [str(command), "backup", "--config", str(config), "--output", str(backup)],
        cwd=directory,
        env=env,
        expected=2,
    )
    require(
        json.loads(unavailable.stdout)["state"] == "RECOVERY_BUNDLE_UNAVAILABLE"
        and not unavailable.stderr
        and (backup / "bundle.json").read_bytes() == original,
        "recovery replaced existing target",
    )
    moved = []
    try:
        # Only generated fixtures: originals are unavailable during verify and restore.
        for path in (
            Path(raw["source_directory"]),
            Path(raw["state_directory"]),
            command_path.parent,
        ):
            hidden = path.with_name(path.name + "-unavailable")
            path.rename(hidden)
            moved.append((path, hidden))
        require(
            invoke("verify", "--bundle", backup, module=True)["state"] == "BUNDLE_VERIFIED",
            "installed module verification",
        )
        restored = invoke("restore", "--bundle", backup, "--output", inspection)
        require(restored["state"] == "INSPECTION_CREATED", "installed recovery restore")
        require(all(not path.exists() for path, _ in moved), "recovery recreated original source")
        manifest = json.loads((inspection / "bundle.json").read_text())
        before = json.loads(original)
        require(
            manifest["parent_bundle_sha256"] == captured["bundle_sha256"]
            and manifest["capture_start"] == before["capture_start"]
            and manifest["capture_end"] == before["capture_end"]
            and manifest["evidence"] == before["evidence"],
            "recovery evidence changed",
        )
        with sqlite3.connect(inspection / "commands/snapshot.sqlite3") as db:
            require(
                db.execute("SELECT state FROM commands").fetchone() == ("unknown",), "lost UNKNOWN"
            )
            require(
                db.execute("SELECT count(*) FROM exposure_slots").fetchone()[0] == 1,
                "lost exposure",
            )
            require(
                db.execute(
                    "SELECT daily_baseline,experiment_baseline,daily_halt,total_halt "
                    "FROM risk_state"
                ).fetchone()
                == ("100000", "100000", 1, 1),
                "lost risk baselines/halts",
            )
        with sqlite3.connect(inspection / "sync/snapshot.sqlite3") as db:
            require(
                db.execute("SELECT state,attempts FROM batches").fetchone() == ("UNKNOWN", 1),
                "lost sync state",
            )
            require(
                db.execute("SELECT receipt FROM meta").fetchone()[0] == 0, "advanced restore cursor"
            )
        require((backup / "bundle.json").read_bytes() == original, "source bundle changed")
        invalid = "sb_secret_" + secrets.token_urlsafe(32)
        rejected = run([str(command), invalid], cwd=directory, env=env, expected=2)
        require(
            invalid not in rejected.stdout + rejected.stderr and not rejected.stderr,
            "recovery argument disclosure",
        )
        # Fixture-only offline activation: the worker above has exited. Preserve the
        # exact original binding/paths, and never modify backup/inspection evidence.
        source_bytes = {
            str(p.relative_to(inspection)): p.read_bytes()
            for p in inspection.rglob("*")
            if p.is_file()
        }
        activation_start = time.monotonic()
        for role, destination in (
            ("archive", Path(raw["source_directory"]) / "bars.sqlite3"),
            ("sync", Path(raw["state_directory"]) / "sync.sqlite3"),
            ("commands", command_path),
        ):
            require(destination.parent.parent == directory, "fixture activation scope")
            destination.parent.mkdir(mode=0o700)
            with destination.open("xb") as handle:
                os.chmod(destination, 0o600)
                handle.write((inspection / role / "snapshot.sqlite3").read_bytes())
            # NativeArchiveSource intentionally refuses DELETE-mode inspection copies.
            with sqlite3.connect(destination) as db:
                require(
                    db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal",
                    "fixture WAL activation",
                )
            db.close()
        lock = Path(raw["state_directory"]) / "sync.lock"
        lock.touch(mode=0o600, exist_ok=False)
        status = invoke_sync("status")
        require(
            status["pending"] == "UNKNOWN"
            and status["attempts"] == 1
            and status["cursor_receipt"] == 0,
            "restored worker initial state",
        )
        require(invoke_sync("reconcile")["state"] == "VERIFIED", "restored worker reconcile")
        require(invoke_sync("reconcile")["state"] == "NO_PENDING", "query-only repeat")
        with sqlite3.connect(Path(raw["state_directory"]) / "sync.sqlite3") as db:
            require(
                db.execute("SELECT state,attempts FROM batches").fetchone() == ("VERIFIED", 1),
                "restored attempt budget",
            )
            require(
                db.execute("SELECT receipt FROM meta").fetchone()[0] == 1,
                "restored cursor evidence",
            )
        db.close()
        probe = run(
            [
                str(python),
                "-I",
                str(ROOT / "tests/fixtures/recovery_query_probe.py"),
                str(command_path),
                str(broker_file),
            ],
            cwd=directory,
            env=env,
        )
        require(not probe.stderr, "restored command probe stderr")
        command_recovery = json.loads(probe.stdout)
        require(
            command_recovery
            == dict(
                result="PASS",
                broker="query-only-simulator",
                queries=4,
                sends=0,
                execution_ready=False,
                auto_trading_enabled=False,
            ),
            "restored command query-only result",
        )
        measurements["application_rehearsal_seconds"] = time.monotonic() - activation_start
        require(
            {
                str(p.relative_to(inspection)): p.read_bytes()
                for p in inspection.rglob("*")
                if p.is_file()
            }
            == source_bytes,
            "activation mutated inspection evidence",
        )
        check(
            "installed recovery backup/verify/isolated restore; unavailable originals; "
            "UNKNOWN/halts preserved"
        )
        check("restored exact-path worker read-back and command query-only simulator; no new sends")
        return {
            **measurements,
            "capture_start": before["capture_start"],
            "capture_end": before["capture_end"],
            "backup_sha256": captured["bundle_sha256"],
            "inspection_sha256": restored["bundle_sha256"],
            "execution_ready": False,
            "broker_reconciliation": "NOT_RUN",
            "destination_reconciliation": "NOT_RUN",
            "restored_application_rehearsal": dict(
                worker="VERIFIED_THEN_NO_PENDING",
                attempts=1,
                cursor_receipt=1,
                command=command_recovery,
                scope="synthetic-only",
            ),
        }
    finally:
        for path, hidden in reversed(moved):
            if path.exists():
                path.rename(path.with_name(path.name + "-rehearsed"))
            hidden.rename(path)


def exercise(command, python, directory, wheel_hash):
    # Parent creates fixtures using development helpers. Child has only the installed wheel.
    sys.path[:0] = [str(ROOT / p) for p in ("services/api/src", "services/worker/src", "tests")]
    from sochron1k.bar_history import BarHistory
    from test_chart import packet, setup_chart
    from test_native_source import record_packet

    env = {"PATH": os.defpath, "LANG": "C.UTF-8"}

    def invoke(*args, expected=0):
        reply = run([str(command), *args], cwd=directory, env=env, expected=expected)
        require(not reply.stderr, "unexpected worker stderr")
        status = json.loads(reply.stdout)
        require(
            status["execution_ready"] is False and status["auto_trading_enabled"] is False,
            "unsafe readiness",
        )
        return status

    require(invoke("run", "--once")["state"] == "DISABLED", "default must be disabled")
    require(invoke("reconcile")["state"] == "DISABLED", "query-only default must be disabled")
    require(
        invoke("reconcile", "--once", expected=2)["state"] == "SYNC_CONFIG_INVALID",
        "query-only flags",
    )
    require(
        "private config" in run([str(command), "--help"], cwd=directory, env=env).stdout,
        "installed help",
    )
    invalid = "sb_secret_" + secrets.token_urlsafe(32)
    result = run([str(command), invalid], cwd=directory, env=env, expected=2)
    require(invalid not in result.stdout + result.stderr, "argument disclosure")
    require(json.loads(result.stdout)["state"] == "SYNC_CONFIG_INVALID", "invalid command")
    module = run(
        [str(python), "-I", "-m", "sochron_worker", "run", "--once"], cwd=directory, env=env
    )
    require(json.loads(module.stdout)["state"] == "DISABLED", "installed module")
    check("installed console/module disabled, help and redacted invalid argument")

    source_dir, state_dir = directory / "source", directory / "state"
    source_dir.mkdir(mode=0o700)
    state_dir.mkdir(mode=0o700)
    setup = setup_chart.__wrapped__()
    archive = BarHistory(source_dir, setup[1].settings, setup[2].settings)
    record_packet(setup, archive, packet(setup))
    binding = json.loads(archive._binding)
    accepted, release = threading.Event(), threading.Event()
    stores = []
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                require(0 < size <= 262144, "fixture request bound")
                args = json.loads(self.rfile.read(size))
                if self.path == "/rest/v1/rpc/sochron_store_native_m1":
                    stores.append(args)
                    accepted.set()
                    require(release.wait(15), "fixture hold deadline")
                    self.close_connection = True
                    return
                require(self.path == "/rest/v1/rpc/sochron_read_native_m1", "fixture RPC path")
                response = json.dumps(
                    {
                        "archive_id": args["p_archive_id"],
                        "binding": stores[0]["p_binding"],
                        "rows": stores[0]["p_rows"],
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            except Exception:
                errors.append("fixture server failed")
                self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = directory / "config.json"
    key = directory / "key"
    config.write_text(
        json.dumps(
            dict(
                enabled=True,
                source_directory=str(source_dir),
                state_directory=str(state_dir),
                archive_id=archive.archive_id,
                identity=binding["identity"],
                offset_seconds=binding["offset"],
                chart=binding["chart"],
                owner_id=str(uuid4()),
                origin=f"http://127.0.0.1:{server.server_port}",
                service_key_file=str(key),
            )
        )
    )
    config.chmod(0o600)
    env["SOCHRON_SYNC_CONFIG_FILE"] = str(config)
    child = None
    try:
        require(invoke("init")["state"] == "INITIALIZED", "private init without key")
        require(invoke("status")["state"] == "LOCAL_STATUS", "status without key")
        require(
            invoke("init", expected=2)["state"] == "SYNC_JOURNAL_UNAVAILABLE",
            "duplicate init reset",
        )
        require(not stores, "local command contacted destination")
        key.write_text("sb_secret_" + secrets.token_urlsafe(32))
        key.chmod(0o600)
        child = subprocess.Popen(
            [str(command), "run", "--once"],
            cwd=directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(accepted.wait(10), "installed worker did not send")
        child.send_signal(signal.SIGTERM)
        stdout, stderr = child.communicate(timeout=5)
        require(child.returncode == 130 and not stderr, "installed SIGTERM exit")
        require(json.loads(stdout)["state"] == "STOPPED", "installed SIGTERM state")
        require(key.read_text() not in stdout, "installed key disclosure")
        with sqlite3.connect(state_dir / "sync.sqlite3") as db:
            require(
                db.execute("select state,attempts from batches").fetchone() == ("UNKNOWN", 1),
                "installed UNKNOWN not durable",
            )
            require(db.execute("select receipt from meta").fetchone()[0] == 0, "early cursor")
        release.set()
        recovery = exercise_recovery(
            directory / "venv/bin/sochron-recovery", python, directory, config, wheel_hash, invoke
        )
        require(invoke("run", "--once")["state"] == "VERIFIED", "installed reconciliation")
        require(invoke("run", "--once")["state"] == "IDLE", "installed idle")
        status = invoke("status")
        require(status["cursor_receipt"] == 1 and status["pending"] is None, "installed cursor")
        require(len(stores) == 1 and not errors, "duplicate send or fixture error")
        check(
            "installed init/status, duplicate-init denial, "
            "SIGTERM UNKNOWN and restart without resend"
        )
        return recovery
    finally:
        release.set()
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def verify(output):
    uv = os.environ.get("SOCHRON_UV") or shutil.which("uv")
    require(bool(uv), "pinned uv required; set SOCHRON_UV to its executable")
    require(run([uv, "--version"]).stdout.startswith("uv 0.12.15 "), "pinned uv required")
    require(platform.python_version() == "3.14.7", "pinned Python required")
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    locked = {p["name"]: p["version"] for p in lock["package"]}
    build_names = ("hatchling", "packaging", "pathspec", "pluggy", "tomlkit", "trove-classifiers")
    require(
        all(importlib.metadata.version(n) == locked[n] for n in build_names),
        "build environment differs from lock",
    )
    build_env = {**os.environ, "SOURCE_DATE_EPOCH": "1580601600"}
    run(
        [uv, "build", "--no-build-isolation", "--python", sys.executable, "--out-dir", str(output)],
        env=build_env,
    )
    wheel = next(output.glob("*.whl"))
    sdist = next(output.glob("*.tar.gz"))
    modules = {
        str(p.relative_to(ROOT / base)): p
        for base in ("services/api/src", "services/worker/src")
        for p in (ROOT / base).glob("*/*.py")
    }
    with zipfile.ZipFile(wheel) as archive:
        files = set(archive.namelist())
        metadata = {
            f"sochron1k-0.1.0.dist-info/{name}"
            for name in ("METADATA", "WHEEL", "RECORD", "entry_points.txt")
        }
        require(files == set(modules) | metadata, "unexpected wheel members")
        require(
            all(archive.read(n) == p.read_bytes() for n, p in modules.items()),
            "wheel source mismatch",
        )
        require(
            "sochron-sync = sochron_worker.__main__:cli"
            in archive.read("sochron1k-0.1.0.dist-info/entry_points.txt").decode(),
            "entry point mismatch",
        )
        require(
            "sochron-recovery = sochron_worker.recovery_cli:cli"
            in archive.read("sochron1k-0.1.0.dist-info/entry_points.txt").decode(),
            "recovery entry point mismatch",
        )
        require(
            "sochron-pa01 = sochron_worker.pa01_cli:cli"
            in archive.read("sochron1k-0.1.0.dist-info/entry_points.txt").decode(),
            "PA01 entry point mismatch",
        )
        require(
            "sochron-news-gate = sochron_worker.news_gate_cli:cli"
            in archive.read("sochron1k-0.1.0.dist-info/entry_points.txt").decode(),
            "News Gate entry point mismatch",
        )
    with tarfile.open(sdist) as archive:
        prefix = "sochron1k-0.1.0/"
        members = {m.name.removeprefix(prefix) for m in archive.getmembers() if m.isfile()}
        expected = {str(p.relative_to(ROOT)) for p in modules.values()}
        require(
            members == expected | {"pyproject.toml", "uv.lock", ".gitignore", "PKG-INFO"},
            "unexpected sdist members",
        )
        # Hatch always includes VCS ignore metadata; verify its exact reviewed bytes too.
        require(
            archive.extractfile(prefix + ".gitignore").read() == (ROOT / ".gitignore").read_bytes(),
            "sdist ignore metadata mismatch",
        )
    direct = output / "direct"
    run(
        [
            uv,
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(direct),
        ],
        env=build_env,
    )
    require(digest(wheel) == digest(next(direct.glob("*.whl"))), "sdist/direct wheel mismatch")
    check("exact source/build-metadata contents and byte-identical wheel rebuild")
    requirements = output / "requirements.txt"
    run(
        [
            uv,
            "export",
            "--locked",
            "--no-default-groups",
            "--no-emit-project",
            "--no-header",
            "--output-file",
            str(requirements),
        ]
    )
    expected_runtime = {}
    for line in requirements.read_text().splitlines():
        if line and line[0].isalnum():
            requirement = Requirement(line.removesuffix(" \\"))
            if requirement.marker is None or requirement.marker.evaluate():
                expected_runtime[canonicalize_name(requirement.name)] = next(
                    iter(requirement.specifier)
                ).version
    require(not set(build_names) & expected_runtime.keys(), "build tools in runtime export")
    with tempfile.TemporaryDirectory(prefix="sochron-wheel-") as temporary:
        directory = Path(temporary).resolve()
        environment = directory / "venv"
        python = environment / "bin/python"
        run([uv, "venv", "--no-project", "--python", sys.executable, str(environment)])
        run(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(python),
                "--require-hashes",
                "--only-binary",
                ":all:",
                "-r",
                str(requirements),
            ]
        )
        run([uv, "pip", "install", "--python", str(python), "--no-deps", "--no-index", str(wheel)])
        probe = run(
            [
                str(python),
                "-I",
                "-c",
                """
import importlib.metadata as m, importlib.util, json, pathlib, sys
import sochron1k, sochron_worker
import sochron_worker.news_gate
import sochron_worker.pa01_envelope
import sochron_worker.pa01_journal
assert all(pathlib.Path(p.__file__).is_relative_to(sys.prefix)
           for p in (sochron1k, sochron_worker, sochron_worker.news_gate,
                     sochron_worker.pa01_envelope,
                     sochron_worker.pa01_journal))
assert importlib.util.find_spec('pytest') is None
assert importlib.util.find_spec('hatchling') is None
values = {d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()}
print(json.dumps(values))
""",
            ],
            cwd=directory,
            env={"PATH": os.defpath},
        )
        require(
            json.loads(probe.stdout) == {**expected_runtime, "sochron1k": "0.1.0"},
            "installed dependency mismatch",
        )
        check(
            "fresh non-editable environment, exact production dependencies, no source/dev imports"
        )
        disabled_pa01 = run(
            [str(environment / "bin/sochron-pa01"), "run", "--once"],
            cwd=directory,
            env={"PATH": os.defpath},
        )
        require(
            json.loads(disabled_pa01.stdout)
            == {
                "state": "DISABLED",
                "execution_ready": False,
                "auto_trading_enabled": False,
            }
            and not disabled_pa01.stderr,
            "installed PA01 default-disabled boundary",
        )
        check("installed PA01 command is inert without private configuration")
        disabled_news = run(
            [str(environment / "bin/sochron-news-gate"), "run", "--once"],
            cwd=directory,
            env={"PATH": os.defpath},
        )
        require(
            json.loads(disabled_news.stdout)
            == {
                "state": "DISABLED",
                "news_ready": False,
                "execution_ready": False,
                "auto_trading_enabled": False,
            }
            and not disabled_news.stderr,
            "installed News Gate default-disabled boundary",
        )
        check("installed News Gate command is inert without private configuration")
        recovery = exercise(environment / "bin/sochron-sync", python, directory, digest(wheel))
        startup = exercise_startup(python, directory)
    return dict(
        result="PASS",
        revision=run(["git", "rev-parse", "HEAD"]).stdout.strip(),
        dirty=bool(run(["git", "status", "--porcelain"]).stdout),
        recorded_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        uv="0.12.15",
        build={n: locked[n] for n in build_names},
        checks=CHECKS,
        recovery_rehearsal=recovery,
        startup_rehearsal=startup,
        artifact_sha256={p.name: digest(p) for p in (wheel, sdist, requirements)},
        input_sha256={
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                *modules.values(),
                ROOT / "pyproject.toml",
                ROOT / "uv.lock",
                Path(__file__),
                ROOT / ".gitignore",
                ROOT / "tests/test_chart.py",
                ROOT / "tests/conftest.py",
                ROOT / "tests/fixtures/recovery_query_probe.py",
                ROOT / "tests/fixtures/execution_startup_probe.py",
                ROOT / "tests/test_native_source.py",
                ROOT / "tests/test_bar_history.py",
                ROOT / "tests/test_telemetry_bridge.py",
                ROOT / "tests/fixtures/mt5-telemetry-v1.json",
            ]
        },
        hosted="NOT_RUN",
        mt5="NOT_RUN",
        deployment="NOT_RUN",
        release="NOT_READY",
    )


if __name__ == "__main__":
    output = ROOT / "output/worker-package" / uuid4().hex
    output.mkdir(parents=True)
    try:
        report = verify(output)
    except Exception as error:
        report = dict(
            result="FAIL",
            error_type=type(error).__name__,
            stage=str(error) if isinstance(error, VerificationFailure) else "details suppressed",
            checks=CHECKS,
            recorded_at=datetime.now(UTC).isoformat(),
        )
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"result": report["result"], "evidence": str(output / "result.json")}))
    raise SystemExit(0 if report["result"] == "PASS" else 1)
