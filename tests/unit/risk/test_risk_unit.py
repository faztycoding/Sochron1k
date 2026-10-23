"""Implementer unit tests for sochron.risk (CORE-003). The locked acceptance and golden tests own
the contract; these cover internals the implementer relied on: exact decisions versus display
rounding, state immutability, the gate's independence from stale inputs, and error messages."""

from dataclasses import replace
from datetime import date
from decimal import Context, Decimal, Inexact, Rounded, localcontext

import pytest

from sochron.costs import H001_COSTS, Provenance
from sochron.risk import (
    H001_RISK,
    POLICY_FIELDS,
    BadHaltClear,
    EntryRequest,
    HaltState,
    RiskError,
    check_entry,
    restart_experiment,
    size_position,
    start_experiment,
    unknowns,
    update_equity,
)

DAY = date(2026, 10, 22)
NEXT = date(2026, 10, 23)
REQUEST = EntryRequest("long", Decimal("0.02"), Decimal("4012.90"), Decimal("4000.90"), 0)


def _start(equity="10000"):
    return start_experiment(Decimal(equity), DAY, H001_RISK, "owner", "unit test")


def _gate(request, equity, state, model, cost_per_lot=Decimal("0")):
    """check_entry on the state's own Thai day (v1.3 added the day argument)."""
    return check_entry(request, equity, state.day, state, model, cost_per_lot)


def test_actual_risk_never_exceeds_the_budget_on_a_grid_of_inputs():
    for equity in ("100", "1000", "5000", "10000", "123456.78", "9599.9999999999999999999999999"):
        for stop in ("0.10", "1", "3.33", "12", "20", "55.5"):
            sized = size_position(Decimal(equity), Decimal(stop), H001_COSTS, H001_RISK)
            if sized.reason != "below_min_volume":
                assert sized.lots * Decimal(stop) * 100 <= Decimal("0.0025") * Decimal(equity)
                assert sized.lots % Decimal("0.01") == 0


def test_display_rounding_does_not_feed_the_decision():
    sized = size_position(Decimal("9599.9999999999999999999999999"), Decimal("12"), H001_COSTS, H001_RISK)
    assert sized.risk_money == Decimal("24.00000000000000000000000000")  # displayed after one rounding
    assert sized.lots == Decimal("0.01")  # decided on the exact 23.99...975


def test_callers_context_is_untouched_by_every_entry_point():
    with localcontext(Context(prec=3)) as caller:
        caller.traps[Inexact] = True
        caller.traps[Rounded] = True
        caller.clear_flags()
        state = _start()
        state = update_equity(state, Decimal("9925.01"), DAY)
        size_position(Decimal("9599.9999999999999999999999999"), Decimal("12"), H001_COSTS, H001_RISK)
        _gate(REQUEST, Decimal("9925.01"), state, H001_COSTS)
        assert not any(caller.flags.values())
        assert caller.prec == 3


def test_states_are_never_mutated():
    state = _start()
    halted = update_equity(state, Decimal("9800"), DAY)
    assert (state.daily_halted, state.experiment_halted) == (False, False)
    restarted = restart_experiment(halted, Decimal("9800"), DAY, "owner", "reviewed")
    assert halted.experiment_halted is True
    assert restarted.policy is halted.policy is H001_RISK
    _gate(REQUEST, Decimal("9800"), state, H001_COSTS)
    assert state == _start()


def test_restart_rebases_the_experiment_budget_to_the_restart_equity():
    halted = update_equity(_start(), Decimal("9800"), DAY)
    restarted = restart_experiment(halted, Decimal("9800"), NEXT, "owner", "reviewed")
    assert restarted.experiment_start_equity == Decimal("9800")
    assert update_equity(restarted, Decimal("9604.01"), NEXT).experiment_halted is False  # 195.99 < 196
    assert update_equity(restarted, Decimal("9604"), NEXT).experiment_halted is True  # 196 = 2% of 9800


