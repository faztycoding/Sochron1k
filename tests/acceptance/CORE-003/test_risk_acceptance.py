"""CORE-003 v1.2 acceptance tests derived before the risk implementation."""

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import date, datetime
from decimal import (
    Decimal, Inexact, ROUND_UP, Rounded, Subnormal, Underflow, Overflow,
    getcontext, localcontext,
)
from fractions import Fraction
from importlib import import_module
from pathlib import Path
from runpy import run_path
from types import MappingProxyType

import pytest


DAY = date(2026, 10, 22)
NEXT_DAY = date(2026, 10, 23)


def _api(monkeypatch, ac, *names):
    """Missing risk fails each AC, never collection; only contracted public names."""
    monkeypatch.syspath_prepend(str(Path.cwd() / "src"))
    try:
        module = import_module("sochron.risk")
    except ImportError as error:
        pytest.fail(f"{ac}: sochron.risk not implemented ({error})", pytrace=False)
    symbols = []
    for name in names:
        try:
            symbols.append(getattr(module, name))
        except AttributeError:
            pytest.fail(f"{ac}: sochron.risk.{name} not implemented", pytrace=False)
    return tuple(symbols)


def _golden():
    return run_path(str(Path(__file__).resolve().parents[2] / "golden/CORE-003/risk_cases.py"))


def _context_state():
    context = getcontext()
    return (
        context.prec, context.rounding, context.Emin, context.Emax,
        context.capitals, context.clamp, dict(context.traps), dict(context.flags),
    )


def _call(function, *args, **kwargs):
    """Preserve caller context identity/settings/traps/flags even on rejection."""
    context, before = getcontext(), _context_state()
    try:
        return function(*args, **kwargs)
    finally:
        assert getcontext() is context
        assert _context_state() == before


def _hostile(context):
    context.prec = 4
    context.rounding = ROUND_UP
    context.traps[Inexact] = True
    context.traps[Rounded] = True
    context.traps[Subnormal] = True
    # Risk must enable these locally even when the caller has disabled them.
    context.traps[Overflow] = False
    context.traps[Underflow] = False
    context.clear_flags()
    context.flags[Rounded] = True


def _money(actual, expected):
    assert isinstance(actual, Decimal)
    assert actual == Decimal(expected)


def _fixture(model, Provenance, **changes):
    provenance = dict(model.provenance)
    for name in changes:
        provenance[name] = Provenance("synthetic test fixture", DAY, "assumed")
    return _call(replace, model, provenance=provenance, **changes)


def _snapshot(instance):
    return tuple(getattr(instance, field.name) for field in fields(instance))


def _state(actual, policy, day, daily_base, experiment_base, daily, experiment):
    assert actual.policy == policy
    assert type(actual.day) is date and actual.day == day
    _money(actual.day_start_equity, daily_base)
    _money(actual.experiment_start_equity, experiment_base)
    assert actual.daily_halted is daily
    assert actual.experiment_halted is experiment


def _gate(actual, reasons, GateDecision):
    assert isinstance(actual, GateDecision)
    assert type(actual.reasons) is tuple
    assert actual.reasons == reasons
    assert actual.allowed is (reasons == ())


def _reject(error, function, *args, **kwargs):
    with pytest.raises(error):
        _call(function, *args, **kwargs)


