"""CORE-001 fixed oracles, prepared independently with Python 3.12 datetime/zoneinfo.

tzdata 2026.5; no expected result is calculated by sochron.timebase.
The preparation script lives outside the patch; its method/hash is in the handoff.
Bar and offset rows use the integer arithmetic shown beside each literal row.
"""

# raw seconds, milliseconds, exact UTC result: remainder 35 means 35,000 microseconds.
SPIKE_TICK = (1792525992, 1792525992035, "2026-10-20T19:53:12.035000+00:00")
# Same second plus 999ms; dropping the fraction must never round up to second 13.
LAST_MILLISECOND = (1792525992, 1792525992999, "2026-10-20T19:53:12.999000+00:00")

# Explicit fixed raw values across 2000..2099, including both accepted endpoints.
# The separate scratch script converted the stated UTC instants to Unix seconds.
ROUND_TRIP_ROWS = (
    # 2000-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 946684800.
    (946684800, "2000-01-01T00:00:00+00:00"),
    # 2000-01-01T00:00:01+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 946684801.
    (946684801, "2000-01-01T00:00:01+00:00"),
    # 2000-02-29T12:34:56+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 951827696.
    (951827696, "2000-02-29T12:34:56+00:00"),
    # 2005-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 1104537600.
    (1104537600, "2005-01-01T00:00:00+00:00"),
    # 2010-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 1262304000.
    (1262304000, "2010-01-01T00:00:00+00:00"),
    # 2015-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 1420070400.
    (1420070400, "2015-01-01T00:00:00+00:00"),
    # 2020-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 1577836800.
    (1577836800, "2020-01-01T00:00:00+00:00"),
    # 2025-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 1735689600.
    (1735689600, "2025-01-01T00:00:00+00:00"),
    # 2030-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 1893456000.
    (1893456000, "2030-01-01T00:00:00+00:00"),
    # 2035-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2051222400.
    (2051222400, "2035-01-01T00:00:00+00:00"),
    # 2040-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2208988800.
    (2208988800, "2040-01-01T00:00:00+00:00"),
    # 2045-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2366841600.
    (2366841600, "2045-01-01T00:00:00+00:00"),
    # 2050-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2524608000.
    (2524608000, "2050-01-01T00:00:00+00:00"),
    # 2055-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2682374400.
    (2682374400, "2055-01-01T00:00:00+00:00"),
    # 2060-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2840140800.
    (2840140800, "2060-01-01T00:00:00+00:00"),
    # 2065-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 2997993600.
    (2997993600, "2065-01-01T00:00:00+00:00"),
    # 2070-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 3155760000.
    (3155760000, "2070-01-01T00:00:00+00:00"),
    # 2075-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 3313526400.
    (3313526400, "2075-01-01T00:00:00+00:00"),
    # 2080-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 3471292800.
    (3471292800, "2080-01-01T00:00:00+00:00"),
    # 2085-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 3629145600.
    (3629145600, "2085-01-01T00:00:00+00:00"),
    # 2090-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 3786912000.
    (3786912000, "2090-01-01T00:00:00+00:00"),
    # 2095-01-01T00:00:00+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 3944678400.
    (3944678400, "2095-01-01T00:00:00+00:00"),
    # 2099-12-31T23:59:59+00:00: elapsed seconds from 1970-01-01T00:00:00Z = 4102444799.
    (4102444799, "2099-12-31T23:59:59+00:00"),
)

# offset_seconds, expected UTC for the same SPIKE_TICK (explicit synthetic rules).
SHIFTED_TICK_ROWS = (
    # Subtract +7200 seconds: 19:53:12.035 - 02:00 = 17:53:12.035 UTC.
    (7200, "2026-10-20T17:53:12.035000+00:00"),
    # Subtract -7200 seconds: 19:53:12.035 + 02:00 = 21:53:12.035 UTC.
    (-7200, "2026-10-20T21:53:12.035000+00:00"),
)