def test_gate_uses_current_equity_even_with_a_stale_clear_state():
    stale = _start()
    assert _gate(REQUEST, Decimal("9925"), stale, H001_COSTS).reasons == ("daily_halt",)
    assert _gate(REQUEST, Decimal("9925.01"), stale, H001_COSTS).allowed is True


def test_gate_resizes_from_the_request_stop_and_short_side():
    short = EntryRequest("short", Decimal("0.02"), Decimal("4000.90"), Decimal("4012.90"), 0)
    assert _gate(short, Decimal("10000"), _start(), H001_COSTS).allowed is True
    wider = replace(short, stop_loss=Decimal("4020.90"))
    assert _gate(wider, Decimal("10000"), _start(), H001_COSTS).reasons == ("lots_exceed_sized",)


def test_cost_budget_reduces_lots_in_the_gate_too():
    request = replace(REQUEST, lots=Decimal("0.02"))
    budget = Decimal("100")  # 1300 per lot: 25 / 1300 = 0.0192 -> 0.01
    assert _gate(request, Decimal("10000"), _start(), H001_COSTS, budget).reasons == ("lots_exceed_sized",)


def test_overflow_and_inexact_underflow_are_risk_errors_with_short_messages():
    with pytest.raises(RiskError) as caught:
        size_position(Decimal("4E-1000025"), Decimal("12"), H001_COSTS, H001_RISK)
    assert len(str(caught.value)) < 200
    with pytest.raises(RiskError):
        size_position(Decimal("10000"), Decimal("1E+999999"), H001_COSTS, H001_RISK)


def test_authorization_is_exact_and_needs_a_reason_for_start_too():
    for name in ("owner ", " owner", "OWNER"):
        with pytest.raises(BadHaltClear):
            start_experiment(Decimal("10000"), DAY, H001_RISK, name, "x")
    with pytest.raises(BadHaltClear):
        start_experiment(Decimal("10000"), DAY, H001_RISK, "owner", "\t")
    custom = replace(
        H001_RISK,
        halt_clearers=("owner", "risk-officer"),
        provenance={**H001_RISK.provenance, "halt_clearers": Provenance("synthetic", DAY, "assumed")},
    )
    assert start_experiment(Decimal("10000"), DAY, custom, "risk-officer", "x").policy is custom


def _custom_policy(**values):
    synthetic = Provenance("synthetic", DAY, "assumed")
    return replace(H001_RISK, **values, provenance={**H001_RISK.provenance, **{k: synthetic for k in values}})


def test_gate_and_halts_follow_the_bound_policy_not_h001_values():
    # Coverage suggested by the owner's Codex tests review (2026-10-22): catch hard-coded H001 limits.
    wide = _custom_policy(daily_loss_limit=Decimal("0.01"), experiment_loss_limit=Decimal("0.05"), risk_per_trade=Decimal("0.005"))
    state = start_experiment(Decimal("10000"), DAY, wide, "owner", "custom limits")
    assert _gate(REQUEST, Decimal("9925"), state, H001_COSTS).allowed is True  # 75 < 100
    assert _gate(REQUEST, Decimal("9900"), state, H001_COSTS).reasons == ("daily_halt",)  # 100 = 1%
    assert update_equity(state, Decimal("9500"), DAY).experiment_halted is True  # 500 = 5%
    assert size_position(Decimal("10000"), Decimal("12.00"), H001_COSTS, wide).lots == Decimal("0.04")  # R 50
    two = _custom_policy(max_open_exposures=2)
    two_state = start_experiment(Decimal("10000"), DAY, two, "owner", "two exposures")
    assert _gate(replace(REQUEST, open_exposures=1), Decimal("10000"), two_state, H001_COSTS).allowed is True