def test_ac01_exact_sizing_grid_caps_and_display_context(monkeypatch):
    policy, size_position, SizeDecision = _api(
        monkeypatch, "AC-01", "H001_RISK", "size_position", "SizeDecision",
    )
    from sochron.costs import H001_COSTS, Provenance

    policy_before, model_before = _snapshot(policy), _snapshot(H001_COSTS)
    with localcontext() as caller:
        _hostile(caller)
        for label, equity, distance, budget, overrides, expected in _golden()["SIZE_ROWS"]:
            # Reset *every* operand from H001 for each row (AC-01 fixture-reset rule).
            model = _fixture(H001_COSTS, Provenance, **{
                name: Decimal(value) for name, value in overrides.items()
            })
            actual = _call(
                size_position, Decimal(equity), Decimal(distance), model, policy, Decimal(budget),
            )
            assert isinstance(actual, SizeDecision), label
            for name, value in zip(
                ("lots", "risk_money", "risk_per_lot", "actual_risk"), expected[:4], strict=True,
            ):
                _money(getattr(actual, name), value)
            assert actual.reason == expected[4], label
            # Independent exact safety/grid invariants, never rounded display operands.
            risk = Fraction(Decimal(equity)) * Fraction(policy.risk_per_trade)
            per_lot = (
                Fraction(Decimal(distance)) * Fraction(model.contract_size)
                + Fraction(Decimal(budget))
            )
            assert Fraction(actual.lots) * per_lot <= risk, label
            assert (Fraction(actual.lots) / Fraction(model.volume_step)).denominator == 1, label
            if actual.lots:
                assert model.volume_min <= actual.lots <= model.volume_max, label

        default = _call(size_position, Decimal("10000"), Decimal("12.00"), H001_COSTS, policy)
        _money(default.lots, "0.02")
        _money(default.risk_money, "25")
        _money(default.risk_per_lot, "1200")
        _money(default.actual_risk, "24")
        assert default.reason == "ok"
        # stress_factor is explicitly excluded from sizing, even with an explicit budget.
        stressed = _call(replace, H001_COSTS, stress_factor=Decimal("2"))
        assert _call(size_position, Decimal("10000"), Decimal("12"), stressed, policy, Decimal("10")) == (
            _call(size_position, Decimal("10000"), Decimal("12"), H001_COSTS, policy, Decimal("10"))
        )
    assert _snapshot(policy) == policy_before
    assert _snapshot(H001_COSTS) == model_before


def test_ac02_daily_threshold_latch_rollover_and_time_reversal(monkeypatch):
    policy, start, update, TimeReversal = _api(
        monkeypatch, "AC-02", "H001_RISK", "start_experiment", "update_equity", "TimeReversal",
    )
    from sochron.costs import Provenance

    initial = _call(start, Decimal("10000"), DAY, policy, "owner", "H001 R1 run")
    _state(initial, policy, DAY, "10000", "10000", False, False)
    with localcontext() as caller:
        _hostile(caller)
        state = initial
        for _, equity, day, daily_base, experiment_base, daily, experiment in _golden()["DAILY_SEQUENCE"]:
            before = _snapshot(state)
            result = _call(update, state, Decimal(equity), date(2026, 10, day))
            _state(result, policy, date(2026, 10, day), daily_base, experiment_base, daily, experiment)
            assert _snapshot(state) == before
            state = result
        # First-new-day observations reset daily baseline even below yesterday's limit.
        for equity, experiment in (("9900", False), ("9800", True)):
            result = _call(update, initial, Decimal(equity), NEXT_DAY)
            _state(result, policy, NEXT_DAY, equity, "10000", False, experiment)
        halted = _call(update, initial, Decimal("9925"), DAY)
        recovered = _call(update, halted, Decimal("10500"), DAY)
        _state(recovered, policy, DAY, "10000", "10000", True, False)
        for baseline, equity, daily, experiment in _golden()["THRESHOLD_ROWS"]:
            fresh = _call(start, Decimal(baseline), DAY, policy, "owner", "exact threshold fixture")
            result = _call(update, fresh, Decimal(equity), DAY)
            _state(result, policy, DAY, baseline, baseline, daily, experiment)
        custom = _fixture(policy, Provenance, daily_loss_limit=Decimal("0.01"))
        custom_state = _call(start, Decimal("10000"), DAY, custom, "owner", "custom daily limit")
        # Custom daily budget100: loss75 does not halt; loss100 does.
        _state(_call(update, custom_state, Decimal("9925"), DAY),
               custom, DAY, "10000", "10000", False, False)
        _state(_call(update, custom_state, Decimal("9900"), DAY),
               custom, DAY, "10000", "10000", True, False)
        with pytest.raises(TimeReversal):
            _call(update, initial, Decimal("10000"), date(2026, 10, 21))
    _state(initial, policy, DAY, "10000", "10000", False, False)


