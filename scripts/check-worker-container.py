#!/usr/bin/env python3
"""Verify an invocation-owned Linux worker candidate; no hosted/broker access."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class VerificationFailure(RuntimeError):
    """Fixed verifier messages only, never raw tool output."""


def require(condition, stage):
    if not condition:
        raise VerificationFailure(stage)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(directory):
    sys.path[:0] = [str(ROOT / p) for p in ("services/api/src", "services/worker/src", "tests")]
    from sochron1k.bar_history import BarHistory
    from test_chart import packet, setup_chart
    from test_native_source import record_packet

    with tempfile.TemporaryDirectory(prefix="sochron-container-source-") as temporary:
        setup = setup_chart.__wrapped__()
        archive = BarHistory(Path(temporary).resolve(), setup[1].settings, setup[2].settings)
        record_packet(setup, archive, packet(setup))
        # A consistent synthetic snapshot, not a copy of an active main database.
        with (
            sqlite3.connect(archive.path) as source,
            sqlite3.connect(directory / "bars.sqlite3") as target,
        ):
            source.backup(target)
        (directory / "binding.json").write_text(
            json.dumps(
                dict(
                    archive_id=archive.archive_id,
                    binding=json.loads(archive._binding),
                )
            )
        )


def main():
    env = os.environ.copy()

    def run(*args, expected=0, timeout=60, input_text=None):
        reply = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        require(reply.returncode == expected, "subprocess failed; output suppressed")
        return reply.stdout.strip()

    endpoint = env.get("DOCKER_HOST", "")
    if not endpoint or env.get("DOCKER_CONTEXT"):
        endpoint = json.loads(run("docker", "context", "inspect"))[0]["Endpoints"]["docker"]["Host"]
    require(endpoint.startswith("unix://"), "local Unix Docker endpoint required")
    engine = json.loads(run("docker", "version", "--format", "{{json .Server}}"))
    project = "sochron-worker-" + uuid4().hex[:12]
    output = ROOT / "output/worker-container" / project
    output.mkdir(parents=True)
    candidate = project + ":candidate"
    fixture_image = project + ":fixture"
    env["SOCHRON_WORKER_IMAGE"] = candidate
    base = ["docker", "compose", "-p", project, "-f", str(ROOT / "compose.worker.yaml")]
    inputs = [
        "compose.worker.yaml",
        "services/worker/Dockerfile",
        ".dockerignore",
        ".gitignore",
        "pyproject.toml",
        "uv.lock",
        "scripts/check-worker-container.py",
        "tests/fixtures/worker_container_receiver.py",
        "tests/fixtures/mt5-telemetry-v1.json",
        "tests/test_chart.py",
        "tests/test_native_source.py",
        "tests/test_bar_history.py",
        "tests/test_owner_auth.py",
        "tests/test_telemetry_bridge.py",
        "services/runtime/sqlite.lock.json",
        "scripts/build-container-sqlite.py",
        "scripts/check-container-sqlite.py",
    ]
    inputs += [
        str(p.relative_to(ROOT))
        for base_path in ("services/api/src", "services/worker/src")
        for p in sorted((ROOT / base_path).rglob("*.py"))
    ]
    report = dict(
        source_revision=run("git", "rev-parse", "HEAD"),
        dirty=bool(run("git", "status", "--porcelain")),
        inputs_sha256={p: digest(ROOT / p) for p in inputs},
        engine_version=engine["Version"],
        engine_arch=engine["Arch"],
        compose_version=run("docker", "compose", "version", "--short"),
        project=project,
        candidate=candidate,
        fixture_image=fixture_image,
        result="FAIL",
        checks=[],
        started_at=datetime.now(UTC).isoformat(),
    )
    compose = base
    fixture = None

    def check(name):
        report["checks"].append(name)
        print("PASS " + name, flush=True)

    def build(args, name):
        with (output / name).open("w") as log:
            result = subprocess.run(
                args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1200
            )
        require(result.returncode == 0, "image build failed; see scoped build log")

    def oracle(action, *, input_text=None):
        return run(
            "docker",
            "exec",
            "-i",
            fixture,
            "python",
            "/fixture/receiver.py",
            action,
            input_text=input_text,
        )

    def invoke(*args, expected=0):
        raw = run(*compose, "run", "--rm", "--no-deps", "-T", "worker", *args, expected=expected)
        result = json.loads(raw)
        require(
            result["execution_ready"] is False and result["auto_trading_enabled"] is False,
            "unsafe readiness",
        )
        return result

    def container(service):
        identifier = run(*compose, "ps", "--all", "--quiet", service)
        require(bool(identifier), "container missing")
        return identifier

    def inspect(identifier):
        return json.loads(run("docker", "inspect", identifier))[0]

    def hardening(state):
        host = state["HostConfig"]
        require(state["Config"]["User"] == "10001:10001", "non-root identity")
        require(host["ReadonlyRootfs"] and host["Init"], "read-only/init")
        require(host["CapDrop"] == ["ALL"] and not host["Privileged"], "capabilities")
        require("no-new-privileges:true" in host["SecurityOpt"], "privilege escalation")
        require(not host["PortBindings"] and not state["Config"].get("ExposedPorts"), "ports")
        require(host["RestartPolicy"]["Name"] == "no", "automatic retry restart")
        require(host["PidsLimit"] == 64 and host["Memory"] == 256 * 1024 * 1024, "resource limits")
        require(host["LogConfig"]["Config"] == {"max-file": "3", "max-size": "5m"}, "log bounds")

    try:
        report["stage"] = "build"
        config = json.loads(run(*base, "config", "--format", "json"))["services"]["worker"]
        require(config["network_mode"] == "none" and config["restart"] == "no", "default isolation")
        require(not config.get("volumes") and not config.get("environment"), "default private data")
        build([*base, "build", "--pull", "--no-cache"], "build.log")
        report["candidate_image"] = json.loads(run("docker", "image", "inspect", candidate))[0][
            "Id"
        ]
        require(invoke("run", "--once")["state"] == "DISABLED", "default not disabled")
        disabled_alert_delivery = json.loads(
            run(
                *base,
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "sochron-alert-delivery",
                "worker",
                "run",
                "--once",
            )
        )
        require(
            disabled_alert_delivery
            == {
                "state": "DISABLED",
                "execution_ready": False,
                "auto_trading_enabled": False,
            },
            "alert delivery default not disabled",
        )
        run(*base, "up", "--detach", "--no-build")
        default = inspect(container("worker"))
        hardening(default)
        require(
            default["HostConfig"]["NetworkMode"] == "none" and not default["Mounts"],
            "default network/mounts",
        )
        require(run("docker", "wait", default["Id"]) == "0", "default exit")
        require(
            json.loads(run("docker", "logs", default["Id"]))["state"] == "DISABLED",
            "default status",
        )
        check("default disabled; no network, volumes or ports; runtime hardening")

        code = """
