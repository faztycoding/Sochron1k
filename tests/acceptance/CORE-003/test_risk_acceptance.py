"""CORE-003 v1.6 acceptance tests derived from the approved risk contract."""

from collections.abc import KeysView, Mapping
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
import faulthandler
import platform
import sys
from threading import Thread
from time import perf_counter

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
    with pytest.raises(error) as caught:
        _call(function, *args, **kwargs)
    assert type(caught.value) is error


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
        ({"lots": Decimal("200")}, {}, ("lots_exceed_sized",)),
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
            _gate(_call(check_entry, altered_request, Decimal("10000"), DAY, altered_state, H001_COSTS),
                  reasons, GateDecision)
        isolated = _call(start, Decimal("100"), DAY, policy, "owner", "isolated sizing fixture")
        small_request = _call(replace, request, lots=Decimal("0.01"))
        _gate(_call(check_entry, small_request, Decimal("100"), DAY, isolated, H001_COSTS, Decimal("0")),
              ("below_min_volume", "lots_exceed_sized"), GateDecision)
        # Loss200 meets daily75 and experiment200; sized.02 still fits.
        _gate(_call(check_entry, request, Decimal("9800"), DAY, state, H001_COSTS),
              ("daily_halt", "experiment_halt"), GateDecision)
        combined_state = _call(replace, state, daily_halted=True, experiment_halted=True)
        combined_request = _call(replace, request, lots=Decimal("0.015"), open_exposures=1)
        _gate(_call(check_entry, combined_request, Decimal("100"), DAY, combined_state, H001_COSTS),
              ("below_min_volume", "daily_halt", "experiment_halt", "lots_exceed_sized",
               "lots_not_on_grid", "max_exposure"), GateDecision)
        # Missing/wrong-side SL must not invent sizing reasons, but retain all other denials.
        for stop, reason in ((None, "missing_stop_loss"), (Decimal("4013"), "stop_loss_wrong_side")):
            changed = _call(replace, combined_request, stop_loss=stop)
            _gate(_call(check_entry, changed, Decimal("100"), DAY, combined_state, H001_COSTS),
                  ("daily_halt", "experiment_halt", "lots_not_on_grid", "max_exposure", reason),
                  GateDecision)

        # Cost budget and supplied model participate in the recomputation.
        budget_state = _call(start, Decimal("9600"), DAY, policy, "owner", "cost fixture")
        _gate(_call(check_entry, request, Decimal("9600"), DAY, budget_state, H001_COSTS), (), GateDecision)
        _gate(_call(check_entry, request, Decimal("9600"), DAY, budget_state, H001_COSTS, Decimal("10")),
              ("lots_exceed_sized",), GateDecision)
        larger_contract = _fixture(H001_COSTS, Provenance, contract_size=Decimal("200"))
        _gate(_call(check_entry, request, Decimal("10000"), DAY, state, larger_contract),
              ("lots_exceed_sized",), GateDecision)
        # Exact subtraction: distance is1.0000000000000000000000000001, not rounded1.
        edge_state = _call(start, Decimal("800"), DAY, policy, "owner", "distance edge")
        edge_request = _call(
            EntryRequest, "long", Decimal("0.02"),
            Decimal("2.0000000000000000000000000001"), Decimal("1"), 0,
        )
        _gate(_call(check_entry, edge_request, Decimal("800"), DAY, edge_state, H001_COSTS),
              ("lots_exceed_sized",), GateDecision)

        for baseline, equity, daily, experiment in _golden()["THRESHOLD_ROWS"]:
            fresh = _call(start, Decimal(baseline), DAY, policy, "owner", "threshold fixture")
            reasons = tuple(name for name, flag in (
                ("daily_halt", daily), ("experiment_halt", experiment),
            ) if flag)
            _gate(_call(check_entry, request, Decimal(equity), DAY, fresh, H001_COSTS), reasons, GateDecision)
        # A custom policy is bound in state; gate must not substitute H001 defaults.
        custom = _fixture(policy, Provenance, risk_per_trade=Decimal("0.005"), max_open_exposures=2)
        custom_state = _call(start, Decimal("10000"), DAY, custom, "owner", "bound policy")
        custom_request = _call(replace, request, lots=Decimal("0.04"), open_exposures=1)
        _gate(_call(check_entry, custom_request, Decimal("10000"), DAY, custom_state, H001_COSTS),
              (), GateDecision)
        _gate(_call(check_entry, _call(replace, custom_request, open_exposures=2),
                    Decimal("10000"), DAY, custom_state, H001_COSTS),
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
    gate = _call(entry, request, Decimal("10000"), DAY, state, H001_COSTS)

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
        (entry, dict(request=request, equity=Decimal("10000"), day=DAY, state=state,
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
            "stop_loss_widened", "stale_state",
        ):
            _call(GateDecision, False, (reason,))

        # Business-denial branches never suppress validation of another argument.
        for candidate in (
            request, _call(replace, request, stop_loss=None),
            _call(replace, request, stop_loss=Decimal("4013")),
        ):
            for selected_state in (state, halted):
                valid = dict(request=candidate, equity=Decimal("10000"), day=DAY, state=selected_state,
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
                with pytest.raises(RiskError) as caught:
                    _call(size, Decimal(equity), Decimal("12"), H001_COSTS, policy)
                assert type(caught.value) is RiskError
        # Range validation applies to per-lot risk, even when the selected lots is zero.
        # 1E999998*100=1E1000000 -> Overflow; R25/per -> floor0.
        with pytest.raises(RiskError) as caught:
            _call(size, Decimal("10000"), Decimal("1E999998"), H001_COSTS, policy)
        assert type(caught.value) is RiskError
        # 1E-1000029*100=1E-1000027 -> Underflow (R25 is normal).
        with pytest.raises(RiskError) as caught:
            _call(size, Decimal("10000"), Decimal("1E-1000029"), H001_COSTS, policy)
        assert type(caught.value) is RiskError
        # Per=1.1E-1000026 is inexact subnormal; reject even though capped lots200
        # would have exact actual2.2E-1000024.
        with pytest.raises(RiskError) as caught:
            _call(size, Decimal("10000"), Decimal("1.1E-1000028"), H001_COSTS, policy)
        assert type(caught.value) is RiskError
        # Per=1E-1000025 is exact, cap=.01, actual=1E-1000027 -> Underflow.
        tiny_cap = _fixture(H001_COSTS, Provenance, volume_max=Decimal("0.01"))
        with pytest.raises(RiskError) as caught:
            _call(size, Decimal("10000"), Decimal("1E-1000027"), tiny_cap, policy)
        assert type(caught.value) is RiskError


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

@pytest.fixture
def v13(monkeypatch):
    names = (
        "H001_RISK", "RiskPolicy", "HaltState", "EntryRequest", "SizeDecision", "GateDecision",
        "size_position", "start_experiment", "update_equity", "restart_experiment",
        "check_entry", "check_stop_change", "unknowns", "RiskError", "BadPolicy",
        "BadEquity", "BadStop", "TimeReversal",
    )
    return dict(zip(names, _api(monkeypatch, "AC-06", *names), strict=True))


def _v13_calls(api):
    """Fresh valid objects for each negative row; never mutate the H001 singletons."""
    from sochron.costs import H001_COSTS

    policy = _call(replace, api["H001_RISK"])
    model = _call(replace, H001_COSTS)
    state = _call(api["start_experiment"], Decimal("10000"), DAY, policy, "owner", "fixture")
    halted = _call(api["update_equity"], state, Decimal("9800"), DAY)
    request = _call(api["EntryRequest"], "long", Decimal("0.02"),
                    Decimal("4012.90"), Decimal("4000.90"), 0)
    return {
        "RiskPolicy": {field.name: getattr(policy, field.name) for field in fields(policy)},
        "HaltState": {field.name: getattr(state, field.name) for field in fields(state)},
        "EntryRequest": {field.name: getattr(request, field.name) for field in fields(request)},
        "SizeDecision": dict(lots=Decimal("0.02"), risk_money=Decimal("25"),
                             risk_per_lot=Decimal("1200"), actual_risk=Decimal("24"), reason="ok"),
        "GateDecision": dict(allowed=False, reasons=("daily_halt",)),
        "size_position": dict(equity=Decimal("10000"), stop_distance=Decimal("12"),
                              model=model, policy=policy, cost_per_lot=Decimal("0")),
        "start_experiment": dict(equity=Decimal("10000"), day=DAY, policy=policy,
                                 authorized_by="owner", reason="fixture"),
        "update_equity": dict(state=state, equity=Decimal("10000"), day=DAY),
        "restart_experiment": dict(state=halted, equity=Decimal("9800"), day=DAY,
                                   authorized_by="owner", reason="fixture"),
        "check_entry": dict(request=request, equity=Decimal("10000"), day=DAY,
                            state=state, model=model, cost_per_lot=Decimal("0")),
        "check_stop_change": dict(side="long", current_stop=Decimal("4000.90"),
                                  new_stop=Decimal("4001")),
        "unknowns": dict(policy=policy),
    }


def _changed_call(api, slot, value):
    """slot = (public API, dotted field path); change exactly that leaf."""
    public, path = slot
    arguments = _v13_calls(api)[public]
    parts = path.split(".")
    if len(parts) == 1:
        arguments[path] = value
    else:
        instance = arguments[parts[0]]
        for part in parts[1:-1]:
            instance = getattr(instance, part)
        object.__setattr__(instance, parts[-1], value)
    return api[public], arguments


# Every Decimal slot, including at-use fields. Errors are intentionally explicit.
_NUMERIC_SLOTS = (
    *((public, "equity", "BadEquity") for public in (
        "size_position", "start_experiment", "update_equity", "restart_experiment", "check_entry",
    )),
    *(("HaltState", field, "BadEquity")
      for field in ("day_start_equity", "experiment_start_equity")),
    ("size_position", "stop_distance", "BadStop"),
    *(("EntryRequest", field, "BadStop") for field in ("entry_price", "stop_loss")),
    *(("check_stop_change", field, "BadStop") for field in ("current_stop", "new_stop")),
    *(("RiskPolicy", field, "BadPolicy")
      for field in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit")),
    *((public, "cost_per_lot", "BadPolicy") for public in ("size_position", "check_entry")),
    ("EntryRequest", "lots", "RiskError"),
    *(("SizeDecision", field, "RiskError")
      for field in ("lots", "risk_money", "risk_per_lot", "actual_risk")),
    *((public, "model." + field, "RiskError")
      for public in ("size_position", "check_entry")
      for field in ("contract_size", "volume_min", "volume_step", "volume_max")),
    *(("check_entry", "request." + field, error) for field, error in (
        ("lots", "RiskError"), ("entry_price", "BadStop"), ("stop_loss", "BadStop"),
    )),
    *((public, "state." + field, "BadEquity")
      for public in ("check_entry", "update_equity", "restart_experiment")
      for field in ("day_start_equity", "experiment_start_equity")),
    *((public, "policy." + field, "BadPolicy")
      for public in ("HaltState", "size_position", "start_experiment", "unknowns")
      for field in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit")),
    *((public, "state.policy." + field, "BadPolicy")
      for public in ("check_entry", "update_equity", "restart_experiment")
      for field in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit")),
)


def _slot_id(row):
    return ".".join(row[:2])


def _timed_rejection(error, function, arguments, record_property, capsys):
    """F14: time only the public invocation, transport every worker outcome."""
    environment = f"{platform.platform()}; {sys.implementation.name} {platform.python_version()} via uv"
    record_property("oversized_environment", environment)
    outcome = []

    def invoke():
        with localcontext() as caller:
            _hostile(caller)
            before = _context_state()
            started = perf_counter()
            try:
                function(**arguments)
            except BaseException as caught:
                # Transport even unexpected exceptions to the test thread; none is swallowed.
                elapsed = perf_counter() - started
                outcome.append((elapsed, type(caught), _context_state() == before))
            else:
                elapsed = perf_counter() - started
                outcome.append((elapsed, None, _context_state() == before))

    worker = Thread(target=invoke, daemon=True)
    # tests-r3 F3: pytest captures fd 2, and a watchdog exit discards that capture.
    # Arm, run and cancel with capture disabled, so a hang ends with a visible traceback.
    with capsys.disabled():
        faulthandler.dump_traceback_later(20, exit=True)
        try:
            worker.start()
            worker.join(timeout=10)
        finally:
            faulthandler.cancel_dump_traceback_later()
    if worker.is_alive():
        record_property("oversized_elapsed_seconds", "unfinished after join(timeout=10)")
        print(f"oversized rejection: {environment}; unfinished after join(timeout=10)")
        pytest.fail("oversized rejection worker still alive after join(timeout=10)")
    assert len(outcome) == 1, "worker supplied no outcome"
    elapsed, actual_error, context_unchanged = outcome[0]
    record_property("oversized_elapsed_seconds", elapsed)
    print(f"oversized rejection: {environment}; elapsed={elapsed:.9f} s; exception={actual_error}")
    assert actual_error is error, f"expected {error.__name__}, got {actual_error}; return is forbidden"
    assert elapsed < 1.000, f"oversized rejection took {elapsed:.9f} s (must be < 1.000 s)"
    assert context_unchanged, "public call changed the caller's Decimal context"


# Ratios cannot have a positive adjusted exponent and remain in (0,1).
# An oversized positive volume_min or negative volume_max cannot also satisfy
# min<=max with the other endpoint in-bound. Use the opposite exponent there.
_OVERSIZED_CASES = tuple(
    (row, bound)
    for row in _NUMERIC_SLOTS
    for bound in _golden()["BOUND_REJECTED"] + (("positive_adjusted", "1E+1100001"),)
    if not (bound[0] == "negative_adjusted" and row[1] == "model.volume_max")
    if not (bound[0] == "positive_adjusted" and (
        row[1].split(".")[-1] in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit")
        or row[1] == "model.volume_min"
    ))
)


@pytest.mark.parametrize("row,bound", _OVERSIZED_CASES,
                         ids=[_slot_id(row) + "." + bound[0] for row, bound in _OVERSIZED_CASES])
def test_ac06_oversized_decimal_per_slot(v13, row, bound, record_property, capsys):
    public, field, error = row
    # All creation/import/setup occurs before the worker's timed public call.
    value = Decimal(bound[1])
    function, arguments = _changed_call(v13, (public, field), value)
    if field == "model.contract_size" and bound[0] in ("negative_adjusted", "positive_adjusted"):
        # Compensating distance keeps per-lot risk displayable: without the
        # model bound these calls return instead of raising a display error.
        distance, entry, stop = _golden()["MODEL_EXPONENT_COMPENSATION"][bound[0]]
        if public == "size_position":
            arguments["stop_distance"] = Decimal(distance)
        else:
            arguments["request"] = _call(
                replace, arguments["request"], entry_price=Decimal(entry), stop_loss=Decimal(stop),
            )
    _timed_rejection(v13[error], function, arguments, record_property, capsys)


def test_ac06_extreme_equity_rejection_deadline(v13, record_property, capsys):
    value = Decimal("1E-999999999")
    function, arguments = _changed_call(v13, ("size_position", "equity"), value)
    _timed_rejection(v13["BadEquity"], function, arguments, record_property, capsys)


@pytest.mark.parametrize("bound", _golden()["BOUND_ACCEPTED"] + (
    ("positive_adjusted", "1E+1100000"),
    ("one_with_trailing_zeros", "1." + "0" * 999),
), ids=lambda row: row[0])
def test_ac06_inclusive_decimal_bound_accepts_original_representation(v13, bound):
    value = Decimal(bound[1])
    calls = _v13_calls(v13)
    # No deadline for accepted input and no need for million-digit rational arithmetic.
    for public, names in (
        ("HaltState", ("day_start_equity", "experiment_start_equity")),
        ("EntryRequest", ("lots", "entry_price", "stop_loss")),
        ("SizeDecision", ("lots", "risk_money", "risk_per_lot", "actual_risk")),
        ("start_experiment", ("equity",)),
    ):
        for name in names:
            result = _call(v13[public], **{**calls[public], name: value})
            actual = result.day_start_equity if name == "equity" else getattr(result, name)
            assert type(actual) is Decimal and actual == value
    if bound[0] not in ("positive_adjusted", "one_with_trailing_zeros"):
        for name in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit"):
            result = _call(v13["RiskPolicy"], **{**calls["RiskPolicy"], name: value})
            assert getattr(result, name) == value


@pytest.mark.parametrize("literal", ("0E-999999999", "0E+999999999"))
def test_ac06_zero_ignores_adjusted_exponent(v13, literal):
    value = Decimal(literal)
    calls = _v13_calls(v13)
    request = _call(v13["EntryRequest"], **{**calls["EntryRequest"], "lots": value})
    assert request.lots == Decimal("0")
    decision = _call(v13["SizeDecision"], value, value, value, value, "below_min_volume")
    assert all(getattr(decision, name) == Decimal("0")
               for name in ("lots", "risk_money", "risk_per_lot", "actual_risk"))
    arguments = calls["check_entry"]
    arguments["request"] = _call(replace, arguments["request"], stop_loss=None)
    arguments["cost_per_lot"] = value
    _gate(_call(v13["check_entry"], **arguments), ("missing_stop_loss",), v13["GateDecision"])

@pytest.mark.parametrize("row", _golden()["TEMPORAL_ROWS"])
def test_ac04_gate_day_and_complete_temporal_reasons(v13, row):
    equity, daily, experiment, day, expected = row
    arguments = _v13_calls(v13)["check_entry"]
    original = arguments["state"]
    # Reach the two latch states independently through public transitions.
    if experiment:
        original = _call(v13["update_equity"], original, Decimal("9800"), DAY)
    elif daily:
        original = _call(v13["update_equity"], original, Decimal("9925"), DAY)
    arguments.update(state=original, equity=Decimal(equity), day=date(2026, 10, day))
    before = _snapshot(original)
    request_before = _snapshot(arguments["request"])
    with localcontext() as caller:
        _hostile(caller)
        if expected == "TimeReversal":
            _reject(v13["TimeReversal"], v13["check_entry"], **arguments)
        else:
            _gate(_call(v13["check_entry"], **arguments), expected, v13["GateDecision"])
    assert _snapshot(original) == before
    assert _snapshot(arguments["request"]) == request_before


def test_ac04_rollover_control_preserves_stale_original(v13):
    arguments = _v13_calls(v13)["check_entry"]
    halted = _call(v13["update_equity"], arguments["state"], Decimal("9925"), DAY)
    before = _snapshot(halted)
    rolled = _call(v13["update_equity"], halted, Decimal("10000"), NEXT_DAY)
    _state(rolled, halted.policy, NEXT_DAY, "10000", "10000", False, False)
    for state, reasons in ((rolled, ()), (halted, ("daily_halt", "stale_state"))):
        _gate(_call(v13["check_entry"], **{**arguments, "state": state, "day": NEXT_DAY}),
              reasons, v13["GateDecision"])
    assert _snapshot(halted) == before


@pytest.mark.parametrize("row", _golden()["DISTINCT_BASELINE_ROWS"])
def test_ac02_ac04_same_day_uses_distinct_daily_and_experiment_baselines(v13, row):
    opening, equity, daily, experiment = row
    arguments = _v13_calls(v13)["check_entry"]
    state = _call(v13["update_equity"], arguments["state"], Decimal(opening), NEXT_DAY)
    before = _snapshot(state)
    with localcontext() as caller:
        _hostile(caller)
        updated = _call(v13["update_equity"], state, Decimal(equity), NEXT_DAY)
        _state(updated, state.policy, NEXT_DAY, opening, "10000", daily, experiment)
        reasons = tuple(name for name, flag in (
            ("daily_halt", daily), ("experiment_halt", experiment),
        ) if flag)
        _gate(_call(v13["check_entry"], **{
            **arguments, "state": state, "equity": Decimal(equity), "day": NEXT_DAY,
        }), reasons, v13["GateDecision"])
    assert _snapshot(state) == before


def test_ac03_restart_uses_distinct_daily_baseline(v13):
    halted = _v13_calls(v13)["restart_experiment"]["state"]
    recovered = _call(v13["update_equity"], halted, Decimal("10500"), NEXT_DAY)
    before = _snapshot(recovered)
    # Daily loss10500-10421.25=78.75=.0075*10500. Experiment rebases on restart.
    result = _call(v13["restart_experiment"], recovered, Decimal("10421.25"),
                   NEXT_DAY, "owner", "reviewed restart")
    _state(result, recovered.policy, NEXT_DAY, "10500", "10421.25", True, False)
    assert _snapshot(recovered) == before


@pytest.mark.parametrize("row", _golden()["CUSTOM_LIMIT_ROWS"])
def test_ac02_ac04_use_bound_non_h001_loss_limits(v13, row):
    from sochron.costs import Provenance

    equity, daily, experiment = row
    arguments = _v13_calls(v13)["check_entry"]
    policy = _fixture(v13["H001_RISK"], Provenance, daily_loss_limit=Decimal("0.01"),
                      experiment_loss_limit=Decimal("0.03"))
    state = _call(v13["start_experiment"], Decimal("10000"), DAY, policy, "owner", "custom limits")
    before = _snapshot(state)
    updated = _call(v13["update_equity"], state, Decimal(equity), DAY)
    _state(updated, policy, DAY, "10000", "10000", daily, experiment)
    reasons = tuple(name for name, flag in (
        ("daily_halt", daily), ("experiment_halt", experiment),
    ) if flag)
    _gate(_call(v13["check_entry"], **{**arguments, "state": state, "equity": Decimal(equity)}),
          reasons, v13["GateDecision"])
    assert _snapshot(state) == before


class _RatioDecimal(Decimal):
    def as_integer_ratio(self):
        return (1, 100)


class _Count(int):
    def __ge__(self, other):
        return False


class _Name(str):
    def __eq__(self, other):
        return True

    __hash__ = str.__hash__


class _Names(tuple):
    def __contains__(self, item):
        return True


class _Day(date):
    def __eq__(self, other):
        return False

    __hash__ = date.__hash__


@pytest.mark.parametrize("row", _NUMERIC_SLOTS, ids=_slot_id)
def test_ac06_decimal_subclass_rejected_in_every_slot(v13, row):
    public, field, _ = row
    # Exact-type validation must precede this misleading rational representation.
    function, arguments = _changed_call(v13, (public, field), _RatioDecimal("0.125"))
    _reject(TypeError, function, **arguments)


_TYPE_SLOTS = (
    ("RiskPolicy", "max_open_exposures", _Count(1)),
    ("EntryRequest", "open_exposures", _Count(0)),
    ("check_entry", "request.open_exposures", _Count(7)),
    ("RiskPolicy", "halt_clearers", _Names(("owner",))),
    ("RiskPolicy", "halt_clearers", (_Name("owner"),)),
    ("GateDecision", "reasons", _Names(("daily_halt",))),
    ("GateDecision", "reasons", (_Name("daily_halt"),)),
    ("SizeDecision", "reason", _Name("ok")),
    ("EntryRequest", "side", _Name("long")),
    ("check_entry", "request.side", _Name("long")),
    ("check_stop_change", "side", _Name("long")),
    *((public, "day", _Day(2026, 10, 22)) for public in (
        "HaltState", "start_experiment", "update_equity", "restart_experiment", "check_entry",
    )),
    *((public, "state.day", _Day(2026, 10, 22))
      for public in ("check_entry", "update_equity", "restart_experiment")),
    *((public, field, _Name(value))
      for public in ("start_experiment", "restart_experiment")
      for field, value in (("authorized_by", "owner"), ("reason", "valid"))),
    # Malicious equality can otherwise authenticate an unlisted name.
    *((public, "authorized_by", _Name("codex"))
      for public in ("start_experiment", "restart_experiment")),
    *(("check_entry", "day", value) for value in (
        "2026-10-22", None, 22, datetime(2026, 10, 22),
    )),
)


@pytest.mark.parametrize("public,field,value", _TYPE_SLOTS)
def test_ac06_exact_scalar_and_container_types(v13, public, field, value):
    function, arguments = _changed_call(v13, (public, field), value)
    _reject(TypeError, function, **arguments)


_OBJECT_SLOTS = (
    ("HaltState", "policy"),
    ("size_position", "policy"), ("size_position", "model"),
    ("start_experiment", "policy"), ("unknowns", "policy"),
    ("check_entry", "request"), ("check_entry", "state"), ("check_entry", "model"),
    ("update_equity", "state"), ("restart_experiment", "state"),
    *((public, "state.policy") for public in ("check_entry", "update_equity", "restart_experiment")),
)


@pytest.mark.parametrize("public,path", _OBJECT_SLOTS)
def test_ac06_exact_public_object_types(v13, public, path):
    arguments = _v13_calls(v13)[public]
    parts = path.split(".")
    original = arguments[parts[0]]
    for part in parts[1:]:
        original = getattr(original, part)
    subclass = type("Derived" + type(original).__name__, (type(original),), {})
    # Construct the input without relying on subclass constructors being allowed.
    derived = object.__new__(subclass)
    for field in fields(original):
        object.__setattr__(derived, field.name, getattr(original, field.name))
    if len(parts) == 1:
        arguments[path] = derived
    else:
        object.__setattr__(arguments[parts[0]], parts[1], derived)
    _reject(TypeError, v13[public], **arguments)


class _SnapshotMapping(Mapping):
    """Valid custom Mapping; expose any second read of a value or second traversal."""
    def __init__(self, data):
        self.data = data
        self.reads = {key: 0 for key in data}
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        self.reads[key] += 1
        if self.reads[key] > 1:
            return "second read is not the validated snapshot"
        return self.data[key]


@pytest.mark.parametrize("container", ("dict", "proxy", "mapping"))
def test_ac06_provenance_mapping_copied_once_and_frozen(v13, container):
    from sochron.costs import Provenance

    original = dict(v13["H001_RISK"].provenance)
    source = original if container == "dict" else (
        MappingProxyType(original) if container == "proxy" else _SnapshotMapping(original)
    )
    policy = _call(replace, v13["H001_RISK"], provenance=source)
    assert type(policy.provenance) is MappingProxyType
    assert policy.provenance == v13["H001_RISK"].provenance
    if container == "mapping":
        assert source.iterations == 1
        assert set(source.reads.values()) == {1}
    original["risk_per_trade"] = Provenance("changed backing dict", DAY, "measured")
    del original["halt_clearers"]
    assert policy.provenance == v13["H001_RISK"].provenance
    with pytest.raises(TypeError):
        policy.provenance["risk_per_trade"] = original["risk_per_trade"]
    with pytest.raises(TypeError):
        del policy.provenance["halt_clearers"]


def test_ac06_provenance_valid_pairs_are_not_a_mapping(v13):
    pairs = list(v13["H001_RISK"].provenance.items())
    _reject(TypeError, replace, v13["H001_RISK"], provenance=pairs)


@pytest.mark.parametrize("subclass_value", (False, True))
def test_ac06_validates_copied_mapping_values(v13, subclass_value):
    from sochron.costs import Provenance

    values = dict(v13["H001_RISK"].provenance)
    derived_type = type("DerivedProvenance", (Provenance,), {})
    derived = object.__new__(derived_type)
    for field in fields(values["risk_per_trade"]):
        object.__setattr__(derived, field.name, getattr(values["risk_per_trade"], field.name))
    values["risk_per_trade"] = derived if subclass_value else "not Provenance"
    _reject(v13["BadPolicy"], replace, v13["H001_RISK"], provenance=_SnapshotMapping(values))

_REQUEST_DEFECTS = (
    ("side", "buy", "RiskError"), ("side", 1, "TypeError"),
    ("open_exposures", -1, "RiskError"), ("open_exposures", True, "TypeError"),
    ("lots", Decimal("NaN"), "RiskError"), ("lots", 1, "TypeError"),
    ("entry_price", Decimal("Infinity"), "BadStop"), ("entry_price", "4012.90", "TypeError"),
    ("stop_loss", Decimal("0"), "BadStop"), ("stop_loss", "4000.90", "TypeError"),
)
_STATE_DEFECTS = (
    ("day", datetime(2026, 10, 22), "TypeError"),
    ("daily_halted", 1, "TypeError"), ("experiment_halted", 1, "TypeError"),
    ("policy", None, "TypeError"),
    *((name, value, error) for name in ("day_start_equity", "experiment_start_equity")
      for value, error in ((Decimal("0"), "BadEquity"), (Decimal("NaN"), "BadEquity"),
                           (Decimal("Infinity"), "BadEquity"), ("10000", "TypeError"))),
    *(("policy." + name, Decimal("0"), "BadPolicy")
      for name in ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit")),
    ("policy.max_open_exposures", 0, "BadPolicy"),
    ("policy.max_open_exposures", _Count(1), "TypeError"),
    ("policy.halt_clearers", (), "BadPolicy"),
    ("policy.halt_clearers", _Names(("owner",)), "TypeError"),
    ("policy.halt_clearers", (_Name("owner"),), "TypeError"),
    ("policy.provenance", {}, "BadPolicy"),
)


def _refusal_branch(api, arguments, branch):
    if branch == "halted":
        arguments["state"] = _call(api["update_equity"], arguments["state"], Decimal("9800"), DAY)
    elif branch == "missing_stop":
        arguments["request"] = _call(replace, arguments["request"], stop_loss=None)
    elif branch == "wrong_side_stop":
        arguments["request"] = _call(replace, arguments["request"], stop_loss=Decimal("4013"))
    elif branch == "stale":
        arguments["day"] = NEXT_DAY


def _mutate_field(instance, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        instance = getattr(instance, part)
    object.__setattr__(instance, parts[-1], value)


@pytest.mark.parametrize("branch", ("ordinary", "halted", "missing_stop", "wrong_side_stop", "stale"))
@pytest.mark.parametrize("field,value,error", _REQUEST_DEFECTS)
def test_ac06_revalidates_every_request_field_at_use(v13, branch, field, value, error):
    arguments = _v13_calls(v13)["check_entry"]
    _refusal_branch(v13, arguments, branch)
    _mutate_field(arguments["request"], field, value)
    _reject(v13[error] if error != "TypeError" else TypeError, v13["check_entry"], **arguments)


@pytest.mark.parametrize("public,branch", (
    ("check_entry", "ordinary"), ("check_entry", "halted"),
    ("check_entry", "missing_stop"), ("check_entry", "wrong_side_stop"), ("check_entry", "stale"),
    ("update_equity", "ordinary"), ("restart_experiment", "ordinary"),
))
@pytest.mark.parametrize("field,value,error", _STATE_DEFECTS)
def test_ac06_revalidates_every_state_field_at_use(v13, public, branch, field, value, error):
    arguments = _v13_calls(v13)[public]
    if public == "check_entry":
        _refusal_branch(v13, arguments, branch)
    # restart fixtures are genuinely experiment-halted with valid authorization.
    if public == "restart_experiment" and field == "policy.halt_clearers" and value == ():
        # Duplicate names violate policy without also removing authorization.
        value = ("owner", "owner")
    _mutate_field(arguments["state"], field, value)
    _reject(v13[error] if error != "TypeError" else TypeError, v13[public], **arguments)


@pytest.mark.parametrize("branch", ("halted", "missing_stop", "wrong_side_stop", "stale"))
@pytest.mark.parametrize("target,field,error", (
    ("request", "lots", "RiskError"), ("request", "entry_price", "BadStop"),
    ("request", "stop_loss", "BadStop"),
    ("state", "day_start_equity", "BadEquity"),
    ("state", "experiment_start_equity", "BadEquity"),
    ("state", "policy.risk_per_trade", "BadPolicy"),
))
def test_ac06_oversized_at_use_before_early_denials(v13, branch, target, field, error, record_property,
                                                   capsys):
    arguments = _v13_calls(v13)["check_entry"]
    _refusal_branch(v13, arguments, branch)
    value = Decimal("0.1" + "0" * 1000)
    _mutate_field(arguments[target], field, value)
    _timed_rejection(v13[error], v13["check_entry"], arguments, record_property, capsys)


@pytest.mark.parametrize("branch", ("halted", "missing_stop", "wrong_side_stop", "stale"))
@pytest.mark.parametrize("field,value,error", (
    ("cost_per_lot", Decimal("-1"), "BadPolicy"),
    ("equity", Decimal("0"), "BadEquity"),
    ("cost_per_lot", 0, "TypeError"),
))
def test_ac06_refusal_never_hides_independent_bad_argument(v13, branch, field, value, error):
    arguments = _v13_calls(v13)["check_entry"]
    _refusal_branch(v13, arguments, branch)
    arguments[field] = value
    _reject(v13[error] if error != "TypeError" else TypeError, v13["check_entry"], **arguments)


@pytest.mark.parametrize("public", ("update_equity", "restart_experiment"))
def test_ac06_inclusive_coefficient_equity_in_halt_arithmetic(v13, public):
    arguments = _v13_calls(v13)[public]
    arguments["equity"] = Decimal("1." + "0" * 999)
    original = arguments["state"]
    before = _snapshot(original)
    with localcontext() as caller:
        _hostile(caller)
        result = _call(v13[public], **arguments)
    if public == "update_equity":
        # Loss9999 exceeds daily75 and experiment200; both baselines stay10000.
        _state(result, original.policy, DAY, "10000", "10000", True, True)
    else:
        # Same-day restart keeps daily baseline/latch; experiment rebases to1.
        _state(result, original.policy, DAY, "10000", "1", True, False)
        assert result.policy is original.policy
    assert _snapshot(original) == before


def test_ac06_inclusive_coefficient_budget_in_gate_arithmetic(v13):
    arguments = _v13_calls(v13)["check_entry"]
    arguments["cost_per_lot"] = Decimal("0." + "1" * 1000)
    # 1200 < per < 1201, so .02*per <24.02 <25 and .03*per >36 >25.
    with localcontext() as caller:
        _hostile(caller)
        _gate(_call(v13["check_entry"], **arguments), (), v13["GateDecision"])
        arguments["request"] = _call(replace, arguments["request"], lots=Decimal("0.03"))
        _gate(_call(v13["check_entry"], **arguments), ("lots_exceed_sized",), v13["GateDecision"])


_MODEL_DOMAIN_DEFECTS = (
    *((field, value) for field in ("contract_size", "volume_step", "volume_min")
      for value in ("0", "-0.01")),
    ("volume_max", "0.005"),  # H001 volume_min=.01, so max < min.
)


@pytest.mark.parametrize("public,branch", (
    ("size_position", "ordinary"), ("check_entry", "ordinary"),
    ("check_entry", "halted"), ("check_entry", "missing_stop"),
    ("check_entry", "wrong_side_stop"), ("check_entry", "stale"),
))
@pytest.mark.parametrize("field,literal", _MODEL_DOMAIN_DEFECTS)
def test_ac06_revalidates_model_domain_before_deciding(v13, public, branch, field, literal):
    arguments = _v13_calls(v13)[public]
    if public == "check_entry":
        _refusal_branch(v13, arguments, branch)
    # Fresh copy from _v13_calls: never corrupt the shared H001 model.
    object.__setattr__(arguments["model"], field, Decimal(literal))
    _reject(v13["RiskError"], v13[public], **arguments)


@pytest.mark.parametrize("literal", ("0E-999999999999999999", "-0E-999999999999999999"))
def test_ac01_ac04_zero_budget_extreme_exponent_is_arithmetic_zero(v13, literal):
    calls = _v13_calls(v13)
    zero = Decimal(literal)
    with localcontext() as caller:
        _hostile(caller)
        sizing = calls["size_position"]
        expected = _call(v13["size_position"], **sizing)
        actual = _call(v13["size_position"], **{**sizing, "cost_per_lot": zero})
        assert actual == expected
        _money(actual.lots, "0.02")
        _money(actual.risk_money, "25")
        _money(actual.risk_per_lot, "1200")
        _money(actual.actual_risk, "24")
        assert actual.reason == "ok"
        _gate(_call(v13["check_entry"], **{**calls["check_entry"], "cost_per_lot": zero}),
              (), v13["GateDecision"])


@pytest.mark.parametrize("public,path,error", (
    ("EntryRequest", "open_exposures", "RiskError"),
    ("check_entry", "request.open_exposures", "RiskError"),
    ("RiskPolicy", "max_open_exposures", "BadPolicy"),
    *((public, "policy.max_open_exposures", "BadPolicy")
      for public in ("HaltState", "size_position", "start_experiment", "unknowns")),
    *((public, "state.policy.max_open_exposures", "BadPolicy")
      for public in ("check_entry", "update_equity", "restart_experiment")),
))
def test_ac06_huge_negative_counts_keep_contract_errors(v13, public, path, error):
    # Construct in the body so pytest never stringifies the 5,001-digit integer as an ID.
    function, arguments = _changed_call(v13, (public, path), -(10**5000))
    _reject(v13[error], function, **arguments)


class _HookMapping(Mapping):
    """A valid provenance Mapping whose every read path runs the attack (tests-r3 F1).

    keys(), __iter__, __getitem__ and __len__ each call the action, so the Mapping
    mixins built on them (items(), values(), get(), __contains__, __eq__) and every
    copy strategy (dict(m), {**m}, iteration plus lookup) run it as well. ``calls``
    counts action runs; ``traversals`` counts __iter__ calls, one per full read.
    """
    def __init__(self, data, action):
        self.data = data
        self.action = action
        self.calls = 0
        self.traversals = 0

    def _run(self):
        self.calls += 1
        self.action(self)

    def __getitem__(self, key):
        self._run()
        return self.data[key]

    def __iter__(self):
        self.traversals += 1
        self._run()
        return iter(self.data)

    def __len__(self):
        self._run()
        return len(self.data)

    def keys(self):
        self._run()
        # A live view of this Mapping: iterating it goes through __iter__ again.
        return KeysView(self)


@pytest.mark.parametrize("proxy", (False, True))
@pytest.mark.parametrize("attack", ("side", "policy", "nan_lots"))
def test_ac04_ac06_provenance_callback_cannot_bypass_gate(v13, proxy, attack):
    arguments = _v13_calls(v13)["check_entry"]
    state, request = arguments["state"], arguments["request"]
    if attack == "side":
        request = _call(replace, request, stop_loss=Decimal("4024.90"))
        arguments["request"] = request
        _gate(_call(v13["check_entry"], **arguments), ("stop_loss_wrong_side",), v13["GateDecision"])
        action = lambda hook: object.__setattr__(request, "side", "buy")
        attacked = lambda: request.side == "buy"
    elif attack == "policy":
        request = _call(replace, request, lots=Decimal("41.66"))
        arguments["request"] = request
        _gate(_call(v13["check_entry"], **arguments), ("lots_exceed_sized",), v13["GateDecision"])
        substituted = _call(replace, v13["H001_RISK"])
        object.__setattr__(substituted, "risk_per_trade", Decimal("5"))
        action = lambda hook: object.__setattr__(state, "policy", substituted)
        attacked = lambda: state.policy is substituted
    else:
        _gate(_call(v13["check_entry"], **arguments), (), v13["GateDecision"])
        action = lambda hook: object.__setattr__(request, "lots", Decimal("NaN"))
        attacked = lambda: request.lots.is_nan()
    hook = _HookMapping(dict(state.policy.provenance), action)
    object.__setattr__(state.policy, "provenance", MappingProxyType(hook) if proxy else hook)
    try:
        decision = _call(v13["check_entry"], **arguments)
    except v13["RiskError"] as caught:
        # No plain ValueError/TypeError escape; side and lots have the base error.
        if attack != "policy":
            assert type(caught) is v13["RiskError"]
    else:
        assert decision.allowed is False
        assert decision.reasons
    # tests-r3 F1: the attack ran, whichever read path the gate used.
    assert hook.calls >= 1
    assert attacked()


@pytest.mark.parametrize("proxy", (False, True))
def test_ac03_restart_keeps_policy_validated_before_provenance_reread(v13, proxy):
    arguments = _v13_calls(v13)["restart_experiment"]
    state = arguments["state"]
    validated_policy = state.policy
    # A valid but more permissive substitute makes identity checking necessary:
    # simply validating the replacement on a later read would still be wrong.
    substituted = _call(replace, v13["H001_RISK"], risk_per_trade=Decimal("0.5"))

    def swap_on_reread(hook):
        # The first full read is clean; any later traversal swaps the state's policy.
        if hook.traversals > 1:
            object.__setattr__(state, "policy", substituted)

    hook = _HookMapping(dict(validated_policy.provenance), swap_on_reread)
    object.__setattr__(validated_policy, "provenance", MappingProxyType(hook) if proxy else hook)
    result = _call(v13["restart_experiment"], **arguments)
    assert result.policy is validated_policy
    assert result.policy.risk_per_trade == Decimal("0.0025")
    assert result.day == DAY
    _money(result.day_start_equity, "10000")
    _money(result.experiment_start_equity, "9800")
    assert result.daily_halted is True
    assert result.experiment_halted is False
    # tests-r3 F1: the call read the hook (v1.6 exact-str keys need a traversal),
    # so any reread of the provenance would have swapped the policy.
    assert hook.calls >= 1
    assert hook.traversals >= 1


def test_ac06_large_coefficient_small_adjusted_rejection_deadline(v13, record_property, capsys):
    # 30M digits bounds routine memory use. The adjusted exponent is -1, so an
    # exponent-only check cannot reject this input. Construction is not timed.
    value = Decimal("0." + "7" * 30_000_000)
    assert value.adjusted() == -1
    function, arguments = _changed_call(v13, ("size_position", "equity"), value)
    _timed_rejection(v13["BadEquity"], function, arguments, record_property, capsys)


def test_ac01_ac04_sized_lots_over_coefficient_bound_keeps_gate_exact(v13):
    from sochron.costs import H001_COSTS, Provenance

    row = _golden()["EXACT_LOTS_BOUND_CASE"]
    step, sized, permitted = (Decimal(row[key]) for key in ("step", "sized", "permitted"))
    assert len(step.as_tuple().digits) == 1000
    assert len(sized.as_tuple().digits) == 1002
    assert len(permitted.as_tuple().digits) == 1000
    assert Fraction(sized) == 199 * Fraction(step)
    assert Fraction(permitted) == 9 * Fraction(step)
    model = _fixture(H001_COSTS, Provenance, volume_step=step, volume_min=step)
    policy = _call(replace, v13["H001_RISK"])
    equity = Decimal("1E8")
    state = _call(v13["start_experiment"], equity, DAY, policy, "owner", "exact lots bound")
    request = _call(v13["EntryRequest"], "long", permitted, Decimal("4007"), Decimal("4000"), 0)
    with localcontext() as caller:
        _hostile(caller)
        _reject(v13["RiskError"], v13["size_position"], equity, Decimal("7"), model, policy)
        _gate(_call(v13["check_entry"], request, equity, DAY, state, model), (), v13["GateDecision"])
        too_large = _call(replace, request, lots=Decimal("200"))
        _gate(_call(v13["check_entry"], too_large, equity, DAY, state, model),
              ("lots_exceed_sized", "lots_not_on_grid"), v13["GateDecision"])


# Contract v1.6 (review r2 F4): provenance keys must be exactly str. Construction
# plus every policy consumer named in the v1.4 row.
_PROVENANCE_PATHS = (
    ("RiskPolicy", "provenance"),
    *((public, "policy.provenance")
      for public in ("HaltState", "size_position", "start_experiment", "unknowns")),
    *((public, "state.policy.provenance")
      for public in ("check_entry", "update_equity", "restart_experiment")),
)


class _EqualityHookKey(str):
    """A provenance key equal to its text; every equality test runs caller code."""
    __hash__ = str.__hash__

    def __eq__(self, other):
        self.effects.append(other)
        self.action()
        return str.__eq__(self, other)


def _path_owner(arguments, path):
    """The object that holds the leaf of a dotted path, or None for an argument."""
    parts = path.split(".")
    if len(parts) == 1:
        return None
    owner = arguments[parts[0]]
    for part in parts[1:-1]:
        owner = getattr(owner, part)
    return owner


@pytest.mark.parametrize("container", ("dict", "proxy"))
@pytest.mark.parametrize("key_kind", ("str_subclass", "int"))
@pytest.mark.parametrize("public,path", _PROVENANCE_PATHS)
def test_ac06_provenance_keys_must_be_exact_str(v13, public, path, key_kind, container):
    good = dict(v13["H001_RISK"].provenance)
    record = good["risk_per_trade"]
    if key_kind == "str_subclass":
        # Review r2 R4: the key equals "risk_per_trade", so the key set looks complete.
        key = _EqualityHookKey("risk_per_trade")
        key.effects = []
        key.action = lambda: None
        bad = {name: value for name, value in good.items() if name != "risk_per_trade"}
        bad[key] = record
        assert key.effects == []  # building the fixture ran no equality test
    else:
        # Contract v1.6 makes any non-str key a TypeError.
        bad = {**good, 1: record}
    value = MappingProxyType(bad) if container == "proxy" else bad
    function, arguments = _changed_call(v13, (public, path), value)
    owner = _path_owner(arguments, path)
    if key_kind == "str_subclass" and owner is not None:
        # R4's attack: lift the already validated risk fraction from inside ==.
        key.action = lambda: object.__setattr__(owner, "risk_per_trade", Decimal("5"))
    _reject(TypeError, function, **arguments)
    if key_kind == "str_subclass":
        assert key.effects == []  # the key was refused before any equality test
    if owner is not None:
        assert owner.risk_per_trade == Decimal("0.0025")


def _lower_daily_limit_on_reread(policy):
    """Review r2 R5: from the second full read on, the daily limit drops to .0001."""
    def action(hook):
        if hook.traversals > 1:
            object.__setattr__(policy, "daily_loss_limit", Decimal("0.0001"))
    return action


def _policy_values(policy):
    return tuple(getattr(policy, name) for name in (
        "risk_per_trade", "daily_loss_limit", "experiment_loss_limit",
        "max_open_exposures", "halt_clearers",
    ))


@pytest.mark.parametrize("proxy", (False, True))
@pytest.mark.parametrize("public", ("start_experiment", "update_equity", "restart_experiment"))
def test_ac02_ac03_second_provenance_read_cannot_change_bound_policy(v13, public, proxy):
    start, update, restart = (
        v13[name] for name in ("start_experiment", "update_equity", "restart_experiment")
    )
    policy = _call(replace, v13["H001_RISK"])
    if public != "start_experiment":
        state = _call(start, Decimal("10000"), DAY, policy, "owner", "fixture")
    if public == "restart_experiment":
        # Experiment halt on day22, then a fresh day23 baseline of10000.
        state = _call(update, state, Decimal("9800"), DAY)
        state = _call(update, state, Decimal("10000"), NEXT_DAY)
        _state(state, policy, NEXT_DAY, "10000", "10000", False, True)
    hook = _HookMapping(dict(policy.provenance), _lower_daily_limit_on_reread(policy))
    object.__setattr__(policy, "provenance", MappingProxyType(hook) if proxy else hook)
    if public == "start_experiment":
        result = _call(start, Decimal("10000"), DAY, policy, "owner", "fixture")
        expected = (DAY, "10000", "10000", False, False)
    elif public == "update_equity":
        # Loss10 < daily75 under the validated .0075; .0001 would make the threshold1.
        result = _call(update, state, Decimal("9990"), DAY)
        expected = (DAY, "10000", "10000", False, False)
    else:
        # Same day: daily baseline10000 kept, loss10 < 75; experiment rebases to9990.
        result = _call(restart, state, Decimal("9990"), NEXT_DAY, "owner", "fixture")
        expected = (NEXT_DAY, "10000", "9990", False, False)
    assert hook.calls >= 1  # the attack Mapping was read during the call
    assert result.policy is policy
    # Contract v1.6: one read per call and no reread after deciding, so the values
    # bound to the result are still the validated H001 values.
    assert _policy_values(result.policy) == _policy_values(v13["H001_RISK"])
    _state(result, policy, *expected)


@pytest.mark.parametrize("proxy", (False, True))
@pytest.mark.parametrize("public", ("update_equity", "restart_experiment"))
def test_ac02_ac03_ac04_limit_changed_before_decision_keeps_daily_latch(v13, public, proxy):
    from sochron.costs import H001_COSTS

    start, update, restart = (
        v13[name] for name in ("start_experiment", "update_equity", "restart_experiment")
    )
    policy = _call(replace, v13["H001_RISK"])
    model = _call(replace, H001_COSTS)
    request = _call(v13["EntryRequest"], "long", Decimal("0.02"),
                    Decimal("4012.90"), Decimal("4000.90"), 0)
    hook = _HookMapping(dict(policy.provenance), _lower_daily_limit_on_reread(policy))
    if public == "update_equity":
        object.__setattr__(policy, "provenance", MappingProxyType(hook) if proxy else hook)
        # First read: start binds the unchanged policy.
        state = _call(start, Decimal("10000"), DAY, policy, "owner", "fixture")
        day, experiment_base = DAY, "10000"
    else:
        state = _call(start, Decimal("10000"), DAY, policy, "owner", "fixture")
        state = _call(update, state, Decimal("9800"), DAY)
        object.__setattr__(policy, "provenance", MappingProxyType(hook) if proxy else hook)
        # First read: a fresh day23 baseline; the experiment stays halted.
        state = _call(update, state, Decimal("10000"), NEXT_DAY)
        _state(state, policy, NEXT_DAY, "10000", "10000", False, True)
        day, experiment_base = NEXT_DAY, "9990"
    assert policy.daily_loss_limit == Decimal("0.0075")
    # Second read: v1.6 reads provenance before every other field, so this call
    # decides with the lowered limit: threshold .0001*10000=1 <= loss10.
    if public == "update_equity":
        changed = _call(update, state, Decimal("9990"), day)
    else:
        changed = _call(restart, state, Decimal("9990"), day, "owner", "fixture")
    assert policy.daily_loss_limit == Decimal("0.0001")  # the attack ran
    assert changed.policy is policy
    # Review r2 R5: never daily_halted False under a bound limit that the loss meets.
    _state(changed, policy, day, "10000", experiment_base, True, False)
    # The recovered continuation keeps the latch, so entry stays refused.
    recovered = _call(update, changed, Decimal("10000"), day)
    _state(recovered, policy, day, "10000", experiment_base, True, False)
    _gate(_call(v13["check_entry"], request, Decimal("10000"), day, recovered, model),
          ("daily_halt",), v13["GateDecision"])


# Attack -> ((target, field path, value set from inside the provenance read),
#            complete refusal for the changed input). Request: long .02 4012.90/4000.90.
_GATE_INPUT_CHANGES = {
    # Sized lots stay .02 (R25/per1200), so 41.66 exceeds them.
    "oversized_lots": (("request", "lots", Decimal("41.66")), ("lots_exceed_sized",)),
    "open_exposures": (("request", "open_exposures", 1), ("max_exposure",)),
    "stop_removed": (("request", "stop_loss", None), ("missing_stop_loss",)),
    "daily_latch": (("state", "daily_halted", True), ("daily_halt",)),
    "experiment_latch": (("state", "experiment_halted", True), ("experiment_halt",)),
    # Daily loss10200-10000=200 >= .0075*10200=76.5; experiment baseline stays10000.
    "daily_baseline": (("state", "day_start_equity", Decimal("10200")), ("daily_halt",)),
    # R=.0001*10000=1, per1200 -> floor0 < min.01; requested .02 exceeds 0.
    "policy_rate": (("state", "policy.risk_per_trade", Decimal("0.0001")),
                    ("below_min_volume", "lots_exceed_sized")),
    # state.day23 > request day22: the error table requires TimeReversal.
    "state_day": (("state", "day", NEXT_DAY), None),
}


@pytest.mark.parametrize("proxy", (False, True))
@pytest.mark.parametrize("attack", tuple(_GATE_INPUT_CHANGES))
def test_ac04_ac06_input_changed_during_validation_is_never_allowed(v13, attack, proxy):
    arguments = _v13_calls(v13)["check_entry"]
    (target, path, value), reasons = _GATE_INPUT_CHANGES[attack]
    # Honest precondition: the unchanged request is allowed.
    _gate(_call(v13["check_entry"], **arguments), (), v13["GateDecision"])
    state = arguments["state"]
    hook = _HookMapping(dict(state.policy.provenance),
                        lambda hook: _mutate_field(arguments[target], path, value))
    object.__setattr__(state.policy, "provenance", MappingProxyType(hook) if proxy else hook)
    try:
        outcome = _call(v13["check_entry"], **arguments)
    except v13["RiskError"] as caught:
        outcome = caught  # v1.6 also permits refusing the changed input with an error
    if isinstance(outcome, v13["GateDecision"]):
        # The request was checked after state/policy: the exact reasons for the
        # changed input. A state day after the request day must raise instead.
        assert reasons is not None, "day < state.day must raise TimeReversal"
        _gate(outcome, reasons, v13["GateDecision"])
    assert hook.calls >= 1
    holder = arguments[target]
    *parents, leaf = path.split(".")
    for part in parents:
        holder = getattr(holder, part)
    assert getattr(holder, leaf) == value  # the change was made inside the read