def test_ac03_experiment_latch_authorized_restart_and_daily_preservation(monkeypatch):
    policy, start, update, restart, BadHaltClear, TimeReversal = _api(
        monkeypatch, "AC-03", "H001_RISK", "start_experiment", "update_equity",
        "restart_experiment", "BadHaltClear", "TimeReversal",
    )
    initial = _call(start, Decimal("10000"), DAY, policy, "owner", "H001 R1 run")
    with localcontext() as caller:
        _hostile(caller)
        state = initial
        for operation, equity, day, daily_base, experiment_base, daily, experiment in _golden()["RESTART_SEQUENCE"]:
            before = _snapshot(state)
            args = (state, Decimal(equity), date(2026, 10, day))
            result = _call(restart, *args, "owner", "approved restart") if operation == "restart" else (
                _call(update, *args)
            )
            _state(result, policy, date(2026, 10, day), daily_base, experiment_base, daily, experiment)
            assert _snapshot(state) == before
            state = result

        halted = _call(update, initial, Decimal("9800"), DAY)
        recovered = _call(update, halted, Decimal("10500"), NEXT_DAY)
        _state(recovered, policy, NEXT_DAY, "10500", "10000", False, True)
        restarted = _call(restart, recovered, Decimal("10500"), NEXT_DAY, "owner", "reviewed recovery")
        _state(restarted, policy, NEXT_DAY, "10500", "10500", False, False)
        # New experiment budget is10500*.02=210: equality at10290, not old budget200.
        assert not _call(update, restarted, Decimal("10290.01"), NEXT_DAY).experiment_halted
        assert _call(update, restarted, Decimal("10290"), NEXT_DAY).experiment_halted
        # Restart itself must evaluate a newly reached daily threshold.
        daily_clear = _call(update, halted, Decimal("10000"), NEXT_DAY)
        _state(daily_clear, policy, NEXT_DAY, "10000", "10000", False, True)
        crossing = _call(restart, daily_clear, Decimal("9925"), NEXT_DAY, "owner", "new budget")
        _state(crossing, policy, NEXT_DAY, "10000", "9925", True, False)
        # Direct next-day restart uses rollover, without a prior update call.
        next_day_restart = _call(restart, halted, Decimal("9800"), NEXT_DAY, "owner", "next day")
        _state(next_day_restart, policy, NEXT_DAY, "9800", "9800", False, False)
        same_day_recovery = _call(restart, halted, Decimal("10500"), DAY, "owner", "same day")
        _state(same_day_recovery, policy, DAY, "10000", "10500", True, False)

        for name in ("claude", "codex", "", "Owner", " owner", "owner "):
            with pytest.raises(BadHaltClear):
                _call(restart, halted, Decimal("9800"), DAY, name, "valid reason")
            with pytest.raises(BadHaltClear):
                _call(start, Decimal("10000"), DAY, policy, name, "valid reason")
        for reason in ("", "  "):
            with pytest.raises(BadHaltClear):
                _call(restart, halted, Decimal("9800"), DAY, "owner", reason)
            with pytest.raises(BadHaltClear):
                _call(start, Decimal("10000"), DAY, policy, "owner", reason)
        # Even a current equity at the limit cannot authorize restarting a clear input state.
        for equity in ("10000", "9800"):
            with pytest.raises(BadHaltClear):
                _call(restart, initial, Decimal(equity), DAY, "owner", "not halted")
        with pytest.raises(TimeReversal):
            _call(restart, halted, Decimal("9800"), date(2026, 10, 21), "owner", "past date")
        _state(halted, policy, DAY, "10000", "10000", True, True)


