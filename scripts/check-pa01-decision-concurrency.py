"""SCN-020 forward migration and overlapping PA01 decision writers.

Uses only the guarded local Supabase Postgres container. Each invocation creates a
random disposable database, applies repository migrations, observes real lock
overlap between independent connections, and drops only that database afterward.
"""

from __future__ import annotations

import copy
import hashlib
import json
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = [
    ROOT / "supabase/migrations/20260916193652_create_initial_data_foundation.sql",
    ROOT / "supabase/migrations/20260916224038_owner_session_validation.sql",
    ROOT / "supabase/migrations/20260917050541_native_m1_receiver.sql",
    ROOT / "supabase/migrations/20260920000837_pa01_decision_receiver.sql",
]
OWNER = "10000000-0000-0000-0000-000000000001"
PARAMETER_HASH = "62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822"


def command(database: str) -> list[str]:
    return [
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
        database,
    ]


def sql(database: str, query: str) -> str:
    return subprocess.run(
        command(database), input=query, text=True, capture_output=True, timeout=60, check=True
    ).stdout.strip()


def literal(value: object) -> str:
    return "'" + json.dumps(value, separators=(",", ":")).replace("'", "''") + "'::jsonb"


def decision(label: str) -> dict[str, object]:
    signal_id = f"decision-{label}"
    fingerprint = hashlib.sha256(signal_id.encode()).hexdigest()
    values = {
        "schema": "sochron.pa01.features.v1",
        "decision_id": signal_id,
        "strategy_version": "PA01-v1",
        "code_hash": "1" * 64,
        "parameter_version": "PA01-v1.0.1",
        "parameter_hash": PARAMETER_HASH,
        "aggregation_version": "native-pa01-aggregation-v1",
        "aggregation_hash": "b" * 64,
        "source_dataset_hash": "c" * 64,
        "dataset_hash": "a" * 64,
        "data_cutoff_utc": "2026-09-19T00:05:02Z",
        "ai_enabled": False,
        "action": "wait",
        "reason_code": "INSUFFICIENT_WARMUP",
        "blocked_reason": None,
        "features": {
            "structure": "incomplete",
            "ema20": None,
            "ema50": None,
            "previous_ema20": None,
            "atr14": None,
            "adx14": None,
            "spread_cap": None,
            "proposed_stop": None,
            "stop_distance_at_close": None,
            "stop_distance_atr": None,
            "latest_swing_highs": [],
            "latest_swing_lows": [],
        },
        "execution_parameters": {
            "next_tick_entry_required": True,
            "max_entry_drift_atr": "0.20",
            "stop_buffer_atr": "0.20",
            "stop_min_atr": "0.50",
            "stop_max_atr": "2.00",
            "target_r": "2",
            "time_exit_m5_bars": 12,
            "signal_expiry_seconds": 30,
            "order_created": False,
            "risk_admitted": False,
        },
    }
    return {
        "protocol": "sochron.pa01.decision.v1",
        "producer_revision": "PA01-v1.0.1/native-pa01-aggregation-v1",
        "decision_fingerprint": fingerprint,
        "snapshot": {
            "snapshot_id": f"snapshot-{label}",
            "feed_id": "mt5-copyrates:80000000-0000-4000-8000-000000000001",
            "symbol": "XAUUSD.fixture",
            "timeframe": "M5",
            "event_time": "2026-09-19T00:05:00Z",
            "received_at": "2026-09-19T00:05:02Z",
            "available_at": "2026-09-19T00:05:02Z",
            "dataset_hash": "a" * 64,
            "values": values,
        },
        "signal": {
            "signal_id": signal_id,
            "setup_id": f"setup-{label}",
            "action": "wait",
            "formed_at": "2026-09-19T00:05:00Z",
            "confirmed_at": "2026-09-19T00:05:02Z",
            "expires_at": "2026-09-19T00:05:32Z",
            "evidence_ids": ["native-m5:evidence-1", "native-h1:evidence-2"],
            "blocked_reason": None,
        },
    }


