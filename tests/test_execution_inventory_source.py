from __future__ import annotations

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = runpy.run_path(str(ROOT / "scripts/check-execution-inventory-source.py"))
SOURCE = ROOT / GUARD["SOURCE"]


def test_scn024_ac01_ac07_source_is_read_only_default_off_and_secret_scanned():
    source = SOURCE.read_text()
    assert GUARD["findings"](source) == []
    scanner = runpy.run_path(str(ROOT / "scripts/check-no-secrets.py"))
    assert SOURCE in scanner["candidate_files"]()


@pytest.mark.parametrize("identifier", sorted(GUARD["FORBIDDEN"]))
def test_scn024_ac07_guard_detects_mutation_or_authority_expansion(identifier):
    source = SOURCE.read_text()
    assert GUARD["findings"](source + f"\nvoid injected() {{ {identifier}(); }}")


@pytest.mark.parametrize("identifier", sorted(GUARD["REQUIRED"]))
def test_scn024_ac03_guard_detects_removed_inventory_boundary(identifier):
    source = SOURCE.read_text()
    changed = source.replace(identifier, "Removed" + identifier)
    assert changed != source
    assert GUARD["findings"](changed)


def test_scn024_ac01_ac06_guard_detects_config_transport_and_file_expansion():
    source = SOURCE.read_text()
    assert GUARD["findings"](
        source.replace(
            "EnableReadOnlyExecutionInventory=false",
            "EnableReadOnlyExecutionInventory=true",
        )
    )
    assert GUARD["findings"](source + '\n#import "external.dll"')
    assert GUARD["findings"](source + "\n#include <Trade/Trade.mqh>")
    assert GUARD["findings"](source + '\ninput string PrivateToken="";')
    assert GUARD["findings"](source + '\ninput string ApiUrl="";')
    assert GUARD["findings"](source + '\nvoid injected(){ FileOpen("x",FILE_WRITE); }')
    assert GUARD["findings"](source + '\nstring route="/commands/next";')


def test_scn024_ac04_source_keeps_empty_arrays_conditional_and_policy_only():
    source = SOURCE.read_text()
    assert "sample.complete=(after.owned_orders==0 && after.owned_positions==0);" in source
    assert "sample.foreign_orders=after.foreign_orders;" in source
    assert "sample.foreign_positions=after.foreign_positions;" in source
    assert "before.fingerprint!=after.fingerprint" in source
    assert "sample.algo_trading_allowed=false" in source