def test_ac04_entry_recomputes_sizing_and_collects_exact_reasons(monkeypatch):
    policy, start, EntryRequest, GateDecision, check_entry = _api(
        monkeypatch, "AC-04", "H001_RISK", "start_experiment", "EntryRequest",
        "GateDecision", "check_entry",
    )
    from sochron.costs import H001_COSTS, Provenance

    state = _call(start, Decimal("10000"), DAY, policy, "owner", "H001 R1 run")
    request = _call(EntryRequest, "long", Decimal("0.02"), Decimal("4012.90"), Decimal("4000.90"), 0)
    state_before, request_before = _snapshot(state), _snapshot(request)
    # Request/state changes are independent; each row starts from the original fixture.
    rows = (
        ({}, {}, ()),
        ({}, {"daily_halted": True}, ("daily_halt",)),
        ({}, {"experiment_halted": True}, ("experiment_halt",)),
        ({"open_exposures": 1}, {}, ("max_exposure",)),
        ({"open_exposures": 2}, {}, ("max_exposure",)),
        ({"stop_loss": None}, {}, ("missing_stop_loss",)),
        ({"stop_loss": Decimal("4012.90")}, {}, ("stop_loss_wrong_side",)),
        ({"stop_loss": Decimal("4013.00")}, {}, ("stop_loss_wrong_side",)),
        ({"lots": Decimal("0.03")}, {}, ("lots_exceed_sized",)),
        # |4012.90-3992.90|=20, R25/per2000=1/80 -> floor.01; requested.02 is too big.
        ({"stop_loss": Decimal("3992.90")}, {}, ("lots_exceed_sized",)),
        ({"lots": Decimal("0.015")}, {}, ("lots_not_on_grid",)),
        ({"lots": Decimal("0")}, {}, ("lots_not_on_grid",)),
        ({"lots": Decimal("-0.01")}, {}, ("lots_not_on_grid",)),
        ({"lots": Decimal("0.005")}, {}, ("lots_not_on_grid",)),
        ({"lots": Decimal("200.01")}, {}, ("lots_exceed_sized", "lots_not_on_grid")),
        ({"side": "short", "stop_loss": Decimal("4024.90")}, {}, ()),
        ({"side": "short", "stop_loss": Decimal("4012.90")}, {}, ("stop_loss_wrong_side",)),
        ({"side": "short", "stop_loss": Decimal("4012.80")}, {}, ("stop_loss_wrong_side",)),
    )
    with localcontext() as caller:
        _hostile(caller)
        for request_changes, state_changes, reasons in rows:
            altered_request = _call(replace, request, **request_changes)
            altered_state = _call(replace, state, **state_changes)
            _gate(_call(check_entry, altered_request, Decimal("10000"), altered_state, H001_COSTS),
                  reasons, GateDecision)
        isolated = _call(start, Decimal("100"), DAY, policy, "owner", "isolated sizing fixture")
        small_request = _call(replace, request, lots=Decimal("0.01"))
        _gate(_call(check_entry, small_request, Decimal("100"), isolated, H001_COSTS, Decimal("0")),
              ("below_min_volume", "lots_exceed_sized"), GateDecision)
        # Loss200 meets daily75 and experiment200; sized.02 still fits.
        _gate(_call(check_entry, request, Decimal("9800"), state, H001_COSTS),
              ("daily_halt", "experiment_halt"), GateDecision)
        combined_state = _call(replace, state, daily_halted=True, experiment_halted=True)
        combined_request = _call(replace, request, lots=Decimal("0.015"), open_exposures=1)
        _gate(_call(check_entry, combined_request, Decimal("100"), combined_state, H001_COSTS),
              ("below_min_volume", "daily_halt", "experiment_halt", "lots_exceed_sized",
               "lots_not_on_grid", "max_exposure"), GateDecision)
        # Missing/wrong-side SL must not invent sizing reasons, but retain all other denials.
        for stop, reason in ((None, "missing_stop_loss"), (Decimal("4013"), "stop_loss_wrong_side")):
            changed = _call(replace, combined_request, stop_loss=stop)
            _gate(_call(check_entry, changed, Decimal("100"), combined_state, H001_COSTS),
                  ("daily_halt", "experiment_halt", "lots_not_on_grid", "max_exposure", reason),
                  GateDecision)

        # Cost budget and supplied model participate in the recomputation.
        budget_state = _call(start, Decimal("9600"), DAY, policy, "owner", "cost fixture")
        _gate(_call(check_entry, request, Decimal("9600"), budget_state, H001_COSTS), (), GateDecision)
        _gate(_call(check_entry, request, Decimal("9600"), budget_state, H001_COSTS, Decimal("10")),
              ("lots_exceed_sized",), GateDecision)
        larger_contract = _fixture(H001_COSTS, Provenance, contract_size=Decimal("200"))
        _gate(_call(check_entry, request, Decimal("10000"), state, larger_contract),
              ("lots_exceed_sized",), GateDecision)
        # Exact subtraction: distance is1.0000000000000000000000000001, not rounded1.
        edge_state = _call(start, Decimal("800"), DAY, policy, "owner", "distance edge")
        edge_request = _call(
            EntryRequest, "long", Decimal("0.02"),
            Decimal("2.0000000000000000000000000001"), Decimal("1"), 0,
        )
        _gate(_call(check_entry, edge_request, Decimal("800"), edge_state, H001_COSTS),
              ("lots_exceed_sized",), GateDecision)

        for baseline, equity, daily, experiment in _golden()["THRESHOLD_ROWS"]:
            fresh = _call(start, Decimal(baseline), DAY, policy, "owner", "threshold fixture")
            reasons = tuple(name for name, flag in (
                ("daily_halt", daily), ("experiment_halt", experiment),
            ) if flag)
            _gate(_call(check_entry, request, Decimal(equity), fresh, H001_COSTS), reasons, GateDecision)
        # A custom policy is bound in state; gate must not substitute H001 defaults.
        custom = _fixture(policy, Provenance, risk_per_trade=Decimal("0.005"), max_open_exposures=2)
        custom_state = _call(start, Decimal("10000"), DAY, custom, "owner", "bound policy")
        custom_request = _call(replace, request, lots=Decimal("0.04"), open_exposures=1)
        _gate(_call(check_entry, custom_request, Decimal("10000"), custom_state, H001_COSTS),
              (), GateDecision)
        _gate(_call(check_entry, _call(replace, custom_request, open_exposures=2),
                    Decimal("10000"), custom_state, H001_COSTS),
              ("max_exposure",), GateDecision)
    assert _snapshot(state) == state_before
    assert _snapshot(request) == request_before


