"""CORE-004 v1 acceptance tests: sochron.costs refuses hostile input the way sochron.risk does.

Contract: docs/contracts/CORE-004-costs-hardening.md (approved 2026-10-22). Every negative test
changes exactly one slot of a valid fixture built from a fresh copy of H001_COSTS; the ``api``
fixture proves the shared singleton was never touched. Only the CORE-002 public API is used.
"""

from collections.abc import KeysView, Mapping
from dataclasses import fields, replace
from datetime import date, datetime
from decimal import Decimal, Inexact, ROUND_UP, Rounded, Subnormal, getcontext, localcontext
from importlib import import_module
from pathlib import Path
from types import MappingProxyType
import faulthandler
import platform
import sys
from threading import Thread
from time import perf_counter

import pytest


DAY = date(2026, 10, 21)
LOTS = Decimal("0.02")

NAMES = (
    "H001_COSTS", "CostModel", "Provenance", "CostBreakdown", "stress", "check_volume",
    "points_to_money", "spread_charge", "slippage_charge", "commission_charge", "swap_charge",
    "round_trip_cost", "r_multiple", "unknowns", "CostsError", "BadProvenance", "BadStress",
    "BadVolume", "BadPoints", "BadSides", "BadNights", "BadR",
)
MODEL_DECIMAL_FIELDS = (
    "point", "contract_size", "volume_min", "volume_step", "volume_max",
    "commission_per_lot_per_side", "swap_long_points_per_night", "swap_short_points_per_night",
    "stress_factor",
)
MODEL_INT_FIELDS = ("spread_fallback_points", "slippage_points_per_side", "triple_swap_weekday")
PROVENANCE_FIELDS = (
    "point", "contract_size", "volume_min", "volume_step", "volume_max",
    "spread_fallback_points", "commission_per_lot_per_side", "slippage_points_per_side",
    "swap_long_points_per_night", "swap_short_points_per_night", "triple_swap_weekday",
)
BREAKDOWN_FIELDS = ("spread", "commission", "slippage", "swap", "total", "stress_factor")
# Every public callable that takes a model, and the ones that take lots.
MODEL_PUBLICS = (
    "stress", "check_volume", "points_to_money", "spread_charge", "slippage_charge",
    "commission_charge", "swap_charge", "round_trip_cost", "unknowns",
)
LOTS_PUBLICS = (
    "check_volume", "points_to_money", "spread_charge", "slippage_charge",
    "commission_charge", "swap_charge", "round_trip_cost",
)
# Model uses for AC-03: every model-taking callable, plus its zero-count paths.
_MODEL_USES = (
    ("stress", {}), ("check_volume", {}), ("points_to_money", {}), ("spread_charge", {}),
    ("slippage_charge", {}), ("slippage_charge", {"sides": 0}),
    ("commission_charge", {}), ("commission_charge", {"sides": 0}),
    ("swap_charge", {}), ("swap_charge", {"nights": 0}),
    ("round_trip_cost", {}), ("round_trip_cost", {"sides": 0}),
    ("unknowns", {}),
)
# Honest H001 results of the fixture calls in _calls (CORE-002 AC-01 to AC-04 literals).
HONEST = {
    "stress": "2",
    "check_volume": "0.02",
    "points_to_money": "0.48",
    "spread_charge": "0.48",
    "slippage_charge": "0.20",
    "commission_charge": "0",
    "swap_charge": "1.00760",
    "round_trip_cost": ("0.48", "0", "0.20", "1.00760", "1.68760", "1"),
    "r_multiple": "0.067504",
    "unknowns": ("commission_per_lot_per_side", "slippage_points_per_side", "triple_swap_weekday"),
}
_HONEST_BREAKDOWN = dict(
    spread=Decimal("0.48"), commission=Decimal("0"), slippage=Decimal("0.20"),
    swap=Decimal("1.00760"), total=Decimal("1.68760"), stress_factor=Decimal("1"),
)
# H001_COSTS values (CORE-002 table); Decimal fields as strings.
H001_DECIMALS = (
    ("point", "0.001"), ("contract_size", "100"), ("volume_min", "0.01"), ("volume_step", "0.01"),
    ("volume_max", "200"), ("commission_per_lot_per_side", "0"),
    ("swap_long_points_per_night", "-503.8"), ("swap_short_points_per_night", "0"),
    ("stress_factor", "1"),
)
H001_INTS = (("spread_fallback_points", 240), ("slippage_points_per_side", 50), ("triple_swap_weekday", 2))
H001_STATUSES = (
    ("point", "measured"), ("contract_size", "measured"), ("volume_min", "measured"),
    ("volume_step", "measured"), ("volume_max", "measured"), ("spread_fallback_points", "measured"),
    ("commission_per_lot_per_side", "assumed"), ("slippage_points_per_side", "assumed"),
    ("swap_long_points_per_night", "spec"), ("swap_short_points_per_night", "spec"),
    ("triple_swap_weekday", "assumed"),
)


def _api(monkeypatch, ac, *names):
    """Missing costs fails each test, never collection; only contracted public names."""
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


def _context_state():
    context = getcontext()
    return (
        context.prec, context.rounding, context.Emin, context.Emax,
        context.capitals, context.clamp, dict(context.traps), dict(context.flags),
    )


def _call(function, *args, **kwargs):
    """Preserve caller context identity, settings, traps and flags even on rejection."""
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
    context.clear_flags()
    context.flags[Rounded] = True


def _money(actual, expected):
    assert type(actual) is Decimal
    assert actual == Decimal(expected)


def _breakdown(actual, expected, CostBreakdown):
    assert type(actual) is CostBreakdown
    for name, value in zip(BREAKDOWN_FIELDS, expected, strict=True):
        _money(getattr(actual, name), value)


