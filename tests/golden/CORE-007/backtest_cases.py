"""CORE-007 hand-computed oracles: single trades through simulate_trade and whole runs through run.

No expected value below comes from sochron.backtest. The test author computed every value by hand
from docs/contracts/CORE-007-backtest.md v1.4 (the fill and SL table and the lines under it, R
(D8), nights (D4), the event order steps 1-6, equity points, data_flags) and from the sochron.costs
formulas of contract CORE-002 (Decimal, precision 28, ROUND_HALF_EVEN). Every value here is exact:
no digit is dropped at 28 digits, so the order of the multiplications does not matter.

Model H001_COSTS: point p = 0.001, contract 100 oz, commission 0, slippage 50 points per side,
swap long -503.8 / short 0 points per night, triple swap on Wednesday (weekday 2), spread
fallback 240 points. s is the spread of the M1 an event happens on, 240 when that M1 has none.
  long  entry ask = open + s*p, stop_price = ask - stop_distance
        gap  : open <= stop_price            -> exit_bid = open
        touch: low <= stop_price              -> exit_bid = stop_price
  short stop_price = open + stop_distance (an ask level)
        gap  : open + s*p >= stop_price       -> exit_bid = open
        touch: high + s*p >= stop_price       -> exit_bid = stop_price - s*p
  The open is checked before the touch, on every M1 from entry_index (the entry M1 included) to
  exit_index - 1, or to the end. At exit_index the trade closes at the open ("signal"), or
  "stop" with ambiguous True at the open when that open is beyond the stop by the gap row.
  Without exit_index and without a stop the trade closes at the close of the last M1
  ("end_of_data").
  gross  = (exit_bid - entry_bid) * 100 * lots * (+1 long, -1 short), never times the stress
  spread = s * 0.001 * 100 * lots, s of the entry for a long and of the exit for a short
  slippage = 50 * 0.001 * 100 * lots * 2; commission = 0
  swap   = -(swap points * 0.001 * 100 * lots) * (nights - triple + 3 * triple)
  total  = spread + commission + slippage + swap; net = gross - total; r = net / risk_money
With lots 0.10 the money of one USD/oz is 10: spread 200 -> 2.00, 240 -> 2.40, 300 -> 3.00,
slippage 1.00, one long night 50.38 * 0.10 = 5.038.

Nights (D4 [A]): the count of 17:00 New York on Monday-Friday of New York with entry < T <= exit
(the time_utc of the entry and exit M1); triple = those on a Wednesday. 17:00 EDT = 21:00 UTC,
17:00 EST = 22:00 UTC; US daylight time began 2026-03-08 and ends 2026-11-01. 2026-03-10 is a
Tuesday (H001 section 3), so 2026-03-13 is a Friday and 2026-10-30 a Friday.

Each M1 row: (open time UTC "YYYY-MM-DDTHH:MM", open, high, low, close, spread); prices are bid
Decimal strings, spread is points (int, None = the bar has none). Each expected trade is a dict
made by _trade below; "entry" and "exit" are (time UTC, bid, spread points used).

Round 2 (tests r2: docs/reviews/CORE-007-tests-r1.md F1, F2, F4, F5, F7 and contract v1.5) adds the
tables after SIZE_CASES and changes nothing above them. A second test author recomputed every
round-2 value by hand from contract v1.5 and the same costs formulas; the arithmetic is in the
comments there.
"""

from datetime import datetime, timedelta

RULE_SERVER = "Exness-MT5Trial14"  # offset 0: raw time = UTC seconds (CORE-001)
ROLLOVER = ("America/New_York", 17, 0)  # D4 [A]: Rollover("America/New_York", time(17, 0))
# 2026-03-10T00:00Z = 20522 days after 1970-01-01 (56 years with 14 leap days = 20454, plus 31 +
# 28 + 9 = 68) = 1773100800 s; + 13:45 = 1773150300; 2026-03-11T14:00Z = 1773100800 + 86400 +
# 50400 = 1773237600.
ANCHORS = (("2026-03-10T13:45", 1773150300), ("2026-03-11T14:00", 1773237600))


def _trade(side, entry, exit_, lots, stop_distance, stop_price, reason, ambiguous, nights, costs,
           gross, net, risk_money, actual_risk, r, data_flags=()):
    return {
        "side": side, "entry": entry, "exit": exit_, "lots": lots, "stop_distance": stop_distance,
        "stop_price": stop_price, "exit_reason": reason, "ambiguous": ambiguous, "nights": nights,
        "costs": costs, "gross": gross, "net": net, "risk_money": risk_money,
        "actual_risk": actual_risk, "r": r, "data_flags": tuple(data_flags),
    }


# ---------------------------------------------------------------------------------------------
# AC-01: the H001 worked example. Long: entry bid 4012.66, s 240 -> ask 4012.90, stop 4012.90 -
# 12.00 = 4000.90. Entry Tuesday 13:45 UTC (09:45 EDT), exit Wednesday 14:00 UTC (10:00 EDT):
# one rollover, Tuesday 17:00 EDT = 21:00 UTC, not a Wednesday -> nights 1, triple 0.
#   gross = (4029.86 - 4012.66) * 100 * 0.02 = 17.20 * 2 = 34.40
#   spread = 240 * 0.001 * 100 * 0.02 = 0.48; slippage = 0.05 * 100 * 0.02 * 2 = 0.20
#   swap = -(-503.8 * 0.001 * 100 * 0.02) * 1 = 1.0076; total = 0.48 + 0 + 0.20 + 1.0076 = 1.6876
#   net = 34.40 - 1.6876 = 32.7124; r = 32.7124 / 25 = 1.308496 (D8: R from the formula, so the
#   actual risk 24 of H001's lot rounding changes nothing; 32.7124 / 24 would be 1.363016...)
# Short: entry bid 4029.86, stop 4029.86 + 12.00 = 4041.86; exit bid 4012.66.
#   gross = (4012.66 - 4029.86) * 100 * 0.02 * -1 = 34.40; spread of the exit 0.48; slippage
#   0.20; swap 0 (short 0 points); total 0.68; net 33.72; r = 33.72 / 25 = 1.3488.
# The middle M1 (Tuesday 21:30 UTC) is far from both stops.
AC01_LONG_M1 = (
    ("2026-03-10T13:45", "4012.66", "4013.00", "4012.50", "4012.80", 240),
    ("2026-03-10T21:30", "4015.00", "4015.50", "4014.80", "4015.20", 250),
    ("2026-03-11T14:00", "4029.86", "4030.20", "4029.50", "4030.00", 240),
)
AC01_SHORT_M1 = (
    ("2026-03-10T13:45", "4029.86", "4030.20", "4029.50", "4030.00", 240),
    ("2026-03-10T21:30", "4020.00", "4020.50", "4019.50", "4020.10", 250),
    ("2026-03-11T14:00", "4012.66", "4013.00", "4012.50", "4012.80", 240),
)
AC01_LONG = _trade("long", ("2026-03-10T13:45", "4012.66", 240), ("2026-03-11T14:00", "4029.86", 240),
                   "0.02", "12.00", "4000.90", "signal", False, (1, 0),
                   ("0.48", "0", "0.20", "1.0076", "1.6876"), "34.40", "32.7124", "25", None, "1.308496")
AC01_SHORT = _trade("short", ("2026-03-10T13:45", "4029.86", 240), ("2026-03-11T14:00", "4012.66", 240),
                    "0.02", "12.00", "4041.86", "signal", False, (1, 0),
                    ("0.48", "0", "0.20", "0", "0.68"), "34.40", "33.72", "25", None, "1.3488")
# AC-04 with stress(H001_COSTS, 2) on the AC-01 long: every charge doubles, prices do not.
#   spread 0.96, commission 0, slippage 0.40, swap 2.0152, total 3.3752; gross stays 34.40;
#   net = 34.40 - 3.3752 = 31.0248; r = 31.0248 / 25 = 1.240992.
AC01_LONG_STRESS2 = {"costs": ("0.96", "0", "0.40", "2.0152", "3.3752"), "net": "31.0248", "r": "1.240992"}

# ---------------------------------------------------------------------------------------------
# AC-02: every row of the fill table on both sides. Unless a case says otherwise: lots 0.10,
# risk_money 25, actual_risk None, no data_flags, stop_distance 5.00, entry at 14:00 UTC on
# Tuesday 2026-03-10 (10:00 EDT, no rollover: nights 0, swap 0) at open 4000.00 with spread 200.
#   long : ask 4000.00 + 0.200 = 4000.200, stop_price 3995.200
#   short: stop_price 4000.00 + 5.00 = 4005.00
_ENTRY = ("2026-03-10T14:00", "4000.00", "4000.50", "3999.50", "4000.20", 200)
_E = ("2026-03-10T14:00", "4000.00", 200)
_LOSS_48 = ("2.00", "0", "1.00", "0", "3.00")  # spread 200 at the side that pays it