def test_sizing_and_gate_respect_a_non_default_volume_step():
    # Coverage suggested by the owner's Codex tests review: step and minimum 0.02 instead of 0.01.
    synthetic = Provenance("synthetic", DAY, "assumed")
    model = replace(
        H001_COSTS,
        volume_step=Decimal("0.02"),
        volume_min=Decimal("0.02"),
        provenance={**H001_COSTS.provenance, "volume_step": synthetic, "volume_min": synthetic},
    )
    sized = size_position(Decimal("15000"), Decimal("12"), model, H001_RISK)  # R 37.5 / 1200 = 0.03125
    assert (sized.lots, sized.reason) == (Decimal("0.02"), "ok")
    state = start_experiment(Decimal("15000"), DAY, H001_RISK, "owner", "step 0.02")
    assert _gate(replace(REQUEST, lots=Decimal("0.03")), Decimal("15000"), state, model).reasons == (
        "lots_exceed_sized",
        "lots_not_on_grid",
    )
    assert _gate(replace(REQUEST, lots=Decimal("0.02")), Decimal("15000"), state, model).allowed is True


def _split_baselines():
    """Day 2 opens at 9900 while the experiment baseline stays 10000 (daily limit 74.25, experiment 200)."""
    return update_equity(_start(), Decimal("9900"), NEXT)


def test_same_day_updates_use_each_baseline_separately():
    # Review CORE-003-tests-r1 F1: kills mutations that swap the daily and experiment baselines.
    state = _split_baselines()
    assert (state.day_start_equity, state.experiment_start_equity) == (Decimal("9900"), Decimal("10000"))
    calm = update_equity(state, Decimal("9850"), NEXT)  # daily 50 < 74.25, experiment 150 < 200
    assert (calm.daily_halted, calm.experiment_halted) == (False, False)
    edge = update_equity(state, Decimal("9825.75"), NEXT)  # daily 74.25 = 0.75% of 9900
    assert (edge.daily_halted, edge.experiment_halted) == (True, False)
    deep = update_equity(state, Decimal("9800"), NEXT)  # experiment 200 = 2% of 10000
    assert (deep.daily_halted, deep.experiment_halted) == (True, True)
    restarted = restart_experiment(deep, Decimal("9800"), NEXT, "owner", "reviewed")
    assert (restarted.day_start_equity, restarted.daily_halted) == (Decimal("9900"), True)
    assert (restarted.experiment_start_equity, restarted.experiment_halted) == (Decimal("9800"), False)


def test_gate_thresholds_use_each_baseline_and_the_bound_limits():
    # Review CORE-003-tests-r1 F2: gate states with different baselines and non-H001 loss limits.
    state = _split_baselines()
    assert _gate(REQUEST, Decimal("9850"), state, H001_COSTS).allowed is True
    assert _gate(REQUEST, Decimal("9825.75"), state, H001_COSTS).reasons == ("daily_halt",)
    assert _gate(REQUEST, Decimal("9800"), state, H001_COSTS).reasons == ("daily_halt", "experiment_halt")
    loose = _custom_policy(daily_loss_limit=Decimal("0.02"), experiment_loss_limit=Decimal("0.03"))
    loose_state = update_equity(start_experiment(Decimal("10000"), DAY, loose, "owner", "x"), Decimal("9900"), NEXT)
    assert _gate(REQUEST, Decimal("9800"), loose_state, H001_COSTS).allowed is True  # 100 < 198, 200 < 300
    assert _gate(REQUEST, Decimal("9700"), loose_state, H001_COSTS).reasons == ("daily_halt", "experiment_halt")


def test_cap_boundary_is_not_a_cap_and_volume_max_is_on_the_grid():
    # Review CORE-003-tests-r1 F3: uncapped exactly at the largest grid point is "ok"; volume_max is allowed.
    sized = size_position(Decimal("800000"), Decimal("0.10"), H001_COSTS, H001_RISK)  # R 2000 / 10 = 200
    assert (sized.lots, sized.reason) == (Decimal("200"), "ok")
    state = start_experiment(Decimal("800000"), DAY, H001_RISK, "owner", "cap boundary")
    at_max = EntryRequest("long", Decimal("200"), Decimal("4012.90"), Decimal("4012.80"), 0)
    assert _gate(at_max, Decimal("800000"), state, H001_COSTS).allowed is True


