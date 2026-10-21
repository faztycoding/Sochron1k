"""Approved CORE-002 v1.2 contract tests; run pytest from the repository root."""

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import date
from decimal import Decimal, Inexact, ROUND_UP, Rounded, getcontext, localcontext
from importlib import import_module
from pathlib import Path
from runpy import run_path
from types import MappingProxyType

import pytest


def _api(monkeypatch, ac, *names):
    """Missing implementation fails each AC without breaking collection."""
    monkeypatch.syspath_prepend(str(Path.cwd() / "src"))
    try:
        module = import_module("sochron.costs")
    except ImportError as error:
        pytest.fail(f"{ac}: sochron.costs not implemented ({error})", pytrace=False)
    symbols = []
    for name in names:
        try:
            symbols.append(getattr(module, name))
        except AttributeError:
            pytest.fail(f"{ac}: sochron.costs.{name} not implemented", pytrace=False)
    return tuple(symbols)


def _golden():
    return run_path(str(Path(__file__).resolve().parents[2] / "golden/CORE-002/costs_cases.py"))


def _context_state():
    context = getcontext()
    return (
        context.prec, context.rounding, context.Emin, context.Emax,
        context.capitals, context.clamp, dict(context.flags), dict(context.traps),
    )


def _call(function, *args, **kwargs):
    """Every checked call, including a rejection, must preserve the caller context."""
    context = getcontext()
    before = _context_state()
    try:
        return function(*args, **kwargs)
    finally:
        assert getcontext() is context
        assert _context_state() == before


def _money(actual, expected):
    assert isinstance(actual, Decimal)
    assert actual == Decimal(expected)


def _fixture(model, Provenance, **changes):
    provenance = dict(model.provenance)
    for field in changes:
        provenance[field] = Provenance("synthetic test fixture", date(2026, 10, 21), "assumed")
    return replace(model, provenance=provenance, **changes)


def _breakdown(actual, expected, CostBreakdown):
    assert isinstance(actual, CostBreakdown)
    for field, value in zip(
        ("spread", "commission", "slippage", "swap", "total", "stress_factor"),
        expected, strict=True,
    ):
        _money(getattr(actual, field), value)


def test_ac01_spread_fallback_points_and_decimal_context(monkeypatch):
    model, stress, spread_charge, points_to_money = _api(
        monkeypatch, "AC-01", "H001_COSTS", "stress", "spread_charge", "points_to_money"
    )
    golden = _golden()
    # Deliberately hostile caller precision/rounding; every result still uses p28 half-even.
    with localcontext(prec=4, rounding=ROUND_UP) as caller:
        caller.traps[Inexact] = True
        caller.traps[Rounded] = True
        for points, lots, factor, expected in golden["SPREAD_ROWS"]:
            stressed = _call(stress, model, Decimal(factor))
            _money(_call(spread_charge, points, Decimal(lots), stressed), expected)
        for points, lots, factor, expected in golden["POINT_ROWS"]:
            stressed = _call(stress, model, Decimal(factor))
            _money(_call(points_to_money, Decimal(points), Decimal(lots), stressed), expected)
        # The separate int branch for points must also be supported.
        _money(_call(points_to_money, 1, Decimal("1"), model), "0.1")


def test_ac02_slippage_commission_sides_and_stress(monkeypatch):
    model, Provenance, stress, slippage_charge, commission_charge = _api(
        monkeypatch, "AC-02", "H001_COSTS", "Provenance", "stress",
        "slippage_charge", "commission_charge",
    )
    golden = _golden()
    synthetic = _fixture(model, Provenance, commission_per_lot_per_side=Decimal("3.5"))
    with localcontext(prec=4, rounding=ROUND_UP):
        for lots, sides, factor, expected in golden["SLIPPAGE_ROWS"]:
            stressed = _call(stress, model, Decimal(factor))
            _money(_call(slippage_charge, Decimal(lots), stressed, sides=sides), expected)
        for rate, lots, sides, factor, expected in golden["COMMISSION_ROWS"]:
            selected = model if Decimal(rate) == Decimal("0") else synthetic
            stressed = _call(stress, selected, Decimal(factor))
            _money(_call(commission_charge, Decimal(lots), stressed, sides=sides), expected)
        # Omitted sides is two for both functions, including nonzero commission.
        _money(_call(slippage_charge, Decimal("0.02"), model), "0.20")
        _money(_call(commission_charge, Decimal("1.5"), synthetic), "10.5")


