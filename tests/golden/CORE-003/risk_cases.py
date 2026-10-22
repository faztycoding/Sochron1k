"""CORE-003 v1.2 hand-computed literal oracles; no production risk imports.

Sizing rows reset H001_COSTS/H001_RISK for every row. Rate = .0025,
contract_size = 100, step = .01, min = .01, max = 200 unless stated.
Money/display strings are compared numerically as Decimal; decisions are exact.
"""

# Label, equity, distance, cost/lot, model overrides,
# (lots, risk_money, risk_per_lot, actual_risk, reason).
SIZE_ROWS = (
    # R=25; per=1200; raw=1/48; floor=.02; cap=200; actual=.02*1200=24.
    ("h001", "10000", "12.00", "0", {},
     ("0.02", "25", "1200", "24", "ok")),
    # R=25; per=1200+10=1210; raw=5/242; floor=.02; cap=200; actual=24.2.
    ("cost_budget", "10000", "12.00", "10", {},
     ("0.02", "25", "1210", "24.2", "ok")),
    # R=1/4; per=1200; raw=1/4800; floor=0; cap=200; 0<.01; actual=0.
    ("below_min", "100", "12.00", "0", {},
     ("0", "0.25", "1200", "0", "below_min_volume")),
    # R=250000; per=10; raw=25000/1; floor=25000; cap=200; actual=2000.
    ("capped", "100000000", "0.10", "0", {},
     ("200", "250000", "10", "2000", "capped_at_volume_max")),
    # R=24; per=1200; raw=1/50 exactly; floor=.02; cap=200; actual=24.
    ("exact_step", "9600", "12.00", "0", {},
     ("0.02", "24", "1200", "24", "ok")),
    # Exact R=23.99999999999999999999999999975, display=24.
    # per=1200; raw=95999999999999999999999999999/4800000000000000000000000000000;
    # floor=.01 (not .02); cap=200; actual=12.
    ("numerator_edge", "9599.9999999999999999999999999", "12", "0", {},
     ("0.01", "24", "1200", "12", "ok")),
    # R=2; exact per=100.00000000000000000000000001, display=100;
    # raw=200000000000000000000000000/10000000000000000000000000001;
    # floor=.01; cap=200; exact actual=1.0000000000000000000000000001 -> display1.
    ("denominator_edge", "800", "1.0000000000000000000000000001", "0", {},
     ("0.01", "2", "100", "1", "ok")),
    # R=25; per=100; raw=1/4; floor=.25; cap=floor(.025/.01)*.01=.02; actual=2.
    ("off_grid_cap", "10000", "1.00", "0", {"volume_max": "0.025"},
     ("0.02", "25", "100", "2", "capped_at_volume_max")),
    # R=25; per=100; raw=1/4; floor=.25; cap=floor(.029/.01)*.01=.02<min.026.
    # No valid grid point: lots=0, actual=0; below-min takes precedence over cap.
    ("no_grid", "10000", "1.00", "0", {"volume_min": "0.026", "volume_max": "0.029"},
     ("0", "25", "100", "0", "below_min_volume")),
    # R=24; per=1210; raw=12/605; floor=.01; cap=200; actual=12.1.
    ("budget_changes_step", "9600", "12.00", "10", {},
     ("0.01", "24", "1210", "12.1", "ok")),
    # R=25; per=2000; raw=1/80; floor=.01; cap=200; actual=20.
    ("gate_distance20", "10000", "20.00", "0", {},
     ("0.01", "25", "2000", "20", "ok")),
    # R=49/2; per=1200; raw=49/2400; floor=.02; cap=200; actual=24.
    ("gate_equity9800", "9800", "12.00", "0", {},
     ("0.02", "24.5", "1200", "24", "ok")),
    # R=25; exact per=100.00000000000000000000000005, display100.
    # raw=500000000000000000000000000/2000000000000000000000000001;
    # floor=.24; cap=200; exact actual=24.000000000000000000000000012 -> display ...01.
    # Multiplying the rounded per-lot display would incorrectly give 24.
    ("round_actual_once", "10000", "1.0000000000000000000000000005", "0", {},
     ("0.24", "25", "100", "24.00000000000000000000000001", "ok")),
)