def send(payload: dict[str, object]) -> str:
    return f"select public.sochron_store_pa01_decision('{OWNER}',1,1,{literal(payload)});"


def read(signal_id: str) -> str:
    return f"select public.sochron_read_pa01_decision('{OWNER}','{signal_id}');"


def race(database: str, label: str, *, changed: bool) -> None:
    original = decision(label)
    alternate = copy.deepcopy(original)
    if changed:
        alternate_signal = alternate["signal"]
        assert isinstance(alternate_signal, dict)
        alternate_signal["setup_id"] = f"setup-{label}-changed"
    waiter_name = "scn020_wait_" + uuid.uuid4().hex
    first = subprocess.Popen(
        command(database),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    second = None
    try:
        assert first.stdin is not None and first.stdout is not None
        first.stdin.write(
            "begin; set local statement_timeout='15s'; set local role service_role;"
            + send(original)
            + "\n"
        )
        first.stdin.flush()
        ready: queue.Queue[str] = queue.Queue()
        threading.Thread(target=lambda: ready.put(first.stdout.readline()), daemon=True).start()
        first_result = json.loads(ready.get(timeout=10))
        assert first_result["found"] is True, first_result

        second = subprocess.Popen(
            command(database),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert second.stdin is not None
        second.stdin.write(
            f"set application_name='{waiter_name}'; begin; "
            "set local statement_timeout='15s'; set local role service_role;"
            + send(alternate)
            + "commit;\n"
        )
        second.stdin.close()
        second.stdin = None
        deadline = time.monotonic() + 10
        while (
            sql(
                database,
                "select count(*) from pg_stat_activity "
                f"where datname='{database}' and application_name='{waiter_name}' "
                "and wait_event_type='Lock';",
            )
            != "1"
        ):
            assert second.poll() is None, "Second writer exited before lock overlap"
            if time.monotonic() >= deadline:
                raise AssertionError("No actual PA01 writer lock overlap was observed")
            time.sleep(0.05)

        first.stdin.write("commit;\n")
        first.stdin.close()
        first.stdin = None
        _, first_errors = first.communicate(timeout=10)
        assert first.returncode == 0, first_errors
        output, errors = second.communicate(timeout=10)
        if changed:
            assert second.returncode != 0 and "PA01_DECISION_CONFLICT" in errors, (
                output,
                errors,
            )
        else:
            assert second.returncode == 0, errors
            assert json.loads(output)["found"] is True

        stored = json.loads(sql(database, "set role service_role; " + read(f"decision-{label}")))
        assert stored["found"] is True
        assert stored["signal"]["setup_id"] == f"setup-{label}"
        assert (
            sql(
                database,
                "select (select count(*) from public.feature_snapshots "
                f"where snapshot_id='snapshot-{label}')::text || ':' || "
                "(select count(*) from public.signals "
                f"where signal_id='decision-{label}')::text;",
            )
            == "1:1"
        )
        outcome = "named conflict" if changed else "matching convergence"
        print(f"PASS concurrent {outcome}: lock overlap, one linked pair, independent read-back")
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=20)


def main() -> None:
    if not __debug__:
        raise RuntimeError("Verification requires assertions enabled")
    subprocess.run(["bash", "scripts/supabase-local.sh", "guard"], cwd=ROOT, check=True)
    database = "scn020_verify_" + uuid.uuid4().hex
    created = False
    try:
        sql("postgres", f'create database "{database}" template template0;')
        created = True
        sql(
            database,
            """
            create schema auth;
            create table auth.users(id uuid primary key);
            create table auth.sessions(id uuid primary key, user_id uuid, not_after timestamptz);
            create function auth.uid() returns uuid language sql stable as
              $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
            grant usage on schema auth, public to authenticated, service_role;
            """,
        )
        for migration in MIGRATIONS[:3]:
            sql(database, "begin;" + migration.read_text() + "commit;")
        sql(
            database,
            f"""
            insert into auth.users values('{OWNER}');
            insert into public.accounts(
              owner_id,account_ref,server_ref,currency,initial_equity,policy_version)
              values('{OWNER}','fixture-account','Synthetic-Demo','USD',10000,'risk-v1');
            insert into public.strategy_versions(
              owner_id,version_id,code_hash,parameters,status,data_cutoff)
              values('{OWNER}','PA01-v1',repeat('1',64),jsonb_build_object(
                'parameter_version','PA01-v1.0.1','parameter_hash','{PARAMETER_HASH}',
                'aggregation_version','native-pa01-aggregation-v1'),
                'active','2026-01-01T00:00:00Z');
            insert into public.experiments(owner_id,account_id,strategy_version_id,experiment_id,
              status,initial_equity,policy_version)
              values('{OWNER}',1,1,'fixture-experiment','demo',10000,'risk-v1');
            insert into public.feature_snapshots(owner_id,strategy_version_id,snapshot_id,feed_id,
              symbol,timeframe,event_time,received_at,available_at,values,dataset_hash)
              values('{OWNER}',1,'legacy-snapshot','legacy-feed','XAUUSD.fixture','M5',
                '2026-09-18T00:00:00Z','2026-09-18T00:00:00Z','2026-09-18T00:00:00Z',
                '{{}}',repeat('f',64));
            insert into public.signals(
              owner_id,experiment_id,strategy_version_id,signal_id,setup_id,action,
              formed_at,confirmed_at,expires_at,evidence_ids)
              values('{OWNER}',1,1,'legacy-signal','legacy-setup','wait',
                '2026-09-18T00:00:00Z','2026-09-18T00:00:00Z','2026-09-18T00:01:00Z','[]');
            """,
        )
        before_snapshot = json.loads(
            sql(database, "select to_jsonb(row) from public.feature_snapshots row;")
        )
        before_signal = json.loads(sql(database, "select to_jsonb(row) from public.signals row;"))
        sql(database, "begin;" + MIGRATIONS[3].read_text() + "commit;")
        after_snapshot = json.loads(
            sql(database, "select to_jsonb(row) from public.feature_snapshots row;")
        )
        after_signal = json.loads(sql(database, "select to_jsonb(row) from public.signals row;"))
        assert all(after_snapshot[key] == value for key, value in before_snapshot.items())
        assert all(after_signal[key] == value for key, value in before_signal.items())
        assert after_snapshot["producer_revision"] is None
        assert after_snapshot["decision_fingerprint"] is None
        assert after_signal["feature_snapshot_id"] is None
        assert after_signal["producer_revision"] is None
        assert after_signal["decision_fingerprint"] is None
        sql(
            database,
            "set role service_role; update public.feature_snapshots set feed_id='legacy-updated';"
            "update public.signals set setup_id='legacy-updated';"
            "delete from public.signals where signal_id='legacy-signal';"
            "delete from public.feature_snapshots where snapshot_id='legacy-snapshot';",
        )
        print("PASS forward migration: legacy rows unchanged and legacy-only CRUD preserved")

        race(database, "race-match", changed=False)
        race(database, "race-conflict", changed=True)

        lost = decision("lost-response")
        sql(database, "set role service_role; " + send(lost))  # Deliberately discard response.
        reconciled = json.loads(
            sql(database, "set role service_role; " + read("decision-lost-response"))
        )
        assert reconciled["found"] is True
        sql(database, "set role service_role; " + send(lost))
        assert (
            sql(
                database,
                "select (select count(*) from public.feature_snapshots "
                "where producer_revision is not null)::text || ':' || "
                "(select count(*) from public.signals "
                "where producer_revision is not null)::text;",
            )
            == "3:3"
        )
        assert sql(database, "select count(*) from public.commands;") == "0"
        assert sql(database, "select count(*) from public.risk_events;") == "0"
        print("PASS committed response loss: read-back found exact pair and retry stayed singular")

        for source in [*MIGRATIONS, Path(__file__)]:
            print(f"SHA256 {source.name} {hashlib.sha256(source.read_bytes()).hexdigest()}")
    finally:
        if created:
            sql("postgres", f'drop database "{database}";')
            print("PASS removed only invocation-owned synthetic verification database")


if __name__ == "__main__":
    main()
