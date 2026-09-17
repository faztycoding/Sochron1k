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


def exercise(command, python, directory):
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
        require(invoke("run", "--once")["state"] == "VERIFIED", "installed reconciliation")
        require(invoke("run", "--once")["state"] == "IDLE", "installed idle")
        status = invoke("status")
        require(status["cursor_receipt"] == 1 and status["pending"] is None, "installed cursor")
        require(len(stores) == 1 and not errors, "duplicate send or fixture error")
        check(
            "installed init/status, duplicate-init denial, "
            "SIGTERM UNKNOWN and restart without resend"
        )
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
assert all(pathlib.Path(p.__file__).is_relative_to(sys.prefix) for p in (sochron1k, sochron_worker))
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
        exercise(environment / "bin/sochron-sync", python, directory)
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
