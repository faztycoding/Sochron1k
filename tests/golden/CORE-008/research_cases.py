"""Known answers for the CORE-008 acceptance tests (docs/contracts/CORE-008-research.md v1.5).

Every value here was worked out by hand from the contract text, never from an implementation. The
arithmetic is in the comments so the owner can check it. Numbers are strings; the tests turn them
into Decimal and compare by value unless a case says the representation is pinned. Times are UTC.
This file imports no sochron module; tests/acceptance/CORE-008/test_research.py loads it with
runpy.run_path.

Three SHA-256 values cannot be worked out by hand: the run_id of the normative example (taken
from the contract) and of the two other golden lines below. Their JSON text was written by hand
from the canonical rules (sorted keys, no spaces, Decimal as str, None as null, nested dataclass as
an object keyed by field name, expectancy_by_year as [year, str] pairs) and hashed with hashlib.
"""

from datetime import UTC, datetime, timedelta

# ------------------------------------------------------------------------------------ shared setup

RULE_SERVER = "Exness-MT5Trial14"  # timebase.rule_for: offset 0 (SPIKE-001)
ROLLOVER = ("America/New_York", 17, 0)
CODE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
OTHER_COMMIT = "fedcba9876543210fedcba9876543210fedcba98"
SIZER_LABEL = "fixed-0.02"
EQUITY = "10000"
CUTOFF = "2025-01-01T00:00:00"  # H001 section 5; HOLDOUT_CUTOFF_UTC
DEFAULTS = {"f": 16, "s": 64, "n": 20, "theta": "0.50", "N": 96, "M": 48, "k": "2.0"}  # H001 section 4
# Inside H001 section 4 with the shortest warm-up: warm = t >= max(3s, N+1, M+1, 97, n+1) = 97.
RUN_PARAMS = {"f": 8, "s": 32, "n": 10, "theta": "0.50", "N": 48, "M": 24, "k": "3.0"}
PARAM_ORDER = ("f", "s", "n", "theta", "N", "M", "k")
# The valid neighbours of RUN_PARAMS by variant (worked out like NEIGHBOUR_CASES below): f 8 x 1.1 =
# 8.8 -> 9 (s 32 >= 27), s 32 x 1.1 = 35.2 -> 35, n 10 x 1.1 = 11.0 -> 11, theta 0.450 and 0.550, N 48 x 1.1
# = 52.8 -> 53, M 24 x 1.1 = 26.4 -> 26, k 3.0 x 0.9 = 2.70. Invalid: f 7, s 29, n 9, N 43, M 22, k 3.30.
RUN_NEIGHBOURS = {
    "A": (("f", 9), ("s", 35), ("n", 11), ("theta", "0.450"), ("theta", "0.550"), ("k", "2.70")),
    "B": (("n", 11), ("N", 53), ("M", 26), ("k", "2.70")),
    "C": (("f", 9), ("s", 35), ("n", 11), ("N", 53), ("M", 26), ("k", "2.70")),
}

# The record strings of H001_COSTS (str of every CostModel field but provenance, in field order) and
# its provenance as [name, status] sorted by name; both are copied from the normative line below.
H001_COST_PAIRS = (
    ("symbol", "XAUUSDm"), ("point", "0.001"), ("contract_size", "100"), ("volume_min", "0.01"),
    ("volume_step", "0.01"), ("volume_max", "200"), ("spread_fallback_points", "240"),
    ("commission_per_lot_per_side", "0"), ("slippage_points_per_side", "50"),
    ("swap_long_points_per_night", "-503.8"), ("swap_short_points_per_night", "0"),
    ("triple_swap_weekday", "2"), ("stress_factor", "1"),
)
H001_PROVENANCE_PAIRS = (
    ("commission_per_lot_per_side", "assumed"), ("contract_size", "measured"), ("point", "measured"),
    ("slippage_points_per_side", "assumed"), ("spread_fallback_points", "measured"),
    ("swap_long_points_per_night", "spec"), ("swap_short_points_per_night", "spec"),
    ("triple_swap_weekday", "assumed"), ("volume_max", "measured"), ("volume_min", "measured"),
    ("volume_step", "measured"),
)
# stress(H001_COSTS) multiplies stress_factor 1 by Decimal("2") = Decimal("2"), record string "2".
# stress(H001_COSTS, Decimal("2.0")) gives 1 x 2.0 = Decimal("2.0"), record string "2.0" (F19).

# ------------------------------------------------------------------------- AC-01 normative example

# Dataset("SYN-0001", "a" x 64, 2023-01-02T00:00:00Z, 2023-01-07T00:00:00Z, 7200)
NORMATIVE_DATASET = ("SYN-0001", "a" * 64, "2023-01-02T00:00:00", "2023-01-07T00:00:00", 7200)
NORMATIVE_RUN_ID = "e35809037fb2878f02919adc04332a45e841ac04b54354f5548b3f88732d314f"
NORMATIVE_LINE_SHA256 = "f50c0bcb139bc587cef4882c8650e34cfa714df8ac51721eab20f23140533f44"
NORMATIVE_LINE_BYTES = 1671  # including the LF
_HEAD = (
    '{"backtest_version":"backtest-v1","base_run_id":null,"baseline":null,'
    '"code_commit":"0123456789abcdef0123456789abcdef01234567",'
    '"cost_model":[["symbol","XAUUSDm"],["point","0.001"],["contract_size","100"],["volume_min","0.01"],'
    '["volume_step","0.01"],["volume_max","200"],["spread_fallback_points","240"],'
    '["commission_per_lot_per_side","0"],["slippage_points_per_side","50"],'
    '["swap_long_points_per_night","-503.8"],["swap_short_points_per_night","0"],'
    '["triple_swap_weekday","2"],["stress_factor","1"]],'
    '"cost_provenance":[["commission_per_lot_per_side","assumed"],["contract_size","measured"],'
    '["point","measured"],["slippage_points_per_side","assumed"],["spread_fallback_points","measured"],'
    '["swap_long_points_per_night","spec"],["swap_short_points_per_night","spec"],'
    '["triple_swap_weekday","assumed"],["volume_max","measured"],["volume_min","measured"],'
    '["volume_step","measured"]],'
    '"dataset":{"m1_bars":7200,"manifest_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    '"period_end_utc":"2023-01-07T00:00:00Z","period_start_utc":"2023-01-02T00:00:00Z","snapshot_id":"SYN-0001"},'
    '"equity":"10000","error":null,"hypothesis":"H001",'
    '"params":[["f","16"],["s","64"],["n","20"],["theta","0.50"],["N","96"],["M","48"],["k","2.0"]],'
)
NORMATIVE_LINE = (
    _HEAD
    + '"purpose":"select","research_version":"research-v1","rollover_at":"17:00",'
    '"rollover_zone":"America/New_York",'
    '"run_id":"e35809037fb2878f02919adc04332a45e841ac04b54354f5548b3f88732d314f",'
    '"runs":null,"seed":null,"seq":1,"sides":["long","short"],"sizer_label":"fixed-0.02",'
    '"started_seq":null,"status":"started","strategy_version":"H001-v1","summary":null,'
    '"time_rule_server":"Exness-MT5Trial14","time_rule_version":"1","variant":"B"}'
)

# The ok line that pairs with the normative started line (seq 2, started_seq 1). Its Summary:
OK_SUMMARY = {
    "trades": 3, "expectancy_r": "0.5", "max_drawdown_r": "1.25", "net_money": "37.50",
    "long_trades": 2, "long_expectancy_r": "0.75", "short_trades": 1, "short_expectancy_r": "0.0",
    "top5_removed_expectancy_r": None, "expectancy_by_year": ((2023, "0.5"),),
    "ambiguous_trades": 1, "flagged_trades": 1, "gap_fills": 0, "end_of_data_trades": 0,
}
_OK_SUMMARY_JSON = (
    '{"ambiguous_trades":1,"end_of_data_trades":0,"expectancy_by_year":[[2023,"0.5"]],"expectancy_r":"0.5",'
    '"flagged_trades":1,"gap_fills":0,"long_expectancy_r":"0.75","long_trades":2,"max_drawdown_r":"1.25",'
    '"net_money":"37.50","short_expectancy_r":"0.0","short_trades":1,"top5_removed_expectancy_r":null,'
    '"trades":3}'
)
OK_RUN_ID = "dd5d8f72304a1d9a47bebdb33f63102ba5abca22ea4cb882990ff14b09641ac3"
OK_LINE = (
    _HEAD
    + '"purpose":"select","research_version":"research-v1","rollover_at":"17:00",'
    '"rollover_zone":"America/New_York",'
    f'"run_id":"{OK_RUN_ID}",'
    '"runs":null,"seed":null,"seq":2,"sides":["long","short"],"sizer_label":"fixed-0.02",'
    '"started_seq":1,"status":"ok","strategy_version":"H001-v1","summary":'
    + _OK_SUMMARY_JSON
    + ',"time_rule_server":"Exness-MT5Trial14","time_rule_version":"1","variant":"B"}'
)

# A random_entry ok line on the ok record above as its base (seq 4, started_seq 3).
# seed = int(OK_RUN_ID[:15], 16) (contract baseline step 5); runs = 1000.
RANDOM_SEED = 996941448488460761  # int("dd5d8f72304a1d9", 16)
RANDOM_BASELINE = {
    "runs": 1000, "trades_per_run": 3, "seed": RANDOM_SEED, "mean_r": "-0.024", "p05_r": "-0.0240",
    "p50_r": "-0.024", "p95_r": "-0.02", "variant_mean_hold_m1": "2", "variant_median_hold_m1": 0,
    "baseline_mean_hold_m1": "4", "baseline_median_hold_m1": 5,
}
RANDOM_RUN_ID = "af0c3bda159684599553d3580264c57c67bb4150c3cb1cbc5bbe23743982b8c2"
RANDOM_LINE = (
    '{"backtest_version":"backtest-v1",'
    f'"base_run_id":"{OK_RUN_ID}",'
    '"baseline":{"baseline_mean_hold_m1":"4","baseline_median_hold_m1":5,"mean_r":"-0.024","p05_r":"-0.0240",'
    '"p50_r":"-0.024","p95_r":"-0.02","runs":1000,'
    f'"seed":{RANDOM_SEED},'
    '"trades_per_run":3,"variant_mean_hold_m1":"2","variant_median_hold_m1":0},'
    + _HEAD[_HEAD.index('"code_commit"'):]
    + '"purpose":"random_entry","research_version":"research-v1","rollover_at":"17:00",'
    '"rollover_zone":"America/New_York",'
    f'"run_id":"{RANDOM_RUN_ID}",'
    f'"runs":1000,"seed":{RANDOM_SEED},"seq":4,"sides":["long","short"],"sizer_label":"fixed-0.02",'
    '"started_seq":3,"status":"ok","strategy_version":"H001-v1","summary":null,'
    '"time_rule_server":"Exness-MT5Trial14","time_rule_version":"1","variant":"B"}'
)

# ------------------------------------------------------------------------------ AC-03 summarize

