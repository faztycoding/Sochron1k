"""SCN-029 forward migration and overlapping evaluation writers.

Uses only the guarded local Supabase Postgres container. Each invocation creates a
random disposable database, applies repository migrations, observes a real lock
overlap between independent sessions, and drops only that database afterward.
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
MIGRATIONS = sorted((ROOT / "supabase/migrations").glob("*.sql"))
OWNER = "39000000-0000-4000-8000-000000000001"


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
    reply = subprocess.run(
        command(database), input=query, text=True, capture_output=True, timeout=60
    )
    if reply.returncode:
        raise AssertionError(reply.stderr.strip())
    return reply.stdout.strip()


def literal(value: object) -> str:
    return "'" + json.dumps(value, separators=(",", ":")).replace("'", "''") + "'::jsonb"


def envelope(label: str) -> dict[str, object]:
    fingerprint = hashlib.sha256(label.encode()).hexdigest()
    dataset_hash = hashlib.sha256(f"{label}:dataset".encode()).hexdigest()
    return {
        "protocol": "sochron.research-evaluation-envelope.v1",
        "producer_revision": "SCN-029/research-evaluation-v1.0.0",
        "evaluation_fingerprint": fingerprint,
        "dataset_hash": dataset_hash,
        "strategy_code_hash": "a" * 64,
        "split": "walk_forward",
        "data_cutoff_utc": "2026-01-03T00:00:00.000000Z",
        "metrics": {
            "sample_size": 3,
            "wins": 1,
            "losses": 1,
            "breakeven": 1,
            "net_return_pct": "1",
            "expectancy_r": "0.33333333",
            "expectancy_r_ci95_low": "-0.66666667",
            "expectancy_r_ci95_high": "1.33333333",
            "max_drawdown_pct": "1.96078431",
            "profit_factor": "2",
        },
        "cost_assumptions": {
            "spread_points": "1",
            "slippage_points": "1",
            "commission_per_lot": "2",
            "swap_included": True,
            "operating_cost_per_trade": "1",
            "currency": "USD",
        },
        "evidence_manifest": {
            "manifest_protocol": "sochron.research-evaluation-manifest.v1",
            "bundle_hash": dataset_hash,
            "strategy_version": "PA01-v1",
            "strategy_code_hash": "a" * 64,
            "evaluation_window": {
                "start_utc": "2026-01-02T00:00:00.000000Z",
                "end_utc": "2026-01-03T00:00:00.000000Z",
                "prior_development_cutoff_utc": "2026-01-01T00:00:00.000000Z",
                "embargo_seconds": 3600,
            },
            "bootstrap": {"seed": 17, "samples": 1000, "block_length": 2},
            "record_counts": {
                "closed_trade": 3,
                "wait": 1,
                "rejected": 1,
                "counterfactual": 1,
                "ambiguous": 1,
            },
            "equity_basis": "mark_to_market_including_open_exposure",
            "cost_currency": "USD",
        },
    }


def send(payload: dict[str, object]) -> str:
    return (
        f"select public.sochron_store_research_evaluation('{OWNER}',1,1,"
        f"{literal(payload)});"
    )


def read(fingerprint: str) -> str:
    return (
        f"select public.sochron_read_research_evaluation('{OWNER}','{fingerprint}');"
    )


def race(database: str, label: str, *, changed: bool) -> None:
    original = envelope(label)
    alternate = copy.deepcopy(original)
    if changed:
        alternate["evaluation_fingerprint"] = hashlib.sha256(
            f"{label}:changed".encode()
        ).hexdigest()
    waiter_name = "scn029_wait_" + uuid.uuid4().hex
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
        assert json.loads(ready.get(timeout=10))["found"] is True

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
            assert second.poll() is None, "second writer exited before lock overlap"
            if time.monotonic() >= deadline:
                raise AssertionError("no actual evaluation writer lock overlap was observed")
            time.sleep(0.05)

        first.stdin.write("commit;\n")
        first.stdin.close()
        first.stdin = None
        _, first_errors = first.communicate(timeout=10)
        assert first.returncode == 0, first_errors
        output, errors = second.communicate(timeout=10)
        if changed:
            assert second.returncode != 0 and "RESEARCH_EVALUATION_CONFLICT" in errors
        else:
            assert second.returncode == 0, errors
            assert json.loads(output)["found"] is True

        stored = json.loads(
            sql(database, "set role service_role; " + read(original["evaluation_fingerprint"]))
        )
        assert stored["found"] is True and stored["evaluation"] == original
        assert (
            sql(
                database,
                "select count(*) from public.evaluations "
                f"where dataset_hash='{original['dataset_hash']}';",
            )
            == "1"
        )
        outcome = "named conflict" if changed else "matching convergence"
        print(f"PASS concurrent {outcome}: lock overlap, one row, exact read-back")
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=20)


def main() -> None:
    if not __debug__:
        raise RuntimeError("verification requires assertions enabled")
    subprocess.run(["bash", "scripts/supabase-local.sh", "guard"], cwd=ROOT, check=True)
    assert MIGRATIONS[-1].name == "20260920044437_reproducible_research_evaluation.sql"
    database = "scn029_verify_" + uuid.uuid4().hex
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
        for migration in MIGRATIONS[:-1]:
            sql(database, "begin;" + migration.read_text() + "commit;")
        sql(
            database,
            f"""
            insert into auth.users values('{OWNER}');
            insert into public.accounts(
              owner_id,account_ref,server_ref,currency,initial_equity,policy_version)
              values('{OWNER}','fixture-account','Synthetic-Demo','USD',1000,'risk-v1');
            insert into public.strategy_versions(
              owner_id,version_id,code_hash,parameters,status,data_cutoff)
              values('{OWNER}','PA01-v1',repeat('a',64),'{{}}','candidate',
                '2026-01-01T00:00:00Z');
            insert into public.experiments(
              owner_id,account_id,strategy_version_id,experiment_id,status,
              initial_equity,policy_version)
              values('{OWNER}',1,1,'fixture-experiment','shadow',1000,'risk-v1');
            insert into public.evaluations(
              owner_id,strategy_version_id,experiment_id,dataset_hash,split,metrics,
              cost_assumptions,data_cutoff)
              values('{OWNER}',1,1,repeat('9',64),'train','{{}}','{{}}',
                '2026-01-01T00:00:00Z');
            """,
        )
        before = json.loads(sql(database, "select to_jsonb(row) from public.evaluations row;"))
        sql(database, "begin;" + MIGRATIONS[-1].read_text() + "commit;")
        after = json.loads(sql(database, "select to_jsonb(row) from public.evaluations row;"))
        assert all(after[key] == value for key, value in before.items())
        assert all(
            after[key] is None
            for key in (
                "producer_revision",
                "evaluation_protocol",
                "evaluation_fingerprint",
                "evidence_manifest",
            )
        )
        sql(
            database,
            "set role service_role; update public.evaluations set metrics='{\"legacy\":true}' "
            "where producer_revision is null;",
        )
        print("PASS forward migration: legacy evaluation unchanged and legacy CRUD preserved")

        race(database, "race-match", changed=False)
        race(database, "race-conflict", changed=True)

        lost = envelope("lost-response")
        sql(database, "set role service_role; " + send(lost))
        reconciled = json.loads(
            sql(database, "set role service_role; " + read(lost["evaluation_fingerprint"]))
        )
        assert reconciled["found"] is True and reconciled["evaluation"] == lost
        sql(database, "set role service_role; " + send(lost))
        assert sql(database, "select count(*) from public.commands;") == "0"
        assert sql(database, "select count(*) from public.risk_events;") == "0"
        print("PASS committed response loss: exact read-back and replay stayed singular")

        for source in [*MIGRATIONS, Path(__file__)]:
            print(f"SHA256 {source.name} {hashlib.sha256(source.read_bytes()).hexdigest()}")
    finally:
        if created:
            sql("postgres", f'drop database "{database}";')
            print("PASS removed only invocation-owned synthetic verification database")


if __name__ == "__main__":
    main()