def _case(label, side, m1, expected, entry_index=0, exit_index=None, stop_distance="5.00",
          lots="0.10", risk_money="25", actual_risk=None, data_flags=()):
    return {"label": label, "side": side, "m1": m1, "entry_index": entry_index,
            "exit_index": exit_index, "stop_distance": stop_distance, "lots": lots,
            "risk_money": risk_money, "actual_risk": actual_risk, "data_flags": tuple(data_flags),
            "expected": expected}


FILL_CASES = (
    # --- long -----------------------------------------------------------------------------
    # Gap: 14:02 opens at 3994.00 <= 3995.20 with low 3993.00 < open < stop: exit at the open
    # 3994.00, not at the stop (the open is checked before the touch). gross = -6.00 * 10 = -60.00,
    # costs 2.00 + 1.00 = 3.00, net -63.00, r = -63.00 / 25 = -2.52 (R is risk_money: dividing
    # by the actual risk 24.80 would give -2.540...).
    _case("long gap at a later M1 (low < open < stop)", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4000.40", "3998.00", "3998.50", 210),
        ("2026-03-10T14:02", "3994.00", "3994.80", "3993.00", "3994.50", 300),
        ("2026-03-10T14:03", "3994.50", "3995.00", "3994.00", "3994.80", 200),
    ), _trade("long", _E, ("2026-03-10T14:02", "3994.00", 300), "0.10", "5.00", "3995.20", "stop", False,
              (0, 0), _LOSS_48, "-60.00", "-63.00", "25", "24.80", "-2.52"), actual_risk="24.80"),
    # Touch: 14:01 opens at 3996.00 (above the stop), low 3995.00 <= 3995.20: exit at 3995.20.
    # The M1 before entry_index (13:59, low 3985.00) is not checked. gross = -4.80 * 10 = -48.00.
    _case("long touch inside the bar; the M1 before entry_index is not read", "long", (
        ("2026-03-10T13:59", "3990.00", "3991.00", "3985.00", "3990.50", 200),
        _ENTRY,
        ("2026-03-10T14:01", "3996.00", "3996.40", "3995.00", "3995.50", 250),
        ("2026-03-10T14:02", "3990.00", "3990.50", "3989.00", "3989.50", 200),
    ), _trade("long", _E, ("2026-03-10T14:01", "3995.20", 250), "0.10", "5.00", "3995.20", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04"), entry_index=1),
    # Touch with low exactly at the stop (low <= stop_price).
    _case("long touch with low equal to the stop", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "3996.00", "3996.40", "3995.20", "3995.60", 220),
    ), _trade("long", _E, ("2026-03-10T14:01", "3995.20", 220), "0.10", "5.00", "3995.20", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04")),
    # The entry M1 itself: low 3995.00 <= 3995.20 inside the M1 that opened the trade.
    _case("long stop inside the entry M1", "long", (
        ("2026-03-10T14:00", "4000.00", "4000.10", "3995.00", "3995.80", 200),
        ("2026-03-10T14:01", "3996.00", "3996.50", "3995.60", "3996.20", 200),
    ), _trade("long", _E, ("2026-03-10T14:00", "3995.20", 200), "0.10", "5.00", "3995.20", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04")),
    # stop_distance = s*p = 0.20: stop 4000.200 - 0.20 = 4000.00, so the entry open 4000.00 <= stop
    # is a gap at the entry M1: exit 4000.00 at 14:00. gross 0, net = -3.00, r = -0.12.
    _case("long stop_distance equal to s*p stops at the entry open", "long", (
        ("2026-03-10T14:00", "4000.00", "4000.60", "3999.90", "4000.50", 200),
        ("2026-03-10T14:01", "4000.50", "4001.00", "4000.40", "4000.90", 200),
    ), _trade("long", _E, ("2026-03-10T14:00", "4000.00", 200), "0.10", "0.20", "4000.00", "stop", False,
              (0, 0), _LOSS_48, "0", "-3.00", "25", None, "-0.12"), stop_distance="0.20"),
    # stop_distance 0.05 < s*p: stop 4000.15 above the open: the same gap at the entry open.
    _case("long stop_distance below s*p stops at the entry open", "long", (
        ("2026-03-10T14:00", "4000.00", "4000.60", "3999.90", "4000.50", 200),
        ("2026-03-10T14:01", "4000.50", "4001.00", "4000.40", "4000.90", 200),
    ), _trade("long", _E, ("2026-03-10T14:00", "4000.00", 200), "0.10", "0.05", "4000.15", "stop", False,
              (0, 0), _LOSS_48, "0", "-3.00", "25", None, "-0.12"), stop_distance="0.05"),
    # End of data: a low of 3995.21 is one tick above the stop (no touch); close of the last M1
    # 3997.30 at 14:02 with its spread 230. gross = -2.70 * 10 = -27.00, net -30.00, r -1.20.
    _case("long end of data; a low one tick above the stop is no stop", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4000.30", "3995.21", "3996.00", 220),
        ("2026-03-10T14:02", "3996.00", "3997.40", "3995.80", "3997.30", 230),
    ), _trade("long", _E, ("2026-03-10T14:02", "3997.30", 230), "0.10", "5.00", "3995.20", "end_of_data",
              False, (0, 0), _LOSS_48, "-27.00", "-30.00", "25", None, "-1.20")),
    # Signal exit at exit_index 2 at its open 4001.50 (above the stop); that M1's low 3990.00 is
    # never checked (SL runs to exit_index - 1). data_flags pass through. gross = 1.50 * 10 = 15.00,
    # net 12.00, r 0.48.
    _case("long signal exit; the low of the exit M1 is not checked", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4002.00", "4000.10", "4001.90", 200),
        ("2026-03-10T14:02", "4001.50", "4001.60", "3990.00", "3991.00", 260),
        ("2026-03-10T14:03", "3991.00", "3991.50", "3990.50", "3991.20", 200),
    ), _trade("long", _E, ("2026-03-10T14:02", "4001.50", 260), "0.10", "5.00", "3995.20", "signal", False,
              (0, 0), _LOSS_48, "15.00", "12.00", "25", None, "0.48", ("incomplete", "unexpected_gap")),
          exit_index=2, data_flags=("incomplete", "unexpected_gap")),
    # Signal exit whose open 3995.00 is beyond the stop (gap row): "stop", ambiguous, at the open.
    # gross = -5.00 * 10 = -50.00, net -53.00, r -2.12.
    _case("long exit open beyond the stop is stop + ambiguous at the open", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4000.30", "3996.00", "3996.10", 200),
        ("2026-03-10T14:02", "3995.00", "3995.50", "3990.00", "3991.00", 280),
    ), _trade("long", _E, ("2026-03-10T14:02", "3995.00", 280), "0.10", "5.00", "3995.20", "stop", True,
              (0, 0), _LOSS_48, "-50.00", "-53.00", "25", None, "-2.12"), exit_index=2),
    _case("long exit open equal to the stop is stop + ambiguous", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4000.30", "3996.00", "3996.10", 200),
        ("2026-03-10T14:02", "3995.20", "3995.90", "3994.00", "3995.50", 240),
    ), _trade("long", _E, ("2026-03-10T14:02", "3995.20", 240), "0.10", "5.00", "3995.20", "stop", True,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04"), exit_index=2),
    # A stop before exit_index wins: touch at 14:01, the exit at 14:02 never happens.
    _case("long stop before the signal exit", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "3996.00", "3996.40", "3995.00", "3995.50", 250),
        ("2026-03-10T14:02", "4001.00", "4001.20", "4000.80", "4001.10", 200),
    ), _trade("long", _E, ("2026-03-10T14:01", "3995.20", 250), "0.10", "5.00", "3995.20", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04"), exit_index=2),
    # No spread at entry: s = 240, ask 4000.240, stop 3995.24; entry_spread_points 240 and the
    # long pays it: spread 2.40, total 3.40; gross = 1.00 * 10 = 10.00, net 6.60, r 0.264.
    _case("long spread None at entry uses the fallback for the ask and the cost", "long", (
        ("2026-03-10T14:00", "4000.00", "4000.50", "3999.50", "4000.20", None),
        ("2026-03-10T14:01", "4001.00", "4001.20", "4000.80", "4001.10", 200),
    ), _trade("long", ("2026-03-10T14:00", "4000.00", 240), ("2026-03-10T14:01", "4001.00", 200), "0.10",
              "5.00", "3995.24", "signal", False, (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "10.00",
              "6.60", "25", None, "0.264"), exit_index=1),
    _case("long spread None at the signal exit", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4001.00", "4001.20", "4000.80", "4001.10", None),
    ), _trade("long", _E, ("2026-03-10T14:01", "4001.00", 240), "0.10", "5.00", "3995.20", "signal", False,
              (0, 0), _LOSS_48, "10.00", "7.00", "25", None, "0.28"), exit_index=1),
    _case("long spread None at the M1 of the stop", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "3996.00", "3996.40", "3995.00", "3995.50", None),
    ), _trade("long", _E, ("2026-03-10T14:01", "3995.20", 240), "0.10", "5.00", "3995.20", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04")),
    # End of data on an M1 without spread: 4000.80 at 14:01, spread 240; gross 8.00, net 5.00.
    _case("long spread None at the last M1", "long", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4000.90", "4000.10", "4000.80", None),
    ), _trade("long", _E, ("2026-03-10T14:01", "4000.80", 240), "0.10", "5.00", "3995.20", "end_of_data",
              False, (0, 0), _LOSS_48, "8.00", "5.00", "25", None, "0.20")),
    # No spread at the entry M1 that also stops: ask 4000.240, stop 3995.24, low 3995.00 touches;
    # exit 3995.24 with s 240 on both sides. gross = -4.76 * 10 = -47.60, spread 2.40, total
    # 3.40, net -51.00, r -2.04.
    _case("long spread None at an entry M1 that stops", "long", (
        ("2026-03-10T14:00", "4000.00", "4000.10", "3995.00", "3995.80", None),
        ("2026-03-10T14:01", "3996.00", "3996.50", "3995.60", "3996.20", 200),
    ), _trade("long", ("2026-03-10T14:00", "4000.00", 240), ("2026-03-10T14:00", "3995.24", 240), "0.10",
              "5.00", "3995.24", "stop", False, (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "-47.60",
              "-51.00", "25", None, "-2.04")),
    # --- short ----------------------------------------------------------------------------
    # Gap: 14:02 opens at 4005.50, ask 4005.80 >= 4005.00, high 4007.00 > open > stop: exit at
    # the open 4005.50 (a touch-first rule would give 4005.00 - 0.300 = 4004.70). The short pays
    # the exit spread 300 -> 3.00. gross = 5.50 * 10 * -1 = -55.00, total 4.00, net -59.00,
    # r -2.36.
    _case("short gap at a later M1 (stop < open < high)", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4002.00", "4000.10", "4001.80", 200),
        ("2026-03-10T14:02", "4005.50", "4007.00", "4005.00", "4006.00", 300),
        ("2026-03-10T14:03", "4006.00", "4006.50", "4005.50", "4006.20", 200),
    ), _trade("short", _E, ("2026-03-10T14:02", "4005.50", 300), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), ("3.00", "0", "1.00", "0", "4.00"), "-55.00", "-59.00", "25", "24.80", "-2.36"),
          actual_risk="24.80"),
    # Gap made by the spread: bid open 4004.90 < 4005.00 but ask open 4004.90 + 0.150 = 4005.05:
    # exit at the open 4004.90 (without the spread in the gap row it would be a touch at 4004.85).
    # gross = -4.90 * 10 = -49.00, spread 1.50, total 2.50, net -51.50, r -2.06.
    _case("short gap made by the spread at the open", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4002.00", "4000.10", "4001.80", 200),
        ("2026-03-10T14:02", "4004.90", "4005.50", "4004.50", "4005.20", 150),
    ), _trade("short", _E, ("2026-03-10T14:02", "4004.90", 150), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), ("1.50", "0", "1.00", "0", "2.50"), "-49.00", "-51.50", "25", None, "-2.06")),
    # Touch: ask open 4003.20 (no gap), ask high 4004.85 + 0.200 = 4005.05 >= 4005.00: exit bid =
    # 4005.00 - 0.200 = 4004.80. The M1 before entry_index (13:59, high 4011.00) is not checked.
    _case("short touch inside the bar; the M1 before entry_index is not read", "short", (
        ("2026-03-10T13:59", "4010.00", "4011.00", "4009.00", "4010.50", 200),
        _ENTRY,
        ("2026-03-10T14:01", "4003.00", "4004.85", "4002.90", "4004.00", 200),
        ("2026-03-10T14:02", "4010.00", "4011.00", "4009.50", "4010.50", 200),
    ), _trade("short", _E, ("2026-03-10T14:01", "4004.80", 200), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04"), entry_index=1),
    # Touch with the ask high exactly at the stop: 4004.80 + 0.200 = 4005.00.
    _case("short touch with ask high equal to the stop", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4003.00", "4004.80", "4002.90", "4004.00", 200),
    ), _trade("short", _E, ("2026-03-10T14:01", "4004.80", 200), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04")),
    _case("short stop inside the entry M1", "short", (
        ("2026-03-10T14:00", "4000.00", "4004.90", "3999.80", "4004.00", 200),
        ("2026-03-10T14:01", "4004.00", "4004.20", "4003.00", "4003.50", 200),
    ), _trade("short", _E, ("2026-03-10T14:00", "4004.80", 200), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04")),
    # stop_distance = s*p: stop 4000.20 and the entry ask open 4000.20 >= stop: gap at the entry.
    _case("short stop_distance equal to s*p stops at the entry open", "short", (
        ("2026-03-10T14:00", "4000.00", "4000.10", "3999.40", "3999.50", 200),
        ("2026-03-10T14:01", "3999.50", "3999.60", "3999.00", "3999.20", 200),
    ), _trade("short", _E, ("2026-03-10T14:00", "4000.00", 200), "0.10", "0.20", "4000.20", "stop", False,
              (0, 0), _LOSS_48, "0", "-3.00", "25", None, "-0.12"), stop_distance="0.20"),
    _case("short stop_distance below s*p stops at the entry open", "short", (
        ("2026-03-10T14:00", "4000.00", "4000.10", "3999.40", "3999.50", 200),
        ("2026-03-10T14:01", "3999.50", "3999.60", "3999.00", "3999.20", 200),
    ), _trade("short", _E, ("2026-03-10T14:00", "4000.00", 200), "0.10", "0.05", "4000.05", "stop", False,
              (0, 0), _LOSS_48, "0", "-3.00", "25", None, "-0.12"), stop_distance="0.05"),
    # End of data: ask high 4004.79 + 0.200 = 4004.99 is one tick below the stop; close 3998.70
    # with spread 230. gross = -1.30 * 10 * -1 = 13.00, spread 2.30, total 3.30, net 9.70, r 0.388.
    _case("short end of data; an ask high one tick below the stop is no stop", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4004.79", "3999.80", "4000.50", 200),
        ("2026-03-10T14:02", "4000.50", "4000.60", "3998.50", "3998.70", 230),
    ), _trade("short", _E, ("2026-03-10T14:02", "3998.70", 230), "0.10", "5.00", "4005.00", "end_of_data",
              False, (0, 0), ("2.30", "0", "1.00", "0", "3.30"), "13.00", "9.70", "25", None, "0.388")),
    # Signal exit at the open 3998.00 of exit_index 2; its high 4010.00 is not checked. risk_money
    # 40: gross = -2.00 * 10 * -1 = 20.00, spread 2.60, total 3.60, net 16.40, r = 16.40 / 40 = 0.41.
    _case("short signal exit; the high of the exit M1 is not checked", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4001.00", "3998.00", "3998.20", 200),
        ("2026-03-10T14:02", "3998.00", "4010.00", "3997.50", "4009.00", 260),
        ("2026-03-10T14:03", "4009.00", "4010.00", "4008.50", "4009.50", 200),
    ), _trade("short", _E, ("2026-03-10T14:02", "3998.00", 260), "0.10", "5.00", "4005.00", "signal", False,
              (0, 0), ("2.60", "0", "1.00", "0", "3.60"), "20.00", "16.40", "40", None, "0.41"),
          exit_index=2, risk_money="40"),
    # Exit open 4004.90: ask 4005.10 >= 4005.00: "stop", ambiguous, at the open 4004.90.
    _case("short exit open beyond the stop is stop + ambiguous at the open", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4003.00", "4000.10", "4002.50", 200),
        ("2026-03-10T14:02", "4004.90", "4005.20", "4004.70", "4005.00", 200),
    ), _trade("short", _E, ("2026-03-10T14:02", "4004.90", 200), "0.10", "5.00", "4005.00", "stop", True,
              (0, 0), _LOSS_48, "-49.00", "-52.00", "25", None, "-2.08"), exit_index=2),
    _case("short exit ask open equal to the stop is stop + ambiguous", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4003.00", "4000.10", "4002.50", 200),
        ("2026-03-10T14:02", "4004.80", "4005.00", "4004.60", "4004.90", 200),
    ), _trade("short", _E, ("2026-03-10T14:02", "4004.80", 200), "0.10", "5.00", "4005.00", "stop", True,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04"), exit_index=2),
    _case("short stop before the signal exit", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4003.00", "4004.85", "4002.90", "4004.00", 200),
        ("2026-03-10T14:02", "3999.00", "3999.20", "3998.80", "3999.10", 200),
    ), _trade("short", _E, ("2026-03-10T14:01", "4004.80", 200), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), _LOSS_48, "-48.00", "-51.00", "25", None, "-2.04"), exit_index=2),
    # No spread at entry: recorded as 240; the short stop does not use it (4005.00) and the
    # short pays the exit spread 200. gross = 1.00 * 10 = 10.00, net 7.00, r 0.28.
    _case("short spread None at entry is recorded as the fallback", "short", (
        ("2026-03-10T14:00", "4000.00", "4000.50", "3999.50", "4000.20", None),
        ("2026-03-10T14:01", "3999.00", "3999.20", "3998.80", "3999.10", 200),
    ), _trade("short", ("2026-03-10T14:00", "4000.00", 240), ("2026-03-10T14:01", "3999.00", 200), "0.10",
              "5.00", "4005.00", "signal", False, (0, 0), _LOSS_48, "10.00", "7.00", "25", None, "0.28"),
          exit_index=1),
    _case("short spread None at the signal exit", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "3999.00", "3999.20", "3998.80", "3999.10", None),
    ), _trade("short", _E, ("2026-03-10T14:01", "3999.00", 240), "0.10", "5.00", "4005.00", "signal", False,
              (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "10.00", "6.60", "25", None, "0.264"), exit_index=1),
    # No spread at the M1 of the stop: s = 240, ask high 4004.80 + 0.240 = 4005.04 >= 4005.00
    # (with s = 0 there would be no stop); exit bid = 4005.00 - 0.240 = 4004.76. gross = -4.76 *
    # 10 = -47.60, spread 2.40, total 3.40, net -51.00, r -2.04.
    _case("short spread None at the M1 of the stop widens the ask", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4003.00", "4004.80", "4002.90", "4004.00", None),
    ), _trade("short", _E, ("2026-03-10T14:01", "4004.76", 240), "0.10", "5.00", "4005.00", "stop", False,
              (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "-47.60", "-51.00", "25", None, "-2.04")),
    _case("short spread None at the last M1", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4000.30", "3999.10", "3999.20", None),
    ), _trade("short", _E, ("2026-03-10T14:01", "3999.20", 240), "0.10", "5.00", "4005.00", "end_of_data",
              False, (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "8.00", "4.60", "25", None, "0.184")),
)