class _Lots(Decimal):
    def as_integer_ratio(self):
        return (1, 100)


class _AnyName(str):
    def __eq__(self, other):
        return True

    __hash__ = str.__hash__


class _Anyone(tuple):
    def __contains__(self, item):
        return True


class _NeverSameDay(date):
    def __eq__(self, other):
        return False

    __hash__ = date.__hash__


class _Count(int):
    def __ge__(self, other):
        return False


def test_subclasses_of_value_types_are_refused():
    # Security pre-review F1: subclasses answered validation and decision differently.
    with pytest.raises(TypeError):
        EntryRequest("long", _Lots("1.00"), Decimal("4012.90"), Decimal("4000.90"), 0)
    with pytest.raises(TypeError):
        start_experiment(Decimal("10000"), DAY, H001_RISK, _AnyName("claude"), "x")
    with pytest.raises(TypeError):
        start_experiment(Decimal("10000"), DAY, H001_RISK, "owner", _AnyName("  "))
    with pytest.raises(TypeError):
        replace(H001_RISK, halt_clearers=_Anyone(("owner",)))
    with pytest.raises(TypeError):
        update_equity(_start(), Decimal("9925"), _NeverSameDay(2026, 10, 22))
    with pytest.raises(TypeError):
        EntryRequest("long", Decimal("0.02"), Decimal("4012.90"), Decimal("4000.90"), _Count(7))
    with pytest.raises(TypeError):
        size_position(_Lots("10000"), Decimal("12"), H001_COSTS, H001_RISK)
    # Since CORE-004 the constructor refuses a subclass, so it is planted after construction
    # (review CORE-004-tests-r1 F1; owner decision 2026-10-23 18:3x).
    step_model = replace(H001_COSTS)
    object.__setattr__(step_model, "volume_step", _Lots("0.01"))
    with pytest.raises(TypeError):
        size_position(Decimal("10000"), Decimal("12"), step_model, H001_RISK)


def test_huge_lots_are_built_without_the_int_to_str_digit_limit():
    # Security pre-review F2: grid_lots went through str(int) and hit Python's 4300-digit limit.
    synthetic = Provenance("synthetic", DAY, "assumed")
    big = replace(H001_COSTS, volume_max=Decimal("1E+5000"), provenance={**H001_COSTS.provenance, "volume_max": synthetic})
    sized = size_position(Decimal("1E+5010"), Decimal("12"), big, H001_RISK)
    assert (sized.lots, sized.reason) == (Decimal("1E+5000"), "capped_at_volume_max")


def test_provenance_is_read_once_from_a_changing_mapping():
    # Security pre-review F5: a Mapping that changed between iterations stored unvalidated records.
    from collections.abc import Mapping

    class Flipping(Mapping):
        def __init__(self, good):
            self.good, self.reads = dict(good), 0

        def __getitem__(self, key):
            self.reads += 1
            return self.good[key] if self.reads <= len(self.good) else "not a Provenance"

        def __iter__(self):
            return iter(self.good)

        def __len__(self):
            return len(self.good)

    policy = replace(H001_RISK, provenance=Flipping(H001_RISK.provenance))
    assert all(type(record) is Provenance for record in policy.provenance.values())
    assert unknowns(policy) == unknowns(H001_RISK)