def _snapshot(instance):
    return tuple(getattr(instance, field.name) for field in fields(instance))


def _reject(error, function, *args, **kwargs):
    with pytest.raises(error) as caught:
        _call(function, *args, **kwargs)
    assert type(caught.value) is error


@pytest.fixture
def api(monkeypatch):
    loaded = dict(zip(NAMES, _api(monkeypatch, "CORE-004", *NAMES), strict=True))
    singleton = loaded["H001_COSTS"]
    before = (_snapshot(singleton), dict(singleton.provenance))
    yield loaded
    # Every test works on fresh copies: the shared singleton must come out untouched.
    assert (_snapshot(singleton), dict(singleton.provenance)) == before


def _calls(api):
    """Valid keyword arguments for every public callable, on a fresh copy of H001_COSTS."""
    model = _call(replace, api["H001_COSTS"])
    return {
        "stress": dict(model=model, factor=Decimal("2")),
        "check_volume": dict(lots=LOTS, model=model),
        "points_to_money": dict(points=240, lots=LOTS, model=model),
        "spread_charge": dict(spread_points=240, lots=LOTS, model=model),
        "slippage_charge": dict(lots=LOTS, model=model, sides=2),
        "commission_charge": dict(lots=LOTS, model=model, sides=2),
        "swap_charge": dict(side="long", lots=LOTS, nights=1, triple_nights=0, model=model),
        "round_trip_cost": dict(side="long", lots=LOTS, entry_spread_points=240, exit_spread_points=240,
                                nights=1, triple_nights=0, model=model, sides=2),
        "r_multiple": dict(money=Decimal("1.68760"), r=Decimal("25")),
        "unknowns": dict(model=model),
        "CostModel": {field.name: getattr(model, field.name) for field in fields(model)},
        "Provenance": dict(source="synthetic test fixture", as_of=DAY, status="assumed", note=""),
        "CostBreakdown": dict(_HONEST_BREAKDOWN),
    }


def _current(arguments, path):
    value = arguments[path.split(".")[0]]
    for part in path.split(".")[1:]:
        value = getattr(value, part)
    return value


def _changed_call(api, public, path, value, overrides=()):
    """The public callable and valid arguments with exactly the slot at path changed."""
    arguments = _calls(api)[public]
    arguments.update(overrides)
    parts = path.split(".")
    if len(parts) == 1:
        arguments[path] = value
    else:
        holder = arguments[parts[0]]
        for part in parts[1:-1]:
            holder = getattr(holder, part)
        object.__setattr__(holder, parts[-1], value)
    return api[public], arguments


def _expect_honest(api, public, actual):
    expected = HONEST[public]
    if public == "stress":
        assert type(actual) is api["CostModel"]
        _money(actual.stress_factor, expected)
    elif public == "round_trip_cost":
        _breakdown(actual, expected, api["CostBreakdown"])
    elif public == "unknowns":
        assert actual == expected
    else:
        _money(actual, expected)


def _derived(instance):
    """An instance of an anonymous subclass carrying the same fields, built without its constructor."""
    subclass = type("Derived" + type(instance).__name__, (type(instance),), {})
    derived = object.__new__(subclass)
    for field in fields(instance):
        object.__setattr__(derived, field.name, getattr(instance, field.name))
    return derived


def _slot_id(row):
    return ".".join(row[:2])


def _use_id(use):
    public, overrides = use
    return public + "".join(f".{name}{value}" for name, value in overrides.items())


# ---------------------------------------------------------------------------------------------
# Hostile scalar subclasses: isinstance passes and the answers an implementation might trust lie.
# ---------------------------------------------------------------------------------------------

class _PlainDecimal(Decimal):
    """A subclass with no overrides: exact-type checks must refuse even this one."""


class _RatioDecimal(Decimal):
    """Reports the rational value of 0.01 whatever it holds, so a grid check that trusts it passes."""
    def as_integer_ratio(self):
        return (1, 100)


class _FiniteDecimal(Decimal):
    """Claims to be finite whatever it holds; the tests build it from NaN."""
    def is_finite(self):
        return True


class _AgreeableDecimal(Decimal):
    """Equal to, and within, anything: ==, <= and >= answer True; < and > answer False."""
    __hash__ = Decimal.__hash__

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __le__(self, other):
        return True

    def __ge__(self, other):
        return True

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return False


class _PlainInt(int):
    """A subclass with no overrides."""


class _Count(int):
    """Answers every order comparison as if it were in range: < and > False, <= and >= True."""
    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return False

    def __le__(self, other):
        return True

    def __ge__(self, other):
        return True


class _PlainStr(str):
    """A subclass with no overrides."""


class _Name(str):
    """Equal to every string, so membership tests and == accept it as any valid value."""
    __hash__ = str.__hash__

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class _Stranger(str):
    """Equal to nothing: an assumed status that unknowns() would never report."""
    __hash__ = str.__hash__

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True


class _PlainDate(date):
    """A subclass with no overrides."""


class _Day(date):
    __hash__ = date.__hash__

    def __eq__(self, other):
        return False


# ---------------------------------------------------------------------------------------------
# AC-01: exact types in every slot; subclasses of CostModel and Provenance are refused.
# ---------------------------------------------------------------------------------------------

_DECIMAL_SLOTS = (
    *((public, "lots") for public in LOTS_PUBLICS),
    ("points_to_money", "points"), ("stress", "factor"),
    ("r_multiple", "money"), ("r_multiple", "r"),
    *(("CostModel", field) for field in MODEL_DECIMAL_FIELDS),
    *(("CostBreakdown", field) for field in BREAKDOWN_FIELDS),
    *((public, "model." + field) for public in MODEL_PUBLICS for field in MODEL_DECIMAL_FIELDS),
)