# UTC instant, New York wall time with offset, abbreviation, inside window.
# March 8 has no 02:59:59 local instant: clocks jump from 01:59:59 to 03:00:00.
# The nonexistent minute is not fabricated; March 7 and 9 test 02:59:59.
NY_WINDOW_ROWS = (
    # 2026-03-07T07:59:59+00:00 UTC -> 2026-03-07 02:59:59 EST; outside.
    ("2026-03-07T07:59:59+00:00", "2026-03-07T02:59:59-05:00", "EST", False),
    # 2026-03-07T08:00:00+00:00 UTC -> 2026-03-07 03:00:00 EST; inside.
    ("2026-03-07T08:00:00+00:00", "2026-03-07T03:00:00-05:00", "EST", True),
    # 2026-03-07T20:59:59+00:00 UTC -> 2026-03-07 15:59:59 EST; inside.
    ("2026-03-07T20:59:59+00:00", "2026-03-07T15:59:59-05:00", "EST", True),
    # 2026-03-07T21:00:00+00:00 UTC -> 2026-03-07 16:00:00 EST; outside.
    ("2026-03-07T21:00:00+00:00", "2026-03-07T16:00:00-05:00", "EST", False),
    # 2026-03-08T06:59:59+00:00 UTC -> 2026-03-08 01:59:59 EST; outside.
    ("2026-03-08T06:59:59+00:00", "2026-03-08T01:59:59-05:00", "EST", False),
    # 2026-03-08T07:00:00+00:00 UTC -> 2026-03-08 03:00:00 EDT; inside.
    ("2026-03-08T07:00:00+00:00", "2026-03-08T03:00:00-04:00", "EDT", True),
    # 2026-03-08T19:59:59+00:00 UTC -> 2026-03-08 15:59:59 EDT; inside.
    ("2026-03-08T19:59:59+00:00", "2026-03-08T15:59:59-04:00", "EDT", True),
    # 2026-03-08T20:00:00+00:00 UTC -> 2026-03-08 16:00:00 EDT; outside.
    ("2026-03-08T20:00:00+00:00", "2026-03-08T16:00:00-04:00", "EDT", False),
    # 2026-03-09T06:59:59+00:00 UTC -> 2026-03-09 02:59:59 EDT; outside.
    ("2026-03-09T06:59:59+00:00", "2026-03-09T02:59:59-04:00", "EDT", False),
    # 2026-03-09T07:00:00+00:00 UTC -> 2026-03-09 03:00:00 EDT; inside.
    ("2026-03-09T07:00:00+00:00", "2026-03-09T03:00:00-04:00", "EDT", True),
    # 2026-03-09T19:59:59+00:00 UTC -> 2026-03-09 15:59:59 EDT; inside.
    ("2026-03-09T19:59:59+00:00", "2026-03-09T15:59:59-04:00", "EDT", True),
    # 2026-03-09T20:00:00+00:00 UTC -> 2026-03-09 16:00:00 EDT; outside.
    ("2026-03-09T20:00:00+00:00", "2026-03-09T16:00:00-04:00", "EDT", False),
    # 2026-10-31T06:59:59+00:00 UTC -> 2026-10-31 02:59:59 EDT; outside.
    ("2026-10-31T06:59:59+00:00", "2026-10-31T02:59:59-04:00", "EDT", False),
    # 2026-10-31T07:00:00+00:00 UTC -> 2026-10-31 03:00:00 EDT; inside.
    ("2026-10-31T07:00:00+00:00", "2026-10-31T03:00:00-04:00", "EDT", True),
    # 2026-10-31T19:59:59+00:00 UTC -> 2026-10-31 15:59:59 EDT; inside.
    ("2026-10-31T19:59:59+00:00", "2026-10-31T15:59:59-04:00", "EDT", True),
    # 2026-10-31T20:00:00+00:00 UTC -> 2026-10-31 16:00:00 EDT; outside.
    ("2026-10-31T20:00:00+00:00", "2026-10-31T16:00:00-04:00", "EDT", False),
    # 2026-11-01T07:59:59+00:00 UTC -> 2026-11-01 02:59:59 EST; outside.
    ("2026-11-01T07:59:59+00:00", "2026-11-01T02:59:59-05:00", "EST", False),
    # 2026-11-01T08:00:00+00:00 UTC -> 2026-11-01 03:00:00 EST; inside.
    ("2026-11-01T08:00:00+00:00", "2026-11-01T03:00:00-05:00", "EST", True),
    # 2026-11-01T20:59:59+00:00 UTC -> 2026-11-01 15:59:59 EST; inside.
    ("2026-11-01T20:59:59+00:00", "2026-11-01T15:59:59-05:00", "EST", True),
    # 2026-11-01T21:00:00+00:00 UTC -> 2026-11-01 16:00:00 EST; outside.
    ("2026-11-01T21:00:00+00:00", "2026-11-01T16:00:00-05:00", "EST", False),
    # 2026-11-02T07:59:59+00:00 UTC -> 2026-11-02 02:59:59 EST; outside.
    ("2026-11-02T07:59:59+00:00", "2026-11-02T02:59:59-05:00", "EST", False),
    # 2026-11-02T08:00:00+00:00 UTC -> 2026-11-02 03:00:00 EST; inside.
    ("2026-11-02T08:00:00+00:00", "2026-11-02T03:00:00-05:00", "EST", True),
    # 2026-11-02T20:59:59+00:00 UTC -> 2026-11-02 15:59:59 EST; inside.
    ("2026-11-02T20:59:59+00:00", "2026-11-02T15:59:59-05:00", "EST", True),
    # 2026-11-02T21:00:00+00:00 UTC -> 2026-11-02 16:00:00 EST; outside.
    ("2026-11-02T21:00:00+00:00", "2026-11-02T16:00:00-05:00", "EST", False),
    # 2026-03-07T07:30:00+00:00 UTC -> 2026-03-07 02:30:00 EST; outside.
    ("2026-03-07T07:30:00+00:00", "2026-03-07T02:30:00-05:00", "EST", False),
    # 2026-03-08T07:30:00+00:00 UTC -> 2026-03-08 03:30:00 EDT; inside.
    ("2026-03-08T07:30:00+00:00", "2026-03-08T03:30:00-04:00", "EDT", True),
    # 2026-11-01T05:30:00+00:00 UTC -> 2026-11-01 01:30:00 EDT; outside.
    ("2026-11-01T05:30:00+00:00", "2026-11-01T01:30:00-04:00", "EDT", False),
    # 2026-11-01T05:59:59+00:00 UTC -> 2026-11-01 01:59:59 EDT; outside.
    ("2026-11-01T05:59:59+00:00", "2026-11-01T01:59:59-04:00", "EDT", False),
    # 2026-11-01T06:00:00+00:00 UTC -> 2026-11-01 01:00:00 EST; outside.
    ("2026-11-01T06:00:00+00:00", "2026-11-01T01:00:00-05:00", "EST", False),
    # 2026-11-01T06:30:00+00:00 UTC -> 2026-11-01 01:30:00 EST; outside.
    ("2026-11-01T06:30:00+00:00", "2026-11-01T01:30:00-05:00", "EST", False),
)

