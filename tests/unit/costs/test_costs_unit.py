"""Implementer unit tests for sochron.costs (CORE-002). The locked acceptance and golden tests own
the contract; these cover internals the implementer relied on: the module-owned Decimal context,
sign handling, provenance isolation and the validation helpers."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from decimal import Context, Decimal, localcontext

import pytest

from sochron.costs import (
    CONTEXT,
    H001_COSTS,
    PROVENANCE_FIELDS,
    BadPoints,
    BadProvenance,
    BadStress,
    BadVolume,
    CostsError,
    Provenance,
    check_volume,
    points_to_money,
    r_multiple,
    round_trip_cost,
    spread_charge,
    stress,
    swap_charge,
    unknowns,
)

LOTS = Decimal("0.02")
SYNTHETIC = Provenance("synthetic test fixture", date(2026, 10, 21), "assumed")


def test_module_context_is_used_not_the_callers():
    with localcontext(Context(prec=4)):
        breakdown = round_trip_cost("long", LOTS, 240, 240, 1, 0, H001_COSTS)
        assert breakdown.total == Decimal("1.68760")
        assert r_multiple(breakdown.total, Decimal("25")) == Decimal("0.067504")
    assert CONTEXT.prec == 28


def test_division_rounds_at_precision_28_half_even():
    assert r_multiple(Decimal("1"), Decimal("3")) == Decimal("0.3333333333333333333333333333")
    assert r_multiple(Decimal("2"), Decimal("3")) == Decimal("0.6666666666666666666666666667")


def test_swap_charge_never_returns_negative_zero():
    charge = swap_charge("short", LOTS, 7, 1, H001_COSTS)
    assert charge == 0
    assert not charge.is_signed()


def test_points_to_money_accepts_signed_points_but_spread_does_not():
    assert points_to_money(-240, LOTS, H001_COSTS) == Decimal("-0.48")
    with pytest.raises(BadPoints):
        spread_charge(-240, LOTS, H001_COSTS)


def test_check_volume_compares_numerically_whatever_the_exponent():
    assert check_volume(Decimal("0.010"), H001_COSTS) == Decimal("0.01")
    assert check_volume(Decimal("2E2"), H001_COSTS) == Decimal("200")
    with pytest.raises(BadVolume):
        check_volume(Decimal("0.0150"), H001_COSTS)
    with pytest.raises(TypeError):
        check_volume(1, H001_COSTS)  # type: ignore[arg-type]


def test_provenance_copy_is_isolated_and_read_only():
    source = dict(H001_COSTS.provenance)
    model = replace(H001_COSTS, provenance=source)
    source["point"] = SYNTHETIC
    assert model.provenance["point"] is H001_COSTS.provenance["point"]
    with pytest.raises(TypeError):
        model.provenance["point"] = SYNTHETIC  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        model.provenance["point"].status = "unknown"  # type: ignore[misc]
    assert tuple(sorted(model.provenance)) == tuple(sorted(PROVENANCE_FIELDS))


def test_replace_revalidates_the_model():
    with pytest.raises(CostsError):
        replace(H001_COSTS, volume_max=Decimal("0.001"))
    with pytest.raises(BadStress):
        replace(H001_COSTS, stress_factor=Decimal("NaN"))
    with pytest.raises(BadProvenance):
        replace(H001_COSTS, provenance={**H001_COSTS.provenance, "stress_factor": SYNTHETIC})
    with pytest.raises(TypeError):
        replace(H001_COSTS, point=0.001)  # type: ignore[arg-type]


def test_stress_accumulates_and_keeps_everything_else():
    doubled = stress(H001_COSTS)
    quadrupled = stress(doubled)
    assert quadrupled.stress_factor == Decimal("4")
    assert stress(H001_COSTS, 3).stress_factor == Decimal("3")
    for name in PROVENANCE_FIELDS:
        assert getattr(quadrupled, name) == getattr(H001_COSTS, name)
    assert quadrupled.provenance == H001_COSTS.provenance
    assert H001_COSTS.stress_factor == Decimal("1")


def test_unknowns_follow_status_not_field_order():
    model = replace(
        H001_COSTS,
        provenance={
            **H001_COSTS.provenance,
            "volume_max": Provenance("synthetic", date(2026, 10, 21), "unknown"),
            "commission_per_lot_per_side": Provenance("synthetic", date(2026, 10, 21), "measured"),
        },
    )
    assert unknowns(model) == ("slippage_points_per_side", "triple_swap_weekday", "volume_max")


def test_h001_provenance_notes_name_the_unknown_history():
    for name in ("swap_long_points_per_night", "swap_short_points_per_night"):
        record = H001_COSTS.provenance[name]
        assert record.status == "spec"
        assert "UNKNOWN" in record.note
    assert H001_COSTS.provenance["spread_fallback_points"].status == "measured"
    assert all(record.as_of == date(2026, 10, 21) for record in H001_COSTS.provenance.values())


def test_check_volume_grid_check_never_overflows_the_context():
    # Review r1 F1: `lots % step` at precision 28 raised InvalidOperation when the integer quotient
    # needed more than 28 digits; the grid check must stay exact for any finite step.
    fine = replace(H001_COSTS, volume_step=Decimal("1e-30"), provenance={**H001_COSTS.provenance, "volume_step": SYNTHETIC})
    assert check_volume(Decimal("1"), fine) == Decimal("1")
    assert check_volume(Decimal("0.01"), fine) == Decimal("0.01")
    with pytest.raises(BadVolume):
        check_volume(Decimal("1.0000000000000000000000000000005"), fine)


def test_cost_breakdown_rejects_wrong_types_and_totals():
    # Review r1 F2: the public frozen dataclass accepted ints and an inconsistent total.
    from sochron.costs import CostBreakdown

    with pytest.raises(TypeError):
        CostBreakdown(1, 2, 3, 4, 10, 1)  # type: ignore[arg-type]
    with pytest.raises(CostsError):
        CostBreakdown(Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("999"), Decimal("1"))
    good = CostBreakdown(Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("10"), Decimal("1"))
    assert good.total == Decimal("10")


def test_cost_breakdown_rejects_non_finite_fields_without_touching_the_callers_context():
    # Review r2 F4: comparing an sNaN total outside the module context raised InvalidOperation in
    # the caller's context (or passed, depending on its traps) and set the caller's flags.
    from sochron.costs import CostBreakdown

    with localcontext() as caller:
        caller.clear_flags()
        for bad in (Decimal("sNaN"), Decimal("NaN"), Decimal("Infinity")):
            with pytest.raises(CostsError):
                CostBreakdown(Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), bad, Decimal("1"))
            with pytest.raises(CostsError):
                CostBreakdown(bad, Decimal("2"), Decimal("3"), Decimal("4"), Decimal("10"), Decimal("1"))
        assert not any(caller.flags.values())


def test_provenance_must_be_a_mapping():
    # Review r1 F3: a list of the eleven keys reached .items() and raised AttributeError.
    with pytest.raises(TypeError):
        replace(H001_COSTS, provenance=list(PROVENANCE_FIELDS))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(H001_COSTS, provenance="point")  # type: ignore[arg-type]


def test_int_arguments_are_exact_and_not_size_bounded():
    # CORE-004 implementer decision: the size bound protects rational conversions, which only
    # Decimals reach; an int converts exactly, so an in-domain huge int keeps its CORE-002 result.
    # 10**1500 points x 0.001 x 100 x 0.01 lots = 10**1497 USD
    assert points_to_money(10**1500, Decimal("0.01"), H001_COSTS) == Decimal("1E+1497")
    assert stress(H001_COSTS, 10**1500).stress_factor == Decimal("1E+1500")
    with pytest.raises(BadStress):
        stress(H001_COSTS, -(10**5000))


def test_model_check_returns_a_private_copy_of_provenance_each_time():
    # CORE-004: every use validates the model once and works from its own snapshot, so a caller
    # who keeps the snapshot cannot reach the model's stored provenance.
    from sochron.costs.model import validate_model

    first = validate_model(H001_COSTS)
    second = validate_model(H001_COSTS)
    assert first == dict(H001_COSTS.provenance)
    assert first is not second
    first.clear()
    assert set(H001_COSTS.provenance) == set(PROVENANCE_FIELDS)


class _SwapOnClassRead:
    """Claims to be a dict to isinstance(), and swaps the model's provenance while it is asked."""

    def __init__(self, model, replacement):
        self._model = model
        self._replacement = replacement

    @property
    def __class__(self):
        object.__setattr__(self._model, "provenance", self._replacement)
        return dict