@pytest.mark.parametrize("hostile", ("plain", "ratio", "finite", "agreeable"))
@pytest.mark.parametrize("public,path", _DECIMAL_SLOTS, ids=[_slot_id(row) for row in _DECIMAL_SLOTS])
def test_ac01_decimal_subclass_rejected_in_every_slot(api, public, path, hostile):
    honest = _current(_calls(api)[public], path)
    leaf = path.split(".")[-1]
    if hostile == "plain":
        value = _PlainDecimal(honest)
    elif hostile == "ratio":
        # An off-grid lots or step whose claimed ratio is on the 0.01 grid.
        value = _RatioDecimal("0.125" if leaf == "lots" else "0.03" if leaf == "volume_step" else honest)
    elif hostile == "finite":
        value = _FiniteDecimal("NaN")
    else:
        value = _AgreeableDecimal(honest)
    function, arguments = _changed_call(api, public, path, value)
    _reject(TypeError, function, **arguments)


_INT_SLOTS = (
    ("points_to_money", "points"), ("spread_charge", "spread_points"),
    ("round_trip_cost", "entry_spread_points"), ("round_trip_cost", "exit_spread_points"),
    *((public, "sides") for public in ("slippage_charge", "commission_charge", "round_trip_cost")),
    *((public, field) for public in ("swap_charge", "round_trip_cost") for field in ("nights", "triple_nights")),
    ("stress", "factor"),
    *(("CostModel", field) for field in MODEL_INT_FIELDS),
    *((public, "model." + field) for public in MODEL_PUBLICS for field in MODEL_INT_FIELDS),
)


@pytest.mark.parametrize("hostile", ("plain", "count"))
@pytest.mark.parametrize("public,path", _INT_SLOTS, ids=[_slot_id(row) for row in _INT_SLOTS])
def test_ac01_int_subclass_rejected_in_every_slot(api, public, path, hostile):
    honest = _current(_calls(api)[public], path)
    # _Count(-1) is out of every count domain, but its comparisons say it is inside.
    value = _PlainInt(honest) if hostile == "plain" else _Count(-1)
    function, arguments = _changed_call(api, public, path, value)
    _reject(TypeError, function, **arguments)


_STR_SLOTS = (
    ("swap_charge", "side"), ("round_trip_cost", "side"),
    ("CostModel", "symbol"),
    *((public, "model.symbol") for public in MODEL_PUBLICS),
    ("Provenance", "source"), ("Provenance", "note"), ("Provenance", "status"),
)


@pytest.mark.parametrize("hostile", ("plain", "name"))
@pytest.mark.parametrize("public,path", _STR_SLOTS, ids=[_slot_id(row) for row in _STR_SLOTS])
def test_ac01_str_subclass_rejected_in_every_slot(api, public, path, hostile):
    honest = _current(_calls(api)[public], path)
    value = _PlainStr(honest) if hostile == "plain" else _Name(honest)
    function, arguments = _changed_call(api, public, path, value)
    _reject(TypeError, function, **arguments)


def test_ac01_hostile_equality_cannot_impersonate_a_valid_value(api):
    for public in ("swap_charge", "round_trip_cost"):
        function, arguments = _changed_call(api, public, "side", _Name("buy"))
        _reject(TypeError, function, **arguments)
    for status in (_Name("nonsense"), _Name("measured"), _Stranger("assumed")):
        function, arguments = _changed_call(api, "Provenance", "status", status)
        _reject(TypeError, function, **arguments)


@pytest.mark.parametrize("value", (_PlainDate(2026, 10, 21), _Day(2026, 10, 21), datetime(2026, 10, 21)),
                         ids=("plain", "never_equal", "datetime"))
def test_ac01_date_subclass_rejected_in_as_of(api, value):
    function, arguments = _changed_call(api, "Provenance", "as_of", value)
    _reject(TypeError, function, **arguments)


@pytest.mark.parametrize("public", MODEL_PUBLICS)
def test_ac01_model_must_be_exactly_costmodel(api, public):
    arguments = _calls(api)[public]
    _reject(TypeError, api[public], **{**arguments, "model": _derived(arguments["model"])})
    for bad in ({}, "model", 1, True, 1.0, None):
        _reject(TypeError, api[public], **{**arguments, "model": bad})


def test_ac01_subclass_constructors_are_refused(api):
    derived_model = type("DerivedCostModel", (api["CostModel"],), {})
    _reject(TypeError, derived_model, **_calls(api)["CostModel"])
    derived_provenance = type("DerivedProvenance", (api["Provenance"],), {})
    _reject(TypeError, derived_provenance, **_calls(api)["Provenance"])


# ---------------------------------------------------------------------------------------------
# AC-02: provenance containers, read once into a frozen copy; exact-str keys; exact values.
# ---------------------------------------------------------------------------------------------

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


