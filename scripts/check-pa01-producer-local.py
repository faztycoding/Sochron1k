#!/usr/bin/env python3
"""SCN-022 local PostgREST producer crash/reconciliation evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import secrets
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID, uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / path) for path in ("services/api/src", "services/worker/src", "tests")]
from sochron1k.bar_history import BarHistory  # noqa: E402
from sochron1k.telemetry import TelemetryFrame  # noqa: E402
from sochron_worker.native_source import NativeArchiveSource  # noqa: E402
from sochron_worker.pa01 import PARAMETER_HASH  # noqa: E402
from sochron_worker.pa01_aggregation import aggregate_native_m1  # noqa: E402
from sochron_worker.pa01_envelope import (  # noqa: E402
    PA01PolicyEvidence,
    PA01PolicyObservations,
    PolicyObservation,
)
from test_chart import PERIODS, packet, setup_chart  # noqa: E402
from test_native_source import record_packet  # noqa: E402

ORIGIN = "http://127.0.0.1:54321"
CHECKS: list[str] = []


class VerificationFailure(RuntimeError):
    pass


def require(condition: bool, stage: str) -> None:
    if not condition:
        raise VerificationFailure(stage)


def command(args, *, data=None, timeout=30) -> str:
    result = subprocess.run(
        args, cwd=ROOT, input=data, text=True, capture_output=True, timeout=timeout
    )
    require(result.returncode == 0, "local prerequisite/query failed (details suppressed)")
    return result.stdout.strip()


def sql(query: str) -> str:
    return command(
        [
            "docker",
            "exec",
            "-i",
            "supabase_db_sochron1k",
            "psql",
            "-X",
            "-Atq",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            "postgres",
        ],
        data=query,
    )


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def check(stage: str) -> None:
    CHECKS.append(stage)
    print("PASS " + stage, flush=True)


def source_fixture(directory: Path, code_hash: str):
    source_dir = directory / "source"
    source_dir.mkdir(mode=0o700)
    setup = setup_chart.__wrapped__()
    clock, bridge, store, quote = setup
    now = datetime.now(UTC).replace(microsecond=0)
    clock.advance((now - clock.utc).total_seconds())
    fresh = copy.deepcopy(quote)
    fresh.update(
        sequence=2,
        observed_at=now.isoformat(),
        tick_time_server_msc=int(now.timestamp() * 1000) + 7_200_000,
    )
    bridge.accept(TelemetryFrame.model_validate(fresh))
    archive = BarHistory(source_dir, bridge.settings, store.settings)
    data = packet(setup)
    current = data["bars"][-1]["time_server_s"]
    data["bars"] = [
        {
            "time_server_s": current - (239 - index) * PERIODS["M1"],
            "open": f"{2500 + index / 100:.2f}",
            "high": f"{2500.05 + index / 100:.2f}",
            "low": f"{2499.95 + index / 100:.2f}",
            "close": f"{2500.01 + index / 100:.2f}",
            "tick_volume": 100 + index,
            "spread_points": 20,
        }
        for index in range(240)
    ]
    record_packet(setup, archive, data)
    source = NativeArchiveSource(
        source_dir,
        UUID(archive.archive_id),
        bridge.settings.identity,
        bridge.settings.broker_utc_offset_seconds,
        store.settings,
    )
    rows = source.read_pa01(now)
    require(len(rows) == 239, "native PA01 source fixture")
    aggregation = aggregate_native_m1(rows, cutoff_utc=now)
    require(len(aggregation.m5_bars) >= 2, "complete M5 fixture")
    observations = PA01PolicyObservations(
        quote=PolicyObservation(evidence_id="quote:scn022", observed_at_utc=now),
        market=PolicyObservation(evidence_id="market:scn022", observed_at_utc=now),
        news=PolicyObservation(evidence_id="news:scn022", observed_at_utc=now),
        account=PolicyObservation(evidence_id="account:scn022", observed_at_utc=now),
    )
    evidence = PA01PolicyEvidence(
        cutoff_utc=now,
        symbol=aggregation.symbol,
        feed_id=aggregation.feed_id,
        spread_price=Decimal(str(Decimal(str(fresh["ask"])) - Decimal(str(fresh["bid"])))),
        market_open=True,
        price_stale=False,
        news_blocked=False,
        has_exposure=False,
        has_pending=False,
        observations=observations,
    )
    policy_path = directory / "policy.json"
    policy_path.write_text(evidence.model_dump_json())
    policy_path.chmod(0o600)
    return archive, source, policy_path, code_hash, now


class FaultProxy:
    def __init__(self) -> None:
        self.accepted, self.release = threading.Event(), threading.Event()
        self.stores = 0
        self.statuses: list[tuple[str, int]] = []
        self.errors: list[tuple[object, object]] = []
        self.failed = False
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                try:
                    allowed = (
                        "/rest/v1/rpc/sochron_store_pa01_decision",
                        "/rest/v1/rpc/sochron_read_pa01_decision",
                    )
                    require(self.path in allowed, "proxy path denied")
                    size = int(self.headers.get("Content-Length", "0"))
                    require(0 < size <= 262_144, "proxy request bound")
                    body = self.rfile.read(size)
                    headers = {
                        name: self.headers[name]
                        for name in ("apikey", "Authorization", "Content-Type")
                        if name in self.headers
                    }
                    headers["Accept-Encoding"] = "identity"
                    with httpx.Client(
                        timeout=10, trust_env=False, follow_redirects=False
                    ) as client:
                        upstream = client.post(ORIGIN + self.path, content=body, headers=headers)
                    proxy.statuses.append((self.path, upstream.status_code))
                    if upstream.status_code != 200:
                        try:
                            error = upstream.json()
                            proxy.errors.append((error.get("code"), error.get("message")))
                        except (ValueError, AttributeError):
                            proxy.errors.append(("NON_JSON", "REDACTED"))
                    if self.path == allowed[0] and upstream.status_code == 200:
                        proxy.stores += 1
                        proxy.accepted.set()
                        require(proxy.release.wait(15), "proxy hold deadline")
                        self.close_connection = True
                        return
                    self.send_response(upstream.status_code)
                    self.send_header("Content-Type", upstream.headers.get("content-type", ""))
                    self.send_header("Content-Length", str(len(upstream.content)))
                    self.end_headers()
                    self.wfile.write(upstream.content)
                except Exception:
                    proxy.failed = True
                    self.close_connection = True

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def close(self) -> None:
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def configure(directory, source, policy_path, owner, strategy_id, experiment_id, origin, key, code):
    state = directory / "state"
    state.mkdir(mode=0o700)
    key_path = directory / "service-key"
    key_path.write_text(key)
    key_path.chmod(0o600)
    binding = json.loads(source.binding_json)
    config = directory / "pa01.json"
    config.write_text(
        json.dumps(
            {
                "enabled": True,
                "source_directory": str(source.directory),
                "state_directory": str(state),
                "policy_file": str(policy_path),
                "archive_id": source.archive_id,
                "identity": binding["identity"],
                "offset_seconds": binding["offset"],
                "chart": binding["chart"],
                "owner_id": owner,
                "strategy_version_id": strategy_id,
                "experiment_id": experiment_id,
                "code_hash": code,
                "origin": origin,
                "service_key_file": str(key_path),
            }
        )
    )
    config.chmod(0o600)
    env = {
        **os.environ,
        "SOCHRON_PA01_CONFIG_FILE": str(config),
        "PYTHONPATH": os.pathsep.join(
            str(ROOT / path) for path in ("services/api/src", "services/worker/src")
        ),
    }
    return state, env


def worker(env, action="run", *, expected=0):
    args = [sys.executable, "-m", "sochron_worker.pa01_cli", action]
    if action == "run":
        args.append("--once")
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    require(result.returncode == expected and not result.stderr, "producer command failed")
    output = [json.loads(line) for line in result.stdout.splitlines()]
    require(len(output) == 1, "producer output shape")
    require(
        output[0]["execution_ready"] is False and output[0]["auto_trading_enabled"] is False,
        "producer expanded execution authority",
    )
    return output[0]


def cleanup(owner: str, email: str, client: httpx.Client, admin: dict) -> None:
    require(
        sql(f"select count(*) from public.signals where owner_id={literal(owner)}::uuid;")
        in {"0", "1"},
        "unexpected fixture signal count",
    )
    sql(
        f"""begin; set local statement_timeout='5s';
        set local session_replication_role=replica;
        delete from public.signals where owner_id={literal(owner)}::uuid;
        delete from public.feature_snapshots where owner_id={literal(owner)}::uuid;
        delete from public.experiments where owner_id={literal(owner)}::uuid;
        delete from public.strategy_versions where owner_id={literal(owner)}::uuid;
        delete from public.accounts where owner_id={literal(owner)}::uuid;
        commit;"""
    )
    reply = client.get("/auth/v1/admin/users/" + owner, headers=admin)
    require(reply.status_code == 200 and reply.json().get("email") == email, "fixture owner")
    require(
        client.delete("/auth/v1/admin/users/" + owner, headers=admin).status_code in (200, 204),
        "fixture user cleanup",
    )
    require(sql(f"select count(*) from auth.users where id={literal(owner)}::uuid;") == "0", "leak")


def verify() -> dict:
    command(["bash", "scripts/supabase-local.sh", "guard"])
    require(command(["node", "--version"]) == "v24.21.0", "pinned Node")
    require(
        command(["npm", "exec", "supabase", "--", "--version"]) == "2.117.0",
        "pinned Supabase CLI",
    )
    local = json.loads(command(["npm", "exec", "supabase", "--", "status", "-o", "json"]))
    require(local["API_URL"] == ORIGIN, "guarded local origin")
    admin = {"apikey": local["SECRET_KEY"]}
    code_hash = hashlib.sha256(
        (ROOT / "services/worker/src/sochron_worker/pa01.py").read_bytes()
    ).hexdigest()
    owner = email = None
    proxy = child = None
    with httpx.Client(
        base_url=ORIGIN, timeout=10, trust_env=False, follow_redirects=False
    ) as client:
        try:
            email = "scn022-" + uuid4().hex + "@sochron.test"
            password = secrets.token_urlsafe(32) + "!aA1"
            reply = client.post(
                "/auth/v1/admin/users",
                headers=admin,
                json={"email": email, "password": password, "email_confirm": True},
            )
            require(reply.status_code in (200, 201), "create synthetic owner")
            owner = str(UUID(reply.json()["id"]))
            account_id = int(
                sql(
                    "insert into public.accounts(owner_id,account_ref,server_ref,currency,"
                    "initial_equity,policy_version) values ("
                    f"{literal(owner)}::uuid,'scn022-demo','Synthetic-Demo','USD',10000,'risk-v1') "
                    "returning id;"
                )
            )
            strategy_id = int(
                sql(
                    "insert into public.strategy_versions(owner_id,version_id,code_hash,parameters,"
                    "status,data_cutoff) values ("
                    f"{literal(owner)}::uuid,'PA01-v1',{literal(code_hash)},"
                    "jsonb_build_object('parameter_version','PA01-v1.0.1','parameter_hash',"
                    f"{literal(PARAMETER_HASH)},'aggregation_version','native-pa01-aggregation-v1'),"
                    "'candidate',now()-interval '1 day') returning id;"
                )
            )
            experiment_id = int(
                sql(
                    "insert into public.experiments(owner_id,account_id,strategy_version_id,"
                    "experiment_id,status,initial_equity,policy_version) values ("
                    f"{literal(owner)}::uuid,{account_id},{strategy_id},'scn022-demo','demo',"
                    "10000,'risk-v1') returning id;"
                )
            )
            with tempfile.TemporaryDirectory(prefix="sochron-pa01-local-") as temporary:
                directory = Path(temporary).resolve()
                _, source, policy_path, code, cutoff = source_fixture(directory, code_hash)
                proxy = FaultProxy()
                state, env = configure(
                    directory,
                    source,
                    policy_path,
                    owner,
                    strategy_id,
                    experiment_id,
                    proxy.origin,
                    local["SECRET_KEY"],
                    code,
                )
                require(worker(env, "init")["state"] == "INITIALIZED", "producer init")
                child = subprocess.Popen(
                    [sys.executable, "-m", "sochron_worker.pa01_cli", "run", "--once"],
                    cwd=ROOT,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if not proxy.accepted.wait(10):
                    child_stdout, child_stderr = child.communicate(timeout=5)
                    state = "NO_STATE"
                    with suppress(ValueError, KeyError, IndexError):
                        state = json.loads(child_stdout.splitlines()[-1])["state"]
                    require(
                        False,
                        "committed PA01 store not observed; "
                        f"worker={state}; statuses={proxy.statuses}; errors={proxy.errors}; "
                        f"stderr={bool(child_stderr)}",
                    )
                child.kill()
                child.communicate(timeout=5)
                require(child.returncode == -signal.SIGKILL, "producer crash not observed")
                with sqlite3.connect(state / "pa01.sqlite3") as db:
                    require(
                        db.execute("select state,attempts from decisions").fetchone()
                        == ("UNKNOWN", 1),
                        "UNKNOWN not durable before response",
                    )
                    require(
                        db.execute("select last_formed_at from meta").fetchone()[0] is None,
                        "cursor advanced before read-back",
                    )
                proxy.release.set()
                verified = worker(env)
                require(
                    verified["state"] == "VERIFIED" and proxy.stores == 1,
                    "restart did not read first",
                )
                require(worker(env)["state"] == "IDLE", "verified source repeated")
                counts = sql(
                    "select (select count(*) from public.feature_snapshots where owner_id="
                    f"{literal(owner)}::uuid),(select count(*) from public.signals where owner_id="
                    f"{literal(owner)}::uuid),(select count(*) from public.commands where owner_id="
                    f"{literal(owner)}::uuid),(select count(*) from public.risk_events "
                    "where owner_id="
                    f"{literal(owner)}::uuid),(select count(*) from public.orders where owner_id="
                    f"{literal(owner)}::uuid);"
                )
                require(counts == "1|1|0|0|0", "producer row or no-authority invariant")
                require(not proxy.failed, "fault proxy failure")
                check("real local store committed before SIGKILL; restart read back without resend")
                check("one immutable snapshot/signal and zero command/risk/order rows")
                check("verified cursor prevents another decision for the same closed M5 bar")
                return {
                    "result": "PASS",
                    "revision": command(["git", "rev-parse", "HEAD"]),
                    "dirty": bool(command(["git", "status", "--porcelain"])),
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "python": platform.python_version(),
                    "node": "24.21.0",
                    "supabase_cli": "2.117.0",
                    "source_rows": 239,
                    "policy_cutoff": cutoff.isoformat(),
                    "checks": CHECKS,
                    "hosted": "NOT_RUN",
                    "mt5": "NOT_RUN",
                    "deployment": "NOT_RUN",
                    "auto_trading_enabled": False,
                }
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
            if proxy is not None:
                proxy.close()
            if owner is not None and email is not None:
                cleanup(owner, email, client, admin)


if __name__ == "__main__":
    output = ROOT / "output/pa01-producer" / uuid4().hex
    output.mkdir(parents=True)
    try:
        result = verify()
    except Exception as error:
        result = {
            "result": "FAIL",
            "error_type": type(error).__name__,
            "stage": str(error) if isinstance(error, VerificationFailure) else "details suppressed",
            "checks": CHECKS,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    evidence = output / "result.json"
    evidence.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "evidence": str(evidence)}))
    raise SystemExit(0 if result["result"] == "PASS" else 1)