# ---------------------------------------------------------------------------------------------
# AC-04: holding periods. Long, lots 0.10, stop_distance 50.00 (never reached), entry open
# 4000.00 spread 200, signal exit at the second M1 open 4001.00 spread 200: gross 10.00, spread
# 2.00, slippage 1.00, swap = 5.038 * (nights - triple + 3 * triple). Prices stay inside
# 3999.50 .. 4001.20. (label, entry time, exit time, side, nights, triple, swap, total, net, r)
# r = net / 25.
NIGHTS_CASES = (
    # Friday 10:00 EDT -> Monday 10:00 EDT: only Friday 17:00 EDT (21:00 UTC); Saturday and Sunday
    # are not Monday-Friday. multiplier 1.
    ("Friday to Monday", "2026-03-13T14:00", "2026-03-16T14:00", "long", 1, 0, "5.038", "8.038", "1.962",
     "0.07848"),
    # Monday 10:00 EDT -> next Monday 10:00 EDT: Monday to Friday 17:00 = 5, Wednesday once:
    # multiplier 5 - 1 + 3 = 7 -> 35.266; total 38.266; net 10.00 - 38.266 = -28.266.
    ("Monday to next Monday", "2026-03-16T14:00", "2026-03-23T14:00", "long", 5, 1, "35.266", "38.266",
     "-28.266", "-1.13064"),
    # Tuesday 10:00 EDT -> Thursday 10:00 EDT: Tuesday and Wednesday 17:00: multiplier 4 -> 20.152.
    ("Tuesday to Thursday", "2026-03-17T14:00", "2026-03-19T14:00", "long", 2, 1, "20.152", "23.152",
     "-13.152", "-0.52608"),
    # Friday 2026-10-30 14:00 UTC (10:00 EDT) -> Monday 2026-11-02 21:30 UTC (16:30 EST, after the
    # end of daylight time on Sunday 2026-11-01): Friday 17:00 EDT = 21:00 UTC counts; Monday
    # 17:00 EST = 22:00 UTC is after the exit. A fixed UTC-4 or 21:00 UTC rule would count 2.
    ("Friday to Monday across the end of daylight time", "2026-10-30T14:00", "2026-11-02T21:30", "long", 1,
     0, "5.038", "8.038", "1.962", "0.07848"),
    # Boundaries of entry < T <= exit: entry exactly at Tuesday 17:00 EDT (21:00 UTC) does not
    # count it; exit exactly at Wednesday 17:00 EDT counts it, a Wednesday: multiplier 3 -> 15.114.
    ("entry at a rollover, exit at the next", "2026-03-17T21:00", "2026-03-18T21:00", "long", 1, 1,
     "15.114", "18.114", "-8.114", "-0.32456"),
    # One minute after Tuesday's rollover to one minute before Wednesday's: none (a count by
    # calendar day would give 1).
    ("one minute after to one minute before", "2026-03-17T21:01", "2026-03-18T20:59", "long", 0, 0, "0",
     "3.00", "7.00", "0.28"),
    # Friday 17:30 EDT -> Monday 16:00 EDT: the weekend has no rollover (a rule on every calendar
    # day would count Saturday and Sunday).
    ("Friday after the rollover to Monday before it", "2026-03-13T21:30", "2026-03-16T20:00", "long", 0, 0,
     "0", "3.00", "7.00", "0.28"),
    # Short over a week: nights still counted (5, 1) but short swap is 0 points; the short pays
    # the exit spread 200 -> 2.00. gross = (4001.00 - 4000.00) * 10 * -1 = -10.00; total 3.00;
    # net -13.00; r -0.52.
    ("short Monday to next Monday", "2026-03-16T14:00", "2026-03-23T14:00", "short", 5, 1, "0", "3.00",
     "-13.00", "-0.52"),
)
NIGHTS_ENTRY = ("4000.00", "4000.50", "3999.50", "4000.20", 200)
NIGHTS_EXIT = ("4001.00", "4001.20", "4000.80", "4001.10", 200)

