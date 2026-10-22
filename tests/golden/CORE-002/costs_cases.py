"""CORE-002 hand-computed literal oracles; all money strings become Decimal.

No expected value is computed by sochron.costs. Factor is applied exactly once.
Swap uses broker sign: negative points mean a positive expense; positive points
mean a negative credit. Counts are supplied rollover events, not calendar days.
"""

# spread points (None selects 240), lots, stress factor, expected USD.
SPREAD_ROWS = (
    # 240 * .001 * 100 * .02 * 1 = .48.
    (240, "0.02", "1", "0.48"),
    # Missing spread selects 240: 240 * .001 * 100 * .02 * 1 = .48.
    (None, "0.02", "1", "0.48"),
    # 240 * .001 * 100 * .02 * 2 = .96.
    (240, "0.02", "2", "0.96"),
    # Missing spread also stresses once: 240 * .001 * 100 * .02 * 2 = .96.
    (None, "0.02", "2", "0.96"),
    # Minimum lots: 240 * .001 * 100 * .01 * 1 = .24.
    (240, "0.01", "1", "0.24"),
    # Maximum lots: 240 * .001 * 100 * 200 * 1 = 4800.
    (240, "200", "1", "4800"),
    # Explicit zero is not fallback: 0 * .001 * 100 * .02 * 1 = 0.
    (0, "0.02", "1", "0"),
    # Explicit zero under stress: 0 * .001 * 100 * .02 * 2 = 0.
    (0, "0.02", "2", "0"),
)

# Signed points as Decimal strings, lots, factor, expected USD.
POINT_ROWS = (
    # Tick value: 1 * .001 * 100 * 1 * 1 = .1.
    ("1", "1", "1", "0.1"),
    # 240 * .001 * 100 * .02 * 1 = .48.
    ("240", "0.02", "1", "0.48"),
    # Double points: 480 * .001 * 100 * .02 * 1 = .96.
    ("480", "0.02", "1", "0.96"),
    # Double lots: 240 * .001 * 100 * .04 * 1 = .96.
    ("240", "0.04", "1", "0.96"),
    # Double factor: 240 * .001 * 100 * .02 * 2 = .96.
    ("240", "0.02", "2", "0.96"),
    # Signed points: -503.8 * .001 * 100 * .02 * 1 = -1.0076.
    ("-503.8", "0.02", "1", "-1.00760"),
    # p28 half-even after first multiply rounds ...0015 to ...002;
    # .001000000000000000000000000002 * 100 * .02 * 1 = ...004.
    # Rounding only at the end would give .002000000000000000000000000003.
    ("1.0000000000000000000000000015", "0.02", "1",
     "0.002000000000000000000000000004"),
    # p28 half-even after first multiply rounds ...0005 to ...000;
    # .001000000000000000000000000000 * 100 * .02 * 1 = .002.
    # Rounding only at the end would give .002000000000000000000000000001.
    ("1.0000000000000000000000000005", "0.02", "1",
     "0.002000000000000000000000000000"),
)

# lots, sides, factor, expected USD; slippage = 50 points per side.
SLIPPAGE_ROWS = (
    # (50 * .001 * 100 * .02 * 1) * 2 = .20.
    ("0.02", 2, "1", "0.20"),
    # (50 * .001 * 100 * .02 * 2) * 2 = .40.
    ("0.02", 2, "2", "0.40"),
    # (50 * .001 * 100 * .02 * 1) * 0 = 0.
    ("0.02", 0, "1", "0"),
    # (50 * .001 * 100 * .02 * 2) * 0 = 0.
    ("0.02", 0, "2", "0"),
    # (50 * .001 * 100 * .02 * 1) * 1 = .10.
    ("0.02", 1, "1", "0.10"),
    # All nonnegative integer sides are admitted: .10 * 3 = .30.
    ("0.02", 3, "1", "0.30"),
    # Minimum lots: (50 * .001 * 100 * .01 * 1) * 2 = .10.
    ("0.01", 2, "1", "0.10"),
    # Maximum lots: (50 * .001 * 100 * 200 * 1) * 2 = 2000.
    ("200", 2, "1", "2000"),
)