class _HookMapping(Mapping):
    """A valid provenance Mapping whose every read path runs the action.

    keys(), __iter__, __getitem__ and __len__ each call the action, so the Mapping mixins
    built on them and every copy strategy (dict(m), {**m}, iteration plus lookup) run it too.
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
        return KeysView(self)


_CONTAINERS = ("dict", "proxy", "mapping", "proxied_mapping")


def _wrap(kind, data):
    """The container under test and the _SnapshotMapping inside it (None for plain containers)."""
    if kind == "dict":
        return data, None
    if kind == "proxy":
        return MappingProxyType(data), None
    source = _SnapshotMapping(data)
    return (source if kind == "mapping" else MappingProxyType(source)), source


@pytest.mark.parametrize("kind", _CONTAINERS)
def test_ac02_provenance_container_copied_once_and_frozen(api, kind):
    singleton = api["H001_COSTS"]
    data = dict(singleton.provenance)
    container, source = _wrap(kind, data)
    model = _call(replace, singleton, provenance=container)
    assert type(model.provenance) is MappingProxyType
    assert model.provenance == singleton.provenance
    if source is not None:
        assert source.iterations == 1
        assert set(source.reads.values()) == {1}
    # The stored copy is independent of the caller's container.
    data["point"] = api["Provenance"]("changed backing dict", DAY, "unknown")
    del data["volume_min"]
    assert model.provenance == singleton.provenance
    with pytest.raises(TypeError):
        model.provenance["point"] = data["point"]
    with pytest.raises(TypeError):
        del model.provenance["volume_min"]


@pytest.mark.parametrize("kind", ("pairs", "keys", "text", "int", "bool", "float", "none"))
def test_ac02_provenance_container_must_be_a_mapping(api, kind):
    singleton = api["H001_COSTS"]
    value = {
        "pairs": list(singleton.provenance.items()), "keys": set(singleton.provenance),
        "text": "mapping", "int": 1, "bool": True, "float": 1.0, "none": None,
    }[kind]
    _reject(TypeError, replace, singleton, provenance=value)
    _reject(TypeError, api["CostModel"], **{**_calls(api)["CostModel"], "provenance": value})


class _EqualityHookKey(str):
    """A provenance key equal to its text; every equality test is recorded."""
    __hash__ = str.__hash__

    def __eq__(self, other):
        self.effects.append(other)
        return str.__eq__(self, other)


def _bad_keys(good, key_kind):
    """A provenance dict with one non-exact-str key; the hook key, if any, is returned too."""
    record = good["point"]
    if key_kind == "int":
        return {**good, 1: record}, None
    if key_kind == "int_with_missing":
        # The key set is also incomplete: the type error must still come first.
        return {**{name: value for name, value in good.items() if name != "point"}, 1: record}, None
    key = _EqualityHookKey("point")
    key.effects = []
    bad = {name: value for name, value in good.items() if name != "point"}
    bad[key] = record
    assert key.effects == []  # building the fixture ran no equality test
    return bad, key


@pytest.mark.parametrize("kind", ("dict", "proxy", "mapping"))
@pytest.mark.parametrize("key_kind", ("int", "int_with_missing", "str_subclass"))
def test_ac02_provenance_keys_must_be_exact_str(api, key_kind, kind):
    singleton = api["H001_COSTS"]
    bad, key = _bad_keys(dict(singleton.provenance), key_kind)
    container, _ = _wrap(kind, bad)
    _reject(TypeError, replace, singleton, provenance=container)
    if key is not None:
        assert key.effects == []  # the key was refused before any equality test


@pytest.mark.parametrize("key_kind", ("int", "str_subclass"))
@pytest.mark.parametrize("public", MODEL_PUBLICS)
def test_ac03_provenance_keys_revalidated_at_use(api, public, key_kind):
    arguments = _calls(api)[public]
    bad, key = _bad_keys(dict(arguments["model"].provenance), key_kind)
    object.__setattr__(arguments["model"], "provenance", bad)
    _reject(TypeError, api[public], **arguments)
    if key is not None:
        assert key.effects == []


@pytest.mark.parametrize("kind", ("dict", "proxy", "mapping"))
def test_ac01_ac02_provenance_value_must_be_exactly_provenance(api, kind):
    singleton = api["H001_COSTS"]
    values = dict(singleton.provenance)
    values["point"] = _derived(values["point"])
    container, _ = _wrap(kind, values)
    _reject(api["BadProvenance"], replace, singleton, provenance=container)
    values["point"] = "not Provenance"
    container, _ = _wrap(kind, values)
    _reject(api["BadProvenance"], replace, singleton, provenance=container)


@pytest.mark.parametrize("proxy", (False, True))
@pytest.mark.parametrize("public", MODEL_PUBLICS)
def test_ac02_ac03_use_reads_provenance_once(api, public, proxy):
    arguments = _calls(api)[public]
    model = arguments["model"]
    source = _SnapshotMapping(dict(model.provenance))
    object.__setattr__(model, "provenance", MappingProxyType(source) if proxy else source)
    with localcontext() as caller:
        _hostile(caller)
        actual = _call(api[public], **arguments)
    _expect_honest(api, public, actual)
    # One traversal, each key once; a second read would have produced garbage.
    assert source.iterations == 1
    assert set(source.reads.values()) == {1}
    if public == "stress":
        # The returned model carries the validated snapshot, not a reread of the container.
        assert type(actual.provenance) is MappingProxyType
        assert actual.provenance == api["H001_COSTS"].provenance


@pytest.mark.parametrize("proxy", (False, True))
@pytest.mark.parametrize("field,literal,error", (
    ("volume_step", "0", "CostsError"), ("stress_factor", "0", "BadStress"),
), ids=("volume_step0", "stress_factor0"))
@pytest.mark.parametrize("public", MODEL_PUBLICS)
def test_ac03_provenance_is_read_before_the_other_fields(api, public, proxy, field, literal, error):
    arguments = _calls(api)[public]
    model = arguments["model"]
    hook = _HookMapping(dict(model.provenance),
                        lambda hook: object.__setattr__(model, field, Decimal(literal)))
    object.__setattr__(model, "provenance", MappingProxyType(hook) if proxy else hook)
    # The field goes bad inside the provenance read; a read-first validation sees it.
    _reject(api[error], api[public], **arguments)
    assert hook.calls >= 1
    assert getattr(model, field) == Decimal(literal)


# ---------------------------------------------------------------------------------------------
# AC-03: every model use re-validates every field with the construction rule and error.
# ---------------------------------------------------------------------------------------------

_MODEL_DEFECTS = (
    ("symbol", 1, "TypeError"),
    *((field, 1, "TypeError") for field in MODEL_DECIMAL_FIELDS),
    *((field, Decimal(literal), "BadStress" if field == "stress_factor" else "CostsError")
      for field in MODEL_DECIMAL_FIELDS for literal in ("NaN", "sNaN", "Infinity")),
    *((field, Decimal(literal), "CostsError")
      for field in ("point", "contract_size", "volume_min", "volume_step") for literal in ("0", "-1")),
    ("volume_max", Decimal("0.005"), "CostsError"),
    ("commission_per_lot_per_side", Decimal("-1"), "CostsError"),
    *(("stress_factor", Decimal(literal), "BadStress") for literal in ("0", "-2")),
    *((field, True, "TypeError") for field in MODEL_INT_FIELDS),
    ("spread_fallback_points", -1, "CostsError"), ("slippage_points_per_side", -1, "CostsError"),
    ("triple_swap_weekday", -1, "CostsError"), ("triple_swap_weekday", 7, "CostsError"),
    ("provenance", "list", "TypeError"), ("provenance", "none", "TypeError"),
    ("provenance", "int_key", "TypeError"), ("provenance", "subclass_key", "TypeError"),
    ("provenance", "empty", "BadProvenance"), ("provenance", "missing", "BadProvenance"),
    ("provenance", "extra", "BadProvenance"), ("provenance", "not_provenance", "BadProvenance"),
    ("provenance", "subclass_value", "BadProvenance"),
)


def _defect_id(row):
    field, value, _ = row
    return f"{field}.{value}"


def _defect_value(api, field, value):
    """Resolve the provenance tags of _MODEL_DEFECTS against the H001 provenance."""
    if field != "provenance":
        return value
    good = dict(api["H001_COSTS"].provenance)
    if value == "list":
        return list(good.items())
    if value == "none":
        return None
    if value == "int_key":
        return {**good, 1: good["point"]}
    if value == "subclass_key":
        return {**{name: record for name, record in good.items() if name != "point"},
                _PlainStr("point"): good["point"]}
    if value == "empty":
        return {}
    if value == "missing":
        return {name: record for name, record in good.items() if name != "point"}
    if value == "extra":
        return {**good, "symbol": good["point"]}
    if value == "not_provenance":
        return {**good, "point": "not Provenance"}
    return {**good, "point": _derived(good["point"])}


@pytest.mark.parametrize("field,value,error", _MODEL_DEFECTS, ids=[_defect_id(row) for row in _MODEL_DEFECTS])
@pytest.mark.parametrize("use", _MODEL_USES, ids=_use_id)
def test_ac03_every_use_revalidates_a_changed_field(api, use, field, value, error):
    value = _defect_value(api, field, value)
    expected = TypeError if error == "TypeError" else api[error]
    # The construction rule of CORE-002 for this defect, and its exact error type.
    with pytest.raises(expected) as built:
        _call(api["CostModel"], **{**_calls(api)["CostModel"], field: value})
    public, overrides = use
    function, arguments = _changed_call(api, public, "model." + field, value, overrides)
    _reject(type(built.value), function, **arguments)


# ---------------------------------------------------------------------------------------------
# AC-04: the Decimal size bound in every slot, refused fast; the edges are accepted.
# ---------------------------------------------------------------------------------------------

_BOUNDS = ("coefficient", "trailing_zero_coefficient", "negative_adjusted", "positive_adjusted")
# 1,001 stored digits (two shapes) and |adjusted exponent| 1,100,001 per slot. Each literal keeps
# every other fixture argument valid, so the only defect is the size. None: no such literal keeps
# the fixture valid (a step without lots 0.02 on its grid; a volume_min above or a volume_max
# below lots 0.02, which would also move the lots domain).
_STEP_1001 = "0." + "0" * 432 + str(5 ** 1431)  # 0.02 = 2**1432 * step; 1,001 digits
_OVERSIZED = {
    "lots": ("0." + "1" * 1001, "0.02" + "0" * 1000, "1E-1100001", "1E+1100001"),
    "points": ("240." + "1" * 998, "240." + "0" * 998, "1E-1100001", "1E+1100001"),
    "factor": ("2." + "1" * 1000, "2." + "0" * 1000, "1E-1100001", "1E+1100001"),
    "money": ("1.68760" + "1" * 995, "1.68760" + "0" * 995, "1E-1100001", "1E+1100001"),
    "r": ("25." + "1" * 999, "25." + "0" * 999, "1E-1100001", "1E+1100001"),
    "point": ("0.001" + "1" * 1000, "0.001" + "0" * 1000, "1E-1100001", "1E+1100001"),
    "contract_size": ("100." + "1" * 998, "100." + "0" * 998, "1E-1100001", "1E+1100001"),
    "volume_min": ("0.0" + "1" * 1001, "0.01" + "0" * 1000, "1E-1100001", None),
    "volume_step": (_STEP_1001, "0.01" + "0" * 1000, "1E-1100001", None),
    "volume_max": ("200." + "1" * 998, "200." + "0" * 998, None, "1E+1100001"),
    "commission_per_lot_per_side": ("3.5" + "1" * 999, "3.5" + "0" * 999, "1E-1100001", "1E+1100001"),
    "swap_long_points_per_night": ("-503.8" + "1" * 997, "-503.8" + "0" * 997, "-1E-1100001", "-1E+1100001"),
    "swap_short_points_per_night": ("-503.8" + "1" * 997, "-503.8" + "0" * 997, "-1E-1100001", "-1E+1100001"),
    "stress_factor": ("1." + "1" * 1000, "1." + "0" * 1000, "1E-1100001", "1E+1100001"),
    "spread": ("0.48" + "1" * 999, "0.48" + "0" * 999, "1E-1100001", "1E+1100001"),
    "commission": ("3.5" + "1" * 999, "3.5" + "0" * 999, "1E-1100001", "1E+1100001"),
    "slippage": ("0.20" + "1" * 999, "0.20" + "0" * 999, "1E-1100001", "1E+1100001"),
    "swap": ("1.00760" + "1" * 995, "1.00760" + "0" * 995, "1E-1100001", "1E+1100001"),
}


def _model_error(field):
    return "BadStress" if field == "stress_factor" else "CostsError"


_SIZE_SLOTS = (
    *((public, "lots", "BadVolume") for public in LOTS_PUBLICS),
    ("points_to_money", "points", "BadPoints"),
    ("stress", "factor", "BadStress"),
    ("r_multiple", "money", "CostsError"), ("r_multiple", "r", "BadR"),
    *(("CostModel", field, _model_error(field)) for field in MODEL_DECIMAL_FIELDS),
    *((public, "model." + field, _model_error(field))
      for public in MODEL_PUBLICS for field in MODEL_DECIMAL_FIELDS),
    *(("CostBreakdown", field, "CostsError") for field in ("spread", "commission", "slippage", "swap", "stress_factor")),
)


def _oversized(path, bound):
    return _OVERSIZED[path.split(".")[-1]][_BOUNDS.index(bound)]


_SIZE_CASES = tuple((row, bound) for row in _SIZE_SLOTS for bound in _BOUNDS if _oversized(row[1], bound) is not None)


def _assert_oversized(value, bound):
    if bound.endswith("coefficient"):
        assert len(value.as_tuple().digits) == 1001
    else:
        assert abs(value.adjusted()) == 1_100_001


def _breakdown_with(field, value):
    """A breakdown whose only unusual field is `field`: other components zero, total consistent."""
    if field == "stress_factor":
        return dict(_HONEST_BREAKDOWN, stress_factor=value)
    zero = Decimal("0")
    arguments = dict(spread=zero, commission=zero, slippage=zero, swap=zero, total=value,
                     stress_factor=Decimal("1"))
    arguments[field] = value
    return arguments


def _timed_rejection(error, function, arguments, record_property, capsys):
    """Time only the public invocation in a daemon thread; transport every worker outcome."""
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
    # pytest captures fd 2, and a watchdog exit discards that capture: arm, run and cancel with
    # capture disabled, so a hang inside a C call ends with a visible traceback.
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


@pytest.mark.parametrize("row,bound", _SIZE_CASES, ids=[_slot_id(row) + "." + bound for row, bound in _SIZE_CASES])
def test_ac04_oversized_decimal_rejected_fast_in_every_slot(api, row, bound, record_property, capsys):
    public, path, error = row
    # All creation and setup happens before the worker's timed public call.
    value = Decimal(_oversized(path, bound))
    _assert_oversized(value, bound)
    if public == "CostBreakdown":
        function, arguments = api["CostBreakdown"], _breakdown_with(path, value)
    else:
        function, arguments = _changed_call(api, public, path, value)
    _timed_rejection(api[error], function, arguments, record_property, capsys)


@pytest.mark.parametrize("public", LOTS_PUBLICS)
def test_ac04_extreme_exponent_lots_rejected_fast(api, public, record_property, capsys):
    function, arguments = _changed_call(api, public, "lots", Decimal("1E-999999999"))
    _timed_rejection(api["BadVolume"], function, arguments, record_property, capsys)


def test_ac04_huge_on_grid_lots_rejected_before_rational_conversion(api, record_property, capsys):
    # 30M stored digits of the on-grid value 0.02 (adjusted exponent -2): a grid check that
    # converts to a rational first runs far past the deadline. Construction is not timed.
    value = Decimal("0.02" + "0" * 30_000_000)
    assert value == LOTS
    function, arguments = _changed_call(api, "check_volume", "lots", value)
    _timed_rejection(api["BadVolume"], function, arguments, record_property, capsys)


def test_ac04_extreme_exponent_volume_step_rejected_fast_at_use(api, record_property, capsys):
    function, arguments = _changed_call(api, "check_volume", "model.volume_step", Decimal("1E-999999999"))
    _timed_rejection(api["CostsError"], function, arguments, record_property, capsys)


# Accepted edge: the same numbers written with exactly 1,000 stored digits give the same results.
_STEP_1000 = "0." + "0" * 432 + str(5 ** 1430)  # 0.02 = 2**1431 * step; 1,000 digits
_MODEL_1000 = (
    ("point", "0.001", "0.001" + "0" * 999),
    ("contract_size", "100", "100." + "0" * 997),
    ("volume_min", "0.01", "0.01" + "0" * 999),
    ("volume_step", "0.01", "0.01" + "0" * 999),
    ("volume_max", "200", "200." + "0" * 997),
    ("commission_per_lot_per_side", "3.5", "3.5" + "0" * 998),
    ("swap_long_points_per_night", "-503.8", "-503.8" + "0" * 996),
    ("swap_short_points_per_night", "-100", "-100." + "0" * 997),
    ("stress_factor", "1", "1." + "0" * 999),
)


def _fixture(api, model, **changes):
    provenance = dict(model.provenance)
    for name in changes:
        if name in provenance:
            provenance[name] = api["Provenance"]("synthetic test fixture", DAY, "assumed")
    return _call(replace, model, provenance=provenance, **changes)


def _results(api, model):
    outcomes = []
    for public in MODEL_PUBLICS:
        arguments = {**_calls(api)[public], "model": model}
        actual = _call(api[public], **arguments)
        if public == "stress":
            outcomes.append(_snapshot(actual))
        elif public == "round_trip_cost":
            outcomes.append(_snapshot(actual))
        else:
            outcomes.append(actual)
    return outcomes


@pytest.mark.parametrize("field,short,long", _MODEL_1000, ids=[row[0] for row in _MODEL_1000])
def test_ac04_thousand_digit_model_field_accepted_with_unchanged_results(api, field, short, long):
    long_value = Decimal(long)
    assert len(long_value.as_tuple().digits) == 1000
    assert long_value == Decimal(short)
    singleton = api["H001_COSTS"]
    with localcontext() as caller:
        _hostile(caller)
        wide = _fixture(api, singleton, **{field: long_value})
        narrow = _fixture(api, singleton, **{field: Decimal(short)})
        assert getattr(wide, field) == long_value
        assert _results(api, wide) == _results(api, narrow)


def test_ac04_thousand_digit_arguments_accepted_with_unchanged_results(api):
    lots = Decimal("0.02" + "0" * 999)
    points = Decimal("240." + "0" * 997)
    factor = Decimal("2." + "0" * 999)
    money = Decimal("1.68760" + "0" * 994)
    r = Decimal("25." + "0" * 998)
    for value in (lots, points, factor, money, r):
        assert len(value.as_tuple().digits) == 1000
    with localcontext() as caller:
        _hostile(caller)
        for public in LOTS_PUBLICS:
            _expect_honest(api, public, _call(api[public], **{**_calls(api)[public], "lots": lots}))
        _money(_call(api["points_to_money"], points, LOTS, _calls(api)["check_volume"]["model"]), "0.48")
        _money(_call(api["stress"], _calls(api)["unknowns"]["model"], factor).stress_factor, "2")
        _money(_call(api["r_multiple"], money, r), "0.067504")
        # A 1,000-digit step that is not a trailing-zero representation: 0.02 = 2**1431 * step.
        step = Decimal(_STEP_1000)
        assert len(step.as_tuple().digits) == 1000
        fine = _fixture(api, api["H001_COSTS"], volume_step=step)
        _money(_call(api["check_volume"], LOTS, fine), "0.02")
        _money(_call(api["spread_charge"], 240, LOTS, fine), "0.48")
        breakdown = _call(
            api["CostBreakdown"], spread=Decimal("0.48" + "0" * 998), commission=Decimal("3.5" + "0" * 998),
            slippage=Decimal("0.20" + "0" * 998), swap=Decimal("1.00760" + "0" * 994),
            total=Decimal("5.18760" + "0" * 994), stress_factor=Decimal("1." + "0" * 999),
        )
        _breakdown(breakdown, ("0.48", "3.5", "0.20", "1.00760", "5.18760", "1"), api["CostBreakdown"])


_MODEL_EDGE_EXPONENTS = (
    *((field, sign) for field in ("point", "contract_size", "commission_per_lot_per_side",
                                  "swap_long_points_per_night", "swap_short_points_per_night",
                                  "stress_factor") for sign in ("-", "+")),
    ("volume_min", "-"), ("volume_max", "+"),
)


@pytest.mark.parametrize("field,sign", _MODEL_EDGE_EXPONENTS, ids=[f"{f}.{s}" for f, s in _MODEL_EDGE_EXPONENTS])
def test_ac04_adjusted_exponent_edge_accepted_in_model_fields(api, field, sign):
    value = Decimal(f"1E{sign}1100000")
    assert abs(value.adjusted()) == 1_100_000
    model = _fixture(api, api["H001_COSTS"], **{field: value})
    assert getattr(model, field) == value
    assert type(model.provenance) is MappingProxyType
    if field in ("volume_min", "volume_max"):
        # In-bound extremes of the range are used, not only stored.
        _money(_call(api["check_volume"], LOTS, model), "0.02")
        _money(_call(api["spread_charge"], 240, LOTS, model), "0.48")
    if field != "stress_factor":
        # Doubling an edge stress factor leaves the precision-28 exponent range; that is CORE-002.
        _money(_call(api["stress"], model).stress_factor, "2")
    # The fixture marks the changed field as assumed; the other H001 unknowns stay.
    expected = set(HONEST["unknowns"]) | ({field} if field in PROVENANCE_FIELDS else set())
    assert _call(api["unknowns"], model) == tuple(sorted(expected))


def test_ac04_adjusted_exponent_edge_accepted_in_arguments(api):
    big, small = Decimal("1E+1100000"), Decimal("1E-1100000")
    with localcontext() as caller:
        _hostile(caller)
        # 1E+1100000 * 1E-1100000 = 1 point-unit; * 100 * 0.02 * 1 = 2 USD, either way round.
        for points, point in ((big, small), (small, big)):
            model = _fixture(api, api["H001_COSTS"], point=point)
            _money(_call(api["points_to_money"], points, LOTS, model), "2")
        for money in (big, small):
            _money(_call(api["r_multiple"], money, money), "1")
        for factor in (big, small):
            breakdown = _call(api["CostBreakdown"], **{**_HONEST_BREAKDOWN, "stress_factor": factor})
            assert breakdown.stress_factor == factor


_ZEROS = ("0E-999999999999999999", "-0E-999999999999999999", "0E+999999999999999999")


@pytest.mark.parametrize("literal", _ZEROS)
def test_ac04_zero_with_any_exponent_behaves_like_zero(api, literal):
    zero = Decimal(literal)
    assert zero.is_zero()
    singleton = api["H001_COSTS"]
    with localcontext() as caller:
        _hostile(caller)
        model = _calls(api)["unknowns"]["model"]
        # Where zero is a valid value, the result is the result for Decimal("0").
        _money(_call(api["points_to_money"], zero, LOTS, model), "0")
        _money(_call(api["r_multiple"], zero, Decimal("25")), "0")
        credit = _fixture(api, singleton, commission_per_lot_per_side=zero, swap_long_points_per_night=zero,
                          swap_short_points_per_night=zero)
        _money(_call(api["commission_charge"], LOTS, credit), "0")
        for side in ("long", "short"):
            swap = _call(api["swap_charge"], side, LOTS, 7, 1, credit)
            _money(swap, "0")
            assert not swap.is_signed()
        _breakdown(_call(api["round_trip_cost"], "long", LOTS, 240, 240, 7, 1, credit),
                   ("0.48", "0", "0.20", "0", "0.68", "1"), api["CostBreakdown"])
        breakdown = _call(api["CostBreakdown"], spread=zero, commission=zero, slippage=zero, swap=zero,
                          total=zero, stress_factor=Decimal("1"))
        _breakdown(breakdown, ("0", "0", "0", "0", "0", "1"), api["CostBreakdown"])
        # Where zero is out of the domain, the error is the error for Decimal("0"), not a size error.
        for public in LOTS_PUBLICS:
            _reject(api["BadVolume"], api[public], **{**_calls(api)[public], "lots": zero})
        _reject(api["BadStress"], api["stress"], model, zero)
        _reject(api["BadR"], api["r_multiple"], Decimal("1"), zero)
        for field in ("point", "contract_size", "volume_min", "volume_step"):
            _reject(api["CostsError"], replace, model, **{field: zero})
        _reject(api["BadStress"], replace, model, stress_factor=zero)


# ---------------------------------------------------------------------------------------------
# AC-05: honest CORE-002 behaviour is unchanged (the locked CORE-002/003 suites run alongside).
# ---------------------------------------------------------------------------------------------

def test_ac05_h001_values_and_honest_results_are_unchanged(api):
    model = api["H001_COSTS"]
    assert type(model) is api["CostModel"]
    assert type(model.symbol) is str and model.symbol == "XAUUSDm"
    for name, literal in H001_DECIMALS:
        _money(getattr(model, name), literal)
    for name, value in H001_INTS:
        assert type(getattr(model, name)) is int and getattr(model, name) == value
    assert type(model.provenance) is MappingProxyType
    assert set(model.provenance) == set(PROVENANCE_FIELDS)
    for name, status in H001_STATUSES:
        record = model.provenance[name]
        assert type(record) is api["Provenance"]
        assert type(record.status) is str and record.status == status
        assert type(record.as_of) is date and record.as_of == DAY
    with localcontext() as caller:
        _hostile(caller)
        for public in HONEST:
            _expect_honest(api, public, _call(api[public], **_calls(api)[public]))
        stressed = _call(api["stress"], model)
        assert stressed.provenance == model.provenance
        _money(_call(api["spread_charge"], 240, LOTS, stressed), "0.96")
        _money(_call(api["spread_charge"], None, LOTS, model), "0.48")
        _breakdown(_call(api["round_trip_cost"], "long", LOTS, 240, 240, 1, 0, stressed),
                   ("0.96", "0", "0.40", "2.01520", "3.37520", "2"), api["CostBreakdown"])
        _breakdown(_call(api["round_trip_cost"], "short", LOTS, 100, 240, 1, 0, model),
                   ("0.48", "0", "0.20", "0", "0.68", "1"), api["CostBreakdown"])
        _money(_call(api["swap_charge"], "long", LOTS, 7, 1, model), "9.06840")
        _money(_call(api["points_to_money"], 1, Decimal("1"), model), "0.1")
        _money(_call(api["r_multiple"], Decimal("1"), Decimal("3")), "0.3333333333333333333333333333")
        _money(_call(api["stress"], stressed).stress_factor, "4")


# ---------------------------------------------------------------------------------------------
# AC-06: huge out-of-domain ints keep the slot's error (never a ValueError from str conversion).
# ---------------------------------------------------------------------------------------------

_HUGE_INT_SLOTS = (
    *((public, field, "BadNights") for public in ("swap_charge", "round_trip_cost")
      for field in ("nights", "triple_nights")),
    *((public, "sides", "BadSides") for public in ("slippage_charge", "commission_charge", "round_trip_cost")),
    ("spread_charge", "spread_points", "BadPoints"),
    ("round_trip_cost", "entry_spread_points", "BadPoints"), ("round_trip_cost", "exit_spread_points", "BadPoints"),
    ("stress", "factor", "BadStress"),
    *(("CostModel", field, "CostsError") for field in MODEL_INT_FIELDS),
    *((public, "model." + field, "CostsError") for public in MODEL_PUBLICS for field in MODEL_INT_FIELDS),
)


@pytest.mark.parametrize("public,path,error", _HUGE_INT_SLOTS, ids=[_slot_id(row) for row in _HUGE_INT_SLOTS])
def test_ac06_huge_negative_int_keeps_the_slot_error(api, public, path, error):
    # Built in the body: pytest must never stringify a 5,001-digit integer for an ID or a report.
    function, arguments = _changed_call(api, public, path, -(10 ** 5000))
    _reject(api[error], function, **arguments)


def test_ac06_huge_positive_int_out_of_domain_keeps_the_slot_error(api):
    huge = 10 ** 5000
    for public in ("swap_charge", "round_trip_cost"):
        function, arguments = _changed_call(api, public, "triple_nights", huge)
        _reject(api["BadNights"], function, **arguments)
    function, arguments = _changed_call(api, "CostModel", "triple_swap_weekday", huge)
    _reject(api["CostsError"], function, **arguments)
    for public in MODEL_PUBLICS:
        function, arguments = _changed_call(api, public, "model.triple_swap_weekday", huge)
        _reject(api["CostsError"], function, **arguments)