def test_gate_and_halts_revalidate_objects_mutated_after_construction():
    # Security pre-review F4: object.__setattr__ after validation slipped past the gate.
    from sochron.risk import BadEquity, BadStop

    def mutated(obj, **fields):
        copy = replace(obj)
        for name, value in fields.items():
            object.__setattr__(copy, name, value)
        return copy

    state = _start()
    with pytest.raises(RiskError):
        _gate(mutated(REQUEST, side="buy"), Decimal("10000"), state, H001_COSTS)
    with pytest.raises(RiskError):
        _gate(mutated(REQUEST, open_exposures=-5), Decimal("10000"), state, H001_COSTS)
    with pytest.raises(RiskError):
        _gate(mutated(REQUEST, lots=Decimal("NaN")), Decimal("10000"), state, H001_COSTS)
    with pytest.raises(BadStop):
        _gate(mutated(REQUEST, entry_price=Decimal("Infinity")), Decimal("10000"), state, H001_COSTS)
    with pytest.raises(BadEquity):
        _gate(REQUEST, Decimal("10000"), mutated(state, day_start_equity=Decimal("NaN")), H001_COSTS)
    with pytest.raises(BadEquity):
        update_equity(mutated(state, experiment_start_equity=Decimal("-1")), Decimal("10000"), DAY)
    with pytest.raises(TypeError):
        restart_experiment(mutated(state, experiment_halted=1), Decimal("10000"), DAY, "owner", "x")


def test_gate_refuses_a_state_not_rolled_to_the_request_day():
    # Contract v1.3 / security pre-review F6: a missed rollover must not let today's loss through.
    from sochron.risk import TimeReversal

    state = _start()  # day 22, baseline 10000
    assert check_entry(REQUEST, Decimal("10000"), NEXT, state, H001_COSTS).reasons == ("stale_state",)
    halted = update_equity(state, Decimal("9925"), DAY)
    assert check_entry(REQUEST, Decimal("9925"), NEXT, halted, H001_COSTS).reasons == ("daily_halt", "stale_state")
    rolled = update_equity(state, Decimal("10100"), NEXT)  # today's baseline 10100: limit 75.75
    assert check_entry(REQUEST, Decimal("10020"), NEXT, rolled, H001_COSTS).reasons == ("daily_halt",)
    with pytest.raises(TimeReversal):
        check_entry(REQUEST, Decimal("10000"), date(2026, 10, 21), state, H001_COSTS)
    with pytest.raises(TypeError):
        check_entry(REQUEST, Decimal("10000"), "2026-10-22", state, H001_COSTS)  # type: ignore[arg-type]


def test_oversized_numbers_are_refused_before_rational_conversion():
    # Contract v1.3 / security pre-review F3: huge exponents or coefficients must fail fast.
    import time

    from sochron.risk import BadEquity, BadPolicy, BadStop

    started = time.perf_counter()
    with pytest.raises(BadEquity):
        size_position(Decimal("1E-999999999"), Decimal("12"), H001_COSTS, H001_RISK)
    with pytest.raises(BadEquity):
        _gate(REQUEST, Decimal("1E+10000000"), _start(), H001_COSTS)
    with pytest.raises(BadStop):
        size_position(Decimal("10000"), Decimal("1" + "0" * 1000), H001_COSTS, H001_RISK)
    with pytest.raises(RiskError):
        EntryRequest("long", Decimal("1E-10000000"), Decimal("4012.90"), Decimal("4000.90"), 0)
    with pytest.raises(BadPolicy):
        size_position(Decimal("10000"), Decimal("12"), H001_COSTS, H001_RISK, Decimal("7" * 1001))
    assert time.perf_counter() - started < 1
    # The edges stay valid: 1,000 digits, |adjusted| of 1,100,000, and a zero with any exponent.
    assert size_position(Decimal("1" * 1000), Decimal("12"), H001_COSTS, H001_RISK).reason == "capped_at_volume_max"
    assert size_position(Decimal("10000"), Decimal("12"), H001_COSTS, H001_RISK, Decimal("0E-5000000")).lots == Decimal("0.02")