# UTC instant, Bangkok wall time, Bangkok calendar date: add seven hours.
BANGKOK_ROWS = (
    # 2026-10-20 16:59:59 UTC + 07:00 = Oct 20 23:59:59; still Oct 20.
    ("2026-10-20T16:59:59+00:00", "2026-10-20T23:59:59+07:00", "2026-10-20"),
    # 2026-10-20 17:00:00 UTC + 07:00 = Oct 21 00:00:00; now Oct 21.
    ("2026-10-20T17:00:00+00:00", "2026-10-21T00:00:00+07:00", "2026-10-21"),
)

# raw M1 open, expected M15 raw open. Fifteen consecutive M1 opens, not one M15 bar.
M1_TO_M15_ROWS = (
    # 1792525980 + 0*60 = 1792525980 (19:53:00 UTC); subtract 480s to M15 open.
    (1792525980, 1792525500),
    # 1792525980 + 1*60 = 1792526040 (19:54:00 UTC); subtract 540s to M15 open.
    (1792526040, 1792525500),
    # 1792525980 + 2*60 = 1792526100 (19:55:00 UTC); subtract 600s to M15 open.
    (1792526100, 1792525500),
    # 1792525980 + 3*60 = 1792526160 (19:56:00 UTC); subtract 660s to M15 open.
    (1792526160, 1792525500),
    # 1792525980 + 4*60 = 1792526220 (19:57:00 UTC); subtract 720s to M15 open.
    (1792526220, 1792525500),
    # 1792525980 + 5*60 = 1792526280 (19:58:00 UTC); subtract 780s to M15 open.
    (1792526280, 1792525500),
    # 1792525980 + 6*60 = 1792526340 (19:59:00 UTC); subtract 840s to M15 open.
    (1792526340, 1792525500),
    # 1792525980 + 7*60 = 1792526400 (20:00:00 UTC); subtract 0s to M15 open.
    (1792526400, 1792526400),
    # 1792525980 + 8*60 = 1792526460 (20:01:00 UTC); subtract 60s to M15 open.
    (1792526460, 1792526400),
    # 1792525980 + 9*60 = 1792526520 (20:02:00 UTC); subtract 120s to M15 open.
    (1792526520, 1792526400),
    # 1792525980 + 10*60 = 1792526580 (20:03:00 UTC); subtract 180s to M15 open.
    (1792526580, 1792526400),
    # 1792525980 + 11*60 = 1792526640 (20:04:00 UTC); subtract 240s to M15 open.
    (1792526640, 1792526400),
    # 1792525980 + 12*60 = 1792526700 (20:05:00 UTC); subtract 300s to M15 open.
    (1792526700, 1792526400),
    # 1792525980 + 13*60 = 1792526760 (20:06:00 UTC); subtract 360s to M15 open.
    (1792526760, 1792526400),
    # 1792525980 + 14*60 = 1792526820 (20:07:00 UTC); subtract 420s to M15 open.
    (1792526820, 1792526400),
)