def test_provenance_attribute_is_read_once_per_check():
    # Review CORE-004-r1 F1: the check read model.provenance twice, so an object planted there could
    # pass isinstance() and swap in a list of pairs that dict() then accepted for one call.
    model = replace(H001_COSTS)
    pairs = list(H001_COSTS.provenance.items())
    object.__setattr__(model, "provenance", _SwapOnClassRead(model, pairs))
    with pytest.raises(TypeError):
        check_volume(Decimal("0.02"), model)


class _NotAStatus(str):
    def __eq__(self, other):
        return False

    __hash__ = str.__hash__


class _OtherDay(date):
    pass


@pytest.mark.parametrize(
    ("field", "planted", "error"),
    [
        ("status", "bogus", BadProvenance),
        ("status", None, TypeError),
        ("status", _NotAStatus("assumed"), TypeError),
        # Review CORE-004-r2 F7: every field is checked again, not only status.
        ("source", 1, TypeError),
        ("source", _NotAStatus("x"), TypeError),
        ("note", None, TypeError),
        ("note", _NotAStatus("x"), TypeError),
        ("as_of", "2026-10-21", TypeError),
        ("as_of", datetime(2026, 10, 21), TypeError),
        ("as_of", _OtherDay(2026, 10, 21), TypeError),
    ],
)
def test_provenance_records_are_checked_again_at_use(field, planted, error):
    # Review CORE-004-r1 F3 (owner: fix): a record changed after construction kept its place, so
    # unknowns() could drop an assumed constant; each use now re-runs the construction rule.
    record = replace(H001_COSTS.provenance["commission_per_lot_per_side"])
    model = replace(H001_COSTS, provenance={**H001_COSTS.provenance, "commission_per_lot_per_side": record})
    assert "commission_per_lot_per_side" in unknowns(model)
    object.__setattr__(record, field, planted)
    with pytest.raises(error):
        unknowns(model)
    with pytest.raises(error):
        stress(model)
    with pytest.raises(error):
        check_volume(Decimal("0.02"), model)