# ---------------------------------------------------------------------------------------------
# AC-02/03/05: whole runs with the real strategy.decide (variant B), built from M1 like R1.
# Params inside H001 section 4: f 8, s 32, n 10, theta 0.50, N 48, M 24, k 3.0. warm from t =
# max(3*32, 48+1, 24+1, 97, 10+1) = 97. V-B: long when close[t] > HH_48[t] (bars t-48..t-1),
# short when close[t] < LL_48[t]; a long exits when close[t] < LL_24[t] or a short signal comes,
# a short when close[t] > HH_24[t] or a long signal comes. stop_distance = 3.0 x ATR_10[t].
RUN_PARAMS = {"variant": "B", "f": 8, "s": 32, "n": 10, "theta": "0.50", "N": 48, "M": 24, "k": "3.0"}
RUN_EQUITY = "10000"
RUN_START = "2026-03-09T11:00"  # bar t opens at RUN_START + 15t minutes: t 100 = 2026-03-10T12:00
RUN_BARS = 112  # bars 0 .. 111
FLAT_BAR = ("4000.00", "4001.00", "3999.00", "4000.00", 240)  # bars 0 .. 99: TR 2, ATR 2
# M15 bar t: (open, high, low, close, spread of its last M1). Each M15 bar has 15 M1 (every
# minute, so no "incomplete"): minutes 0-6 open = high = low = close = O, minute 7 is (O, H, L,
# C), minutes 8-14 are all C; every spread is 240 except minute 14, which carries the bar's
# spread. So the M15 bar is (O, H, L, C) with that spread (aggregate: last M1 spread), its
# first M1 opens at O with spread 240, and a stop inside the bar is hit at minute 7.
RUN_ACTIVE = {
    100: ("4000.00", "4002.50", "3999.50", "4002.00", 240),
    101: ("4002.00", "4002.80", "4001.60", "4002.40", 240),
    102: ("4002.40", "4002.50", "3998.20", "3998.60", 240),
    103: ("3998.60", "3998.90", "3997.80", "3998.00", 800),
    104: ("3998.00", "4003.60", "3997.90", "4003.20", 240),
    105: ("4003.20", "4003.30", "3995.50", "3996.30", 240),
    106: ("3996.30", "3996.80", "3995.40", "3995.80", 240),
    107: ("3995.80", "4004.50", "3995.70", "4004.00", 240),
    108: ("4005.20", "4005.50", "4004.80", "4005.10", 800),
    109: ("4005.10", "4006.00", "4005.00", "4005.80", 240),
    110: ("4005.80", "4006.60", "4005.70", "4006.40", 240),
    111: ("4006.40", "4007.00", "4006.10", "4006.90", 260),
}
# Hand arithmetic (TR from the previous close; ATR[t] = (ATR[t-1] * 9 + TR[t]) / 10, ATR = 2 up to
# t = 99; every spread median of 96 bars is 240, so the filter limit is 3 * 240 = 720):
#   t   TR    ATR            HH_48[t] LL_48[t]  decision (position before it)
#   100 3.00  2.1            4001.00  3999.00   close 4002.00 > 4001.00: enter_long, stop 6.30
#   101 1.20  2.01           4001.00  3999.00   hold (long; LL_24 3999.00)
#   102 4.30  2.239          4002.80  3999.00   close 3998.60 < 3999.00, a short signal: exit
#   103 1.10  2.1251         4002.80  3998.20   close 3998.00 < 3998.20 (short), spread 800 > 720:
#                                               skip spread_filter (flat)
#   104 5.70  2.48259        4002.80  3997.80   close 4003.20 > 4002.80: enter_long, stop 7.44777
#   105 7.80  3.014331       4003.60  3997.80   stop at minute 7 first (step 1), so flat: close
#                                               3996.30 < 3997.80: enter_short, stop 9.042993
#   106 1.40  2.8528979      4003.60  3995.50   hold (short; HH_24 4003.60)
#   107 8.80  3.44760811     4003.60  3995.40   close 4004.00 > 4003.60, a long signal: exit
#   108 1.50  3.252847299    4004.50  3995.40   close 4005.10 > 4004.50 (long), spread 800: skip
#                                               spread_filter (flat)
#   109 1.00  3.0275625691   4005.50  3995.40   close 4005.80 > 4005.50: enter_long, stop
#                                               9.0826877073; the sizer gives no lots: Skip
#   110 0.90  2.81480631219  4006.00  3995.40   close 4006.40 > 4006.00: enter_long, stop
#                                               8.44441893657 (110 is the second-to-last bar)
#   111 last bar: no decide; the position closes at the end of data (step 6).
# e.g. ATR[104] = (2.1251 * 9 + 5.70) / 10 = (19.1259 + 5.70) / 10 = 2.48259 and stop = 3.0 *
# 2.48259 = 7.44777; ATR[105] = (22.34331 + 7.80) / 10 = 3.014331, stop 9.042993; ATR[109] =
# (29.275625691 + 1.00) / 10 = 3.0275625691; ATR[110] = (27.2480631219 + 0.90) / 10 =
# 2.81480631219, stop 8.44441893657. The median of 96 spreads with one or two 800 is still 240.


