"""Run affected Python tests against an existing local candidate's linked SQLite."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: check-container-python.py LOCAL_CANDIDATE_IMAGE")
    candidate = sys.argv[1]

    def run(args, timeout=60):
        return subprocess.check_output(args, cwd=ROOT, text=True, timeout=timeout).strip()

    endpoint = os.environ.get("DOCKER_HOST", "")
    if not endpoint or os.environ.get("DOCKER_CONTEXT"):
        endpoint = json.loads(run(["docker", "context", "inspect"]))[0]["Endpoints"]["docker"][
            "Host"
        ]
    if not endpoint.startswith("unix://"):
        raise SystemExit("local Unix Docker endpoint required")
    image_id = json.loads(run(["docker", "image", "inspect", candidate]))[0]["Id"]
    uv = os.environ.get("SOCHRON_UV") or shutil.which("uv")
    if not uv or not run([uv, "--version"]).startswith("uv 0.12.15 "):
        raise SystemExit("uv 0.12.15 required; set SOCHRON_UV")
    name = "sochron-python-" + uuid4().hex[:12]
    output = ROOT / "output/container-python" / name
    output.mkdir(parents=True)
    context = output / "context"
    context.mkdir()
    report = dict(
        source_revision=run(["git", "rev-parse", "HEAD"]),
        dirty=bool(run(["git", "status", "--porcelain"])),
        candidate=candidate,
        image_id=image_id,
        started_at=datetime.now(UTC).isoformat(),
        result="FAIL",
    )
    boundary = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--user",
        "10001:10001",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--entrypoint",
        "python",
    ]
    try:
        report["sqlite"] = json.loads(run([*boundary, candidate, "/opt/sochron/check-sqlite.py"]))
        python = run([*boundary, candidate, "-c", "import sys; print(sys.executable)"])
        if python not in {"/app/.venv/bin/python", "/opt/worker/bin/python"}:
            raise RuntimeError("unexpected runtime interpreter")
        run(
            [
                uv,
                "export",
                "--locked",
                "--no-emit-project",
                "--no-header",
                "--output-file",
                str(context / "requirements.txt"),
            ]
        )
        for directory in (
            "tests",
            "services/api/src",
            "services/worker/src",
            "services/runtime",
            "mt5/ea",
        ):
            shutil.copytree(
                ROOT / directory,
                context / directory,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        for file in (
            "pyproject.toml",
            "services/api/Dockerfile",
            "services/worker/Dockerfile",
            "scripts/build-container-sqlite.py",
            "scripts/check-container-sqlite.py",
            "scripts/check-execution-inventory-source.py",
            "scripts/check-no-secrets.py",
        ):
            target = context / file
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / file, target)
        report["input_sha256"] = {
            str(p.relative_to(context)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(context.rglob("*"))
            if p.is_file()
        }
        report["verifier_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (context / "Dockerfile").write_text(
            f"FROM {candidate}\nUSER root\nCOPY requirements.txt /fixture/requirements.txt\n"
            f"RUN /usr/local/bin/python -m pip --python {python} install --require-hashes "
            "--only-binary :all: --no-cache-dir -r /fixture/requirements.txt\n"
            'COPY . /suite\nWORKDIR /suite\nUSER 10001:10001\nENTRYPOINT ["python"]\n'
        )
        with (output / "build.log").open("w") as log:
            subprocess.run(
                ["docker", "build", "-t", name, str(context)],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=300,
            )
        # Do not silently test a different candidate if its mutable tag moved during build.
        if json.loads(run(["docker", "image", "inspect", candidate]))[0]["Id"] != image_id:
            raise RuntimeError("candidate image changed")
        report["test_image_id"] = json.loads(run(["docker", "image", "inspect", name]))[0]["Id"]
        if json.loads(run([*boundary, name, "/opt/sochron/check-sqlite.py"])) != report["sqlite"]:
            raise RuntimeError("test environment changed SQLite")
        command = [
            *boundary[:-2],
            "--tmpfs",
            "/tmp:size=128m,mode=1777",
            "-e",
            "HYPOTHESIS_STORAGE_DIRECTORY=/tmp/hypothesis",
            "--entrypoint",
            "python",
            name,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--ignore=tests/test_mt5_source.py",
        ]
        with (output / "pytest.log").open("w") as log:
            result = subprocess.run(
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180
            )
        report["pytest_exit_code"] = result.returncode
        report["pytest_summary"] = (output / "pytest.log").read_text().splitlines()[-1]
        if result.returncode != 0:
            raise RuntimeError("container tests failed")
        report["result"] = "PASS"
    except Exception as error:
        report["failure_type"] = type(error).__name__
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(report["result"] + " " + str(output / "result.json"))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