# Commission per lot/side, lots, sides, factor, expected USD.
# Rate 3.5 uses the AC-02 replace(H001_COSTS, ...) synthetic fixture.
COMMISSION_ROWS = (
    # 0 * .02 * 2 * 1 = 0.
    ("0", "0.02", 2, "1", "0"),
    # 0 * .02 * 2 * 2 = 0.
    ("0", "0.02", 2, "2", "0"),
    # 0 * .02 * 0 * 1 = 0.
    ("0", "0.02", 0, "1", "0"),
    # 0 * .02 * 0 * 2 = 0.
    ("0", "0.02", 0, "2", "0"),
    # 3.5 * 1.5 * 2 * 1 = 10.5.
    ("3.5", "1.5", 2, "1", "10.5"),
    # 3.5 * 1.5 * 2 * 2 = 21.
    ("3.5", "1.5", 2, "2", "21.0"),
    # 3.5 * 1.5 * 0 * 1 = 0.
    ("3.5", "1.5", 0, "1", "0"),
    # 3.5 * 1.5 * 0 * 2 = 0.
    ("3.5", "1.5", 0, "2", "0"),
    # 3.5 * 1.5 * 1 * 1 = 5.25.
    ("3.5", "1.5", 1, "1", "5.25"),
    # 3.5 * 1.5 * 3 * 1 = 15.75.
    ("3.5", "1.5", 3, "1", "15.75"),
)

# Fixture ("h001" or "credit"), side, lots, nights, triple nights, factor, USD.
# Credit fixture replaces only long swap points with 100 and its provenance.
SWAP_ROWS = (
    # -( -503.8 * .001 * 100 * .02 * 1 ) * (1 - 0 + 3*0) = 1.0076.
    ("h001", "long", "0.02", 1, 0, "1", "1.00760"),
    # -( -503.8 * .001 * 100 * .02 * 1 ) * (7 - 1 + 3*1) = 9.0684.
    ("h001", "long", "0.02", 7, 1, "1", "9.06840"),
    # -( 0 * .001 * 100 * .02 * 1 ) * (7 - 1 + 3*1) = 0, not negative zero.
    ("h001", "short", "0.02", 7, 1, "1", "0"),
    # -( -503.8 * .001 * 100 * .02 * 2 ) * (1 - 0 + 3*0) = 2.0152.
    ("h001", "long", "0.02", 1, 0, "2", "2.01520"),
    # -( -503.8 * .001 * 100 * .02 * 2 ) * (7 - 1 + 3*1) = 18.1368.
    ("h001", "long", "0.02", 7, 1, "2", "18.13680"),
    # -( 0 * .001 * 100 * .02 * 2 ) * (7 - 1 + 3*1) = 0.
    ("h001", "short", "0.02", 7, 1, "2", "0"),
    # -( 100 * .001 * 100 * .02 * 1 ) * (1 - 0 + 3*0) = -.2 (credit).
    ("credit", "long", "0.02", 1, 0, "1", "-0.20000"),
    # -( 100 * .001 * 100 * .02 * 2 ) * (1 - 0 + 3*0) = -.4 (credit).
    ("credit", "long", "0.02", 1, 0, "2", "-0.40000"),
    # -( -503.8 * .001 * 100 * .02 * 1 ) * (0 - 0 + 3*0) = 0.
    ("h001", "long", "0.02", 0, 0, "1", "0"),
    # -( 100 * .001 * 100 * .02 * 1 ) * (0 - 0 + 3*0) = 0, not negative zero.
    ("credit", "long", "0.02", 0, 0, "1", "0"),
    # All nights triple: 1.0076 * (1 - 1 + 3*1) = 3.0228.
    ("h001", "long", "0.02", 1, 1, "1", "3.02280"),
    # Minimum lots: .5038 * (1 - 0 + 3*0) = .5038.
    ("h001", "long", "0.01", 1, 0, "1", "0.50380"),
    # Maximum lots: 10076 * (1 - 0 + 3*0) = 10076.
    ("h001", "long", "200", 1, 0, "1", "10076"),
)

