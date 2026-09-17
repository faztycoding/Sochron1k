"""Exercise an isolated local Compose candidate; never use the developer project."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = os.environ.copy()

    def run(*args: str, timeout: int = 60) -> str:
        return subprocess.check_output(args, cwd=ROOT, env=env, text=True, timeout=timeout).strip()

    endpoint = env.get("DOCKER_HOST", "")
    if not endpoint or env.get("DOCKER_CONTEXT"):
        context = json.loads(run("docker", "context", "inspect"))[0]
        endpoint = context["Endpoints"]["docker"]["Host"]
    if not endpoint.startswith("unix://"):
        raise RuntimeError("Verification requires a local Unix socket Docker endpoint")
    try:
        engine = json.loads(run("docker", "version", "--format", "{{json .Server}}"))
    except subprocess.CalledProcessError:
        print("BLOCKED: local Docker engine is unavailable", file=sys.stderr)
        return 2

    project = f"sochron-verify-{uuid.uuid4().hex[:12]}"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    volume = f"{project}_journal"
    env.update(
        SOCHRON_WEB_PORT=str(port),
        SOCHRON_JOURNAL_VOLUME=volume,
        SOCHRON_API_IMAGE=f"{project}-api:local",
        SOCHRON_WEB_IMAGE=f"{project}-web:local",
        TRADING_MODE="live",
        AUTO_TRADING_ENABLED="true",
    )
    compose = ["docker", "compose", "-f", str(ROOT / "compose.yaml"), "-p", project]
    evidence = ROOT / "output" / "compose" / project
    evidence.mkdir(parents=True)
    inputs = [
        "compose.yaml",
        "services/api/Dockerfile",
        "apps/web/Dockerfile",
        "apps/web/nginx.conf",
        "pyproject.toml",
        "uv.lock",
        "package-lock.json",
        "scripts/verify-compose.py",
        "services/runtime/sqlite.lock.json",
        "scripts/build-container-sqlite.py",
        "scripts/check-container-sqlite.py",
    ]
    report = {
        "source_revision": run("git", "rev-parse", "HEAD"),
        "dirty": bool(run("git", "status", "--porcelain")),
        "inputs_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs
        },
        "engine_version": engine["Version"],
        "engine_arch": engine["Arch"],
        "compose_version": run("docker", "compose", "version", "--short"),
        "project": project,
        "volume": volume,
        "result": "FAIL",
        "started_at": datetime.now(UTC).isoformat(),
        "stage": "configuration",
    }
    expected = {
        "status": "ok",
        "service": "sochron1k-api",
        "version": "0.1.0",
        "trading_mode": "demo",
        "auto_trading_enabled": False,
        "execution_ready": False,
    }

    def health() -> None:
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as r:
                    assert json.load(r) == expected
                return
            except urllib.error.URLError, TimeoutError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)

    try:
        config = json.loads(run(*compose, "config", "--format", "json"))
        assert config["services"]["api"]["environment"]["TRADING_MODE"] == "demo"
        assert config["services"]["api"]["environment"]["AUTO_TRADING_ENABLED"] == "false"
        report["stage"] = "build"
        with (evidence / "build.log").open("w") as log:
            subprocess.run(
                [*compose, "build", "--pull", "--no-cache"],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=1200,
                check=True,
            )
        report["stage"] = "startup"
        run(*compose, "up", "--detach", "--wait", "--wait-timeout", "90", timeout=120)
        report["stage"] = "runtime-boundaries"
        images = {}
        for service, user in [("api", "10001:10001"), ("web", "101:101")]:
            container = run(*compose, "ps", "--quiet", service)
            state = json.loads(run("docker", "inspect", container))[0]
            assert state["Config"]["User"] == user
            assert state["HostConfig"]["ReadonlyRootfs"]
            assert state["HostConfig"]["CapDrop"] == ["ALL"]
            assert "no-new-privileges:true" in state["HostConfig"]["SecurityOpt"]
            bindings = state["HostConfig"]["PortBindings"] or {}
            effective = {k: v for k, v in state["NetworkSettings"]["Ports"].items() if v}
            networks = set(state["NetworkSettings"]["Networks"])
            if service == "api":
                assert not bindings
                assert not effective
                assert networks == {f"{project}_app_internal"}
            else:
                assert bindings == {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(port)}]}
                assert effective == bindings, "Requested web port was not actually published"
                assert networks == {f"{project}_app_internal", f"{project}_web_ingress"}
            images[service] = state["Image"]
        report["images"] = images
        report["python"] = run(*compose, "exec", "-T", "api", "python", "--version")
        assert report["python"] == "Python 3.14.7"
        report["sqlite_admission"] = json.loads(
            run(
                *compose,
                "exec",
                "-T",
                "api",
                "python",
                "/opt/sochron/check-sqlite.py",
            )
        )
        report["nginx"] = run(*compose, "exec", "-T", "web", "sh", "-c", "nginx -v 2>&1")
        assert report["nginx"] == "nginx version: nginx/1.30.5"
        report["stage"] = "host-http"
        health()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            assert "Sochron1k" in response.read().decode()
        report["stage"] = "volume-and-recreation"
        before = run(*compose, "ps", "--quiet", "api")
        marker = uuid.uuid4().hex
        run(
            *compose,
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "from pathlib import Path; import sys; "
            "Path('/app/data/verification-marker').write_text(sys.argv[1])",
            marker,
        )
        run(
            *compose,
            "up",
            "--detach",
            "--force-recreate",
            "--no-deps",
            "--wait",
            "api",
            timeout=120,
        )
        assert before != run(*compose, "ps", "--quiet", "api")
        actual = run(
            *compose,
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "from pathlib import Path; print(Path('/app/data/verification-marker').read_text())",
        )
        assert actual == marker
        health()
        report["result"] = "PASS"
        report["stage"] = "complete"
    except Exception as error:
        # Keep diagnostic type/stage without serializing secret-bearing process output.
        report["error_type"] = type(error).__name__
        raise
    finally:
        # Only resources belonging to this invocation are stopped. Keep evidence volumes.
        cleanup = subprocess.run([*compose, "down"], cwd=ROOT, env=env, timeout=90)
        report["cleanup_returncode"] = cleanup.returncode
        if cleanup.returncode:
            report["result"] = "FAIL"
        report["finished_at"] = datetime.now(UTC).isoformat()
        (evidence / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{report['result']}: Compose verification; evidence={evidence}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