# A trade is (side, entry time UTC, r, net_money, exit_reason, ambiguous, data_flags). summarize
# reads nothing else, so every other Trade field is a fixed dummy in the tests.
SUMMARY_CASES = {
    # No trades: expectancies None, drawdown and net Decimal 0, counters 0, no years.
    "none": {"rule": "measured", "trades": (), "expected": {
        "trades": 0, "expectancy_r": None, "max_drawdown_r": "0", "net_money": "0", "long_trades": 0,
        "long_expectancy_r": None, "short_trades": 0, "short_expectancy_r": None,
        "top5_removed_expectancy_r": None, "expectancy_by_year": (), "ambiguous_trades": 0,
        "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0}},
    # Seven trades. Cumulative R from 0: 2, -1, -2.0, 4.0, 3.00, 3.50, 5.00; running peak 2, 2, 2, 4.0,
    # 4.0, 4.0, 5.00; peak - cum 0, 3, 4.0, 0, 1.00, 0.50, 0 -> max_drawdown 4 (the deepest point is
    # before the new peak at trade 4). Sum r = 2 - 3 - 1.0 + 6 - 1.00 + 0.5 + 1.5 = 5.00; 5.00 / 7 at
    # precision 28 = 0.7142857142857142857142857143. net = 50 - 75 - 25 + 150 - 25 + 12.50 + 37.50 = 125.00.
    # long (1, 3, 5, 6): 2 - 1.0 - 1.00 + 0.5 = 0.50 / 4 = 0.125; short (2, 4, 7): -3 + 6 + 1.5 = 4.5 / 3 = 1.5.
    # top 5 by r: 6 (t4), 2 (t1), 1.5 (t7), 0.5 (t6), then the tie -1.0 (t3) / -1.00 (t5): the earlier
    # t3 goes. Left t2, t5: (-3 + -1.00) / 2 = -2.00, so its representation is "-2.00" (t5 kept).
    # Years by the UTC entry time: t3 is 2023-12-31T20:00Z (2024-01-01 03:00 in Bangkok) and belongs
    # to 2023: (2 - 3 - 1.0) / 3 = -0.6666666666666666666666666667; 2024: (6 - 1.00 + 0.5 + 1.5) / 4
    # = 7.00 / 4 = 1.75. ambiguous: t3; flagged: t2, t3, t5; unexpected_gap: t2, t5; end_of_data: t5.
    "seven": {"rule": "measured", "trades": (
        ("long", "2023-03-01T14:00", "2", "50.00", "signal", False, ()),
        ("short", "2023-06-01T14:00", "-3", "-75.00", "stop", False, ("unexpected_gap",)),
        ("long", "2023-12-31T20:00", "-1.0", "-25.00", "stop", True, ("price_jump",)),
        ("short", "2024-02-01T14:00", "6", "150.00", "signal", False, ()),
        ("long", "2024-03-01T14:00", "-1.00", "-25.00", "end_of_data", False, ("unexpected_gap", "price_jump")),
        ("long", "2024-04-01T14:00", "0.5", "12.50", "signal", False, ()),
        ("short", "2024-05-01T14:00", "1.5", "37.50", "signal", False, ()),
    ), "expected": {
        "trades": 7, "expectancy_r": "0.7142857142857142857142857143", "max_drawdown_r": "4",
        "net_money": "125.00", "long_trades": 4, "long_expectancy_r": "0.125", "short_trades": 3,
        "short_expectancy_r": "1.5", "top5_removed_expectancy_r": "-2.00",
        "expectancy_by_year": ((2023, "-0.6666666666666666666666666667"), (2024, "1.75")),
        "ambiguous_trades": 1, "flagged_trades": 3, "gap_fills": 2, "end_of_data_trades": 1},
        "repr": {"top5_removed_expectancy_r": "-2.00"}},
    # Five trades, the first one losing: cumulative -2, -1, -0.5, -1.0, 2.0 with the peak at 0 until
    # the last trade, so peak - cum = 2, 1, 0.5, 1.0, 0 -> max_drawdown 2 (drawdown measured from 0).
    # Sum 2.0 / 5 = 0.4; net -50 + 25 + 12.50 - 12.50 + 75 = 50.00; all long; 5 trades -> top5 None.
    "five_first_loss": {"rule": "measured", "trades": (
        ("long", "2024-01-10T14:00", "-2", "-50.00", "stop", False, ()),
        ("long", "2024-01-11T14:00", "1", "25.00", "signal", False, ()),
        ("long", "2024-01-12T14:00", "0.5", "12.50", "signal", False, ()),
        ("long", "2024-01-15T14:00", "-0.5", "-12.50", "signal", False, ()),
        ("long", "2024-01-16T14:00", "3", "75.00", "signal", False, ()),
    ), "expected": {
        "trades": 5, "expectancy_r": "0.4", "max_drawdown_r": "2", "net_money": "50.00", "long_trades": 5,
        "long_expectancy_r": "0.4", "short_trades": 0, "short_expectancy_r": None,
        "top5_removed_expectancy_r": None, "expectancy_by_year": ((2024, "0.4"),), "ambiguous_trades": 0,
        "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0}},
    # Six trades of equal r written "1.00", "1", "1", "1", "1", "1.0": the five removed are the first
    # five (ties go earlier first), so the one left is "1.0" and its mean 1.0 / 1 keeps "1.0".
    # Sum 6.00 / 6 = 1.00; cumulative never falls below its peak -> max_drawdown 0; net 6 x 25.00.
    "six_equal": {"rule": "measured", "trades": tuple(
        ("long", f"2024-02-0{day}T14:00", r, "25.00", "signal", False, ())
        for day, r in zip(range(1, 7), ("1.00", "1", "1", "1", "1", "1.0"))
    ), "expected": {
        "trades": 6, "expectancy_r": "1", "max_drawdown_r": "0", "net_money": "150.00", "long_trades": 6,
        "long_expectancy_r": "1", "short_trades": 0, "short_expectancy_r": None,
        "top5_removed_expectancy_r": "1.0", "expectancy_by_year": ((2024, "1"),), "ambiguous_trades": 0,
        "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0},
        "repr": {"top5_removed_expectancy_r": "1.0"}},
    # The sum runs in trade order at precision 28 (sochron.costs.CONTEXT): 1E+28 + 1 has 29 digits and
    # rounds half-even back to 1E+28, then + (-1E+28) = 0, so expectancy 0 / 3 = 0. In another order
    # (-1E+28 + 1 is exact at 28 digits, then + 1E+28 = 1) or at a higher precision it would be 1/3.
    # Cumulative 1E+28, 1E+28, 0 -> peak 1E+28 -> max_drawdown 1E+28. net 1.00 + 2.00 + 3.00 = 6.00.
    "order_at_precision_28": {"rule": "measured", "trades": (
        ("long", "2024-03-01T14:00", "1E+28", "1.00", "signal", False, ()),
        ("long", "2024-03-04T14:00", "1", "2.00", "signal", False, ()),
        ("long", "2024-03-05T14:00", "-1E+28", "3.00", "signal", False, ()),
    ), "expected": {
        "trades": 3, "expectancy_r": "0", "max_drawdown_r": "1E+28", "net_money": "6.00", "long_trades": 3,
        "long_expectancy_r": "0", "short_trades": 0, "short_expectancy_r": None,
        "top5_removed_expectancy_r": None, "expectancy_by_year": ((2024, "0"),), "ambiguous_trades": 0,
        "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0}},
    # A synthetic rule with offset_seconds 7200 (raw = UTC + 2 h). The entry_time_raw values are the
    # raw times 2024-01-01T01:00 and 2024-01-01T03:00, i.e. UTC 2023-12-31T23:00 and 2024-01-01T01:00:
    # one trade per year. expectancy (1 - 0.5) / 2 = 0.25; cumulative 1, 0.5 -> max_drawdown 0.5.
    "offset_rule": {"rule": "offset_7200", "trades": (
        ("long", "2024-01-01T01:00", "1", "25.00", "signal", False, ()),
        ("short", "2024-01-01T03:00", "-0.5", "-12.50", "stop", False, ()),
    ), "expected": {
        "trades": 2, "expectancy_r": "0.25", "max_drawdown_r": "0.5", "net_money": "12.50", "long_trades": 1,
        "long_expectancy_r": "1", "short_trades": 1, "short_expectancy_r": "-0.5",
        "top5_removed_expectancy_r": None, "expectancy_by_year": ((2023, "1"), (2024, "-0.5")),
        "ambiguous_trades": 0, "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0}},
}
# For "offset_rule" the stamps above are raw MT5 times (seconds since 1970 of that wall time).
OFFSET_RULE = {"server": "SYN-OFFSET", "symbol": "XAUUSDm", "terminal_build": 1, "offset_seconds": 7200,
               "version": "syn-1"}

# ----------------------------------------------------------------------------- AC-03 percentile

# Nearest rank: sort ascending and take rank ceil(q x n), counted from 1.
PERCENTILE_TWENTY = ("7", "3", "18", "1", "12", "20", "5", "14", "9", "16", "2", "11", "19", "6", "13",
                     "4", "17", "8", "15", "10")  # a shuffle of 1..20
PERCENTILE_CASES = (
    (PERCENTILE_TWENTY, "0.05", "1"),    # ceil(1.00) = 1
    (PERCENTILE_TWENTY, "0.5", "10"),    # ceil(10.0) = 10 (linear interpolation would give 10.5)
    (PERCENTILE_TWENTY, "0.95", "19"),   # ceil(19.00) = 19 (interpolation: 19.05)
    (PERCENTILE_TWENTY, "1", "20"),      # rank n
    (PERCENTILE_TWENTY, "0.951", "20"),  # ceil(19.020) = 20
    (PERCENTILE_TWENTY, "0.949", "19"),  # ceil(18.980) = 19
    (PERCENTILE_TWENTY, "0.001", "1"),   # ceil(0.020) = 1
    (("0.3", "-0.1", "0.2"), "0.5", "0.2"),     # ceil(1.5) = 2 of -0.1, 0.2, 0.3
    (("0.3", "-0.1", "0.2"), "0.333", "-0.1"),  # ceil(0.999) = 1
    (("0.3", "-0.1", "0.2"), "0.34", "0.2"),    # ceil(1.02) = 2
    (("-0.024",), "0.05", "-0.024"),            # n = 1: rank 1
    (("-0.024",), "1", "-0.024"),
)
# A thousand values (37 i mod 1000) - 500 for i = 0..999: a permutation of -500..499, so rank r is
# -501 + r. q = 0.05 -> rank 50 -> -451; 0.5 -> 500 -> -1; 0.95 -> 950 -> 449.
PERCENTILE_THOUSAND = {"0.05": "-451", "0.5": "-1", "0.95": "449"}

# ------------------------------------------------------------------------------ AC-05 neighbours

# Each row: (parameter, direction, value, valid). value = str(old x 0.9 or x 1.1) in CONTEXT, with
# f, s, n, N, M quantized to an integer ROUND_HALF_UP; theta and k keep the product's digits. A valid
# row's params are the base params with that one value; an invalid row (H001Params refuses it) has
# params None. Order f, s, n, theta, N, M, k, each "-" then "+", only USED_PARAMETERS[variant].
NEIGHBOUR_CASES = {
    # 16 x 0.9 = 14.4 -> 14, x 1.1 = 17.6 -> 18; 64 -> 57.6 -> 58, 70.4 -> 70; 20 -> 18.0 -> 18, 22.0 -> 22;
    # 0.50 -> 0.450, 0.550; 96 -> 86.4 -> 86, 105.6 -> 106; 48 -> 43.2 -> 43, 52.8 -> 53; 2.0 -> 1.80, 2.20.
    "A_default": {"variant": "A", "params": DEFAULTS, "rows": (
        ("f", "-", "14", True), ("f", "+", "18", True), ("s", "-", "58", True), ("s", "+", "70", True),
        ("n", "-", "18", True), ("n", "+", "22", True), ("theta", "-", "0.450", True),
        ("theta", "+", "0.550", True), ("k", "-", "1.80", True), ("k", "+", "2.20", True))},
    "B_default": {"variant": "B", "params": DEFAULTS, "rows": (
        ("n", "-", "18", True), ("n", "+", "22", True), ("N", "-", "86", True), ("N", "+", "106", True),
        ("M", "-", "43", True), ("M", "+", "53", True), ("k", "-", "1.80", True), ("k", "+", "2.20", True))},
    "C_default": {"variant": "C", "params": DEFAULTS, "rows": (
        ("f", "-", "14", True), ("f", "+", "18", True), ("s", "-", "58", True), ("s", "+", "70", True),
        ("n", "-", "18", True), ("n", "+", "22", True), ("N", "-", "86", True), ("N", "+", "106", True),
        ("M", "-", "43", True), ("M", "+", "53", True), ("k", "-", "1.80", True), ("k", "+", "2.20", True))},
    # Top of every range: f 24 x 1.1 = 26.4 -> 26 > 24; s 72 x 0.9 = 64.8 -> 65 < 3f = 72; n 30 -> 33.0 -> 33
    # > 30; N 192 -> 211.2 -> 211 > 192; M 96 -> 105.6 -> 106 > 96; k 3.0 -> 3.30 > 3.0; theta 1.00 -> 1.100
    # > 1.00. Valid: f 21.6 -> 22 (72 >= 66), s 79.2 -> 79, n 27.0 -> 27, N 172.8 -> 173, M 86.4 -> 86,
    # k 2.70, theta 0.900.
    "C_top": {"variant": "C", "params": {"f": 24, "s": 72, "n": 30, "theta": "1.00", "N": 192, "M": 96, "k": "3.0"},
              "rows": (
        ("f", "-", "22", True), ("f", "+", "26", False), ("s", "-", "65", False), ("s", "+", "79", True),
        ("n", "-", "27", True), ("n", "+", "33", False), ("N", "-", "173", True), ("N", "+", "211", False),
        ("M", "-", "86", True), ("M", "+", "106", False), ("k", "-", "2.70", True), ("k", "+", "3.30", False))},
    "A_top": {"variant": "A", "params": {"f": 24, "s": 72, "n": 30, "theta": "1.00", "N": 192, "M": 96, "k": "3.0"},
              "rows": (
        ("f", "-", "22", True), ("f", "+", "26", False), ("s", "-", "65", False), ("s", "+", "79", True),
        ("n", "-", "27", True), ("n", "+", "33", False), ("theta", "-", "0.900", True),
        ("theta", "+", "1.100", False), ("k", "-", "2.70", True), ("k", "+", "3.30", False))},
    # Bottom of every range: f 8 x 0.9 = 7.2 -> 7 < 8; s 32 -> 28.8 -> 29 < 32; n 10 -> 9.0 -> 9 < 10;
    # N 48 -> 43.2 -> 43 < 48; M 24 -> 21.6 -> 22 < 24; k 1.5 -> 1.35 < 1.5; theta 0.25 -> 0.225 < 0.25.
    # Valid: f 8.8 -> 9 (32 >= 27), s 35.2 -> 35, n 11.0 -> 11, N 52.8 -> 53, M 26.4 -> 26, k 1.65, theta 0.275.
    "C_bottom": {"variant": "C", "params": {"f": 8, "s": 32, "n": 10, "theta": "0.25", "N": 48, "M": 24, "k": "1.5"},
                 "rows": (
        ("f", "-", "7", False), ("f", "+", "9", True), ("s", "-", "29", False), ("s", "+", "35", True),
        ("n", "-", "9", False), ("n", "+", "11", True), ("N", "-", "43", False), ("N", "+", "53", True),
        ("M", "-", "22", False), ("M", "+", "26", True), ("k", "-", "1.35", False), ("k", "+", "1.65", True))},
    "A_bottom": {"variant": "A", "params": {"f": 8, "s": 32, "n": 10, "theta": "0.25", "N": 48, "M": 24, "k": "1.5"},
                 "rows": (
        ("f", "-", "7", False), ("f", "+", "9", True), ("s", "-", "29", False), ("s", "+", "35", True),
        ("n", "-", "9", False), ("n", "+", "11", True), ("theta", "-", "0.225", False),
        ("theta", "+", "0.275", True), ("k", "-", "1.35", False), ("k", "+", "1.65", True))},
    # s = 3f: f 16 x 1.1 = 17.6 -> 18 needs s >= 54 > 48; s 48 x 0.9 = 43.2 -> 43 < 48. The rest is valid:
    # f 14 (48 >= 42), s 52.8 -> 53.
    "A_s_is_3f": {"variant": "A", "params": {**DEFAULTS, "s": 48}, "rows": (
        ("f", "-", "14", True), ("f", "+", "18", False), ("s", "-", "43", False), ("s", "+", "53", True),
        ("n", "-", "18", True), ("n", "+", "22", True), ("theta", "-", "0.450", True),
        ("theta", "+", "0.550", True), ("k", "-", "1.80", True), ("k", "+", "2.20", True))},
    # M = N = 48: N 43.2 -> 43 < M; M 52.8 -> 53 > N. Valid: N 53, M 43, n 18/22, k 1.80/2.20.
    "B_m_is_n": {"variant": "B", "params": {**DEFAULTS, "N": 48, "M": 48}, "rows": (
        ("n", "-", "18", True), ("n", "+", "22", True), ("N", "-", "43", False), ("N", "+", "53", True),
        ("M", "-", "43", True), ("M", "+", "53", False), ("k", "-", "1.80", True), ("k", "+", "2.20", True))},
    # Exact halves, where ROUND_HALF_UP and ROUND_HALF_EVEN differ on "+": 15 x 1.1 = 16.5 -> 17 (not 16),
    # 55 x 1.1 = 60.5 -> 61 (not 60), 35 x 1.1 = 38.5 -> 39 (not 38); on "-": 15 x 0.9 = 13.5 -> 14,
    # 55 x 0.9 = 49.5 -> 50, 35 x 0.9 = 31.5 -> 32. k 1.5 x 0.9 = 1.35 < 1.5 (invalid), x 1.1 = 1.65.
    # f 17 needs s >= 51 <= 55; s 50 >= 45; N 50 >= M 35; M 39 <= N 55.
    "C_halves": {"variant": "C", "params": {"f": 15, "s": 55, "n": 15, "theta": "0.25", "N": 55, "M": 35, "k": "1.5"},
                 "rows": (
        ("f", "-", "14", True), ("f", "+", "17", True), ("s", "-", "50", True), ("s", "+", "61", True),
        ("n", "-", "14", True), ("n", "+", "17", True), ("N", "-", "50", True), ("N", "+", "61", True),
        ("M", "-", "32", True), ("M", "+", "39", True), ("k", "-", "1.35", False), ("k", "+", "1.65", True))},
}
# Neighbour counts and the pass mark ceil(0.8 x count): A 10 -> 8, B 8 -> 6.4 -> 7, C 12 -> 9.6 -> 10.
NEIGHBOUR_COUNTS = {"A": (10, 8), "B": (8, 7), "C": (12, 10)}

# ------------------------------------------------------------------------------- AC-05 evaluate

EVAL_DATASET = ("SYN-EVAL", "9" * 64, "2023-01-02T00:00:00", "2024-12-30T00:00:00", 700000)
HOLDOUT_DATASET = ("SYN-HOLD", "8" * 64, "2025-01-01T00:00:00", "2025-06-01T00:00:00", 150000)  # start = cutoff
PARTIAL_DATASET = ("SYN-PART", "7" * 64, "2024-12-31T23:59:59", "2025-06-01T00:00:00", 150001)  # 1 s before


def _summary(trades, expectancy, drawdown, long=(60, "0.15"), short=(40, "0"), top5="0.01",
             years=((2023, "0"), (2024, "0.2"))):
    return {"trades": trades, "expectancy_r": expectancy, "max_drawdown_r": drawdown, "net_money": "250.00",
            "long_trades": long[0], "long_expectancy_r": long[1], "short_trades": short[0],
            "short_expectancy_r": short[1], "top5_removed_expectancy_r": top5, "expectancy_by_year": years,
            "ambiguous_trades": 0, "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0}


ZERO_SUMMARY = {"trades": 0, "expectancy_r": None, "max_drawdown_r": "0", "net_money": "0", "long_trades": 0,
                "long_expectancy_r": None, "short_trades": 0, "short_expectancy_r": None,
                "top5_removed_expectancy_r": None, "expectancy_by_year": (), "ambiguous_trades": 0,
                "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0}

# Every row at its passing edge: 100 trades, 0.10 R, 24 R, 7 of 8 neighbours, a year at exactly 0 and
# the short side at exactly 0; stress 0.01 > 0; P95 0.09 < 0.10; long-only equal on expectancy and
# worse on drawdown (25 > 24) so the variant wins on one.
EVAL_GO = {
    "variant": "B", "params": DEFAULTS, "dataset": EVAL_DATASET,
    "base": _summary(100, "0.10", "24"),
    "stress": _summary(100, "0.01", "30"),
    "long_only": _summary(100, "0.10", "25", long=(100, "0.10"), short=(0, None)),
    "random": {"trades_per_run": 100, "mean_r": "-0.03", "p05_r": "-0.08", "p50_r": "-0.03", "p95_r": "0.09",
               "variant_mean_hold_m1": "40", "variant_median_hold_m1": 31, "baseline_mean_hold_m1": "39.5",
               "baseline_median_hold_m1": 30},
    "robustness": ("0.01", "0.01", "0.01", "0.01", "0.01", "0.01", "0.01", "0"),  # one per B neighbour
}
EVAL_GO_ROWS = (
    ("trades", "100", "100", True),
    ("expectancy_1x", "0.10", "0.10", True),
    ("expectancy_2x", "0.01", "0", True),
    ("max_drawdown_r", "24", "24", True),
    ("robustness", "7/8", "7/8", True),
    ("vs_random_entry", "0.10", "0.09", True),
    ("top5_removed", "0.01", "0", True),
    ("years", "2023:0;2024:0.2", "0", True),
    ("sides", "long:0.15;short:0", "0", True),
    ("vs_long_only", "expectancy:0.10/0.10;max_drawdown:24/25", "better on one", True),
)
# (label, changes to EVAL_GO, verdict, screen, {row number: (value, threshold, passed)}). A change
# "base"/"stress"/"long_only" replaces those summary fields; "random" replaces baseline fields; the
# value None for "stress", "long_only" or "random" leaves that input out; "robustness" replaces the
# neighbour expectancies (an empty tuple leaves robustness out; None as one expectancy is a neighbour
# run without trades). trades_per_run follows the base trades (contract: they must be equal).
EVALUATE_CASES = (
    ("every row at its passing edge", {}, "go", True, {}),
    ("99 trades", {"base": {"trades": 99}, "random": {"trades_per_run": 99}}, "insufficient", True,
     {1: ("99", "100", False)}),
    ("expectancy just under 0.10", {"base": {"expectancy_r": "0.0999"}}, "stop", True,
     {2: ("0.0999", "0.10", False), 6: ("0.0999", "0.09", True),
      10: ("expectancy:0.0999/0.10;max_drawdown:24/25", "better on one", True)}),
    ("stress expectancy exactly 0", {"stress": {"expectancy_r": "0"}}, "stop", True, {3: ("0", "0", False)}),
    ("drawdown just over 24", {"base": {"max_drawdown_r": "24.01"}}, "stop", True,
     {4: ("24.01", "24", False), 10: ("expectancy:0.10/0.10;max_drawdown:24.01/25", "better on one", True)}),
    ("6 of 8 neighbours", {"robustness": ("0.01", "0.01", "0.01", "0.01", "0.01", "0.01", "0", "-0.01")}, "stop",
     True, {5: ("6/8", "7/8", False)}),
    ("a neighbour without trades does not pass, the row still counts",
     {"robustness": ("0.01", "0.01", None, "0.01", "0.01", "0.01", "0.01", "0.01")}, "go", True, {}),
    ("expectancy equal to P95", {"random": {"p95_r": "0.10"}}, "stop", True, {6: ("0.10", "0.10", False)}),
    ("top 5 removed exactly 0", {"base": {"top5_removed_expectancy_r": "0"}}, "stop", True,
     {7: ("0", "0", False)}),
    ("a losing year", {"base": {"expectancy_by_year": ((2023, "-0.01"), (2024, "0.2"))}}, "stop", True,
     {8: ("2023:-0.01;2024:0.2", "0", False)}),
    ("no year", {"base": {"expectancy_by_year": ()}}, "stop", True, {8: ("none", "0", False)}),
    ("a losing short side", {"base": {"short_expectancy_r": "-0.01"}}, "stop", True,
     {9: ("long:0.15;short:-0.01", "0", False)}),
    ("no short trades", {"base": {"short_trades": 0, "short_expectancy_r": None}}, "stop", True,
     {9: ("long:0.15;short:none", "0", False)}),
    ("long-only equal on both", {"long_only": {"max_drawdown_r": "24"}}, "stop", True,
     {10: ("expectancy:0.10/0.10;max_drawdown:24/24", "better on one", False)}),
    ("long-only without trades", {"long_only": ZERO_SUMMARY}, "stop", True,
     {10: ("expectancy:0.10/none;max_drawdown:24/0", "better on one", False)}),
    ("better than long-only on expectancy only",
     {"long_only": {"expectancy_r": "0.09", "max_drawdown_r": "20"}}, "go", True,
     {10: ("expectancy:0.10/0.09;max_drawdown:24/20", "better on one", True)}),
    ("no stress run", {"stress": None}, "stop", True, {3: ("none", "0", False)}),
    ("no robustness runs", {"robustness": ()}, "stop", True, {5: ("none", "7/8", False)}),
    ("no random-entry baseline", {"random": None}, "stop", True, {6: ("0.10", "none", False)}),
    ("no long-only run", {"long_only": None}, "stop", True,
     {10: ("expectancy:0.10/none;max_drawdown:24/none", "better on one", False)}),
    ("100 trades and every optional input missing",
     {"stress": None, "long_only": None, "random": None, "robustness": ()}, "stop", True,
     {3: ("none", "0", False), 5: ("none", "7/8", False), 6: ("0.10", "none", False),
      10: ("expectancy:0.10/none;max_drawdown:24/none", "better on one", False)}),
    ("no trades and every optional input missing",
     {"base": ZERO_SUMMARY, "stress": None, "long_only": None, "random": None, "robustness": ()},
     "insufficient", True,
     {1: ("0", "100", False), 2: ("none", "0.10", False), 3: ("none", "0", False), 4: ("0", "24", True),
      5: ("none", "7/8", False), 6: ("none", "none", False), 7: ("none", "0", False), 8: ("none", "0", False),
      9: ("long:none;short:none", "0", False),
      10: ("expectancy:none/none;max_drawdown:0/none", "better on one", False)}),
    ("50 trades and every optional input missing",
     {"base": {"trades": 50}, "stress": None, "long_only": None, "random": None, "robustness": ()},
     "insufficient", True,
     {1: ("50", "100", False), 3: ("none", "0", False), 5: ("none", "7/8", False), 6: ("0.10", "none", False),
      10: ("expectancy:0.10/none;max_drawdown:24/none", "better on one", False)}),
    ("data from the cutoff on: not a screen", {"dataset": HOLDOUT_DATASET}, "go", False, {}),
    ("data from one second before the cutoff: a screen", {"dataset": PARTIAL_DATASET}, "go", True, {}),
    # B with M = N = 48: 2 of the 8 neighbours are invalid (count 8, mark 7), so 6 is the best possible.
    ("M = N: invalid neighbours count as failed", {"params": {**DEFAULTS, "N": 48, "M": 48},
     "robustness": ("0.01",) * 6}, "stop", True, {5: ("6/8", "7/8", False)}),
    # A: 10 neighbours, mark 8; C: 12 neighbours, mark 10.
    ("V-A: 8 of 10", {"variant": "A", "robustness": ("0.01",) * 8 + ("0", "0")}, "go", True,
     {5: ("8/10", "8/10", True)}),
    ("V-C: 10 of 12", {"variant": "C", "robustness": ("0", "0") + ("0.01",) * 10}, "go", True,
     {5: ("10/12", "10/12", True)}),
    ("V-C: 9 of 12", {"variant": "C", "robustness": ("0", "0", "0") + ("0.01",) * 9}, "stop", True,
     {5: ("9/12", "10/12", False)}),
)

# ----------------------------------------------------------------- AC-02 and AC-04 synthetic data

# 106 M15 bars; bar u opens at 2024-01-08T07:45Z + 15u minutes (New York is UTC-5 in January). Bar
# 97 opens at 2024-01-09T08:00Z = 03:00 New York, the first minute of the entry window, and bar 105
# at 10:00Z. Each bar holds M1 at minutes 0, 5 and 10, except bar 101 (minute 0 only) and bar 103
# (minutes 0 and 5). M15 values follow aggregate (first open, highest high, lowest low, last close),
# but the M15 spread is set per bar: 200 everywhere except bar 99, 700 (> 3 x the median 200).
BAR0 = "2024-01-08T07:45"
BARS = 106
BAR_MINUTES = {101: (0,), 103: (0, 5)}
# First M1 index of each bar: 3u up to bar 101 (101 bars x 3 = 303), then 304 (bar 101 has one M1),
# 307, 309 (bar 103 has two), 312; 315 M1 in all, the last at index 314 (bar 105, minute 10).
FIRST_M1 = tuple(3 * u for u in range(102)) + (304, 307, 309, 312)
M1_COUNT = 315
M15_SPREAD = {99: 700}
M15_FLAGS = {1: ("unexpected_gap",), 104: ("price_jump",)}
# entry_blockers on every bar t = 0..104 for RUN_PARAMS (V-B, warm from 97, lookback L = 97 bars,
# so the flags of bar f block t = f..f+96): t <= 95 are warm-up (and spread_unknown below 96);
# t = 96 is in the window with a known median but warm-up only; 97: bar 1's flag is in its lookback
# (97 - 96 = 1); 99: spread 700 > 600 (spread_filter); 104: its own flag. Left: 98, 100, 101, 102, 103.
ELIGIBLE = (98, 100, 101, 102, 103)


def bar_stamp(u, minute=0):
    start = datetime.fromisoformat(BAR0).replace(tzinfo=UTC)
    return (start + timedelta(minutes=15 * u + minute)).strftime("%Y-%m-%dT%H:%M")


def _cents(value):
    return f"{value // 100}.{value % 100:02d}"


def m1_rows(kind):
    """(stamp, open, high, low, close, spread) for every M1; kind is "flat", "signal" or "wave".

    flat: open = close = 2000.00, high 2000.50, low 1999.50 (TR 1.00, ATR 1.00, no H001 signal).
    signal: flat with a V-B breakout in bar 98 (close 2001.00 > HH_48 = 2000.50) for the runner.
    wave: close = 2000.00 + 0.10 x ((7i mod 41) - 20), open = the previous close, plus a gap of
    +3.00 at M1 160 and -12.00 at M1 305, high/low 0.30 beyond open and close. Every M1 spread is 200.
    """
    rows = []
    previous = 200000
    index = 0
    for u in range(BARS):
        for minute in BAR_MINUTES.get(u, (0, 5, 10)):
            stamp = bar_stamp(u, minute)
            if kind == "wave":
                close = 200000 + 10 * (((7 * index) % 41) - 20)
                open_ = previous + {160: 300, 305: -1200}.get(index, 0)
                rows.append((stamp, _cents(open_), _cents(max(open_, close) + 30), _cents(min(open_, close) - 30),
                             _cents(close), 200))
                previous = close
            elif kind == "signal" and u == 98:
                rows.append({0: (stamp, "2000.00", "2000.50", "1999.50", "2000.00", 200),
                             5: (stamp, "2000.00", "2000.60", "1999.90", "2000.40", 200),
                             10: (stamp, "2000.40", "2001.10", "2000.30", "2001.00", 200)}[minute])
            else:
                rows.append((stamp, "2000.00", "2000.50", "1999.50", "2000.00", 200))
            index += 1
    return tuple(rows)


# The datasets of these series (period [start, end), m1_bars 315).
FLAT_DATASET = ("SYN-FLAT", "d" * 64, "2024-01-08T00:00:00", "2024-01-10T00:00:00", 315)
WAVE_DATASET = ("SYN-WAVE", "e" * 64, "2024-01-08T00:00:00", "2024-01-10T00:00:00", 315)
SIGNAL_DATASET = ("SYN-SIG1", "1" * 64, "2024-01-08T00:00:00", "2024-01-10T00:00:00", 315)
SIGNAL_DATASET_2 = ("SYN-SIG2", "2" * 64, "2024-01-08T00:00:00", "2024-01-10T00:00:00", 315)

# Small series at the cutoff: M15 bars at 23:00, 23:15, 23:30, 23:45 on 2024-12-31 with one M1 each at
# 23:00, 23:15, 23:30 and 23:59 (the last minute before the cutoff); flat prices as above.
EDGE_M1 = ("2024-12-31T23:00", "2024-12-31T23:15", "2024-12-31T23:30", "2024-12-31T23:59")
EDGE_BARS = ("2024-12-31T23:00", "2024-12-31T23:15", "2024-12-31T23:30", "2024-12-31T23:45")
EDGE_DATASET = ("SYN-EDGE", "3" * 64, "2024-12-31T00:00:00", "2025-01-01T00:00:00", 4)  # end = cutoff
AT_CUTOFF = "2025-01-01T00:00"
AFTER_CUTOFF = "2025-03-03T14:00"

# ------------------------------------------------------------------------- AC-04 random entry

# Every random-entry test uses RUN_PARAMS (V-B), equity 10000 and a sizer that returns lots 0.02 with
# risk_money 25 (actual_risk None) unless it says otherwise. stop_distance = k x ATR[t] = 3.0 x ATR.

# FLAT: model = H001_COSTS with swap_long 0 (both swaps 0). The variant is built by hand with
# simulate_trade (lots 0.02, risk_money 25): no H001 signal exists on flat prices (contract AC-04).
#   T1 long  entry M1 294 (bar 98, 2024-01-09T08:15Z), exit_index 300, stop_distance 50.00: "signal", hold 6
#   T2 short entry M1 303 (bar 101), stop_distance 0.10: the ask 2000.20 is beyond the stop 2000.10 at
#            the entry open, so "stop" at that open, hold 0 (not a strategy-timed exit)
#   T4 long  entry M1 314 (the last M1), no exit_index, stop_distance 50.00: "end_of_data", hold 0
# Each trade: gross 0 (open = close = 2000.00), spread 200 x 0.001 x 100 x 0.02 = 0.40, slippage
# 50 x 0.001 x 100 x 0.02 x 2 = 0.20, commission 0, swap 0 -> net -0.60 -> r = -0.60 / 25 = -0.024.
FLAT_VARIANT = (
    ("long", 294, "50.00", 300),
    ("short", 303, "0.10", None),
    ("long", 314, "50.00", None),
)
FLAT_VARIANT_REASONS = (("signal", False), ("stop", False), ("end_of_data", False))
# summarize of that variant: 3 trades of -0.024 -> expectancy -0.072 / 3 = -0.024; cumulative -0.024,
# -0.048, -0.072 from 0 -> max_drawdown 0.072; net 3 x -0.60 = -1.80; long T1, T4; short T2; all 2024.
FLAT_SUMMARY = {
    "trades": 3, "expectancy_r": "-0.024", "max_drawdown_r": "0.072", "net_money": "-1.80",
    "long_trades": 2, "long_expectancy_r": "-0.024", "short_trades": 1, "short_expectancy_r": "-0.024",
    "top5_removed_expectancy_r": None, "expectancy_by_year": ((2024, "-0.024"),), "ambiguous_trades": 0,
    "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 1,
}
# hs (holds of signal, end_of_data or ambiguous trades, in trade order) = (6, 0); K = 3.
# Variant holds (exit index - entry index, every trade) 6, 0, 0 -> mean 6 / 3 = 2, median: rank
# ceil(0.5 x 3) = 2 of 0, 0, 6 -> 0.
FLAT_HS = (6, 0)

# A scripted round on FLAT (eligible pool 98, 100, 101, 102, 103; hs (6, 0); K = 3). The fake
# random.Random returns these values in a cycle; the sizer returns lots None on its first call of
# every round (4 calls per round). Each randrange call gets the n shown:
#   bar  randrange(5) -> 0 -> t 98; sizer None: the bar leaves the pool, nothing else is drawn
#   bar  randrange(4) -> 3 -> t 103 (pool 100, 101, 102, 103); side randrange(2) -> 0 long;
#        h randrange(2) -> 0 -> 6; entry = first M1 of bar 104 = 309; planned 315 is not < 315, so
#        exit_index None: end of data at M1 314, hold 5
#   bar  randrange(3) -> 1 -> t 101 (pool 100, 101, 102); side -> 1 short; h -> 1 -> 0;
#        entry = first M1 of bar 102 = 304; planned 304 + max(0, 1) = 305; hold 1
#   bar  randrange(2) -> 0 -> t 100 (pool 100, 102); side -> 1 short; h -> 0 -> 6;
#        entry = first M1 of bar 101 = 303; planned 309; hold 6
FLAT_SCRIPT = (0, 3, 0, 0, 1, 1, 1, 0, 1, 0)
FLAT_SCRIPT_N = (5, 4, 2, 2, 3, 2, 2, 2, 2, 2)
FLAT_SIZER_PATTERN = (None, "0.02", "0.02", "0.02")
# Every random trade is -0.024 as above (no stop is reachable: long stop 2000.20 - 3.00 = 1997.20 <
# low 1999.50, short stop 2003.00 > high + spread 2000.70), so every round expectancy is
# 3 x -0.024 / 3 = -0.024 whatever the draws; mean 1000 x -0.024 / 1000 = -0.024; P5 = P50 = P95 = -0.024.
# Holds per round 5, 1, 6 -> 3000 trades: mean (5 + 1 + 6) x 1000 / 3000 = 4; median rank
# ceil(0.5 x 3000) = 1500 of 1000 x 1, 1000 x 5, 1000 x 6 -> 5.
FLAT_BASELINE = {
    "runs": 1000, "trades_per_run": 3, "mean_r": "-0.024", "p05_r": "-0.024", "p50_r": "-0.024",
    "p95_r": "-0.024", "variant_mean_hold_m1": "2", "variant_median_hold_m1": 0,
    "baseline_mean_hold_m1": "4", "baseline_median_hold_m1": 5,
}
FLAT_ROUND_EXPECTANCY = "-0.024"
FLAT_STOP_DISTANCE = "3"  # 3.0 x ATR 1.00

# WAVE: model = H001_COSTS. The variant (lots 0.02, risk_money 25, built with simulate_trade):
#   V1 long  entry 270, exit_index 276, stop_distance 50.00: "signal", hold 6
#   V2 short entry 282, stop_distance 0.10: "stop" at the entry open (ask beyond the stop), hold 0
#   V3 long  entry 297 (open 2000.20), exit_index 305, stop_distance 3.00: stop 2000.20 + 0.20 - 3.00 =
#            1997.40; the lows of M1 297..304 are 1997.90 at least, so nothing touches it, and M1 305 opens
#            at 2001.70 - 12.00 = 1989.70 <= 1997.40: "stop" + ambiguous at that open, hold 8
#   V4 long  entry 314, no exit_index, stop_distance 50.00: "end_of_data", hold 0
# hs = (6, 8, 0) (V2 is a plain stop and is left out); K = 4. Variant holds 6, 0, 8, 0.
WAVE_VARIANT = (
    ("long", 270, "50.00", 276),
    ("short", 282, "0.10", None),
    ("long", 297, "3.00", 305),
    ("long", 314, "50.00", None),
)
WAVE_VARIANT_REASONS = (("signal", False), ("stop", False), ("stop", True), ("end_of_data", False))
WAVE_HS = (6, 8, 0)
# variant holds 6, 0, 8, 0: mean 14 / 4 = 3.5; median rank ceil(0.5 x 4) = 2 of 0, 0, 6, 8 -> 0.
WAVE_VARIANT_HOLD = ("3.5", 0)
# The WAVE sizer returns lots None on its calls number 3, 10, 17, ... (call index % 7 == 2, from 0);
# at most 5 sizer calls fit in a round (5 eligible bars), so a round never runs out of bars.
WAVE_SIZER_NONE_EVERY = (7, 2)

# ---------------------------------------------------------------------------- AC-06 render_report

# The registry of the report test, seq by seq (all H001, setup of the normative example):
#   (seq, status, started_seq, purpose, variant, params, dataset, base seq, extra)
REPORT_DATASETS = {
    "D1": ("SYN-0001", "a" * 64, "2023-01-02T00:00:00", "2023-01-07T00:00:00", 7200),
    "D2": ("SYN-0002", "b" * 64, "2023-01-09T00:00:00", "2023-01-14T00:00:00", 7200),
    "D3": ("SYN-0003", "c" * 64, "2025-01-01T00:00:00", "2025-03-01T00:00:00", 82080),
}
REPORT_PARAMS = {
    "A0": ("A", DEFAULTS), "A1": ("A", {**DEFAULTS, "k": "2.2"}), "B0": ("B", DEFAULTS),
    "Bn18": ("B", {**DEFAULTS, "n": 18}), "Bn22": ("B", {**DEFAULTS, "n": 22}), "C0": ("C", DEFAULTS),
}


def _report_summary(trades, expectancy, drawdown, long, short, top5, years, counters):
    ambiguous, flagged, gaps, end = counters
    return {"trades": trades, "expectancy_r": expectancy, "max_drawdown_r": drawdown, "net_money": "100.00",
            "long_trades": long[0], "long_expectancy_r": long[1], "short_trades": short[0],
            "short_expectancy_r": short[1], "top5_removed_expectancy_r": top5, "expectancy_by_year": years,
            "ambiguous_trades": ambiguous, "flagged_trades": flagged, "gap_fills": gaps, "end_of_data_trades": end}


REPORT_SUMMARIES = {
    "SA": _report_summary(120, "0.12", "9.5", (70, "0.15"), (50, "0.078"), "0.05", ((2023, "0.12"),), (1, 2, 1, 0)),
    "SAx": _report_summary(40, "0.01", "3", (20, "0.02"), (20, "0"), "-0.1", ((2023, "0.01"),), (0, 0, 0, 0)),
    "SB": _report_summary(80, "0.21", "6", (45, "0.25"), (35, "0.16"), "0.11", ((2023, "0.21"),), (0, 3, 2, 1)),
    "SBR": _report_summary(78, "0.19", "7", (44, "0.2"), (34, "0.18"), "0.09", ((2023, "0.19"),), (2, 0, 0, 0)),
    "SBS": _report_summary(80, "0.04", "11", (45, "0.07"), (35, "0.001"), "-0.05", ((2023, "0.04"),), (0, 3, 2, 1)),
    "SC": _report_summary(104, "-0.02", "30.5", (60, "-0.01"), (44, "-0.034"), "-0.09", ((2025, "-0.02"),),
                          (0, 0, 0, 2)),
}
REPORT_BASELINE = {"runs": 1000, "trades_per_run": 80, "mean_r": "-0.031", "p05_r": "-0.102", "p50_r": "-0.030",
                   "p95_r": "0.044", "variant_mean_hold_m1": "37.5", "variant_median_hold_m1": 31,
                   "baseline_mean_hold_m1": "36.9", "baseline_median_hold_m1": 30}
# extra: summary key, "stress" (model stress(H001_COSTS)), "long_only" (sides long), "random"
# (seed from the base, runs 1000, baseline REPORT_BASELINE), "error" text.
REPORT_RECORDS = (
    (1, "started", None, "select", "A0", "D1", None, {}),
    (2, "ok", 1, "select", "A0", "D1", None, {"summary": "SA"}),
    (3, "started", None, "select", "A1", "D1", None, {}),
    (4, "failed", 3, "select", "A1", "D1", None, {"error": "RuntimeError: boom"}),
    (5, "started", None, "select", "A0", "D2", None, {}),  # interrupted
    (6, "started", None, "select", "B0", "D1", None, {}),
    (7, "ok", 6, "select", "B0", "D1", None, {"summary": "SB"}),
    (8, "started", None, "robustness", "Bn18", "D1", 7, {}),
    (9, "ok", 8, "robustness", "Bn18", "D1", 7, {"summary": "SBR"}),
    (10, "started", None, "robustness", "Bn22", "D1", 7, {}),  # interrupted
    (11, "started", None, "stress", "B0", "D1", 7, {"stress": True}),
    (12, "ok", 11, "stress", "B0", "D1", 7, {"stress": True, "summary": "SBS"}),
    (13, "started", None, "random_entry", "B0", "D1", 7, {"random": True}),
    (14, "ok", 13, "random_entry", "B0", "D1", 7, {"random": True, "baseline": True}),
    (15, "started", None, "select", "C0", "D3", None, {}),
    (16, "ok", 15, "select", "C0", "D3", None, {"summary": "SC"}),
    (17, "started", None, "long_only", "C0", "D3", 16, {"long_only": True}),
    (18, "failed", 17, "long_only", "C0", "D3", 16, {"long_only": True, "error": "KeyboardInterrupt: "}),
)
# Lines appended after seq 18 for the mixed-hypothesis cases: an H002 select ok of B (other equity,
# which the setup of H001 does not see) and an H002 robustness line on it.
REPORT_H002_RECORDS = (
    (19, "started", None, "select", "B0", "D1", None, {"hypothesis": "H002", "equity": "5000"}),
    (20, "ok", 19, "select", "B0", "D1", None, {"hypothesis": "H002", "equity": "5000", "summary": "SB"}),
    (21, "started", None, "robustness", "Bn18", "D1", 20, {"hypothesis": "H002", "equity": "5000"}),
)
# A second H001 select ok of B (k 2.2) appended after seq 18: a base that is not the locked one.
REPORT_SECOND_B = (
    (19, "started", None, "select", "B0k", "D1", None, {}),
    (20, "ok", 19, "select", "B0k", "D1", None, {"summary": "SB"}),
)
REPORT_PARAMS["B0k"] = ("B", {**DEFAULTS, "k": "2.2"})
# The seed of seq 13/14 is int(run_id of seq 7 [:15], 16); run_id of seq 7 hashed as described at the top.
REPORT_RUN_ID_7 = "e6b142d32c19223377daa8192f88e1ad1a4b60b24644272620453f26c94eafdd"
REPORT_SEED = 1038946323396661795  # int("e6b142d32c19223", 16)

# The Evaluations shown in the report (built directly; render_report prints their checks as given).
# Each row: (name, value, threshold, passed). Values as evaluate gives them for the records above
# when every optional input is left out (A, C) or robustness is left out (B).
REPORT_EVALUATIONS = {
    "A": {"base_seq": 2, "screen": True, "verdict": "stop", "checks": (
        ("trades", "120", "100", True), ("expectancy_1x", "0.12", "0.10", True), ("expectancy_2x", "none", "0", False),
        ("max_drawdown_r", "9.5", "24", True), ("robustness", "none", "8/10", False),
        ("vs_random_entry", "0.12", "none", False), ("top5_removed", "0.05", "0", True),
        ("years", "2023:0.12", "0", True), ("sides", "long:0.15;short:0.078", "0", True),
        ("vs_long_only", "expectancy:0.12/none;max_drawdown:9.5/none", "better on one", False))},
    "B": {"base_seq": 7, "screen": True, "verdict": "insufficient", "checks": (
        ("trades", "80", "100", False), ("expectancy_1x", "0.21", "0.10", True), ("expectancy_2x", "0.04", "0", True),
        ("max_drawdown_r", "6", "24", True), ("robustness", "none", "7/8", False),
        ("vs_random_entry", "0.21", "0.044", True), ("top5_removed", "0.11", "0", True),
        ("years", "2023:0.21", "0", True), ("sides", "long:0.25;short:0.16", "0", True),
        ("vs_long_only", "expectancy:0.21/none;max_drawdown:6/none", "better on one", False))},
    "C": {"base_seq": 16, "screen": False, "verdict": "stop", "checks": (
        ("trades", "104", "100", True), ("expectancy_1x", "-0.02", "0.10", False), ("expectancy_2x", "none", "0", False),
        ("max_drawdown_r", "30.5", "24", False), ("robustness", "none", "10/12", False),
        ("vs_random_entry", "-0.02", "none", False), ("top5_removed", "-0.09", "0", False),
        ("years", "2025:-0.02", "0", False), ("sides", "long:-0.01;short:-0.034", "0", False),
        ("vs_long_only", "expectancy:-0.02/none;max_drawdown:30.5/none", "better on one", False))},
}

_SETUP = (
    "setup: commit 0123456789abcdef0123456789abcdef01234567 · sizer fixed-0.02 · equity 10000 · rollover "
    "America/New_York 17:00 · กฎเวลา Exness-MT5Trial14 1 · cost_model symbol=XAUUSDm;point=0.001;"
    "contract_size=100;volume_min=0.01;volume_step=0.01;volume_max=200;spread_fallback_points=240;"
    "commission_per_lot_per_side=0;slippage_points_per_side=50;swap_long_points_per_night=-503.8;"
    "swap_short_points_per_night=0;triple_swap_weekday=2;stress_factor=1"
)
_SCREEN = "การประเมินนี้เป็น screen ไม่ใช่คำตัดสินของ H001: มีข้อมูลก่อน cutoff ของ holdout"


def _table(rows):
    lines = ["| # | เงื่อนไข | ค่า | เกณฑ์ | ผล |", "|---|---|---|---|---|"]
    for number, (name, value, threshold, passed) in enumerate(rows, start=1):
        lines.append(f"| {number} | {name} | {value} | {threshold} | {'ผ่าน' if passed else 'ไม่ผ่าน'} |")
    return lines


_REGISTRY_HEAD = (
    "## Registry",
    "",
    "| โครงสร้าง | purpose | started | ok | failed | interrupted | งบ |",
    "|---|---|---|---|---|---|---|",
)
# Registry rows of REPORT_RECORDS. A select: started 1, 3, 5; ok 2; failed 4 (of 3); interrupted 5;
# distinct params A0, A1 -> 2/6. B select: 6/7 -> 1/6. B robustness: started 8, 10; ok 9; interrupted
# 10 -> 2/14. B stress: 11/12 -> ok 1 -> 1/1. B random_entry: 13/14. C select 15/16; C long_only:
# started 17, failed 18. Budget: select params A 2 + B 1 + C 1 = 4, robustness started 2, stress
# started 1 -> 7. long_only and random_entry are "ไม่นับ".
_REPORT_REGISTRY_ROWS = (
    "| A | select | 3 | 1 | 1 | 1 | 2/6 |",
    "| A | robustness | 0 | 0 | 0 | 0 | 0/14 |",
    "| A | stress | 0 | 0 | 0 | 0 | 0/1 |",
    "| A | long_only | 0 | 0 | 0 | 0 | ไม่นับ |",
    "| A | random_entry | 0 | 0 | 0 | 0 | ไม่นับ |",
    "| B | select | 1 | 1 | 0 | 0 | 1/6 |",
    "| B | robustness | 2 | 1 | 0 | 1 | 2/14 |",
    "| B | stress | 1 | 1 | 0 | 0 | 1/1 |",
    "| B | long_only | 0 | 0 | 0 | 0 | ไม่นับ |",
    "| B | random_entry | 1 | 1 | 0 | 0 | ไม่นับ |",
    "| C | select | 1 | 1 | 0 | 0 | 1/6 |",
    "| C | robustness | 0 | 0 | 0 | 0 | 0/14 |",
    "| C | stress | 0 | 0 | 0 | 0 | 0/1 |",
    "| C | long_only | 1 | 0 | 1 | 0 | ไม่นับ |",
    "| C | random_entry | 0 | 0 | 0 | 0 | ไม่นับ |",
)
_OWNER = (
    "## สิ่งที่เจ้าของตัดสินเอง",
    "",
    "- holdout ครอบคลุม regime เดียวหรือไม่",
    "- leakage audit",
    "- วิธีรวมคำตัดสินของหลายโครงสร้าง: ทดสอบหลายโครงสร้างทำให้โอกาสได้ go โดยบังเอิญสูงขึ้น",
)
# One bullet per ok line with a summary, by seq (2, 7, 9, 12, 16), then one per random_entry ok (14).
_REPORT_LIMITS = (
    "## ข้อจำกัดที่ต้องรายงาน",
    "",
    "- drawdown วัดจาก realized curve เท่านั้น",
    "- A select seq 2: ambiguous 1, data flag 2, fill หลังข้อมูลขาด 1, ข้อมูลหมด 0",
    "- B select seq 7: ambiguous 0, data flag 3, fill หลังข้อมูลขาด 2, ข้อมูลหมด 1",
    "- B robustness seq 9: ambiguous 2, data flag 0, fill หลังข้อมูลขาด 0, ข้อมูลหมด 0",
    "- B stress seq 12: ambiguous 0, data flag 3, fill หลังข้อมูลขาด 2, ข้อมูลหมด 1",
    "- C select seq 16: ambiguous 0, data flag 0, fill หลังข้อมูลขาด 0, ข้อมูลหมด 2",
    f"- baseline B seq 14: runs 1000, seed {REPORT_SEED}, mean -0.031, P5 -0.102, P50 -0.030, P95 0.044, "
    "ระยะถือ M1 variant 37.5/31, baseline 36.9/30",
    "",
)
_SECTIONS = (
    "## ผลการประเมิน A",
    "",
    "ชุดข้อมูล: SYN-0001 2023-01-02T00:00:00Z ถึง 2023-01-07T00:00:00Z",
    _SETUP,
    "ชุดข้อมูลที่ select ของ A ใช้: 2",  # D1 (seq 1, 3) and D2 (seq 5)
    _SCREEN,
    "",
    *_table(REPORT_EVALUATIONS["A"]["checks"]),
    "",
    "คำตัดสิน: stop",
    "",
    "## ผลการประเมิน B",
    "",
    "ชุดข้อมูล: SYN-0001 2023-01-02T00:00:00Z ถึง 2023-01-07T00:00:00Z",
    _SETUP,
    "ชุดข้อมูลที่ select ของ B ใช้: 1",
    _SCREEN,
    "",
    *_table(REPORT_EVALUATIONS["B"]["checks"]),
    "",
    "คำตัดสิน: insufficient",
    "",
    "## ผลการประเมิน C",
    "",
    "ชุดข้อมูล: SYN-0003 2025-01-01T00:00:00Z ถึง 2025-03-01T00:00:00Z",
    _SETUP,
    "ชุดข้อมูลที่ select ของ C ใช้: 1",
    "",  # screen False: no screen line
    *_table(REPORT_EVALUATIONS["C"]["checks"]),
    "",
    "คำตัดสิน: stop",
    "",
)
_REPORT_REGISTRY_HEAD = _REGISTRY_HEAD
# Header, registry table, budget, one section per Evaluation (A, B, C), limits, owner's decisions.
REPORT_FULL = "\n".join(
    ("# รายงานวิจัย H001", "", *_REPORT_REGISTRY_HEAD, *_REPORT_REGISTRY_ROWS, "", "รวมที่นับงบ: 7/63", "",
     *_SECTIONS, *_REPORT_LIMITS, *_OWNER)
) + "\n"
# No Evaluation: "รวมที่นับงบ" then one blank line, then the limits (F38).
REPORT_NO_EVALUATION = "\n".join(
    ("# รายงานวิจัย H001", "", *_REPORT_REGISTRY_HEAD, *_REPORT_REGISTRY_ROWS, "", "รวมที่นับงบ: 7/63", "",
     *_REPORT_LIMITS, *_OWNER)
) + "\n"
# An empty registry and no Evaluation: every count 0, budget 0/63, only the fixed limit bullet.
_EMPTY_ROWS = tuple(
    f"| {variant} | {purpose} | 0 | 0 | 0 | 0 | {budget} |"
    for variant in ("A", "B", "C")
    for purpose, budget in (("select", "0/6"), ("robustness", "0/14"), ("stress", "0/1"),
                            ("long_only", "ไม่นับ"), ("random_entry", "ไม่นับ"))
)
REPORT_EMPTY = "\n".join(
    ("# รายงานวิจัย H001", "", *_REPORT_REGISTRY_HEAD, *_EMPTY_ROWS, "", "รวมที่นับงบ: 0/63", "",
     "## ข้อจำกัดที่ต้องรายงาน", "", "- drawdown วัดจาก realized curve เท่านั้น", "", *_OWNER)
) + "\n"
# The H002 lines alone (hypothesis="H002", no Evaluation): B select 19/20 -> 1/6; B robustness 21
# (interrupted) -> 1/14; budget 1 + 1 = 2; one bullet for the ok at seq 20 (summary SB).
_H002_ROWS = tuple(
    {("B", "select"): "| B | select | 1 | 1 | 0 | 0 | 1/6 |",
     ("B", "robustness"): "| B | robustness | 1 | 0 | 0 | 1 | 1/14 |"}.get(
        (variant, purpose), f"| {variant} | {purpose} | 0 | 0 | 0 | 0 | {budget} |")
    for variant in ("A", "B", "C")
    for purpose, budget in (("select", "0/6"), ("robustness", "0/14"), ("stress", "0/1"),
                            ("long_only", "ไม่นับ"), ("random_entry", "ไม่นับ"))
)
REPORT_H002 = "\n".join(
    ("# รายงานวิจัย H002", "", *_REPORT_REGISTRY_HEAD, *_H002_ROWS, "", "รวมที่นับงบ: 2/63", "",
     "## ข้อจำกัดที่ต้องรายงาน", "", "- drawdown วัดจาก realized curve เท่านั้น",
     "- B select seq 20: ambiguous 0, data flag 3, fill หลังข้อมูลขาด 2, ข้อมูลหมด 1", "", *_OWNER)
) + "\n"


# ===================================================================== tests r2 (review tests-r1 F1-F6)
#
# Appended by the round-2 test author (docs/reviews/CORE-008-tests-r1.md F1-F6); every statement above
# is unchanged. Each value below was worked out by hand from contract v1.5, the arithmetic beside it.
#
# F1 (random_entry_baseline computes in sochron.costs.CONTEXT: contract "Inputs" and baseline steps 7-8).
# No new known answer: the test runs the WAVE baseline with the real generator inside a caller context of
# precision HOSTILE_PRECISION and ROUND_UP (Inexact and Rounded not trapped) and compares the result with
# the contract's steps computed in CONTEXT by the oracle of the round-1 wave tests. Such a context changes
# what the contract computes in CONTEXT. Example: four r values that sum to 0.4292 give a round
# expectancy of 0.4292 / 4 = 0.1073 in CONTEXT; at precision 3 ROUND_UP the sum rounds away from zero to
# 0.430, and 0.430 / 4 = 0.1075 rounds to 0.108. The test also checks on its own data that at least one
# stop distance k x ATR[t] and the mean of the 1000 round expectancies change at that precision, so the
# comparison can fail.
HOSTILE_PRECISION = 3

# F2 (render_report: the stress column and "นับงบ" after an interrupted stress run and its rerun). The
# records use the format of REPORT_RECORDS; all are H001 with the setup of the normative example, dataset D1:
#   seq 1 started select B0; seq 2 its ok (summary SB), the base;
#   seq 3 started stress B0 on base 2, interrupted: no ok or failed line names started_seq 3;
#   seq 4 started stress B0 on base 2, the rerun of seq 3 with the same identity (runner step 5 accepts a
#         rerun while the identity has no ok line);
#   seq 5 the ok of seq 4 (started_seq 4, summary SBS).
REPORT_RERUN_RECORDS = (
    (1, "started", None, "select", "B0", "D1", None, {}),
    (2, "ok", 1, "select", "B0", "D1", None, {"summary": "SB"}),
    (3, "started", None, "stress", "B0", "D1", 2, {"stress": True}),  # interrupted
    (4, "started", None, "stress", "B0", "D1", 2, {"stress": True}),  # its rerun
    (5, "ok", 4, "stress", "B0", "D1", 2, {"stress": True, "summary": "SBS"}),
)
# Registry rows (started/ok/failed count lines by status; interrupted = started lines that no ok or failed
# line names). B select: started 1 (seq 1), ok 1 (seq 2), failed 0, interrupted 0, distinct params {B0}
# -> 1/6. B stress: started 2 (seq 3, 4), ok 1 (seq 5), failed 0, interrupted 1 (seq 3); the "งบ" column
# of stress is {ok}/1 = 1/1 (a {started}/1 column would show 2/1). Every other row is 0.
# "นับงบ" = select params per variant (A 0 + B 1 + C 0 = 1) + robustness started 0 + stress started 2 = 3:
# both stress started lines count (runner step 5 "รันซ้ำนับด้วย"; adding stress ok instead would give 2).
# Limits: one bullet per ok line with a summary, by seq: seq 2 (SB: ambiguous 0, flagged 3, gap fills 2,
# end of data 1) and seq 5 (SBS: 0, 3, 2, 1); no random_entry ok, so no baseline bullet. No Evaluation:
# "รวมที่นับงบ", one blank line, then the limits (F38).
_RERUN_ROWS = tuple(
    {("B", "select"): "| B | select | 1 | 1 | 0 | 0 | 1/6 |",
     ("B", "stress"): "| B | stress | 2 | 1 | 0 | 1 | 1/1 |"}.get(
        (variant, purpose), f"| {variant} | {purpose} | 0 | 0 | 0 | 0 | {budget} |")
    for variant in ("A", "B", "C")
    for purpose, budget in (("select", "0/6"), ("robustness", "0/14"), ("stress", "0/1"),
                            ("long_only", "ไม่นับ"), ("random_entry", "ไม่นับ"))
)
REPORT_RERUN = "\n".join(
    ("# รายงานวิจัย H001", "", *_REPORT_REGISTRY_HEAD, *_RERUN_ROWS, "", "รวมที่นับงบ: 3/63", "",
     "## ข้อจำกัดที่ต้องรายงาน", "", "- drawdown วัดจาก realized curve เท่านั้น",
     "- B select seq 2: ambiguous 0, data flag 3, fill หลังข้อมูลขาด 2, ข้อมูลหมด 1",
     "- B stress seq 5: ambiguous 0, data flag 3, fill หลังข้อมูลขาด 2, ข้อมูลหมด 1", "", *_OWNER)
) + "\n"

# F3 (render_report and the order of its records). (a) has no new value: REPORT_RECORDS in another order
# must give REPORT_FULL and REPORT_NO_EVALUATION again, and REPORT_RERUN_RECORDS reversed REPORT_RERUN
# (the bullets are "เรียงตาม seq"; every count is free of order). (b) is not built: docs/handoff/CORE-008.md,
# round 2, says why.

# F4 (evaluate row 10 when the base has no trades). Base ZERO_SUMMARY with the long-only run of EVAL_GO
# (100 trades, expectancy 0.10, drawdown 25); stress, random entry and robustness left out. Rows 1-9 are
# those of "no trades and every optional input missing": 1 "0" < 100 fails; 2 none; 3 none (no stress);
# 4 "0" <= 24 passes; 5 none with threshold 7/8 (V-B: 8 neighbours, ceil(0.8 x 8) = ceil(6.4) = 7);
# 6 none / none (no baseline); 7 none; 8 none (no year); 9 long:none;short:none.
# Row 10: "expectancy:" + none + "/" + str(Decimal("0.10")) + ";max_drawdown:" + str(Decimal("0")) + "/" +
# str(Decimal("25")) = "expectancy:none/0.10;max_drawdown:0/25". The drawdown 0 < 25 would be better on one,
# but the contract adds "(ถ้า long-only ไม่มีไม้ หรือ base ไม่มีไม้ = ไม่ผ่าน)": the base has no trades, so the
# row fails. Row 1 fails -> insufficient; EVAL_DATASET starts 2023-01-02, before the cutoff -> screen True.
# Same format as EVALUATE_CASES.
EVALUATE_CASES_R2 = (
    ("no trades with a long-only run that has trades",
     {"base": ZERO_SUMMARY, "stress": None, "random": None, "robustness": ()}, "insufficient", True,
     {1: ("0", "100", False), 2: ("none", "0.10", False), 3: ("none", "0", False), 4: ("0", "24", True),
      5: ("none", "7/8", False), 6: ("none", "none", False), 7: ("none", "0", False), 8: ("none", "0", False),
      9: ("long:none;short:none", "0", False),
      10: ("expectancy:none/0.10;max_drawdown:0/25", "better on one", False)}),
)

# F5 (evaluate input rules) and F6 (baseline step 2, exit times) are refusals and need no new value.
# F5 changes one field of one consistent EVAL_GO record: the variant of the stress record (A), the
# base_run_id of the long-only record (the run_id of another B select ok, k 2.9, built in the test) and
# the rollover_zone of the random-entry record (Europe/London; its seed still follows its base).
# F6 moves the exit time of one FLAT_VARIANT trade by 60 s onto no M1: T1 ("signal", exit M1 300 = bar 100
# minute 0 -> minute 1, a hold in hs) and T2 ("stop" at its entry open, exit M1 303 = bar 101 minute 0 ->
# minute 1, not in hs). Every entry time stays an M1 time, and summarize reads no exit time, so the
# variant still matches the summary of its base (baseline step 1) and only step 2 can refuse it.


# ======================================================== tests r3 (implementation review r1 F4)
#
# Appended by the round-3 test author (docs/reviews/CORE-008-r1.md F4); every statement above is
# unchanged. Each value below was worked out by hand from contract v1.5, the arithmetic beside it.
#
# Contract, random-entry baseline step 4: eligible = every t in 0 ... len(m15) - 2, in increasing
# order, with strategy.entry_blockers(rows[t], m15[t+1].bar.time_utc) empty, rows =
# strategy.indicators(m15, params). The entry window (H001: 03:00-15:59 New York wall time, by the
# minute; CORE-006 "outside_window") is judged at the open of bar t+1, where a random trade is filled
# (step 7: entry_index = the first M1 of bar t+1), not at bar t's own open; the last bar is never
# eligible.
#
# WINDOW series: 106 M15 bars u = 0..105 on flat prices (every M1 open = close = 2000.00, high
# 2000.50, low 1999.50, as FLAT), so TR = 1.00, ATR = 1.00 from bar 9 on (n = 10), k x ATR = 3.0 x
# 1.00 = 3 everywhere, and H001 has no signal. Bar u holds two M1, at minutes 0 and 5: M1 2u and
# 2u + 1 (212 M1, the last at 2024-01-11T14:05Z). Both M1 of bar u and the M15 bar carry one spread
# S_u = 200 for u <= 97 and S_u = 200 + 10 x (u - 97) for u >= 98 (210 at bar 98 ... 280 at bar 105);
# no bar has a flag. Bars 0..99 open every 15 minutes from 2024-01-08T07:15Z (bar 97: 07:15 + 97 x 15
# min = 07:15 + 24 h 15 min = 2024-01-09T07:30Z); bars 100..105 open after gaps. New York is UTC-5 in
# January (EST):
#     u   opens (UTC)        New York    in the window      gap before the bar
#    96   2024-01-09T07:15   Tue 02:15   no
#    97   2024-01-09T07:30   Tue 02:30   no
#    98   2024-01-09T07:45   Tue 02:45   no
#    99   2024-01-09T08:00   Tue 03:00   yes (first minute)
#   100   2024-01-09T20:30   Tue 15:30   yes                12 h 30 min after bar 99 (missing hours)
#   101   2024-01-09T20:45   Tue 15:45   yes
#   102   2024-01-09T21:00   Tue 16:00   no (15:59 + 1 min)
#   103   2024-01-10T15:00   Wed 10:00   yes                18 h after bar 102, across a day boundary
#   104   2024-01-10T22:30   Wed 17:30   no                 7 h 30 min after bar 103 (missing hours)
#   105   2024-01-11T14:00   Thu 09:00   yes                15 h 30 min after bar 104, across a day
#                                                           boundary; the last bar
#
# The other blockers, for RUN_PARAMS (V-B: f 8, s 32, n 10, N 48, M 24, k 3.0):
#   warmup: warm = t >= max(3s, N + 1, M + 1, 97, n + 1) = max(96, 49, 25, 97, 11) = 97, so bars 0..96
#     are blocked whatever the window (and spread_unknown below 96);
#   spread_unknown / spread_filter: from t = 96 the median of spread[t-96..t-1] is known; for t <= 105
#     at least 89 of those 96 spreads are 200 (bars 9..97 at t = 105) and the others are at most 270,
#     so the 48th and 49th smallest are 200, the median is 200 and spread_filter needs S_t > 3 x 200 =
#     600: never (S_t <= 280);
#   atr_zero: ATR = 1.00; data_flag: no flag.
# So from bar 97 on (bar 105 included) the window is the only blocker.
#
# Eligible under the contract (t = 97..104, since len(m15) - 2 = 104; bar t+1 in the window):
#   97 -> bar 98 at 02:45 no · 98 -> 99 at 03:00 yes · 99 -> 100 at 15:30 yes · 100 -> 101 at 15:45
#   yes · 101 -> 102 at 16:00 no · 102 -> 103 at 10:00 yes · 103 -> 104 at 17:30 no · 104 -> 105 at
#   09:00 yes  ->  (98, 99, 100, 102, 104), len(eligible) = 5.
# The wrong rules give other sets (the test checks each as a premise of the fixture):
#   bar t's own open: 97 (02:30) no, 98 (02:45) no, 99 (03:00) yes, 100 (15:30) yes, 101 (15:45) yes,
#     102 (16:00) no, 103 (10:00) yes, 104 (17:30) no -> (99, 100, 101, 103): it loses 98 at the start
#     edge (02:45 -> 03:00) and 102 and 104 before the overnight gaps, and it gains 101 at the end edge
#     (15:45 -> 16:00) and 103 before the 17:30 gap;
#   no window check: (97, 98, 99, 100, 101, 102, 103, 104), 8 bars;
#   t up to len(m15) - 1: bar 105 is warm with no other blocker and opens at 09:00 (09:15 one bar
#     later), inside the window whatever next open such a rule takes for it: 6 bars (or no bar t+1).
WINDOW_BAR0 = "2024-01-08T07:15"
WINDOW_GAP_OPENS = ("2024-01-09T20:30", "2024-01-09T20:45", "2024-01-09T21:00", "2024-01-10T15:00",
                    "2024-01-10T22:30", "2024-01-11T14:00")


def _window_open(u):
    start = datetime.fromisoformat(WINDOW_BAR0).replace(tzinfo=UTC)
    return (start + timedelta(minutes=15 * u)).strftime("%Y-%m-%dT%H:%M")


WINDOW_BAR_OPENS = tuple(_window_open(u) for u in range(100)) + WINDOW_GAP_OPENS
WINDOW_M1_COUNT = 212  # 106 bars x 2


def window_spread(u):
    """S_u: the spread of both M1 of bar u and of the M15 bar."""
    return 200 if u <= 97 else 200 + 10 * (u - 97)


def window_m1_rows():
    """(stamp, open, high, low, close, spread) of the 212 M1 of the WINDOW series."""
    rows = []
    for u, opened in enumerate(WINDOW_BAR_OPENS):
        start = datetime.fromisoformat(opened).replace(tzinfo=UTC)
        for minute in (0, 5):
            stamp = (start + timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M")
            rows.append((stamp, "2000.00", "2000.50", "1999.50", "2000.00", window_spread(u)))
    return tuple(rows)


WINDOW_DATASET = ("SYN-WIN1", "c" * 64, "2024-01-08T00:00:00", "2024-01-12T00:00:00", 212)
WINDOW_IN = {96: False, 97: False, 98: False, 99: True, 100: True, 101: True, 102: False, 103: True,
             104: False, 105: True}  # in_entry_window(open of bar u), from the table above
WINDOW_INSIDE = "2024-01-09T14:00"  # 09:00 New York: an instant inside the window
WINDOW_WARM_FROM = 97
WINDOW_ELIGIBLE = (98, 99, 100, 102, 104)
WINDOW_OWN_OPEN = (99, 100, 101, 103)
WINDOW_NO_WINDOW = (97, 98, 99, 100, 101, 102, 103, 104)

# Random trades. Every variant below is built by hand with simulate_trade (lots 0.02, risk_money 25,
# model = H001_COSTS with swap_long 0, as FLAT): long trades on bars with spread 200 that leave by
# exit_index one M1 after the entry ("signal", hold 1). So hs = (1, ..., 1) and every random trade has
# h = 1: drawn at t, it enters at the open of M1 2u (bar u = t + 1, minute 0); planned = 2u + max(1,
# 1) = 2u + 1 < 212, so exit_index = 2u + 1 (minute 5 of the same bar), a "signal" exit at its open.
# Stop distance 3, never reached: long stop = fill ask - 3 = 2000.00 + S_u x 0.001 - 3 <= 1997.28 <
# low 1999.50; short stop (an ask level) 2000.00 + 3 = 2003.00 > high + S_u x 0.001 <= 2000.78, and
# no open + S_u x 0.001 reaches it. Gross 0 (entry and exit open 2000.00). Spread S_u x 0.001 x 100 x
# 0.02 = 0.002 x S_u, paid at the buy (the entry M1 of a long, the exit M1 of a short, both S_u);
# slippage 50 x 0.001 x 100 x 0.02 x 2 = 0.20; commission 0; swap 0 (both swaps 0, and no 17:00 New
# York inside five minutes). r = -(0.002 x S_u + 0.20) / 25: the same for both sides and different for
# every bar u, so the expectancy of a one-trade round names the bar drawn (t = u - 1).
WINDOW_ENTRY_R = {
    98: "-0.0248",   # S 210: -(0.42 + 0.20) / 25 = -0.62 / 25
    99: "-0.0256",   # S 220: -(0.44 + 0.20) / 25 = -0.64 / 25
    100: "-0.0264",  # S 230: -0.66 / 25
    101: "-0.0272",  # S 240: -0.68 / 25
    102: "-0.028",   # S 250: -0.70 / 25
    103: "-0.0288",  # S 260: -0.72 / 25
    104: "-0.0296",  # S 270: -0.74 / 25
    105: "-0.0304",  # S 280: -0.76 / 25
}

# Test 1, K = 1. Variant: one long trade at M1 194 (bar 97, minute 0, S 200), exit_index 195, stop
# distance 50.00: "signal", hold 1, r = -(0.40 + 0.20) / 25 = -0.024; hs = (1,), K = 1.
WINDOW_VARIANT = (("long", 194, "50.00", 195),)
# summarize: 1 trade, expectancy -0.024 / 1; cumulative 0 -> -0.024, so max_drawdown 0 - (-0.024) =
# 0.024; net -0.60; long 1 at -0.024, short 0 (none); top 5 removed: 1 <= 5 trades -> None; 2024 only.
WINDOW_SUMMARY = {
    "trades": 1, "expectancy_r": "-0.024", "max_drawdown_r": "0.024", "net_money": "-0.60",
    "long_trades": 1, "long_expectancy_r": "-0.024", "short_trades": 0, "short_expectancy_r": None,
    "top5_removed_expectancy_r": None, "expectancy_by_year": ((2024, "-0.024"),), "ambiguous_trades": 0,
    "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0,
}
# The fake random.Random returns these values in a cycle. The sizer gives lots 0.02 on every call, so
# each round makes three randrange calls: n = len(pool) = len(eligible) = 5 (K = 1: one bar per
# round), then 2 (the side), then len(hs) = 1 (h):
#   round 5j + 0: randrange(5) -> 0 -> t 98;  randrange(2) -> 0 long;  randrange(1) -> 0 (h 1): enters
#                 bar 99, r -0.0256
#   round 5j + 1: -> 1 -> t 99,  -> 1 short: bar 100, r -0.0264
#   round 5j + 2: -> 2 -> t 100, -> 0 long:  bar 101, r -0.0272
#   round 5j + 3: -> 3 -> t 102, -> 1 short: bar 103, r -0.0288
#   round 5j + 4: -> 4 -> t 104, -> 0 long:  bar 105, r -0.0304
WINDOW_SCRIPT = (0, 0, 0, 1, 1, 0, 2, 0, 0, 3, 1, 0, 4, 0, 0)
WINDOW_SCRIPT_N = (5, 2, 1)
WINDOW_DRAWS = (98, 99, 100, 102, 104)  # t drawn in round i: WINDOW_DRAWS[i % 5]
WINDOW_ROUND_EXPECTANCY = ("-0.0256", "-0.0264", "-0.0272", "-0.0288", "-0.0304")  # round i: [i % 5]
# BaselineSummary: 1000 = 200 x 5 rounds; the sum in round order is 200 x (-0.0256 - 0.0264 - 0.0272 -
# 0.0288 - 0.0304) = 200 x -0.1384 = -27.68, mean -27.68 / 1000 = -0.02768. Sorted, ranks 1-200 are
# -0.0304, 201-400 -0.0288, 401-600 -0.0272, 601-800 -0.0264, 801-1000 -0.0256: P5 = rank ceil(0.05 x
# 1000) = 50 -> -0.0304, P50 = rank 500 -> -0.0272, P95 = rank 950 -> -0.0256. Holds: variant (1) ->
# mean 1, median 1; 1000 random trades of hold 1 -> mean 1000 / 1000 = 1, median (rank 500) 1.
WINDOW_BASELINE = {
    "runs": 1000, "trades_per_run": 1, "mean_r": "-0.02768", "p05_r": "-0.0304", "p50_r": "-0.0272",
    "p95_r": "-0.0256", "variant_mean_hold_m1": "1", "variant_median_hold_m1": 1,
    "baseline_mean_hold_m1": "1", "baseline_median_hold_m1": 1,
}

# Test 2, K = len(eligible) = 5, then K = 6. Variants: long trades at M1 0, 2, 4, 6, 8 (and 10), each
# with exit_index one M1 later and stop distance 50.00, on bars 0..4 (and 5), S 200: "signal", hold 1,
# r -0.024 each.
WINDOW_VARIANT_5 = tuple(("long", 2 * u, "50.00", 2 * u + 1) for u in range(5))
WINDOW_VARIANT_6 = tuple(("long", 2 * u, "50.00", 2 * u + 1) for u in range(6))
# summarize of the 5 trades: expectancy -0.120 / 5 = -0.024; cumulative -0.024, -0.048, -0.072,
# -0.096, -0.120 from 0 -> max_drawdown 0.120; net 5 x -0.60 = -3.00; long 5 at -0.024; short none;
# top 5 removed: 5 <= 5 trades -> None; 2024 only.
WINDOW_SUMMARY_5 = {
    "trades": 5, "expectancy_r": "-0.024", "max_drawdown_r": "0.120", "net_money": "-3.00",
    "long_trades": 5, "long_expectancy_r": "-0.024", "short_trades": 0, "short_expectancy_r": None,
    "top5_removed_expectancy_r": None, "expectancy_by_year": ((2024, "-0.024"),), "ambiguous_trades": 0,
    "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0,
}
# K = 5: hs = (1, 1, 1, 1, 1). The fake returns 0 on every call, so pool.pop(0) takes the smallest bar
# left: t 98, 99, 100, 102, 104 (the whole eligible set; the pool is empty after the fifth bar), all
# long, h = hs[0] = 1. randrange n per round: 5, 2, 5 (len(hs)), 4, 2, 5, 3, 2, 5, 2, 2, 5, 1, 2, 5.
# Round expectancy: (-0.0256 - 0.0264 - 0.0272 - 0.0288 - 0.0304) / 5 = -0.1384 / 5 = -0.02768 in every
# round; mean 1000 x -0.02768 / 1000 = -0.02768 = P5 = P50 = P95. Holds: variant 5 x 1 -> mean 1,
# median rank ceil(2.5) = 3 -> 1; 5000 random trades of hold 1 -> mean 1, median 1.
WINDOW_ALL_SCRIPT_N = (5, 2, 5, 4, 2, 5, 3, 2, 5, 2, 2, 5, 1, 2, 5)
WINDOW_ALL_EXPECTANCY = "-0.02768"
WINDOW_ALL_BASELINE = {
    "runs": 1000, "trades_per_run": 5, "mean_r": "-0.02768", "p05_r": "-0.02768", "p50_r": "-0.02768",
    "p95_r": "-0.02768", "variant_mean_hold_m1": "1", "variant_median_hold_m1": 1,
    "baseline_mean_hold_m1": "1", "baseline_median_hold_m1": 1,
}
# K = 6 (bar 5 added): K > len(eligible) = 5 -> ResearchError before the started line (step 4), the
# registry unchanged. Its summary, so that step 1 accepts the base: expectancy -0.144 / 6 = -0.024;
# max_drawdown 0.144; net -3.60; long 6 at -0.024; top 5 removed: the five highest r are equal and ties
# remove the earlier trades, leaving the sixth: -0.024 / 1 = -0.024; 2024 only.
WINDOW_SUMMARY_6 = {
    "trades": 6, "expectancy_r": "-0.024", "max_drawdown_r": "0.144", "net_money": "-3.60",
    "long_trades": 6, "long_expectancy_r": "-0.024", "short_trades": 0, "short_expectancy_r": None,
    "top5_removed_expectancy_r": "-0.024", "expectancy_by_year": ((2024, "-0.024"),),
    "ambiguous_trades": 0, "flagged_trades": 0, "gap_fills": 0, "end_of_data_trades": 0,
}