def run_m1_rows(start=RUN_START, bars=RUN_BARS, active=RUN_ACTIVE, gap_after=None):
    """Every M1 row of a run scenario. gap_after: (t, minutes) leaves that many minutes empty
    after M15 bar t (no bar is dropped, so the indicators see the same bars)."""
    first = datetime.fromisoformat(start)
    rows = []
    for t in range(bars):
        shift = gap_after[1] if gap_after and t > gap_after[0] else 0
        opened = first + timedelta(minutes=15 * t + shift)
        o, h, l, c, spread = active.get(t, FLAT_BAR)
        for minute in range(15):
            stamp = (opened + timedelta(minutes=minute)).isoformat(timespec="minutes")
            if minute < 7:
                rows.append((stamp, o, o, o, o, 240))
            elif minute == 7:
                rows.append((stamp, o, h, l, c, 240))
            else:
                rows.append((stamp, c, c, c, c, spread if minute == 14 else 240))
    return tuple(rows)


# Scripted sizer responses (lots, risk_money, actual_risk, reason), consumed in call order; each
# call is (equity, stop_distance) and the test checks every call against the list below.
_SIZED_1 = ("0.03", "25", "18.90", "sized")
_SIZED_2 = ("0.03", "25", "22.34331", "sized")

# Trades of the full scenario R (sides both):
# T1 long: entry minute 0 of bar 101 (12:15) at 4002.00, s 240: ask 4002.240, stop 4002.240 -
#   6.30 = 3995.94. Exit at minute 0 of bar 103 (12:45) at 3998.60 > stop: signal.
#   gross = (3998.60 - 4002.00) * 100 * 0.03 = -3.40 * 3 = -10.20; spread 240 * 0.003 = 0.72;
#   slippage 0.05 * 3 * 2 = 0.30; total 1.02; net -11.22; r = -11.22 / 25 = -0.4488.
# T2 long: entry minute 0 of bar 104+1 = 105 (13:15) at 4003.20: ask 4003.440, stop 4003.440 -
#   7.44777 = 3995.99223. Minute 7 of bar 105 (13:22) opens at 4003.20 (no gap) and its low
#   3995.50 touches: exit 3995.99223, spread 240. gross = (3995.99223 - 4003.20) * 3 = -7.20777 *
#   3 = -21.62331; total 1.02; net -22.64331; r = -0.9057324.
# T3 short: entry minute 0 of bar 106 (13:30) at 3996.30, stop 3996.30 + 9.042993 = 4005.342993.
#   Highest ask before the exit: minute 7 of bar 107, 4004.50 + 0.240 = 4004.74 < stop. Exit
#   decided at 107, minute 0 of bar 108 (14:00) opens at 4005.20, ask 4005.44 >= stop: "stop",
#   ambiguous, at the open 4005.20. gross = (4005.20 - 3996.30) * 100 * 0.02 * -1 = -17.80;
#   spread of the exit 240 * 0.002 = 0.48; slippage 0.20; total 0.68; net -18.48; r -0.7392.
# T4 long: decided at bar 110 (second-to-last), entry minute 0 of bar 111 (14:45) at 4006.40:
#   ask 4006.640, stop 4006.640 - 8.44441893657 = 3998.19558106343. No stop (lows >= 4006.10);
#   end of data at minute 14 of bar 111 (14:59), close 4006.90, spread 260. gross = 0.50 * 100 *
#   0.05 = 2.50; spread 240 * 0.005 = 1.20; slippage 0.50; total 1.70; net 0.80; r = 0.80 / 50
#   = 0.016.
# Equity: 10000 -> 9988.78 -> 9966.13669 -> 9947.65669 -> 9948.45669 (realized, one point per
# close). No trade crosses 21:00 UTC: nights 0.
_NO_COST_NIGHTS = (0, 0)
T1 = _trade("long", ("2026-03-10T12:15", "4002.00", 240), ("2026-03-10T12:45", "3998.60", 240), "0.03",
            "6.30", "3995.94", "signal", False, _NO_COST_NIGHTS, ("0.72", "0", "0.30", "0", "1.02"),
            "-10.20", "-11.22", "25", "18.90", "-0.4488")
T2 = _trade("long", ("2026-03-10T13:15", "4003.20", 240), ("2026-03-10T13:22", "3995.99223", 240), "0.03",
            "7.44777", "3995.99223", "stop", False, _NO_COST_NIGHTS, ("0.72", "0", "0.30", "0", "1.02"),
            "-21.62331", "-22.64331", "25", "22.34331", "-0.9057324")
T3 = _trade("short", ("2026-03-10T13:30", "3996.30", 240), ("2026-03-10T14:00", "4005.20", 240), "0.02",
            "9.042993", "4005.342993", "stop", True, _NO_COST_NIGHTS, ("0.48", "0", "0.20", "0", "0.68"),
            "-17.80", "-18.48", "25", "18.085986", "-0.7392")
T4 = _trade("long", ("2026-03-10T14:45", "4006.40", 240), ("2026-03-10T14:59", "4006.90", 260), "0.05",
            "8.44441893657", "3998.19558106343", "end_of_data", False, _NO_COST_NIGHTS,
            ("1.20", "0", "0.50", "0", "1.70"), "2.50", "0.80", "50", None, "0.016")


def _with_flags(trade, flags):
    return {**trade, "data_flags": tuple(flags)}


def _scenario(label, responses, calls, trades, skips, equity, bars=RUN_BARS, sides=("long", "short"),
              start_equity=RUN_EQUITY, flags=None, start=RUN_START, gap_after=None):
    return {"label": label, "bars": bars, "sides": sides, "start_equity": start_equity,
            "flags": flags or {}, "start": start, "gap_after": gap_after, "responses": responses,
            "calls": calls, "trades": trades, "skips": skips, "equity": equity}