def test_ac03_swap_debits_credits_and_triple_counts(monkeypatch):
    model, Provenance, stress, swap_charge = _api(
        monkeypatch, "AC-03", "H001_COSTS", "Provenance", "stress", "swap_charge"
    )
    credit = _fixture(model, Provenance, swap_long_points_per_night=Decimal("100"))
    with localcontext(prec=4, rounding=ROUND_UP):
        for fixture, side, lots, nights, triple, factor, expected in _golden()["SWAP_ROWS"]:
            selected = model if fixture == "h001" else credit
            stressed = _call(stress, selected, Decimal(factor))
            actual = _call(swap_charge, side, Decimal(lots), nights, triple, stressed)
            _money(actual, expected)
            if Decimal(expected) == Decimal("0"):
                assert not actual.is_signed(), "swap must not return negative zero"


def test_ac04_round_trip_selection_breakdown_order_and_r(monkeypatch):
    model, Provenance, stress, round_trip_cost, r_multiple, CostBreakdown = _api(
        monkeypatch, "AC-04", "H001_COSTS", "Provenance", "stress",
        "round_trip_cost", "r_multiple", "CostBreakdown",
    )
    golden = _golden()
    with localcontext(prec=4, rounding=ROUND_UP):
        for side, lots, entry, exit_, nights, triple, sides, factor, expected in golden["ROUND_TRIP_ROWS"]:
            stressed = _call(stress, model, Decimal(factor))
            actual = _call(
                round_trip_cost, side, Decimal(lots), entry, exit_, nights, triple,
                stressed, sides=sides,
            )
            _breakdown(actual, expected, CostBreakdown)
        default = _call(round_trip_cost, "long", Decimal("0.02"), 240, 240, 1, 0, model)
        _breakdown(default, ("0.48", "0", "0.20", "1.00760", "1.68760", "1"), CostBreakdown)
        _money(_call(r_multiple, default.total, Decimal("25")), "0.067504")
        for money, r, expected in golden["R_ROWS"]:
            _money(_call(r_multiple, Decimal(money), Decimal(r)), expected)

        # General input follows ordered p28 arithmetic, not a lossless total.
        row = golden["ORDERED_TOTAL"]
        synthetic = _fixture(
            model, Provenance, commission_per_lot_per_side=Decimal(row["commission"]),
            slippage_points_per_side=row["slippage"],
            swap_long_points_per_night=Decimal(row["swap_points"]),
        )
        actual = _call(
            round_trip_cost, "long", Decimal("1"), row["entry"], 0, 1, 0,
            synthetic, sides=1,
        )
        _breakdown(actual, row["expected"], CostBreakdown)


