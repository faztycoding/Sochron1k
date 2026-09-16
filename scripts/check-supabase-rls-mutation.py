"""Prove the local all-table RLS fixture detects an owner-policy regression.

The mutation, fixture data and helpers exist only in one rolled-back transaction.
This never invokes a hosted CLI operation or changes committed migrations.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "supabase/tests/scn_002_all_table_access.test.sql"
PSQL = [
    "docker",
    "exec",
    "-i",
    "supabase_db_sochron1k",
    "psql",
    "-X",
    "-v",
    "ON_ERROR_STOP=1",
    "-U",
    "postgres",
    "-d",
    "postgres",
    "-At",
]


def sql(statement: str) -> str:
    result = subprocess.run(
        PSQL,
        input=statement,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return result.stdout


def main() -> None:
    if not __debug__:
        raise RuntimeError("Verification requires Python assertions enabled")
    subprocess.run(["bash", "scripts/supabase-local.sh", "guard"], cwd=ROOT, check=True)
    policy_query = """
        select pg_get_expr(polqual, polrelid) from pg_policy
        where polrelid = 'public.audit_events'::regclass
          and polname = 'audit_events_owner_select';
    """
    before = sql(policy_query)
    assert before.strip(), "Expected audit policy is missing"
    source = FIXTURE.read_text()
    anchor = "-- Access assertions (mutation-test insertion point; only within this transaction)."
    assert source.count(anchor) == 1
    assert source.rstrip().endswith("rollback;")
    mutated = source.replace(
        anchor,
        anchor + "\nalter policy audit_events_owner_select on public.audit_events using (true);",
    )
    output = sql(mutated)
    failures = re.findall(r"^not ok .*", output, re.MULTILINE)
    assert len(failures) == 4 and all("audit_events" in line for line in failures), failures
    assert "1..256" in output
    assert sql(policy_query) == before, "Transaction failed to restore original policy"
    restored = sql(source)
    assert not re.search(r"^not ok ", restored, re.MULTILINE), "Restored fixture failed"
    assert len(re.findall(r"^ok \d+ -", restored, re.MULTILINE)) == 256
    assert sql(policy_query) == before
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    print(f"Source revision: {revision}")
    print(f"Working tree dirty: {dirty}")
    print(f"Fixture SHA256: {hashlib.sha256(source.encode()).hexdigest()}")
    print(
        "PASS mutation: 4 audit_events isolation failures detected; "
        "policy restored; 256 checks pass"
    )


if __name__ == "__main__":
    main()