EXTRA_BAR_ROWS = (
    # 19:45:00 UTC is exactly aligned: remainder 0 seconds.
    (1792525500, 1792525500),
    # SPIKE tick 19:53:12 UTC: subtract 492 seconds to 19:45:00.
    (1792525992, 1792525500),
    # 19:59:59 UTC: subtract 899 seconds to 19:45:00.
    (1792526399, 1792525500),
    # 20:00:00 UTC is exactly aligned: remainder 0 seconds; starts the next bar.
    (1792526400, 1792526400),
)

# Nonzero synthetic offset 61s prevents a UTC-aligned implementation ignoring the rule.
# 1792525992 - 61 = 1792525931; floor to 900s = 1792525500; add 61 = 1792525561.
SHIFTED_BAR = (1792525992, 15, 61, 1792525561)

# Every supported timeframe, for tick 1792525992 (19:53:12 UTC).
# Hand-calculated local clock floors; UTC midnight is raw 1792454400.
TIMEFRAME_ROWS = (
    # M1 floor 19:53:00: midnight + 71580 seconds.
    (1, 1792525980),
    # M2 floor 19:52:00: midnight + 71520 seconds.
    (2, 1792525920),
    # M3 floor 19:51:00: midnight + 71460 seconds.
    (3, 1792525860),
    # M4 floor 19:52:00: midnight + 71520 seconds.
    (4, 1792525920),
    # M5 floor 19:50:00: midnight + 71400 seconds.
    (5, 1792525800),
    # M6 floor 19:48:00: midnight + 71280 seconds.
    (6, 1792525680),
    # M10 floor 19:50:00: midnight + 71400 seconds.
    (10, 1792525800),
    # M12 floor 19:48:00: midnight + 71280 seconds.
    (12, 1792525680),
    # M15 floor 19:45:00: midnight + 71100 seconds.
    (15, 1792525500),
    # M20 floor 19:40:00: midnight + 70800 seconds.
    (20, 1792525200),
    # M30 floor 19:30:00: midnight + 70200 seconds.
    (30, 1792524600),
    # H1 floor 19:00:00: midnight + 68400 seconds.
    (60, 1792522800),
    # H2 floor 18:00:00: midnight + 64800 seconds.
    (120, 1792519200),
    # H3 floor 18:00:00: midnight + 64800 seconds.
    (180, 1792519200),
    # H4 floor 16:00:00: midnight + 57600 seconds.
    (240, 1792512000),
    # H6 floor 18:00:00: midnight + 64800 seconds.
    (360, 1792519200),
    # H8 floor 16:00:00: midnight + 57600 seconds.
    (480, 1792512000),
    # H12 floor 12:00:00: midnight + 43200 seconds.
    (720, 1792497600),
    # D1 floor 00:00:00: midnight + 0 seconds.
    (1440, 1792454400),
)

# offsets, tolerance, kind, shifted hours (None = no specified hour), samples.
# Only shifted requires a particular hours value in the contract.
OFFSET_ROWS = (
    # Five values all satisfy abs(x) <= 120, including equality at -120 and +120.
    ((-120.0, -3.8, 0.0, 0.865, 120.0), 120.0, "ok", None, 5),
    # 7080, 7200, 7320 differ from 2*3600 by -120, 0, +120; all within tolerance.
    ((7080.0, 7200.0, 7320.0), 120.0, "shifted", 2, 3),
    # 0.5 and 30 are near zero, but 7200 is near +2h; no common whole hour.
    ((0.5, 7200.0, 30.0), 120.0, "unknown", None, 3),
    # No observations: unknown with zero samples; cannot establish an offset.
    ((), 120.0, "unknown", None, 0),
    # 1800 is 1800s from both 0h and +1h, greater than tolerance 120.
    ((1800.0,), 120.0, "unknown", None, 1),
)

# Additional specified formula edges: negative hour, mixed hours, caller tolerance.
OFFSET_EDGE_ROWS = (
    # -7320, -7200, -7080 are -120, 0, +120 from -2*3600.
    ((-7320.0, -7200.0, -7080.0), 120.0, "shifted", -2, 3),
    # Both are whole hours but -2 and +2 are different; no common hour.
    ((-7200.0, 7200.0), 120.0, "unknown", None, 2),
    # abs(120.001) > 120 and not within 120 of a nonzero whole hour.
    ((120.001,), 120.0, "unknown", None, 1),
    # abs(-5) = abs(+5) = custom tolerance 5; equality remains ok.
    ((-5.0, 5.0), 5.0, "ok", None, 2),
    # 6 > custom tolerance 5, far from any nonzero whole hour.
    ((6.0,), 5.0, "unknown", None, 1),
)