def test_ac05_stop_change_cannot_widen_or_remove(monkeypatch):
    check_stop_change, GateDecision = _api(monkeypatch, "AC-05", "check_stop_change", "GateDecision")
    rows = (
        ("long", "4000.90", "4001.00", ()),
        ("long", "4000.90", "4000.90", ()),
        ("long", "4000.90", "4000.00", ("stop_loss_widened",)),
        ("long", "4000.90", None, ("missing_stop_loss",)),
        ("short", "4024.90", "4024.00", ()),
        ("short", "4024.90", "4024.90", ()),
        ("short", "4024.90", "4025.00", ("stop_loss_widened",)),
        ("short", "4024.90", None, ("missing_stop_loss",)),
    )
    with localcontext() as caller:
        _hostile(caller)
        for side, current, new, reasons in rows:
            _gate(_call(check_stop_change, side, Decimal(current), None if new is None else Decimal(new)),
                  reasons, GateDecision)


def test_ac06_validation_provenance_immutability_and_range(monkeypatch):
    (
        policy, RiskPolicy, SizeDecision, HaltState, EntryRequest, GateDecision,
        size, start, update, restart, entry, stop, unknowns,
        RiskError, BadPolicy, BadEquity, BadStop, BadHaltClear, TimeReversal,
    ) = _api(
        monkeypatch, "AC-06", "H001_RISK", "RiskPolicy", "SizeDecision", "HaltState",
        "EntryRequest", "GateDecision", "size_position", "start_experiment", "update_equity",
        "restart_experiment", "check_entry", "check_stop_change", "unknowns",
        "RiskError", "BadPolicy", "BadEquity", "BadStop", "BadHaltClear", "TimeReversal",
    )
    from sochron.costs import H001_COSTS, Provenance

    assert issubclass(RiskError, ValueError)
    for error in (BadPolicy, BadEquity, BadStop, BadHaltClear, TimeReversal):
        assert issubclass(error, RiskError)
    state = _call(start, Decimal("10000"), DAY, policy, "owner", "validation fixture")
    halted = _call(update, state, Decimal("9800"), DAY)
    request = _call(EntryRequest, "long", Decimal("0.02"), Decimal("4012.90"), Decimal("4000.90"), 0)
    decision = _call(size, Decimal("10000"), Decimal("12"), H001_COSTS, policy)
    gate = _call(entry, request, Decimal("10000"), state, H001_COSTS)

    # Every specification below is valid. Each negative call changes exactly ONE argument.
    specifications = (
        (RiskPolicy, {field.name: getattr(policy, field.name) for field in fields(policy)}),
        (HaltState, {field.name: getattr(state, field.name) for field in fields(state)}),
        (SizeDecision, {field.name: getattr(decision, field.name) for field in fields(decision)}),
        (EntryRequest, {field.name: getattr(request, field.name) for field in fields(request)}),
        (GateDecision, {"allowed": True, "reasons": ()}),
        (size, dict(equity=Decimal("10000"), stop_distance=Decimal("12"),
                    model=H001_COSTS, policy=policy, cost_per_lot=Decimal("0"))),
        (start, dict(equity=Decimal("10000"), day=DAY, policy=policy,
                     authorized_by="owner", reason="valid")),
        (update, dict(state=state, equity=Decimal("10000"), day=DAY)),
        (restart, dict(state=halted, equity=Decimal("9800"), day=DAY,
                       authorized_by="owner", reason="valid")),
        (entry, dict(request=request, equity=Decimal("10000"), state=state,
                     model=H001_COSTS, cost_per_lot=Decimal("0"))),
        (stop, dict(side="long", current_stop=Decimal("4000.90"), new_stop=Decimal("4001"))),
        (unknowns, dict(policy=policy)),
    )
    with localcontext() as caller:
        _hostile(caller)
        for function, valid in specifications:
            _call(function, **valid)
            for name, value in valid.items():
                if isinstance(value, Decimal):
                    invalid = (1, "1", True, 1.0)
                    if name not in ("stop_loss", "new_stop"):
                        invalid += (None,)
                elif type(value) is bool:
                    invalid = (0, 1, "False", Decimal("0"), 0.0, None)
                elif type(value) is int:
                    invalid = (True, Decimal("1"), 1.0, "1", None)
                elif type(value) is date:
                    invalid = (datetime(2026, 10, 22), "2026-10-22", 1, True, 1.0, None)
                elif isinstance(value, str):
                    invalid = (1, True, Decimal("1"), 1.0, None)
                elif name == "halt_clearers":
                    invalid = (["owner"], "owner", 1, True, 1.0, None, (1,), (True,))
                elif name == "reasons":
                    invalid = (["daily_halt"], "daily_halt", 1, True, 1.0, None, (1,), (True,))
                elif name == "provenance":
                    invalid = ([], "mapping", 1, True, 1.0, None)
                else:
                    # model, policy, state, request: structural resemblance is not sufficient.
                    invalid = ({}, "object", 1, True, 1.0, None)
                for bad in invalid:
                    arguments = {**valid, name: bad}
                    if name == "reasons":
                        # Nonempty reasons require allowed=False; isolate the type defect.
                        arguments["allowed"] = False
                    _reject(TypeError, function, **arguments)

        nonfinite = tuple(Decimal(value) for value in ("NaN", "sNaN", "Infinity", "-Infinity"))
        nonpositive = (Decimal("0"), Decimal("-1")) + nonfinite
        for function, valid in specifications:
            for name in valid:
                if name in ("equity", "day_start_equity", "experiment_start_equity"):
                    invalid, error = nonpositive, BadEquity
                elif name in ("stop_distance", "entry_price", "stop_loss", "current_stop", "new_stop"):
                    invalid, error = nonpositive, BadStop
                elif name in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit"):
                    invalid, error = nonpositive + (Decimal("1"), Decimal("2")), BadPolicy
                elif name == "cost_per_lot":
                    invalid, error = (Decimal("-1"),) + nonfinite, BadPolicy
                elif name == "lots":
                    invalid, error = nonfinite, RiskError
                elif name in ("risk_money", "risk_per_lot", "actual_risk"):
                    invalid, error = nonfinite, RiskError
                elif name == "open_exposures":
                    invalid, error = (-1,), RiskError
                elif name == "max_open_exposures":
                    invalid, error = (0, -1), BadPolicy
                elif name == "side":
                    invalid, error = ("buy", "", "LONG"), RiskError
                else:
                    continue
                for bad in invalid:
                    _reject(error, function, **{**valid, name: bad})

        for clearers in ((), ("",), (" ",), ("owner", "owner")):
            _reject(BadPolicy, replace, policy, halt_clearers=clearers)
        for key in policy.provenance:
            missing = dict(policy.provenance)
            del missing[key]
            _reject(BadPolicy, replace, policy, provenance=missing)
            _reject(BadPolicy, replace, policy, provenance={**policy.provenance, key: "not Provenance"})
        _reject(BadPolicy, replace, policy, provenance={
            **policy.provenance, "unexpected": policy.provenance["risk_per_trade"],
        })

        # Consistency validation of directly constructed result dataclasses.
        for changes in (
            {"lots": Decimal("-0.01")}, {"lots": Decimal("0")},
            {"reason": "below_min_volume"}, {"reason": "unrecognized"},
        ):
            _reject(RiskError, replace, decision, **changes)
        _call(SizeDecision, Decimal("0"), Decimal("25"), Decimal("1200"), Decimal("0"), "below_min_volume")
        _call(SizeDecision, Decimal("200"), Decimal("250000"), Decimal("10"), Decimal("2000"), "capped_at_volume_max")
        _reject(RiskError, GateDecision, allowed=False, reasons=())
        _reject(RiskError, GateDecision, allowed=True, reasons=("daily_halt",))
        for reasons in (
            ("max_exposure", "daily_halt"), ("daily_halt", "daily_halt"), ("unrecognized",),
        ):
            _reject(RiskError, GateDecision, allowed=False, reasons=reasons)
        for reason in (
            "below_min_volume", "daily_halt", "experiment_halt", "lots_exceed_sized",
            "lots_not_on_grid", "max_exposure", "missing_stop_loss", "stop_loss_wrong_side",
            "stop_loss_widened",
        ):
            _call(GateDecision, False, (reason,))

        # Business-denial branches never suppress validation of another argument.
        for candidate in (
            request, _call(replace, request, stop_loss=None),
            _call(replace, request, stop_loss=Decimal("4013")),
        ):
            for selected_state in (state, halted):
                valid = dict(request=candidate, equity=Decimal("10000"), state=selected_state,
                             model=H001_COSTS, cost_per_lot=Decimal("0"))
                for name, bad, error in (
                    ("equity", Decimal("0"), BadEquity),
                    ("equity", Decimal("NaN"), BadEquity),
                    ("equity", 1.0, TypeError),
                    ("cost_per_lot", Decimal("-1"), BadPolicy),
                    ("cost_per_lot", Decimal("NaN"), BadPolicy),
                    ("cost_per_lot", 0.0, TypeError),
                    ("model", None, TypeError),
                ):
                    _reject(error, entry, **{**valid, name: bad})
        for bad, error in ((Decimal("0"), BadStop), (Decimal("sNaN"), BadStop), (1.0, TypeError)):
            _reject(error, stop, side="long", current_stop=bad, new_stop=None)
        _reject(RiskError, stop, side="buy", current_stop=Decimal("1"), new_stop=None)

        # Exact subnormal per-lot and actual-risk fields are accepted too.
        # per=1E-1000002*100=1E-1000000, cap200, actual=2E-999998.
        exact_subnormal = _call(size, Decimal("10000"), Decimal("1E-1000002"), H001_COSTS, policy)
        _money(exact_subnormal.risk_per_lot, "1E-1000000")
        _money(exact_subnormal.lots, "200")
        _money(exact_subnormal.actual_risk, "2E-999998")
        assert exact_subnormal.reason == "capped_at_volume_max"
        # per=1E-1000022*100=1E-1000020, cap.01, actual=1E-1000022 exactly.
        exact_cap = _fixture(H001_COSTS, Provenance, volume_max=Decimal("0.01"))
        exact_actual = _call(size, Decimal("10000"), Decimal("1E-1000022"), exact_cap, policy)
        _money(exact_actual.risk_per_lot, "1E-1000020")
        _money(exact_actual.lots, "0.01")
        _money(exact_actual.actual_risk, "1E-1000022")
        assert exact_actual.reason == "capped_at_volume_max"
        for equity, risk_money, accepted in _golden()["RANGE_ROWS"]:
            if accepted:
                actual = _call(size, Decimal(equity), Decimal("12"), H001_COSTS, policy)
                _money(actual.risk_money, risk_money)
                _money(actual.risk_per_lot, "1200")
                _money(actual.lots, "0")
                _money(actual.actual_risk, "0")
                assert actual.reason == "below_min_volume"
            else:
                with pytest.raises(RiskError):
                    _call(size, Decimal(equity), Decimal("12"), H001_COSTS, policy)
        # Range validation applies to per-lot risk, even when the selected lots is zero.
        # 1E999998*100=1E1000000 -> Overflow; R25/per -> floor0.
        with pytest.raises(RiskError):
            _call(size, Decimal("10000"), Decimal("1E999998"), H001_COSTS, policy)
        # 1E-1000029*100=1E-1000027 -> Underflow (R25 is normal).
        with pytest.raises(RiskError):
            _call(size, Decimal("10000"), Decimal("1E-1000029"), H001_COSTS, policy)
        # Per=1.1E-1000026 is inexact subnormal; reject even though capped lots200
        # would have exact actual2.2E-1000024.
        with pytest.raises(RiskError):
            _call(size, Decimal("10000"), Decimal("1.1E-1000028"), H001_COSTS, policy)
        # Per=1E-1000025 is exact, cap=.01, actual=1E-1000027 -> Underflow.
        tiny_cap = _fixture(H001_COSTS, Provenance, volume_max=Decimal("0.01"))
        with pytest.raises(RiskError):
            _call(size, Decimal("10000"), Decimal("1E-1000027"), tiny_cap, policy)

        rows = _golden()["H001_PROVENANCE_ROWS"]
        assert isinstance(policy, RiskPolicy)
        assert set(policy.provenance) == {row[0] for row in rows}
        assert isinstance(policy.provenance, MappingProxyType)
        for name, value, source, as_of, status, note in rows:
            if name in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit"):
                _money(getattr(policy, name), value)
            else:
                assert type(getattr(policy, name)) is type(value)
                assert getattr(policy, name) == value
            record = policy.provenance[name]
            assert isinstance(record, Provenance)
            assert (record.source, record.as_of, record.status, record.note) == (
                source, date.fromisoformat(as_of), status, note,
            )
        expected_unknowns = (
            "daily_loss_limit", "experiment_loss_limit", "halt_clearers",
            "max_open_exposures", "risk_per_trade",
        )
        assert _call(unknowns, policy) == expected_unknowns
        resolved = {
            name: Provenance("synthetic test fixture", DAY, "measured")
            for name in policy.provenance
        }
        assert _call(unknowns, _call(replace, policy, provenance=resolved)) == ()
        mixed = {
            **resolved,
            "daily_loss_limit": Provenance("synthetic test fixture", DAY, "spec"),
            "risk_per_trade": Provenance("synthetic test fixture", DAY, "assumed"),
            "halt_clearers": Provenance("synthetic test fixture", DAY, "unknown"),
        }
        assert _call(unknowns, _call(replace, policy, provenance=mixed)) == ("halt_clearers", "risk_per_trade")

        # Policy parameters include the allowlist and experiment threshold.
        custom = _fixture(policy, Provenance, experiment_loss_limit=Decimal("0.03"),
                          halt_clearers=("reviewer",))
        custom_state = _call(start, Decimal("10000"), DAY, custom, "reviewer", "custom policy")
        _state(_call(update, custom_state, Decimal("9800"), DAY),
               custom, DAY, "10000", "10000", True, False)
        custom_halt = _call(update, custom_state, Decimal("9700"), DAY)
        _state(custom_halt, custom, DAY, "10000", "10000", True, True)
        with pytest.raises(BadHaltClear):
            _call(restart, custom_halt, Decimal("9700"), DAY, "owner", "not in this allowlist")
        _state(_call(restart, custom_halt, Decimal("9700"), DAY, "reviewer", "authorized"),
               custom, DAY, "10000", "9700", True, False)

        original = dict(policy.provenance)
        copied = _call(replace, policy, provenance=original)
        original["risk_per_trade"] = Provenance("changed caller dict", DAY, "measured")
        del original["halt_clearers"]
        assert copied.provenance == policy.provenance
        assert isinstance(copied.provenance, MappingProxyType)
        with pytest.raises(TypeError):
            copied.provenance["risk_per_trade"] = original["risk_per_trade"]
        with pytest.raises(TypeError):
            del copied.provenance["halt_clearers"]
        for instance in (policy, state, decision, request, gate):
            assert is_dataclass(instance)
            for field in fields(instance):
                with pytest.raises(FrozenInstanceError):
                    _call(setattr, instance, field.name, getattr(instance, field.name))