SCENARIOS = {
    # Full scenario: SL inside bar 105 then the opposite entry at 106; Skips from decide (103,
    # 108) and from the sizer (109); an entry decided at the second-to-last bar; the exit of T3 at
    # an open beyond its stop; end of data.
    "R": _scenario(
        "R: the full scenario",
        (_SIZED_1, _SIZED_2, ("0.02", "25", "18.085986", "sized"), (None, "25", None, "below_min_volume"),
         ("0.05", "50", None, "sized")),
        (("10000", "6.30"), ("9988.78", "7.44777"), ("9966.13669", "9.042993"),
         ("9947.65669", "9.0826877073"), ("9947.65669", "8.44441893657")),
        (T1, T2, T3, T4),
        (("2026-03-10T12:45", ("spread_filter",)), ("2026-03-10T14:00", ("spread_filter",)),
         ("2026-03-10T14:15", ("below_min_volume",))),
        (("2026-03-09T11:00", "10000"), ("2026-03-10T12:45", "9988.78"), ("2026-03-10T13:22", "9966.13669"),
         ("2026-03-10T14:00", "9947.65669"), ("2026-03-10T14:59", "9948.45669")),
    ),
    # Long-only (D11): T1, T2 and the skip at 103 (a short signal's skip is recorded whatever
    # sides is, r3 F37) stay. At 105 enter_short is not in sides: none, no Skip, no sizer call.
    # 106: close 3995.80 is not below LL_48 3995.50: none. 107: close 4004.00 > 4003.60:
    # enter_long, stop 3.0 * 3.44760811 = 10.34282433. Entry minute 0 of bar 108 (14:00) at
    # 4005.20: ask 4005.44, stop 4005.44 - 10.34282433 = 3995.09717567; lows of bars 108-111 stay
    # >= 4004.80; held (no exit, and no skip at 108 because the position is long) to the end
    # of data at 14:59, close 4006.90, spread 260. gross = 1.70 * 100 * 0.02 = 3.40; spread 0.48;
    # slippage 0.20; total 0.68; net 2.72; r 0.1088.
    "R_long_only": _scenario(
        "R with sides {long}",
        (_SIZED_1, _SIZED_2, ("0.02", "25", None, "sized")),
        (("10000", "6.30"), ("9988.78", "7.44777"), ("9966.13669", "10.34282433")),
        (T1, T2, _trade("long", ("2026-03-10T14:00", "4005.20", 240), ("2026-03-10T14:59", "4006.90", 260),
                        "0.02", "10.34282433", "3995.09717567", "end_of_data", False, _NO_COST_NIGHTS,
                        ("0.48", "0", "0.20", "0", "0.68"), "3.40", "2.72", "25", None, "0.1088")),
        (("2026-03-10T12:45", ("spread_filter",)),),
        (("2026-03-09T11:00", "10000"), ("2026-03-10T12:45", "9988.78"), ("2026-03-10T13:22", "9966.13669"),
         ("2026-03-10T14:59", "9968.85669")),
        sides=("long",),
    ),
    # Bars 0..103: the exit decided at the second-to-last bar (102) fills at minute 0 of the last
    # bar (103); the last bar has no decide, so no Skip at 103.
    "R_to_103": _scenario(
        "R cut after bar 103: exit at the second-to-last bar",
        (_SIZED_1,), (("10000", "6.30"),), (T1,), (),
        (("2026-03-09T11:00", "10000"), ("2026-03-10T12:45", "9988.78")),
        bars=104,
    ),
    # Bars 0..104 with data_flags (contract: union from the decision bar t to the bar of the exit
    # M1, both ends). Flags other than "incomplete" enter decide's lookback (CORE-006 D3), so the
    # skip at 103 also carries data_flag; bar 104 is last (no decide), so its flag only shows
    # that the bar after the exit is not in the union. T1: t = 100 .. exit bar 103.
    "R_flags_ends": _scenario(
        "R cut after bar 104 with flags on 100, 101, 103, 104",
        (_SIZED_1,), (("10000", "6.30"),),
        (_with_flags(T1, ("incomplete", "missing_spread", "unexpected_gap")),),
        (("2026-03-10T12:45", ("spread_filter", "data_flag")),),
        (("2026-03-09T11:00", "10000"), ("2026-03-10T12:45", "9988.78")),
        bars=105, flags={100: ("incomplete",), 101: ("unexpected_gap",), 103: ("missing_spread",),
                         104: ("duplicate_time",)},
    ),
    # The bar before the decision bar is not in the union.
    "R_flags_before": _scenario(
        "R cut after bar 104 with a flag on 99",
        (_SIZED_1,), (("10000", "6.30"),), (T1,), (("2026-03-10T12:45", ("spread_filter",)),),
        (("2026-03-09T11:00", "10000"), ("2026-03-10T12:45", "9988.78")),
        bars=105, flags={99: ("incomplete",)},
    ),
    # Full R with "incomplete" on bar 105: the bar of T2's stop (its last bar) and the decision
    # bar of T3 (its first bar). decide ignores "incomplete", so everything else is as in R.
    "R_flags_105": _scenario(
        "R with a flag on 105",
        (_SIZED_1, _SIZED_2, ("0.02", "25", "18.085986", "sized"), (None, "25", None, "below_min_volume"),
         ("0.05", "50", None, "sized")),
        (("10000", "6.30"), ("9988.78", "7.44777"), ("9966.13669", "9.042993"),
         ("9947.65669", "9.0826877073"), ("9947.65669", "8.44441893657")),
        (T1, _with_flags(T2, ("incomplete",)), _with_flags(T3, ("incomplete",)), T4),
        (("2026-03-10T12:45", ("spread_filter",)), ("2026-03-10T14:00", ("spread_filter",)),
         ("2026-03-10T14:15", ("below_min_volume",))),
        (("2026-03-09T11:00", "10000"), ("2026-03-10T12:45", "9988.78"), ("2026-03-10T13:22", "9966.13669"),
         ("2026-03-10T14:00", "9947.65669"), ("2026-03-10T14:59", "9948.45669")),
        flags={105: ("incomplete",)},
    ),
    # D12: start equity 11.22 = T1's loss, so equity is exactly 0 after T1. Every later entry is
    # Skip(t, ("equity_exhausted",)) without a sizer call: 104 (long), 105 (short: no T2, no stop,
    # close 3996.30 < 3997.80), 107, 109, 110 (long); 106 has no signal (3995.80 >= 3995.50);
    # decide's own skips at 103 and 108 stay.
    "R_exhausted": _scenario(
        "R starting with 11.22",
        (_SIZED_1,), (("11.22", "6.30"),), (T1,),
        (("2026-03-10T12:45", ("spread_filter",)), ("2026-03-10T13:00", ("equity_exhausted",)),
         ("2026-03-10T13:15", ("equity_exhausted",)), ("2026-03-10T13:45", ("equity_exhausted",)),
         ("2026-03-10T14:00", ("spread_filter",)), ("2026-03-10T14:15", ("equity_exhausted",)),
         ("2026-03-10T14:30", ("equity_exhausted",))),
        (("2026-03-09T11:00", "11.22"), ("2026-03-10T12:45", "0")),
        start_equity="11.22",
    ),
    "R_negative": _scenario(
        "R starting with 10.00 (equity -1.22 after T1)",
        (_SIZED_1,), (("10.00", "6.30"),), (T1,),
        (("2026-03-10T12:45", ("spread_filter",)), ("2026-03-10T13:00", ("equity_exhausted",)),
         ("2026-03-10T13:15", ("equity_exhausted",)), ("2026-03-10T13:45", ("equity_exhausted",)),
         ("2026-03-10T14:00", ("spread_filter",)), ("2026-03-10T14:15", ("equity_exhausted",)),
         ("2026-03-10T14:30", ("equity_exhausted",))),
        (("2026-03-09T11:00", "10.00"), ("2026-03-10T12:45", "-1.22")),
        start_equity="10.00",
    ),
    # Step 2: next_open_utc is the time of the next bar that exists. Bars 0..103 of R start at
    # 2026-03-09T05:30, so bar 100 opens at 2026-03-10T06:30 UTC (02:30 EDT), and 15 minutes are
    # empty after it: bar 101 opens at 07:00 UTC = 03:00 EDT, inside 03:00-15:59 New York, so T1
    # is entered (bar 100's time + 15 minutes, 02:45 EDT, would be outside). T1 moves to 07:00 and
    # 07:30 with every money value unchanged.
    "R_gap": _scenario(
        "R cut after bar 103, 15 minutes empty after bar 100",
        (_SIZED_1,), (("10000", "6.30"),),
        ({**T1, "entry": ("2026-03-10T07:00", "4002.00", 240), "exit": ("2026-03-10T07:30", "3998.60", 240)},),
        (), (("2026-03-09T05:30", "10000"), ("2026-03-10T07:30", "9988.78")),
        bars=104, start="2026-03-09T05:30", gap_after=(100, 15),
    ),
    # The same bars without the gap: bar 101 opens at 06:45 UTC = 02:45 EDT, so decide skips with
    # outside_window at 100. 101: close 4002.40 is not above HH_48 4002.50 (bar 100): none. 102:
    # close 3998.60 < LL_48 3999.00 and bar 103 opens 07:15 UTC = 03:15 EDT: enter_short, stop
    # 3.0 * 2.239 = 6.717 (decided at the second-to-last bar). Entry minute 0 of bar 103 at
    # 3998.60, stop 4005.317; highest ask 3998.90 + 0.240; end of data at 07:29, close 3998.00,
    # spread 800 (the short pays it): spread 800 * 0.003 = 2.40, slippage 0.30, total 2.70;
    # gross = (3998.00 - 3998.60) * 3 * -1 = 1.80; net -0.90; r = -0.036.
    "R_window": _scenario(
        "R cut after bar 103, bar 100 at 02:30 EDT",
        (_SIZED_1,), (("10000", "6.717"),),
        (_trade("short", ("2026-03-10T07:15", "3998.60", 240), ("2026-03-10T07:29", "3998.00", 800), "0.03",
                "6.717", "4005.317", "end_of_data", False, _NO_COST_NIGHTS, ("2.40", "0", "0.30", "0", "2.70"),
                "1.80", "-0.90", "25", "18.90", "-0.036"),),
        (("2026-03-10T06:30", ("outside_window",)),),
        (("2026-03-09T05:30", "10000"), ("2026-03-10T07:29", "9999.10")),
        bars=104, start="2026-03-09T05:30",
    ),
}

