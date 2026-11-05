"""Approved ENV-002 v1.6 contract tests for the sentinel that AC-02's sentinel item searches for
(docs/contracts/ENV-002-research-host-separation.md, "scripts/env/make_sentinel.py"); run pytest from
the repository root.

The sentinel item can only find a copy when the committed values (name, size, sha256, token) describe
the file make_sentinel.py wrote, so these tests run the script as the owner does on the VPS: in an
empty vault folder (here under tmp_path), with no arguments, by `python -I -B scripts/env/make_sentinel.py`.
-I keeps src and PYTHONPATH off sys.path, so a script that imports sochron fails here as the contract
forbids. Nothing else of the repository is used.

Conventions the contract leaves to these tests (also in docs/handoff/ENV-002.md):
1. Standard output, stripped, is exactly one JSON object with the keys name, size, sha256, token,
   vault_path and created_utc: the text the owner copies. size is an int; vault_path is an absolute
   path of the vault folder or of the file written in it (either one exists only on the VPS);
   created_utc is a non-empty str.
2. The script writes exactly one file in the folder it runs in, SENTINEL-ENV002-<token[:8]>.json,
   whose JSON has exactly the keys synthetic (true), purpose ("ENV-002 sentinel"), token (32
   lower-case hex) and bars: 60 objects with exactly time_utc, open, high, low, close and spread.
   time_utc is "%Y-%m-%dT%H:%M:%SZ", from 2025-01-02T00:00:00Z one minute apart; the four prices
   are str that read as finite Decimals.
3. The token comes from secrets.token_hex: the script refers to secrets and token_hex, and two runs
   give different tokens.
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "env" / "make_sentinel.py"
MISSING = "AC-02: make_sentinel not implemented (scripts/env/make_sentinel.py is missing)"
VALUE_KEYS = {"name", "size", "sha256", "token", "vault_path", "created_utc"}
FILE_KEYS = {"synthetic", "purpose", "token", "bars"}
BAR_KEYS = {"time_utc", "open", "high", "low", "close", "spread"}
HEX32 = re.compile(r"[0-9a-f]{32}")
HEX64 = re.compile(r"[0-9a-f]{64}")
FIRST_BAR = datetime(2025, 1, 2, tzinfo=UTC)


def _script():
    if not SCRIPT.is_file():
        pytest.fail(MISSING, pytrace=False)
    return SCRIPT


def _run(vault):
    """Run the script in vault as the owner does; returns (completed process, files written)."""
    script = _script()
    vault.mkdir(parents=True, exist_ok=True)
    before = set(os.listdir(vault))
    completed = subprocess.run([sys.executable, "-I", "-B", str(script)], cwd=vault, capture_output=True,
                               timeout=120, check=False)
    return completed, sorted(set(os.listdir(vault)) - before)


def _real(path):
    return os.path.normcase(os.path.realpath(path))


def _decimal(text):
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def test_ac02_make_sentinel_imports_only_the_standard_library():
    tree = ast.parse(_script().read_text(encoding="utf-8"), filename=str(SCRIPT))
    imported, wrong = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported.append("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            if name in ("__import__", "import_module"):
                wrong.append(f"line {node.lineno}: dynamic import")
    wrong += [f"import {name}" for name in imported
              if name.startswith(".") or name.split(".")[0] not in sys.stdlib_module_names]
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    names |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    if not any(name.split(".")[0] == "secrets" for name in imported) or "token_hex" not in names:
        wrong.append("the token does not come from secrets.token_hex")
    assert not wrong, "AC-02 make_sentinel imports:\n" + "\n".join(wrong)


def test_ac02_make_sentinel_writes_one_synthetic_file_and_prints_its_values(tmp_path):
    vault = tmp_path / "vps" / "vault"
    completed, written = _run(vault)
    assert completed.returncode == 0, f"AC-02: make_sentinel exited {completed.returncode}: {completed.stderr!r}"
    assert len(written) == 1, f"AC-02: make_sentinel wrote {written}, expected one file"
    path = vault / written[0]
    data = path.read_bytes()
    try:
        values = json.loads(completed.stdout.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        pytest.fail(f"AC-02: standard output is not one JSON object ({error}): {completed.stdout!r}", pytrace=False)
    document = json.loads(data.decode("utf-8"))
    wrong = []
    if not isinstance(values, dict) or set(values) != VALUE_KEYS:
        pytest.fail(f"AC-02: printed keys {sorted(values) if isinstance(values, dict) else values!r}, "
                    f"expected {sorted(VALUE_KEYS)}", pytrace=False)
    token = document.get("token") if isinstance(document, dict) else None
    if not isinstance(token, str) or not HEX32.fullmatch(token):
        pytest.fail(f"AC-02: the file's token {token!r} is not 32 lower-case hex", pytrace=False)
    if written[0] != f"SENTINEL-ENV002-{token[:8]}.json":
        wrong.append(f"file name {written[0]!r}, expected SENTINEL-ENV002-{token[:8]}.json")
    checks = (
        ("name", values["name"] == written[0]),
        ("size", type(values["size"]) is int and values["size"] == len(data)),
        ("sha256", isinstance(values["sha256"], str) and HEX64.fullmatch(values["sha256"]) is not None
         and values["sha256"] == hashlib.sha256(data).hexdigest()),
        ("token", values["token"] == token),
        ("vault_path", isinstance(values["vault_path"], str) and os.path.isabs(values["vault_path"])
         and _real(values["vault_path"]) in {_real(vault), _real(path)}),
        ("created_utc", isinstance(values["created_utc"], str) and values["created_utc"] != ""),
    )
    wrong += [f"printed {key} {values[key]!r} does not describe the written file" for key, ok in checks if not ok]
    if set(document) != FILE_KEYS:
        wrong.append(f"file keys {sorted(document)}, expected {sorted(FILE_KEYS)}")
    if document.get("synthetic") is not True:
        wrong.append(f"synthetic is {document.get('synthetic')!r}, expected true")
    if document.get("purpose") != "ENV-002 sentinel":
        wrong.append(f"purpose is {document.get('purpose')!r}, expected 'ENV-002 sentinel'")
    bars = document.get("bars")
    if not isinstance(bars, list) or len(bars) != 60:
        wrong.append(f"bars is {type(bars).__name__} of {len(bars) if isinstance(bars, list) else '?'}, expected 60")
        bars = []
    for index, bar in enumerate(bars):
        expected = (FIRST_BAR + timedelta(minutes=index)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not isinstance(bar, dict) or set(bar) != BAR_KEYS:
            wrong.append(f"bar {index}: keys {sorted(bar) if isinstance(bar, dict) else bar!r}, expected {sorted(BAR_KEYS)}")
            continue
        if bar["time_utc"] != expected:
            wrong.append(f"bar {index}: time_utc {bar['time_utc']!r}, expected {expected}")
        for key in ("open", "high", "low", "close"):
            if not isinstance(bar[key], str) or _decimal(bar[key]) is None:
                wrong.append(f"bar {index}: {key} {bar[key]!r} is not a price as text")
    assert not wrong, "AC-02 make_sentinel:\n" + "\n".join(wrong)


def test_ac02_make_sentinel_tokens_differ_between_runs(tmp_path):
    tokens = []
    for name in ("first", "second"):
        completed, written = _run(tmp_path / name)
        assert completed.returncode == 0 and len(written) == 1, f"AC-02: run {name}: {completed.stderr!r}, {written}"
        tokens.append(json.loads((tmp_path / name / written[0]).read_bytes().decode("utf-8")).get("token"))
    assert tokens[0] != tokens[1], f"AC-02: two runs gave the same token {tokens[0]!r}"
