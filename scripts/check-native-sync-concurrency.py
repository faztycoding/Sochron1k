"""SCN-008 forward migration and real concurrent SQL writers in a disposable DB.

Uses the guarded local Supabase Postgres engine/roles, never a URL or credentials.
Only this invocation's randomly named database is created/dropped. Minimal auth
tables/functions stand in for Supabase Auth here; the normal pgTAP suite separately
exercises the full local Supabase schema and roles. This is not HTTP/worker evidence.
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
]
OWNER = "10000000-0000-0000-0000-000000000001"
BINDING = {
    "identity": {
        "executor_id": "fixture-executor",
        "account_ref": "fixture-account",
        "server": "Synthetic-Demo",
        "currency": "USD",
        "margin_mode": "retail_hedging",
        "symbol": "XAUUSD.fixture",
    },
    "offset": 0,
    "chart": {"offset_valid_from_server_s": 1700000000, "offset_valid_until_server_s": 2000000000},
}
ROW = {
    "available_at": "2026-09-16T00:02:00Z",
    "bar": {
        "time_server_s": 1789516800,
        "open_time_utc": "2026-09-16T00:00:00Z",
        "closed": True,
        "open": "9999999999999.1234567890",
        "high": "9999999999999.1234567890",
        "low": "9999999999999.1234567890",
        "close": "9999999999999.1234567890",
        "tick_volume": 9007199254740991,
        "spread_points": 20,
        "confirmed_by_server_s": 1789516860,
        "first_receipt": 7,
        "first_received_at": "2026-09-16T00:01:01.000002Z",
        "source_observed_at": "2026-09-16T00:01:01.000001Z",
        "terminal_build": 5430,
        "price_basis": "bid",
        "digits": 10,
        "tick_size": "0.0000000001",
        "broker_utc_offset_seconds": 0,
    },
}


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
    return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"


def send(archive: str, row: dict, binding: dict) -> str:
    return (
        f"select public.sochron_store_native_m1('{OWNER}','{archive}',"
        f"{literal(binding)},{literal([row])});"
    )


def race(database: str, *, existing_archive: bool, conflict: str | None) -> None:
    archive = str(uuid.uuid4())
    label = f"{'bar' if existing_archive else 'archive'}-{conflict or 'duplicate'}"
    if existing_archive:
        sql(
            database,
            f"set role service_role; insert into public.native_bar_archives "
            f"(owner_id,archive_id,binding) values('{OWNER}','{archive}',{literal(BINDING)});",
        )
    alternate_row, alternate_binding = copy.deepcopy(ROW), copy.deepcopy(BINDING)
    if conflict == "payload":
        alternate_row["bar"]["first_receipt"] = 8
    elif conflict == "binding":
        alternate_binding["identity"]["server"] = "Changed-Demo"
    waiter_name = "scn008_wait_" + uuid.uuid4().hex
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
            + send(archive, ROW, BINDING)
            + "\n"
        )
        first.stdin.flush()
        ready: queue.Queue[str] = queue.Queue()
        threading.Thread(target=lambda: ready.put(first.stdout.readline()), daemon=True).start()
        result = json.loads(ready.get(timeout=10))
        assert result == {"archive_id": archive, "verified_count": 1}, result
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
            + send(archive, alternate_row, alternate_binding)
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
            assert second.poll() is None, "Second writer exited before overlapping first"
            if time.monotonic() >= deadline:
                raise AssertionError("No actual database lock overlap was observed")
            time.sleep(0.05)
        first.stdin.write("commit;\n")
        first.stdin.close()
        first.stdin = None
        _, first_errors = first.communicate(timeout=10)
        assert first.returncode == 0, first_errors
        output, errors = second.communicate(timeout=10)
        if conflict:
            expected = "NATIVE_BAR_CONFLICT" if conflict == "payload" else "NATIVE_ARCHIVE_CONFLICT"
            assert second.returncode != 0 and expected in errors, (output, errors)
        else:
            assert second.returncode == 0, errors
            assert json.loads(output) == {"archive_id": archive, "verified_count": 1}
        readback = json.loads(
            sql(
                database,
                "set role service_role; "
                f"select public.sochron_read_native_m1('{OWNER}','{archive}',"
                "array[1789516800]::bigint[]);",
            )
        )
        assert readback["binding"] == BINDING and len(readback["rows"]) == 1, readback
        assert readback["rows"][0]["bar"] == ROW["bar"], readback
        assert (
            sql(
                database,
                f"select available_at='2026-09-16T00:02:00Z'::timestamptz "
                f"from public.bars where native_archive_id='{archive}';",
            )
            == "t"
        )
        print(
            f"PASS {label}: observed lock overlap, correct result, independent immutable read-back"
        )
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=20)


def main() -> None:
    if not __debug__:
        raise RuntimeError("Verification requires assertions enabled")
    subprocess.run(["bash", "scripts/supabase-local.sh", "guard"], cwd=ROOT, check=True)
    database = "scn008_verify_" + uuid.uuid4().hex
    created = False
    try:
        sql("postgres", f'create database "{database}" template template0;')
        created = True
        # Deliberately minimal Auth scaffold; no login, JWT, or session claim is made.
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
        for migration in MIGRATIONS[:2]:
            sql(database, "begin;" + migration.read_text() + "commit;")
        sql(
            database,
            f"insert into auth.users values('{OWNER}');"
            + f"""
            set role service_role;
            insert into public.bars(owner_id,feed_id,source_revision,symbol,timeframe,
              event_time,received_at,available_at,open_price,high_price,low_price,close_price,tick_volume)
            values('{OWNER}','legacy','fixture','XAUUSD.fixture','M5',
              '2026-09-16Z','2026-09-16Z','2026-09-16Z',999999999999.12345678,
              999999999999.12345678,999999999999.12345678,999999999999.12345678,
              999999999999.12345678);
        """,
        )
        before = json.loads(
            sql(database, "select to_jsonb(b) from public.bars b;"), parse_float=str
        )
        sql(database, "begin;" + MIGRATIONS[2].read_text() + "commit;")
        after = json.loads(sql(database, "select to_jsonb(b) from public.bars b;"), parse_float=str)
        from decimal import Decimal

        for field, value in before.items():
            if field in ("open_price", "high_price", "low_price", "close_price", "tick_volume"):
                assert Decimal(after[field]) == Decimal(value), field
            else:
                assert after[field] == value, field
        assert all(after[field] is None for field in after.keys() - before.keys())
        sql(
            database,
            "set role service_role; update public.bars set source_revision='legacy-updated' "
            "where native_archive_id is null;",
        )
        print(
            "PASS forward migration: exact legacy decimals, timestamps, keys "
            "and mutable generic rows"
        )
        race(database, existing_archive=False, conflict=None)
        race(database, existing_archive=False, conflict="binding")
        race(database, existing_archive=True, conflict=None)
        race(database, existing_archive=True, conflict="payload")
        assert sql(database, "select count(*) from public.bars;") == "5"
        for source in [*MIGRATIONS, Path(__file__)]:
            print(f"SHA256 {source.name} {hashlib.sha256(source.read_bytes()).hexdigest()}")
    finally:
        if created:
            # Exact random database owned by this invocation; no force/drop cascade.
            sql("postgres", f'drop database "{database}";')
            print("PASS removed only invocation-owned synthetic verification database")


if __name__ == "__main__":
    main()