# side, lots, entry, exit, nights, triple, sides, factor,
# (spread, commission, slippage, swap, total, factor).
ROUND_TRIP_ROWS = (
    # Long uses entry: .48 + 0 + .20 + 1.00760 = 1.68760.
    ("long", "0.02", 240, 240, 1, 0, 2, "1",
     ("0.48", "0", "0.20", "1.00760", "1.68760", "1")),
    # sides 0 removes only commission/slippage: .48 + 0 + 0 + 1.00760 = 1.48760.
    ("long", "0.02", 240, 240, 1, 0, 0, "1",
     ("0.48", "0", "0", "1.00760", "1.48760", "1")),
    # Short uses exit 240, not entry 100: .48 + 0 + .20 + 0 = .68.
    ("short", "0.02", 100, 240, 1, 0, 2, "1",
     ("0.48", "0", "0.20", "0", "0.68", "1")),
    # Stress each charge once: .96 + 0 + .40 + 2.01520 = 3.37520.
    ("long", "0.02", 240, 240, 1, 0, 2, "2",
     ("0.96", "0", "0.40", "2.01520", "3.37520", "2")),
    # Long entry 100 is .20, unused None exit does not select fallback: .20+.20=.40.
    ("long", "0.02", 100, None, 0, 0, 2, "1",
     ("0.20", "0", "0.20", "0", "0.40", "1")),
    # Short exit 100 is .20, unused None entry does not select fallback: .20+.20=.40.
    ("short", "0.02", None, 100, 0, 0, 2, "1",
     ("0.20", "0", "0.20", "0", "0.40", "1")),
    # Selected entry None uses 240: .48 + 0 + .20 + 0 = .68.
    ("long", "0.02", None, 100, 0, 0, 2, "1",
     ("0.48", "0", "0.20", "0", "0.68", "1")),
    # Selected exit None uses 240: .48 + 0 + .20 + 0 = .68.
    ("short", "0.02", 100, None, 0, 0, 2, "1",
     ("0.48", "0", "0.20", "0", "0.68", "1")),
    # Selected zero remains zero: 0 + 0 + .20 + 0 = .20.
    ("long", "0.02", 0, 240, 0, 0, 2, "1",
     ("0", "0", "0.20", "0", "0.20", "1")),
    # Selected zero remains zero on short: 0 + 0 + .20 + 0 = .20.
    ("short", "0.02", 240, 0, 0, 0, 2, "1",
     ("0", "0", "0.20", "0", "0.20", "1")),
    # One side: .48 + 0 + .10 + 1.00760 = 1.58760.
    ("long", "0.02", 240, 100, 1, 0, 1, "1",
     ("0.48", "0", "0.10", "1.00760", "1.58760", "1")),
)

# money, R, expected dimensionless Decimal.
R_ROWS = (
    # 1.68760 / 25 = .067504.
    ("1.68760", "25", "0.067504"),
    # 3.37520 / 25 = .135008.
    ("3.37520", "25", "0.135008"),
    # -1.68760 / 25 = -.067504; signed money is valid.
    ("-1.68760", "25", "-0.067504"),
    # 0 / 25 = 0.
    ("0", "25", "0"),
    # 1 / 3 at precision 28, ROUND_HALF_EVEN.
    ("1", "3", "0.3333333333333333333333333333"),
)

# field, value (Decimal fields are strings), source identifier, as_of, status,
# whether note must contain UNKNOWN. Source prose is not prescribed verbatim.
H001_PROVENANCE_ROWS = (
    ("point", "0.001", "SPIKE-001", "2026-10-21", "measured", False),
    ("contract_size", "100", "SPIKE-001", "2026-10-21", "measured", False),
    ("volume_min", "0.01", "SPIKE-001", "2026-10-21", "measured", False),
    ("volume_step", "0.01", "SPIKE-001", "2026-10-21", "measured", False),
    ("volume_max", "200", "SPIKE-001", "2026-10-21", "measured", False),
    ("spread_fallback_points", 240, "SPIKE-001", "2026-10-21", "measured", False),
    ("commission_per_lot_per_side", "0", "H001", "2026-10-21", "assumed", False),
    ("slippage_points_per_side", 50, "H001", "2026-10-21", "assumed", False),
    ("swap_long_points_per_night", "-503.8", "SPIKE-001", "2026-10-21", "spec", True),
    ("swap_short_points_per_night", "0", "SPIKE-001", "2026-10-21", "spec", True),
    ("triple_swap_weekday", 2, "SPIKE-001", "2026-10-21", "assumed", False),
)

# Written-order p28 addition, using a synthetic replacement of the three fields
# below and matching synthetic provenance. Long, lots 1, exit 0, nights 1,
# triple 0, sides 1, factor 1. Large integer spread has no undocumented cap.
# Spread = 1e29 * .001 * 100 * 1 * 1 = 1e28.
# Commission = 1 * 1 * 1 * 1 = 1; slippage = 10 * .001 * 100 * 1 * 1 * 1 = 1.
# Swap = 0 - (1e29 * .001 * 100 * 1 * 1) * (1 - 0 + 3*0) = -1e28.
# ((1e28 + 1) + 1) + (-1e28) = 0 after rounding each addition to p28.
# Exact addition or cancelling spread with swap first would incorrectly give 2.
ORDERED_TOTAL = {
    "commission": "1",
    "slippage": 10,
    "swap_points": "100000000000000000000000000000",
    "entry": 100000000000000000000000000000,
    "expected": ("10000000000000000000000000000", "1", "1",
                 "-10000000000000000000000000000", "0", "1"),
}