# AC-03 sizes: bars 0..101 of R. One entry (decided at 100, stop 6.30, fill 4002.00 at 12:15,
# stop_price 3995.94) and the end of data at 12:29, close 4002.40, spread 240. Per lot:
# gross 0.40 * 100 = 40, spread 240 * 0.1 = 24, slippage 0.05 * 100 * 2 = 10, so the money is
# 40 L, 24 L, 10 L, total 34 L, net 6 L. (lots, risk_money, actual_risk, gross, spread, slippage,
# total, net, r)
SIZE_BARS = 102
SIZE_CASES = (
    ("0.01", "25", None, "0.40", "0.24", "0.10", "0.34", "0.06", "0.0024"),
    ("0.37", "25", "233.10", "14.80", "8.88", "3.70", "12.58", "2.22", "0.0888"),
    ("1.00", "50", "630.00", "40.00", "24.00", "10.00", "34.00", "6.00", "0.12"),
    ("200", "1000", None, "8000", "4800", "2000", "6800", "1200", "1.2"),
)

# =============================================================================================
# Round 2 (tests r2). Contract v1.5 and docs/reviews/CORE-007-tests-r1.md F1, F2, F4, F5, F7.
# Same conventions and helpers as above. Where the review gives a case, the round-2 author's own
# values agree with it (docs/handoff/CORE-007.md, round 2).

# ---------------------------------------------------------------------------------------------
# AC-04, review F1: the rollover zone and wall time (D4 [A]) and model.triple_swap_weekday are
# inputs. They are not always New York 17:00 and Wednesday. T = rollover.at in rollover.zone on
# Monday-Friday of that zone, counted when entry < T <= exit; triple when that zone's weekday
# (date.weekday(), Monday 0) is the model's. Every case is a long on NIGHTS_ENTRY and NIGHTS_EXIT,
# lots 0.10, stop_distance 50.00 (stop_price 4000.200 - 50.00 = 3950.20, never reached), risk_money
# 25, signal exit at the second M1: gross 10.00, spread 2.00, slippage 1.00, one long night
# -(-503.8 * 0.001 * 100 * 0.10) = 5.038, swap = 5.038 * (nights - triple + 3 * triple),
# r = net / 25. Asia/Tokyo is UTC+9 all year (no daylight time); US daylight time is in force on
# these dates (17:00 EDT = 21:00 UTC). 2026-03-13 is a Friday, 2026-03-16 a Monday.
# (label, zone, hour, minute, triple_swap_weekday, entry time UTC, exit time UTC, nights, triple,
#  swap, total, net, r)
ROLLOVER_CASES = (
    # (a) = review F1 (a). Entry Friday 2026-03-13 14:00 UTC = Friday 23:00 JST; exit Monday
    # 2026-03-16 14:00 UTC = Monday 23:00 JST; triple on Monday (weekday 0).
    #   Friday 13 06:00 JST = Thursday 12 21:00 UTC: before the entry.
    #   Saturday 14 and Sunday 15 are not Monday-Friday in Tokyo.
    #   Monday 16 06:00 JST = Sunday 15 21:00 UTC: inside, and a Tokyo Monday: triple.
    #   Tuesday 17 06:00 JST = Monday 16 21:00 UTC: after the exit.
    #   nights 1, triple 1, multiplier 1 - 1 + 3 = 3: swap 15.114, total 2.00 + 0 + 1.00 + 15.114 =
    #   18.114, net 10.00 - 18.114 = -8.114, r -0.32456.
    # New York 17:00 instead (Friday 13 21:00 UTC, a Friday), Wednesday as the triple day, or the
    # weekday of T in UTC (Sunday 15) each give (1, 0): swap 5.038, total 8.038, net 1.962.
    ("(a) Asia/Tokyo 06:00 with the triple day on Monday", "Asia/Tokyo", 6, 0, 0, "2026-03-13T14:00",
     "2026-03-16T14:00", 1, 1, "15.114", "18.114", "-8.114", "-0.32456"),
    # (b) = review F1 (b). America/New_York 23:00, triple Wednesday (as H001_COSTS). Entry Tuesday
    # 2026-03-17 14:00 UTC = 10:00 EDT; exit Wednesday 2026-03-18 02:30 UTC = Tuesday 22:30 EDT.
    #   Monday 16 23:00 EDT = Tuesday 17 03:00 UTC: before the entry.
    #   Tuesday 17 23:00 EDT = Wednesday 18 03:00 UTC: after the exit.
    #   nights 0, swap 0, total 3.00, net 7.00, r 0.28.
    # New York 17:00 instead (Tuesday 17 21:00 UTC) counts one night: (1, 0), net 1.962.
    ("(b) America/New_York 23:00", "America/New_York", 23, 0, 2, "2026-03-17T14:00", "2026-03-18T02:30", 0, 0,
     "0", "3.00", "7.00", "0.28"),
    # (c) The zone is read, not only the wall time. Asia/Tokyo 06:00, triple Wednesday. Entry
    # Tuesday 2026-03-17 14:00 UTC = Tuesday 23:00 JST; exit Tuesday 2026-03-17 22:00 UTC =
    # Wednesday 07:00 JST.
    #   Tuesday 17 06:00 JST = Monday 16 21:00 UTC: before the entry.
    #   Wednesday 18 06:00 JST = Tuesday 17 21:00 UTC: inside, and a Tokyo Wednesday: triple.
    #   Thursday 19 06:00 JST = Wednesday 18 21:00 UTC: after the exit.
    #   nights 1, triple 1: the money of (a).
    # New York 06:00 (Tuesday 17 10:00 UTC, Wednesday 18 10:00 UTC) and Tokyo 17:00 (Tuesday 17
    # 08:00 UTC, Wednesday 18 08:00 UTC) give (0, 0), net 7.00; New York 17:00 (Tuesday 17 21:00
    # UTC) and the weekday of T in UTC (Tuesday) give (1, 0), net 1.962.
    ("(c) Asia/Tokyo 06:00 on a Tokyo Wednesday that is a UTC Tuesday", "Asia/Tokyo", 6, 0, 2,
     "2026-03-17T14:00", "2026-03-17T22:00", 1, 1, "15.114", "18.114", "-8.114", "-0.32456"),
)

# ---------------------------------------------------------------------------------------------
# AC-04, review F5: nights compare the time_utc of the entry and exit M1, never time_raw. The two
# M1 carry time_raw = UTC seconds + 3600 (a rule with offset 3600) and the correct time_utc;
# simulate_trade takes no rule, so only time_utc says when the bar opened. Entry Tuesday
# 2026-03-17 21:01 UTC, one minute after Tuesday 17:00 EDT; exit Wednesday 2026-03-18 20:59 UTC,
# one minute before Wednesday 17:00 EDT. Long as in ROLLOVER_CASES with the default Rollover and
# H001_COSTS: nights 0, swap 0, total 3.00, net 7.00, r 0.28. Reading time_raw as UTC (22:01
# Tuesday to 21:59 Wednesday) would count Wednesday 21:00 UTC, a Wednesday: (1, 1), swap 15.114,
# net -8.114.
# Raw anchors: 2026-03-17T00:00Z = 1773100800 + 7 * 86400 = 1773705600. Entry 21:01 = 75660 s:
# 1773705600 + 75660 + 3600 = 1773784860. Exit 20:59 = 75540 s on the next day: 1773705600 +
# 86400 + 75540 + 3600 = 1773871140.
# (label, raw shift, entry time UTC, exit time UTC, raw anchors, nights, triple, swap, total, net, r)
RAW_SHIFT_CASE = ("time_raw = UTC seconds + 3600, time_utc correct", 3600, "2026-03-17T21:01", "2026-03-18T20:59",
                  (1773784860, 1773871140), 0, 0, "0", "3.00", "7.00", "0.28")