def test_corrupted_model_domain_is_refused_at_use():
    # Review CORE-003-r1 F1: a model field set to zero or below after construction let the
    # gate allow 1 lot (risk 1,200) against a budget of 25.
    def corrupted(**fields):
        model = replace(H001_COSTS)
        for name, value in fields.items():
            object.__setattr__(model, name, value)
        return model

    bad_models = [
        corrupted(volume_step=Decimal("-0.01")),
        corrupted(volume_step=Decimal("0")),
        corrupted(contract_size=Decimal("-100")),
        corrupted(contract_size=Decimal("0")),
        corrupted(volume_min=Decimal("-0.01")),
        corrupted(volume_min=Decimal("0")),
        corrupted(volume_min=Decimal("0.5"), volume_max=Decimal("0.1")),
    ]
    one_lot = EntryRequest("long", Decimal("1"), Decimal("4012.90"), Decimal("4000.90"), 0)
    halted = update_equity(_start(), Decimal("9800"), DAY)
    for model in bad_models:
        with pytest.raises(RiskError):
            size_position(Decimal("10000"), Decimal("12"), model, H001_RISK)
        with pytest.raises(RiskError):
            _gate(one_lot, Decimal("10000"), _start(), model, Decimal("10"))
        with pytest.raises(RiskError):  # an earlier refusal must not hide the bad model
            _gate(one_lot, Decimal("9800"), halted, model)


def test_zero_budget_with_any_exponent_sizes_like_zero():
    # Review CORE-003-r1 F2: 1200 + 0E-999999999999999999 tried to build a 10**18-digit
    # coefficient in the exact context and raised MemoryError.
    baseline = size_position(Decimal("10000"), Decimal("12"), H001_COSTS, H001_RISK, Decimal("0"))
    for zero in ("-0", "0E-999999999999999999", "-0E-999999999999999999", "0E+999999999999999999"):
        decision = size_position(Decimal("10000"), Decimal("12"), H001_COSTS, H001_RISK, Decimal(zero))
        assert decision == baseline
        assert _gate(REQUEST, Decimal("10000"), _start(), H001_COSTS, Decimal(zero)).allowed


def test_huge_negative_counts_raise_the_contract_errors():
    # Review CORE-003-r1 F3: formatting -(10**5000) into the message hit Python's int-to-str
    # limit, so a plain ValueError replaced RiskError / BadPolicy.
    from sochron.risk import BadPolicy

    huge = -(10**5000)
    with pytest.raises(RiskError) as caught:
        EntryRequest("long", Decimal("0.02"), Decimal("4012.90"), Decimal("4000.90"), huge)
    assert isinstance(caught.value, RiskError)
    with pytest.raises(BadPolicy):
        replace(H001_RISK, max_open_exposures=huge)
    request = replace(REQUEST)
    object.__setattr__(request, "open_exposures", huge)
    with pytest.raises(RiskError):
        _gate(request, Decimal("10000"), _start(), H001_COSTS)
    policy = replace(H001_RISK)
    state = start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test")
    object.__setattr__(policy, "max_open_exposures", huge)
    with pytest.raises(BadPolicy):
        _gate(REQUEST, Decimal("10000"), state, H001_COSTS)
    with pytest.raises(RiskError):  # ordinary negatives keep their errors
        EntryRequest("long", Decimal("0.02"), Decimal("4012.90"), Decimal("4000.90"), -1)
    with pytest.raises(BadPolicy):
        replace(H001_RISK, max_open_exposures=0)


def test_huge_coefficient_is_refused_without_counting_digits_one_by_one():
    # Security pre-review r2 F11: len(as_tuple().digits) built a tuple of every digit, so 2x10**8
    # digits took over 1 s. 3x10**7 digits took about 0.17 s that way; the bound needs ~0.005 s.
    import time

    from sochron.risk import BadEquity

    # Small exponent (adjusted -1), so only the digit count can refuse it. Built before timing,
    # as the contract's timing rule says.
    huge = Decimal("0." + "7" * 30_000_000)
    started = time.perf_counter()
    with pytest.raises(BadEquity):
        size_position(huge, Decimal("12"), H001_COSTS, H001_RISK)
    assert time.perf_counter() - started < 0.05


class _Hook:
    """A valid provenance Mapping whose keys() runs caller code, planted after construction."""

    def __init__(self, good, action):
        self.good, self.action, self.calls = dict(good), action, 0

    def __getitem__(self, key):
        return self.good[key]

    def __iter__(self):
        return iter(self.good)

    def __len__(self):
        return len(self.good)

    def keys(self):
        self.calls += 1
        self.action(self.calls)
        return self.good.keys()