import hashlib, importlib.metadata as m, json, os, platform, sqlite3
from pathlib import Path
import sochron1k, sochron_worker
packages = {}
for module in (sochron1k, sochron_worker):
    directory = Path(module.__file__).parent
    assert str(directory).startswith('/opt/worker/lib/python3.14/site-packages/')
    packages.update({module.__name__ + '/' + p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in directory.glob('*.py')})
assert os.getuid() == 10001 and 'PYTHONPATH' not in os.environ
assert not any(Path(p).exists() for p in ['/build', '/fixture', '/app', '/worker/config/key'])
print(json.dumps(dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
    modules=packages, distributions={d.metadata['Name'].lower().replace('_', '-'):d.version
                                     for d in m.distributions()},
    artifact_manifest=Path('/opt/artifact/SHA256SUMS').read_text())))
"""
        runtime = json.loads(
            run(
                *base,
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "python",
                "worker",
                "-I",
                "-c",
                code,
            )
        )
        require(runtime["python"] == "3.14.7", "Python pin")
        expected_modules = {
            p.split("/src/")[1]: report["inputs_sha256"][p] for p in inputs if "/src/" in p
        }
        require(runtime["modules"] == expected_modules, "installed source identity")
        locked = {
            p["name"]: p["version"]
            for p in tomllib.loads((ROOT / "uv.lock").read_text())["package"]
        }
        require(
            all(locked.get(k) == v for k, v in runtime["distributions"].items()), "runtime lock"
        )
        require(
            not set(runtime["distributions"]) & {"pytest", "hatchling", "uv", "ruff", "hypothesis"},
            "build/dev tools in runtime",
        )
        report["runtime"] = runtime
        report["sqlite_debian_package"] = run(
            *base,
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "--entrypoint",
            "dpkg-query",
            "worker",
            "-W",
            "-f=${Version}",
            "libsqlite3-0",
        )
        report["release_ready"] = False
        report["sqlite_admission"] = json.loads(
            run(
                *base,
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "python",
                "worker",
                "/opt/sochron/check-sqlite.py",
            )
        )
        report["sqlite_wal_reset_fix_verified"] = True
        check("installed wheel exact source bytes, pinned runtime and no build/dev tools")

        report["stage"] = "fixture"
        context = output / "fixture"
        context.mkdir()
        seed(context)
        shutil.copyfile(
            ROOT / "tests/fixtures/worker_container_receiver.py", context / "receiver.py"
        )
        (context / "Dockerfile").write_text(
            f"FROM {candidate}\nUSER root\n"
            "RUN mkdir /worker/evidence && chown 10001:10001 /worker/evidence "
            "&& chmod 700 /worker/evidence\nCOPY . /fixture\nUSER 10001:10001\n"
            'ENTRYPOINT ["python", "/fixture/receiver.py"]\nCMD ["serve"]\n'
        )
        build(["docker", "build", "-t", fixture_image, str(context)], "fixture-build.log")
        report["fixture_image_id"] = json.loads(run("docker", "image", "inspect", fixture_image))[
            0
        ]["Id"]
        report["seed_sha256"] = digest(context / "bars.sqlite3")
        overlay = output / "compose.fixture.json"
        volumes = ["source:/worker/source", "state:/worker/state", "config:/worker/config"]
        overlay.write_text(
            json.dumps(
                dict(
                    services=dict(
                        worker=dict(
                            network_mode="service:fixture",
                            command=["run", "--once"],
                            environment={"SOCHRON_SYNC_CONFIG_FILE": "/worker/config/config.json"},
                            volumes=[*volumes[:2], volumes[2] + ":ro"],
                        ),
                        fixture=dict(
                            image=fixture_image,
                            user="10001:10001",
                            init=True,
                            read_only=True,
                            cap_drop=["ALL"],
                            security_opt=["no-new-privileges:true"],
                            network_mode="none",
                            restart="no",
                            volumes=[*volumes, "evidence:/worker/evidence"],
                            healthcheck=dict(
                                test=[
                                    "CMD",
                                    "python",
                                    "-c",
                                    "import urllib.request; "
                                    "urllib.request.urlopen("
                                    "'http://127.0.0.1:8765/ready', timeout=1)",
                                ],
                                interval="1s",
                                timeout="2s",
                                retries=15,
                            ),
                        ),
                    ),
                    volumes={name: {} for name in ("source", "state", "config", "evidence")},
                )
            )
        )
        compose = [*base, "-f", str(overlay)]
        run(*compose, "up", "--detach", "--wait", "--wait-timeout", "30", "fixture")
        fixture = container("fixture")
        require(inspect(fixture)["HostConfig"]["NetworkMode"] == "none", "fixture isolation")
        require(invoke("init")["state"] == "INITIALIZED", "init")
        require(invoke("init", expected=2)["state"] == "SYNC_JOURNAL_UNAVAILABLE", "duplicate init")
        require(invoke("status")["state"] == "LOCAL_STATUS", "status")
        require(json.loads(oracle("inspect"))["stores"] == 0, "local command traffic")
        check("private Linux volumes, explicit init/status, duplicate init denial, no send")

        report["stage"] = "stop/replacement"
        run(*compose, "up", "--detach", "--no-deps", "--force-recreate", "worker")
        worker = container("worker")
        deadline = time.monotonic() + 10
        while json.loads(oracle("inspect"))["stores"] == 0:
            require(time.monotonic() < deadline, "store not observed")
            require(inspect(worker)["State"]["Running"], "worker exited before acceptance")
            time.sleep(0.1)
        worker_state = inspect(worker)
        hardening(worker_state)
        require(
            worker_state["HostConfig"]["NetworkMode"] == "container:" + fixture,
            "worker must share only isolated fixture loopback",
        )
        mounts = {m["Destination"]: m for m in worker_state["Mounts"]}
        require(
            set(mounts) == {"/worker/source", "/worker/state", "/worker/config"},
            "unexpected runtime mounts",
        )
        for name in ("source", "state", "config"):
            mount = mounts["/worker/" + name]
            require(
                mount["Type"] == "volume" and mount["Name"] == f"{project}_{name}", "mount identity"
            )
            require(mount["RW"] is (name != "config"), "mount access mode")
        require(
            invoke("status", expected=2)["state"] == "SYNC_JOURNAL_UNAVAILABLE", "writer exclusion"
        )
        run(*compose, "stop", "--timeout", "10", "worker")
        require(inspect(worker)["State"]["ExitCode"] == 130, "SIGTERM did not exit cleanly")
        logs = run("docker", "logs", worker)
        require(json.loads(logs.splitlines()[-1])["state"] == "STOPPED", "SIGTERM status")
        oracle("check-logs", input_text=logs)
        stopped = json.loads(oracle("inspect"))
        require(
            stopped["batches"] == [["UNKNOWN", 1]] and stopped["receipt"] == 0,
            "UNKNOWN/cursor persistence",
        )
        check("exclusive writer and container SIGTERM after acceptance preserves UNKNOWN")
        oracle("release")
        run(*compose, "up", "--detach", "--no-deps", "--force-recreate", "worker")
        replacement = container("worker")
        require(replacement != worker, "container not replaced")
        require(run("docker", "wait", replacement, timeout=30) == "0", "replacement exit")
        logs = run("docker", "logs", replacement)
        require(json.loads(logs)["state"] == "VERIFIED", "replacement reconciliation")
        oracle("check-logs", input_text=logs)
        require(invoke("run", "--once")["state"] == "IDLE", "replacement idle")
        final = json.loads(oracle("inspect"))
        require(
            final["stores"] == 1 and final["reads"] >= 1 and final["source_unchanged"],
            "duplicate send, no readback or source mutation",
        )
        require(final["batches"] == [["VERIFIED", 1]] and final["receipt"] == 1, "verified ledger")
        check("new container reads back without resend; source unchanged; VERIFIED cursor survives")

        oracle("unsafe-config")
        require(
            invoke("run", "--once", expected=2)["state"] == "SYNC_CONFIG_INVALID", "config denial"
        )
        require(
            json.loads(oracle("inspect")) == final, "unsafe config made traffic or state change"
        )
        oracle("safe-config")
        check("unsafe private config denied without traffic or state change")
        report["oracle"] = final
        report["result"] = "PASS"
    except Exception as error:
        # No raw child output/config/headers in the report or terminal.
        report["failure_type"] = type(error).__name__
        if isinstance(error, VerificationFailure):
            report["failure_check"] = str(error)
            print("FAIL " + str(error), flush=True)
        print("FAIL " + report.get("stage", "setup") + "; child output suppressed", flush=True)
    finally:
        if fixture:
            try:
                oracle("remove-key")
                report["fixture_key_removed"] = True
            except Exception:
                report["fixture_key_removed"] = False
                report["result"] = "FAIL"
        try:
            cleanup = subprocess.run(
                [*compose, "down", "--timeout", "10"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            report["cleanup_returncode"] = cleanup.returncode
            report["retained_volumes"] = run(
                "docker",
                "volume",
                "ls",
                "--quiet",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ).splitlines()
        except Exception:
            report["cleanup_returncode"] = "UNKNOWN"
        if report["cleanup_returncode"] != 0:
            report["result"] = "FAIL"
        report["finished_at"] = datetime.now(UTC).isoformat()
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(report["result"] + " evidence: " + str(output / "result.json"), flush=True)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