def test_ac05_reject_invalid_types_domains_and_zero_branch_bypasses(monkeypatch):
    (
        model, Provenance, stress, check_volume, points_to_money, spread_charge,
        slippage_charge, commission_charge, swap_charge, round_trip_cost, r_multiple,
        CostsError, BadProvenance, BadStress, BadVolume, BadPoints, BadSides, BadNights, BadR,
    ) = _api(
        monkeypatch, "AC-05", "H001_COSTS", "Provenance", "stress", "check_volume",
        "points_to_money", "spread_charge", "slippage_charge", "commission_charge",
        "swap_charge", "round_trip_cost", "r_multiple", "CostsError", "BadProvenance",
        "BadStress", "BadVolume", "BadPoints", "BadSides", "BadNights", "BadR",
    )
    assert issubclass(CostsError, ValueError)
    for error in (BadProvenance, BadStress, BadVolume, BadPoints, BadSides, BadNights, BadR):
        assert issubclass(error, CostsError)

    def volume_calls(lots):
        # Test every entry point, including zero-cost and zero-count paths.
        return (
            (check_volume, (lots, model), {}),
            (points_to_money, (0, lots, model), {}),
            (spread_charge, (0, lots, model), {}),
            (slippage_charge, (lots, model), {"sides": 0}),
            (commission_charge, (lots, model), {"sides": 0}),
            (swap_charge, ("short", lots, 0, 0, model), {}),
            (round_trip_cost, ("long", lots, 0, 0, 0, 0, model), {"sides": 0}),
        )

    for lots in (Decimal("0.005"), Decimal("0.015"), Decimal("200.01"),
                 Decimal("0"), Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")):
        for function, args, kwargs in volume_calls(lots):
            with pytest.raises(BadVolume):
                _call(function, *args, **kwargs)
    # Wrong Decimal-only scalar types, deliberately including float and bool.
    for lots in (1, "0.02", True, 0.02):
        for function, args, kwargs in volume_calls(lots):
            with pytest.raises(TypeError):
                _call(function, *args, **kwargs)
    for lots in (Decimal("0.01"), Decimal("0.02"), Decimal("200")):
        result = _call(check_volume, lots, model)
        assert isinstance(result, Decimal)
        assert result == lots

    for points in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(BadPoints):
            _call(points_to_money, points, Decimal("0.02"), model)
    for points in (True, "240", 240.0):
        with pytest.raises(TypeError):
            _call(points_to_money, points, Decimal("0.02"), model)
    for bad, error in ((-1, BadPoints), (True, TypeError), (240.0, TypeError),
                       ("240", TypeError), (Decimal("240"), TypeError)):
        with pytest.raises(error):
            _call(spread_charge, bad, Decimal("0.02"), model)
        # Either spread is validated even when the side selects the other one.
        for side in ("long", "short"):
            for entry, exit_ in ((bad, 240), (240, bad)):
                with pytest.raises(error):
                    _call(round_trip_cost, side, Decimal("0.02"), entry, exit_, 1, 0, model)

    for bad, error in ((-1, BadSides), (True, TypeError), (2.0, TypeError),
                       ("2", TypeError), (Decimal("2"), TypeError)):
        for function in (slippage_charge, commission_charge):
            with pytest.raises(error):
                _call(function, Decimal("0.02"), model, sides=bad)
        with pytest.raises(error):
            _call(round_trip_cost, "long", Decimal("0.02"), 240, 240, 1, 0, model, sides=bad)

    for nights, triple in ((-1, 0), (1, -1), (1, 2)):
        with pytest.raises(BadNights):
            _call(swap_charge, "long", Decimal("0.02"), nights, triple, model)
        with pytest.raises(BadNights):
            _call(round_trip_cost, "long", Decimal("0.02"), 240, 240, nights, triple, model)
    for bad in (True, 1.0, "1", Decimal("1")):
        for nights, triple in ((bad, 0), (1, bad)):
            with pytest.raises(TypeError):
                _call(swap_charge, "long", Decimal("0.02"), nights, triple, model)
            with pytest.raises(TypeError):
                _call(round_trip_cost, "long", Decimal("0.02"), 240, 240, nights, triple, model)
    for side, error in (("buy", CostsError), (1, TypeError), (True, TypeError)):
        with pytest.raises(error):
            _call(swap_charge, side, Decimal("0.02"), 1, 0, model)
        with pytest.raises(error):
            _call(round_trip_cost, side, Decimal("0.02"), 240, 240, 1, 0, model)

    for factor in (0, -2, Decimal("0"), Decimal("-2"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(BadStress):
            _call(stress, model, factor)
    for factor in (True, 2.0, "2"):
        with pytest.raises(TypeError):
            _call(stress, model, factor)
    for r in (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(BadR):
            _call(r_multiple, Decimal("1"), r)
    for money in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(CostsError):
            _call(r_multiple, money, Decimal("25"))
    for bad in (1, True, 1.0, "1"):
        with pytest.raises(TypeError):
            _call(r_multiple, bad, Decimal("25"))
        with pytest.raises(TypeError):
            _call(r_multiple, Decimal("1"), bad)

    decimal_fields = (
        "point", "contract_size", "volume_min", "volume_step", "volume_max",
        "commission_per_lot_per_side", "swap_long_points_per_night",
        "swap_short_points_per_night", "stress_factor",
    )
    for field in decimal_fields:
        for bad in (1, True, "1", 1.0):
            with pytest.raises(TypeError):
                _call(replace, model, **{field: bad})
        for bad in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            error = BadStress if field == "stress_factor" else CostsError
            with pytest.raises(error):
                _call(replace, model, **{field: bad})
    for field in ("spread_fallback_points", "slippage_points_per_side", "triple_swap_weekday"):
        for bad in (True, "1", 1.0, Decimal("1")):
            with pytest.raises(TypeError):
                _call(replace, model, **{field: bad})
    for bad in (1, True, 1.0, None):
        with pytest.raises(TypeError):
            _call(replace, model, symbol=bad)
    for field in ("point", "contract_size", "volume_min", "volume_step"):
        for bad in (Decimal("0"), Decimal("-1")):
            with pytest.raises(CostsError):
                _call(replace, model, **{field: bad})
    for field, bad in (
        ("volume_max", Decimal("0.005")), ("commission_per_lot_per_side", Decimal("-1")),
        ("spread_fallback_points", -1), ("slippage_points_per_side", -1),
        ("triple_swap_weekday", -1), ("triple_swap_weekday", 7),
    ):
        with pytest.raises(CostsError):
            _call(replace, model, **{field: bad})
    for bad in (Decimal("0"), Decimal("-2")):
        with pytest.raises(BadStress):
            _call(replace, model, stress_factor=bad)

    valid = dict(source="synthetic test fixture", as_of=date(2026, 10, 21), status="assumed", note="")
    for field, bad in (("source", 1), ("note", 1), ("as_of", "2026-10-21")):
        with pytest.raises(TypeError):
            _call(Provenance, **{**valid, field: bad})
    with pytest.raises(BadProvenance):
        _call(Provenance, **{**valid, "status": "invalid"})
    missing = dict(model.provenance)
    del missing["point"]
    with pytest.raises(BadProvenance):
        _call(replace, model, provenance=missing)
    for key in ("symbol", "stress_factor", "unexpected"):
        with pytest.raises(BadProvenance):
            _call(replace, model, provenance={**model.provenance, key: model.provenance["point"]})
    with pytest.raises(BadProvenance):
        _call(replace, model, provenance={**model.provenance, "point": "not Provenance"})


def test_ac06_h001_provenance_unknowns_frozen_and_stress_copy(monkeypatch):
    model, CostModel, Provenance, CostBreakdown, unknowns, stress, round_trip_cost = _api(
        monkeypatch, "AC-06", "H001_COSTS", "CostModel", "Provenance", "CostBreakdown",
        "unknowns", "stress", "round_trip_cost",
    )
    assert isinstance(model, CostModel)
    assert model.symbol == "XAUUSDm"
    _money(model.stress_factor, "1")
    rows = _golden()["H001_PROVENANCE_ROWS"]
    assert set(model.provenance) == {row[0] for row in rows}
    assert isinstance(model.provenance, MappingProxyType)
    for field, value, source, as_of, status, unknown_note in rows:
        actual = getattr(model, field)
        if isinstance(value, str):
            _money(actual, value)
        else:
            assert type(actual) is int
            assert actual == value
        provenance = model.provenance[field]
        assert isinstance(provenance, Provenance)
        assert isinstance(provenance.source, str)
        assert source in provenance.source
        assert provenance.as_of == date.fromisoformat(as_of)
        assert provenance.status == status
        assert isinstance(provenance.note, str)
        if unknown_note:
            assert "UNKNOWN" in provenance.note
    assert _call(unknowns, model) == (
        "commission_per_lot_per_side", "slippage_points_per_side", "triple_swap_weekday",
    )
    # All four legal statuses are accepted; unknowns includes assumed and unknown only.
    for status in ("measured", "spec", "assumed", "unknown"):
        provenance = Provenance("synthetic test fixture", date(2026, 10, 21), status)
        assert provenance.note == ""
    marked = replace(model, provenance={
        **model.provenance,
        "point": Provenance("synthetic test fixture", date(2026, 10, 21), "unknown"),
    })
    assert _call(unknowns, marked) == (
        "commission_per_lot_per_side", "point", "slippage_points_per_side", "triple_swap_weekday",
    )

    snapshot = {field.name: getattr(model, field.name) for field in fields(model)}
    with localcontext(prec=4, rounding=ROUND_UP):
        for factor in (1, Decimal("1"), 2, Decimal("2")):
            stressed = _call(stress, model, factor)
            assert isinstance(stressed, CostModel)
            assert stressed is not model
            _money(stressed.stress_factor, "1" if factor == 1 else "2")
            for field in fields(model):
                if field.name != "stress_factor":
                    assert getattr(stressed, field.name) == snapshot[field.name]
        default = _call(stress, model)
        _money(default.stress_factor, "2")
        nested = _call(stress, default)
        _money(nested.stress_factor, "4")
        _money(default.stress_factor, "2")
    assert {field.name: getattr(model, field.name) for field in fields(model)} == snapshot

    original = dict(model.provenance)
    copied = replace(model, provenance=original)
    original["point"] = Provenance("changed caller dict", date(2026, 10, 21), "unknown")
    del original["volume_min"]
    assert copied.provenance == model.provenance
    assert isinstance(copied.provenance, MappingProxyType)
    with pytest.raises(TypeError):
        copied.provenance["point"] = original["point"]
    breakdown = _call(round_trip_cost, "long", Decimal("0.02"), 240, 240, 1, 0, model)
    assert isinstance(breakdown, CostBreakdown)
    for instance, field, replacement in (
        (model, "symbol", "changed"), (model.provenance["point"], "source", "changed"),
        (breakdown, "total", Decimal("0")),
    ):
        assert is_dataclass(instance)
        with pytest.raises(FrozenInstanceError):
            setattr(instance, field, replacement)