def _plant(policy, action):
    from collections.abc import Mapping

    Mapping.register(_Hook)
    object.__setattr__(policy, "provenance", _Hook(H001_RISK.provenance, action))


def test_caller_code_in_provenance_cannot_undo_use_time_validation():
    # Security pre-review r2 F9: the hook ran after the request was validated, so it could turn a
    # wrong-side stop into side "buy", lots into NaN, or swap state.policy for an unvalidated one.
    wrong_side = EntryRequest("long", Decimal("0.02"), Decimal("4012.90"), Decimal("4024.90"), 0)
    state = start_experiment(Decimal("10000"), DAY, replace(H001_RISK), "owner", "unit test")
    _plant(state.policy, lambda n: object.__setattr__(wrong_side, "side", "buy"))
    with pytest.raises(RiskError):
        check_entry(wrong_side, Decimal("10000"), DAY, state, H001_COSTS)

    request = replace(REQUEST)
    state = start_experiment(Decimal("10000"), DAY, replace(H001_RISK), "owner", "unit test")
    _plant(state.policy, lambda n: object.__setattr__(request, "lots", Decimal("NaN")))
    with pytest.raises(RiskError):
        check_entry(request, Decimal("10000"), DAY, state, H001_COSTS)

    evil = replace(H001_RISK)
    object.__setattr__(evil, "risk_per_trade", Decimal("5"))
    one_lot = EntryRequest("long", Decimal("1"), Decimal("4012.90"), Decimal("4000.90"), 0)
    state = start_experiment(Decimal("10000"), DAY, replace(H001_RISK), "owner", "unit test")
    _plant(state.policy, lambda n: object.__setattr__(state, "policy", evil))
    with pytest.raises(RiskError):  # before the fix: allowed, sized with risk_per_trade 5
        check_entry(one_lot, Decimal("10000"), DAY, state, H001_COSTS)

    # restart must keep the policy it validated, even if the hook swaps it on a later read
    policy = replace(H001_RISK)
    halted = update_equity(start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test"), Decimal("9800"), DAY)
    other = replace(H001_RISK, risk_per_trade=Decimal("0.5"))
    _plant(policy, lambda n: n == 2 and object.__setattr__(halted, "policy", other))
    assert restart_experiment(halted, Decimal("9800"), DAY, "owner", "reviewed").policy is policy


def test_provenance_keys_must_be_exact_str_before_any_comparison():
    # Review CORE-003-r2 F4: a str-subclass key's __eq__ ran in the key-set comparison, after the
    # fractions were checked, and set risk_per_trade to 5; the gate then allowed 41.66 lots.
    policy = replace(H001_RISK)
    state = start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test")
    big = EntryRequest("long", Decimal("41.66"), Decimal("4012.90"), Decimal("4000.90"), 0)

    class Key(str):
        __hash__ = str.__hash__

        def __eq__(self, other):
            object.__setattr__(policy, "risk_per_trade", Decimal("5"))
            return str.__eq__(self, other)

    provenance = dict(policy.provenance)
    provenance[Key("risk_per_trade")] = provenance.pop("risk_per_trade")
    object.__setattr__(policy, "provenance", provenance)
    for call in (
        lambda: check_entry(big, Decimal("10000"), DAY, state, H001_COSTS),
        lambda: size_position(Decimal("10000"), Decimal("12"), H001_COSTS, policy),
        lambda: unknowns(policy),
    ):
        with pytest.raises(TypeError):
            call()
        assert policy.risk_per_trade == Decimal("0.0025")  # the key's code never ran

    class Quiet(str):
        __hash__ = str.__hash__

    keyed = dict(H001_RISK.provenance)
    keyed[Quiet("halt_clearers")] = keyed.pop("halt_clearers")
    with pytest.raises(TypeError):  # construction refuses it too
        replace(H001_RISK, provenance=keyed)
    with pytest.raises(TypeError):
        replace(H001_RISK, provenance={**H001_RISK.provenance, 7: H001_RISK.provenance["halt_clearers"]})


def test_result_states_are_built_without_reading_the_policy_again():
    # Review CORE-003-r2 F5: building the returned HaltState validated the policy again; a Mapping
    # changed daily_loss_limit on that second read, after the latches were decided, so the state
    # said "not halted" under a limit its own loss exceeded.
    def limit_changes_on_second_read(policy):
        _plant(policy, lambda n: n == 2 and object.__setattr__(policy, "daily_loss_limit", Decimal("0.0001")))

    policy = replace(H001_RISK)
    state = start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test")
    limit_changes_on_second_read(policy)
    loss = update_equity(state, Decimal("9990"), DAY)
    assert (loss.daily_halted, loss.policy.daily_loss_limit) == (False, Decimal("0.0075"))

    policy = replace(H001_RISK)
    halted = update_equity(start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test"), Decimal("9800"), DAY)
    rolled = update_equity(halted, Decimal("10000"), NEXT)
    limit_changes_on_second_read(policy)
    restarted = restart_experiment(rolled, Decimal("9990"), NEXT, "owner", "reviewed")
    assert (restarted.daily_halted, restarted.policy.daily_loss_limit) == (False, Decimal("0.0075"))

    policy = replace(H001_RISK)
    limit_changes_on_second_read(policy)
    started = start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test")
    assert started.policy.daily_loss_limit == Decimal("0.0075")


class _CountingMapping:
    """A valid provenance Mapping that counts traversals and per-key lookups."""

    def __init__(self, good):
        self.good = dict(good)
        self.traversals = 0
        self.lookups = {key: 0 for key in self.good}

    def __getitem__(self, key):
        self.lookups[key] += 1
        return self.good[key]

    def __iter__(self):
        self.traversals += 1
        return iter(self.good)

    def __len__(self):
        return len(self.good)

    def keys(self):
        self.traversals += 1
        return self.good.keys()

    def reset(self):
        self.traversals = 0
        self.lookups = {key: 0 for key in self.good}


def test_every_public_call_reads_provenance_exactly_once():
    # tests-r4 F1 (owner: guard with a unit test): a re-read after the decision, by traversal or by a
    # second lookup of any key, would let a planted Mapping change the policy behind a returned
    # result (review r2 F5). Each public call must read provenance once: one traversal, each key once.
    from collections.abc import Mapping

    Mapping.register(_CountingMapping)
    policy = replace(H001_RISK)
    state = start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test")
    halted = update_equity(state, Decimal("9800"), DAY)
    counter = _CountingMapping(H001_RISK.provenance)
    object.__setattr__(policy, "provenance", counter)
    calls = {
        "check_entry": lambda: check_entry(REQUEST, Decimal("10000"), DAY, state, H001_COSTS),
        "size_position": lambda: size_position(Decimal("10000"), Decimal("12"), H001_COSTS, policy),
        "start_experiment": lambda: start_experiment(Decimal("10000"), DAY, policy, "owner", "unit test"),
        "update_equity": lambda: update_equity(state, Decimal("9990"), DAY),
        "restart_experiment": lambda: restart_experiment(halted, Decimal("9800"), DAY, "owner", "reviewed"),
        "unknowns": lambda: unknowns(policy),
        "HaltState": lambda: HaltState(policy, DAY, Decimal("10000"), Decimal("10000"), False, False),
    }
    for name, call in calls.items():
        counter.reset()
        call()
        assert counter.traversals == 1, name
        assert set(counter.lookups.values()) == {1}, name


def test_policy_fields_and_halt_state_validation():
    assert set(H001_RISK.provenance) == set(POLICY_FIELDS)
    with pytest.raises(TypeError):
        HaltState(H001_RISK, DAY, Decimal("10000"), Decimal("10000"), 0, False)  # type: ignore[arg-type]
    with pytest.raises(RiskError):
        HaltState(H001_RISK, DAY, Decimal("0"), Decimal("10000"), False, False)