# ---------------------------------------------------------------------------------------------
# AC-02, review F4: spread None at the exit_index M1 of an exit open beyond the stop, and at a
# short entry M1 that stops. Defaults of _case: lots 0.10, risk_money 25, no data_flags.
FILL_CASES_R2 = (
    # (a) = review F4 (a). Short, stop_price = 4000.00 + 5.00 = 4005.00. Entry M1 (_ENTRY, s 200):
    # ask open 4000.20, ask high 4000.70. 14:01 (s 200): ask open 4000.40, ask high 4003.20. No stop.
    # exit_index 2 (14:02) has no spread, so s = 240 there: ask open 4004.78 + 0.240 = 4005.02 >=
    # 4005.00, beyond the stop: "stop", ambiguous True, at the bid open 4004.78,
    # exit_spread_points 240. With the entry M1's 200 (ask 4004.98) or with 0 (4004.78) the ask
    # open stays below 4005.00 and the exit would be a "signal".
    #   gross = (4004.78 - 4000.00) * 100 * 0.10 * -1 = -47.80; the short pays the exit spread
    #   240 * 0.001 * 100 * 0.10 = 2.40; slippage 1.00; swap 0; total 3.40;
    #   net = -47.80 - 3.40 = -51.20; r = -51.20 / 25 = -2.048.
    _case("short spread None at an exit open beyond the stop uses the fallback", "short", (
        _ENTRY,
        ("2026-03-10T14:01", "4000.20", "4003.00", "4000.10", "4002.50", 200),
        ("2026-03-10T14:02", "4004.78", "4005.00", "4004.60", "4004.90", None),
    ), _trade("short", _E, ("2026-03-10T14:02", "4004.78", 240), "0.10", "5.00", "4005.00", "stop", True,
              (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "-47.80", "-51.20", "25", None, "-2.048"), exit_index=2),
    # (b) = review F4 (b). Short entry M1 without spread: s = 240 for its record and its SL check.
    # stop_price = 4000.00 + 0.22 = 4000.22; ask open 4000.00 + 0.240 = 4000.24 >= 4000.22: gap at
    # the entry M1, exit at the bid open 4000.00 at 14:00, entry and exit spread points 240. With
    # s read as 0, the entry M1 (ask open and ask high 4000.00) and 14:01 (s 200: ask open
    # 3999.70, ask high 3999.80) stay below the stop: end of data at 3999.20 instead.
    #   gross = (4000.00 - 4000.00) * 100 * 0.10 * -1 = 0; spread of the exit 2.40; slippage 1.00;
    #   total 3.40; net -3.40; r = -3.40 / 25 = -0.136.
    _case("short spread None at an entry M1 that stops at its open", "short", (
        ("2026-03-10T14:00", "4000.00", "4000.00", "3999.40", "3999.50", None),
        ("2026-03-10T14:01", "3999.50", "3999.60", "3999.00", "3999.20", 200),
    ), _trade("short", ("2026-03-10T14:00", "4000.00", 240), ("2026-03-10T14:00", "4000.00", 240), "0.10",
              "0.22", "4000.22", "stop", False, (0, 0), ("2.40", "0", "1.00", "0", "3.40"), "0", "-3.40", "25",
              None, "-0.136"), stop_distance="0.22"),
)

# ---------------------------------------------------------------------------------------------
# AC-02/03/05, review F2 and F7 (1): whole runs with the real decide, M1 rows of run_m1_rows
# without the rows in "drop". M15 bars come from aggregate as in R1; "incomplete" lists the bars
# that aggregate flags "incomplete" (a fixture check). Bars and decisions are those of the
# hand-arithmetic table above R_to_103 and R_exhausted.
SCENARIOS_R2 = {
    # Review F2. R_to_103 (bars 0..103) without 2026-03-09T11:00 (minute 0 of bar 0) and
    # 2026-03-10T12:15 (minute 0 of bar 101). aggregate still opens bar 0 at 11:00 and bar 101 at
    # 12:15 (time_raw is the slot time) and flags both "incomplete": Monday 07:00 and Tuesday
    # 08:15 New York are in session. Minutes 0-6 of a bar are all O, so the open, high, low,
    # close and last spread of both bars are unchanged; decide ignores "incomplete" (CORE-006),
    # so every decision is as in R_to_103: 100 enter_long (stop 3.0 * 2.1 = 6.30, next_open_utc
    # 12:15 UTC = 08:15 EDT), 101 hold, 102 exit, 103 is the last bar.
    #   Entry at the first M1 present in bar 101: 12:16, open 4002.00, s 240: ask 4002.240,
    #   stop_price 4002.240 - 6.30 = 3995.94. Lows of bars 101-102 stay >= 3998.20: no stop.
    #   Exit at the first M1 of bar 103, minute 0 (12:45), open 3998.60 > 3995.94, s 240: "signal".
    #   gross = (3998.60 - 4002.00) * 100 * 0.03 = -10.20; spread 240 * 0.001 * 100 * 0.03 = 0.72;
    #   slippage 50 * 0.001 * 100 * 0.03 * 2 = 0.30; swap 0 (no 21:00 UTC inside); total 1.02;
    #   net -11.22; r -11.22 / 25 = -0.4488; actual_risk 18.90 from the sizer.
    #   data_flags: bars 100..103, so {"incomplete"} of bar 101 (bar 0 is outside).
    #   Equity: the first M1 is 11:01 (not bar 0's 11:00): (11:01, 10000), then 10000 - 11.22 =
    #   9988.78 at 12:45. No Skip. One sizer call (10000, 6.30).
    "R_first_minutes_missing": {
        **_scenario("R cut after bar 103 without minute 0 of bars 0 and 101", (_SIZED_1,), (("10000", "6.30"),),
                    ({**T1, "entry": ("2026-03-10T12:16", "4002.00", 240), "data_flags": ("incomplete",)},), (),
                    (("2026-03-09T11:01", "10000"), ("2026-03-10T12:45", "9988.78")), bars=104),
        "drop": ("2026-03-09T11:00", "2026-03-10T12:15"), "incomplete": (0, 101),
    },
    # The exit side of review F2. R_to_103 without 2026-03-10T12:45, minute 0 of bar 103, the bar
    # that the exit decided at 102 fills in. Bar 103 keeps its OHLC and last spread (800) and is
    # "incomplete"; it is the last bar, so nothing is decided on it. Entry as T1 (12:15). The exit
    # fills at the first M1 present in bar 103: 12:46, open 3998.60 (minutes 0-6 are O), s 240:
    # "signal", money as T1. data_flags {"incomplete"} of bar 103, the bar of the exit M1.
    # Equity: (11:00, 10000), (12:46, 9988.78).
    "R_exit_minute_missing": {
        **_scenario("R cut after bar 103 without minute 0 of bar 103", (_SIZED_1,), (("10000", "6.30"),),
                    ({**T1, "exit": ("2026-03-10T12:46", "3998.60", 240), "data_flags": ("incomplete",)},), (),
                    (("2026-03-09T11:00", "10000"), ("2026-03-10T12:46", "9988.78")), bars=104),
        "drop": ("2026-03-10T12:45",), "incomplete": (103,),
    },
    # Review F7 (1). R_exhausted (start equity 11.22 = T1's loss) with sides {"long"}. As in
    # R_exhausted, T1 closes at 12:45 with equity 11.22 - 11.22 = 0, and every later long entry is
    # Skip(t, ("equity_exhausted",)) without a sizer call: 104 (13:00), 107 (13:45), 109 (14:15),
    # 110 (14:30). decide's skips at 103 (12:45) and 108 (14:00) stay (step 5). At 105 decide says
    # enter_short (close 3996.30 < LL_48 3997.80): short is not in sides, so it is "none" with no
    # Skip (step 4) although no equity is left, and R_exhausted's 13:15 Skip is not here. 106: no
    # signal (3995.80 >= LL_48 3995.50).
    "R_exhausted_long_only": {
        **_scenario("R starting with 11.22, sides {long}", (_SIZED_1,), (("11.22", "6.30"),), (T1,),
                    (("2026-03-10T12:45", ("spread_filter",)), ("2026-03-10T13:00", ("equity_exhausted",)),
                     ("2026-03-10T13:45", ("equity_exhausted",)), ("2026-03-10T14:00", ("spread_filter",)),
                     ("2026-03-10T14:15", ("equity_exhausted",)), ("2026-03-10T14:30", ("equity_exhausted",))),
                    (("2026-03-09T11:00", "11.22"), ("2026-03-10T12:45", "0")), sides=("long",), start_equity="11.22"),
        "drop": (), "incomplete": (),
    },
}