# Fresh baseline, current equity, expected daily flag, expected experiment flag.
THRESHOLD_ROWS = (
    # Loss74.99 < daily75 < experiment200.
    ("10000", "9925.01", False, False),
    # Loss75 = daily75, < experiment200.
    ("10000", "9925", True, False),
    # Loss75.01 > daily75, < experiment200.
    ("10000", "9924.99", True, False),
    # Loss199.99 > daily75, < experiment200.
    ("10000", "9800.01", True, False),
    # Loss200 >= daily75 and = experiment200.
    ("10000", "9800", True, True),
    # Loss200.01 exceeds both75 and200.
    ("10000", "9799.99", True, True),
    # Let B=10000+1E-26. Equity=B*(1-.0075)+1E-30: daily loss < .0075*B.
    ("10000.00000000000000000000000001", "9925.000000000000000000000000009926",
     False, False),
    # Equity=B*(1-.0075) exactly: daily equality halts; experiment threshold not reached.
    ("10000.00000000000000000000000001", "9925.000000000000000000000000009925",
     True, False),
    # Equity=B*(1-.02)+1E-30: experiment loss just below .02*B; daily already reached.
    ("10000.00000000000000000000000001", "9800.000000000000000000000000009801",
     True, False),
    # Equity=B*(1-.02) exactly: experiment equality halts.
    ("10000.00000000000000000000000001", "9800.0000000000000000000000000098",
     True, True),
)

# Operation, equity, calendar day number, expected day baseline, experiment baseline, flags.
DAILY_SEQUENCE = (
    # 10000-9925.01=74.99 < .0075*10000=75; experiment loss<200.
    ("update", "9925.01", 22, "10000", "10000", False, False),
    # 10000-9925=75 meets daily equality only.
    ("update", "9925", 22, "10000", "10000", True, False),
    # New day: loss0 < .0075*9925=74.4375; experiment loss75<200.
    ("update", "9925", 23, "9925", "10000", False, False),
)
RESTART_SEQUENCE = (
    # Loss200 >= daily75 and experiment200.
    ("update", "9800", 22, "10000", "10000", True, True),
    # Daily retains10000/true; experiment rebase9800 gives new budget196.
    ("restart", "9800", 22, "10000", "9800", True, False),
    # New-day daily loss0<73.5; experiment loss0<196.
    ("update", "9800", 23, "9800", "9800", False, False),
    # New experiment loss195.99<196; daily loss195.99>=73.5.
    ("update", "9604.01", 23, "9800", "9800", True, False),
    # New experiment loss196=196 (not old budget200).
    ("update", "9604", 23, "9800", "9800", True, True),
)

# Field, literal value (numeric ratios are strings), source, date, status, note.
H001_PROVENANCE_ROWS = (
    ("risk_per_trade", "0.0025",
     "SPEC.md section 6 Risk policy [A]; docs/hypotheses/H001-m15-momentum-breakout.md section 3",
     "2026-10-21", "assumed", "Q-04 open"),
    ("daily_loss_limit", "0.0075", "SPEC.md section 6 Risk policy [A]",
     "2026-10-21", "assumed",
     "Q-04 open; baseline is the first equity supplied for the Thai day"),
    ("experiment_loss_limit", "0.02", "SPEC.md section 6 Risk policy [A]",
     "2026-10-21", "assumed", "Q-04 open"),
    ("max_open_exposures", 1,
     "SPEC.md section 6 Risk policy [A]; docs/hypotheses/H001-m15-momentum-breakout.md section 3",
     "2026-10-21", "assumed", "one position or pending order at a time"),
    ("halt_clearers", ("owner",), "SPEC.md section 9 Q-04",
     "2026-10-22", "unknown", "safe default: the owner only; no agent may clear"),
)

# Equity, exact R, accepted. Per=1200, raw=R/1200, floor0, cap200, actual0 for tiny R.
RANGE_ROWS = (
    # 4E-999998*.0025=1E-1000000: exact subnormal below Emin, above Etiny.
    ("4E-999998", "1E-1000000", True),
    # 4E-1000024*.0025=1E-1000026: exact Etiny, Subnormal alone is permitted.
    ("4E-1000024", "1E-1000026", True),
    # 4E-1000025*.0025=1E-1000027: nonzero rounds to zero at Etiny -> Underflow.
    ("4E-1000025", "1E-1000027", False),
    # 4.4E-1000024*.0025=1.1E-1000026: inexact subnormal rounds to1E-1000026.
    ("4.4E-1000024", "1.1E-1000026", False),
    # 4E1000002*.0025=1E1000000: Overflow; raw=1E1000000/1200, floor>cap200.
    ("4E1000002", "1E1000000", False),
)
