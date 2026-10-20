"""SPIKE-001: read-only probe of the MT5 terminal (throwaway spike code).

Proves that Python reaches the terminal, records the account and symbol facts, measures what
the timestamps returned by the Python API mean, and surveys history depth. It never sends,
modifies or checks orders. Contract: docs/contracts/SPIKE-001-mt5-connectivity-time.md (v1.1).

Run (approved pins, temporary uv environment):
  uv run --python 3.12 --with MetaTrader5==5.0.6231 --with numpy==2.5.4 --with tzdata==2026.5 \
    python spikes/SPIKE-001/probe.py --out <file outside the repository>

Raw timestamps are kept as integers. "as_if_utc" fields only format the raw number for reading;
they do not assert that the number is UTC (AC-04 decides that).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")
SYMBOL = "XAUUSDm"
DST_CHANGES = {  # latest changes before the spike (2026-10-21)
    "US 2026-03-08": datetime(2026, 3, 8, tzinfo=timezone.utc),
    "EU 2026-03-29": datetime(2026, 3, 29, tzinfo=timezone.utc),
}


@dataclass(frozen=True)
class Authorization:
    server: str
    login_suffix: str
    valid_until: datetime


AUTH = Authorization("Exness-MT5Trial14", "8107", datetime(2026, 10, 28, 23, 59, tzinfo=BANGKOK))


class Refused(Exception):
    """The probe must stop before reading anything else."""


def mask_login(login: object) -> str:
    text = str(login)
    return "*" * max(len(text) - 4, 4) + text[-4:]


def as_if_utc(raw: int) -> str:
    return datetime.fromtimestamp(int(raw), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def check_expiry(now: datetime, auth: Authorization = AUTH) -> None:
    if now > auth.valid_until:
        raise Refused(f"authorization expired at {auth.valid_until.isoformat()}")


def check_account(info: object, demo_mode: int, auth: Authorization = AUTH) -> None:
    """Stop unless the logged-in account is exactly the authorized Demo account."""
    if info is None:
        raise Refused("terminal is not logged in to an account")
    if info.trade_mode != demo_mode:
        raise Refused(f"account trade mode {info.trade_mode} is not Demo")
    if info.server != auth.server:
        raise Refused(f"server {info.server!r} is not the authorized server")
    if not str(info.login).endswith(auth.login_suffix):
        raise Refused(f"account {mask_login(info.login)} is not the authorized account")


# ---- AC-01 ------------------------------------------------------------------------------------
def connection_facts(mt5: object, info: object) -> dict:
    import numpy

    term = mt5.terminal_info()
    version = mt5.version()
    return {
        "package_MetaTrader5": getattr(mt5, "__version__", None),
        "package_numpy": numpy.__version__,
        "terminal_version": list(version) if version else None,
        "terminal_build": getattr(term, "build", None),
        "terminal_company": getattr(term, "company", None),
        "terminal_connected": getattr(term, "connected", None),
        "terminal_maxbars": getattr(term, "maxbars", None),
        "account_login_masked": mask_login(info.login),
        "account_company": info.company,
        "account_server": info.server,
        "account_currency": info.currency,
        "account_trade_mode": info.trade_mode,
        "account_trade_mode_is_demo": info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
        "account_trade_allowed": info.trade_allowed,
        "account_leverage": info.leverage,
        "account_margin_mode": info.margin_mode,
        "account_margin_mode_is_hedging": info.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
    }


# ---- AC-03 ------------------------------------------------------------------------------------
SPEC_FIELDS = (
    "visible", "select", "digits", "point", "trade_tick_size", "trade_tick_value",
    "trade_contract_size", "volume_min", "volume_step", "volume_max", "trade_stops_level",
    "trade_freeze_level", "filling_mode", "trade_mode", "trade_exemode", "spread", "spread_float",
    "swap_mode", "swap_long", "swap_short", "currency_base", "currency_profit", "currency_margin",
    "path", "description",
)


def symbol_spec(mt5: object) -> dict:
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        names = [s.name for s in (mt5.symbols_get("*XAU*") or [])]
        return {"found": False, "last_error": list(mt5.last_error()), "xau_symbols": names}
    spec = {field: getattr(sym, field, None) for field in SPEC_FIELDS}
    spec["found"] = True
    spec["trade_sessions"] = "not exposed by the MetaTrader5 Python API (no SymbolInfoSessionTrade)"
    return spec


# ---- AC-04 ------------------------------------------------------------------------------------
def windows_time_sync() -> dict:
    try:
        r = subprocess.run(["w32tm", "/query", "/status"], capture_output=True, text=True, timeout=15)
        return {"exit": r.returncode, "output": (r.stdout or r.stderr).strip()[:1500]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit": None, "output": f"{type(exc).__name__}: {exc}"}


def classify_offsets(offsets: list[float], tolerance: float = 120.0) -> str:
    if not offsets:
        return "UNKNOWN (no samples)"
    if all(abs(o) <= tolerance for o in offsets):
        return "UTC"
    hours = {round(o / 3600) for o in offsets}
    if len(hours) == 1 and all(abs(o - round(o / 3600) * 3600) <= tolerance for o in offsets):
        h = hours.pop()
        return f"shifted by {h:+d} h from UTC (server-time style)"
    return "UNKNOWN (offsets inconsistent)"


def time_samples(mt5: object, samples: int, interval: float) -> dict:
    rows = []
    for i in range(samples):
        if i:
            time.sleep(interval)
        wall = time.time()
        tick = mt5.symbol_info_tick(SYMBOL)
        bars = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 1)
        row = {"machine_utc": datetime.fromtimestamp(wall, tz=timezone.utc).isoformat(timespec="milliseconds")}
        if tick is None:
            row["tick"] = None
            row["last_error"] = list(mt5.last_error())
        else:
            row.update({
                "tick_time_raw": int(tick.time),
                "tick_time_msc_raw": int(tick.time_msc),
                "tick_time_as_if_utc": as_if_utc(tick.time),
                "offset_time_s": round(tick.time - wall, 3),
                "offset_time_msc_s": round(tick.time_msc / 1000 - wall, 3),
            })
        if bars is not None and len(bars):
            bar_time = int(bars[0]["time"])
            row["last_m1_open_raw"] = bar_time
            row["last_m1_open_as_if_utc"] = as_if_utc(bar_time)
            row["offset_m1_open_vs_minute_s"] = round(bar_time - (wall // 60) * 60, 3)
        rows.append(row)
    offsets = [r["offset_time_msc_s"] for r in rows if "offset_time_msc_s" in r]
    return {"samples": rows, "classification": classify_offsets(offsets), "windows_time_sync": windows_time_sync()}


# ---- AC-05 / AC-06 helpers ----------------------------------------------------------------------
def times_in_range(mt5: object, timeframe: int, start: datetime, end: datetime) -> tuple[list[int], list | None]:
    """Bar open times inside [start, end), plus the terminal error when the call failed.

    None from the terminal is an error, not "no data" (review r1 F3), so it is returned
    separately. When a range holds no data, the terminal still returns the earliest bar it has
    (observed in round 2), so out-of-range bars are dropped."""
    rates = mt5.copy_rates_range(SYMBOL, timeframe, start, end)
    if rates is None:
        return [], list(mt5.last_error())
    lo, hi = int(start.timestamp()), int(end.timestamp())
    return [int(t) for t in rates["time"] if lo <= int(t) < hi], None


def daily_breaks(times) -> list[dict]:
    """Largest intraday gap of 15 min to 3 h per as-if-UTC day: the broker's daily break."""
    best: dict[str, tuple[int, int]] = {}
    for a, b in zip(times[:-1], times[1:]):
        gap = int(b) - int(a)
        if 15 * 60 <= gap <= 3 * 3600:
            day = as_if_utc(a)[:10]
            if day not in best or gap > best[day][1]:
                best[day] = (int(a), gap)
    return [
        {"day": day, "break_after_bar_as_if_utc": as_if_utc(a)[11:16], "gap_minutes": gap // 60}
        for day, (a, gap) in sorted(best.items())
    ]


GAP_BUCKETS = ("gaps_2_to_5m", "gaps_5_to_15m", "gaps_15m_to_3h", "gaps_3h_to_24h", "gaps_24h_plus")


def gap_bucket(gap: int) -> str | None:
    """Every M1 interval above one minute lands in exactly one bucket (review r1 F1)."""
    if gap <= 60:
        return None
    if gap <= 5 * 60:
        return "gaps_2_to_5m"
    if gap < 15 * 60:
        return "gaps_5_to_15m"
    if gap <= 3 * 3600:
        return "gaps_15m_to_3h"
    if gap < 24 * 3600:
        return "gaps_3h_to_24h"
    return "gaps_24h_plus"


def gap_census(times: list[int], prev_last: int | None = None) -> tuple[dict, list[dict]]:
    """Counts per bucket, plus notable gaps (5-15 min and 3-24 h). prev_last is the previous
    chunk's final bar, so a gap that crosses a month boundary is counted once."""
    counts = dict.fromkeys(GAP_BUCKETS, 0)
    notable = []
    seq = ([prev_last] if prev_last is not None else []) + list(times)
    for a, b in zip(seq[:-1], seq[1:]):
        bucket = gap_bucket(int(b) - int(a))
        if bucket:
            counts[bucket] += 1
            if bucket in ("gaps_5_to_15m", "gaps_3h_to_24h"):
                notable.append({"after_as_if_utc": as_if_utc(a), "gap_minutes": round((int(b) - int(a)) / 60, 1)})
    return counts, notable


def week_edges(times) -> list[dict]:
    edges = []
    for a, b in zip(times[:-1], times[1:]):
        if int(b) - int(a) >= 24 * 3600:
            edges.append({"last_bar_before": as_if_utc(a), "first_bar_after": as_if_utc(b),
                          "gap_hours": round((int(b) - int(a)) / 3600, 2)})
    return edges


def dst_study(mt5: object) -> dict:
    """M1 is the contract's timeframe. When the terminal's bar limit hides M1 that far back,
    M5 is added and marked as supplementary, so the M1 gap is visible rather than replaced."""
    out = {}
    for label, change in DST_CHANGES.items():
        entry = {}
        for tf_name in ("TIMEFRAME_M1", "TIMEFRAME_M5"):
            times, error = times_in_range(mt5, getattr(mt5, tf_name), change - timedelta(days=10),
                                          change + timedelta(days=10))
            entry[tf_name[10:]] = {
                "bars": len(times),
                "first_as_if_utc": as_if_utc(times[0]) if times else None,
                "call_error": error,
                "daily_breaks": daily_breaks(times),
                "week_edges": week_edges(times),
            }
            if tf_name == "TIMEFRAME_M1" and len(times) >= 10000:
                break  # enough M1; M5 not needed
        if "M5" in entry:
            entry["M5"]["note"] = "supplementary: M1 for this window was not available to the API"
        out[label] = entry
    return out


def history_depth(mt5: object, now: datetime) -> dict:
    out: dict = {}
    term = mt5.terminal_info()
    maxbars = int(getattr(term, "maxbars", None) or 100000)
    out["terminal_maxbars"] = maxbars
    count = min(maxbars, 5_000_000) - 1  # asking for exactly maxbars returns "Invalid params"
    pos = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, count)
    out["m1_by_position"] = {
        "requested": count,
        "returned": 0 if pos is None else len(pos),
        "earliest_as_if_utc": as_if_utc(pos[0]["time"]) if pos is not None and len(pos) else None,
        "last_error": list(mt5.last_error()),
    }
    out["earliest_by_position"] = {}
    for tf_name in ("TIMEFRAME_M5", "TIMEFRAME_H1", "TIMEFRAME_D1"):
        bars = mt5.copy_rates_from_pos(SYMBOL, getattr(mt5, tf_name), 0, count)
        out["earliest_by_position"][tf_name[10:]] = {
            "returned": 0 if bars is None else len(bars),
            "earliest_as_if_utc": as_if_utc(bars[0]["time"]) if bars is not None and len(bars) else None,
        }
    # Month-sized requests stay below the bar limit per call; whole-year requests did not.
    years: dict[int, dict] = {}
    first_month = None
    other_gaps: list[dict] = []
    call_errors: list[dict] = []
    prev_last: int | None = None
    y, m = 2005, 1
    while (y, m) <= (now.year, now.month):
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        nxt = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1, tzinfo=timezone.utc)
        times, error = times_in_range(mt5, mt5.TIMEFRAME_M1, start, min(nxt, now))
        if error is not None:
            call_errors.append({"month": f"{y}-{m:02d}", "error": error})
        row = years.setdefault(y, {"year": y, "m1_bars": 0, "months_with_data": 0, **dict.fromkeys(GAP_BUCKETS, 0)})
        if error is not None:
            prev_last = None  # continuity across a failed month is unknown
        elif times:
            first_month = first_month or f"{y}-{m:02d} (first bar {as_if_utc(times[0])})"
            row["m1_bars"] += len(times)
            row["months_with_data"] += 1
            counts, notable = gap_census(times, prev_last)
            for bucket, n in counts.items():
                row[bucket] += n
            other_gaps.extend(notable)
            prev_last = times[-1]
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    out["m1_by_month_range"] = [r for r in years.values() if r["m1_bars"]]
    out["m1_first_month_with_data"] = first_month
    out["m1_range_call_errors"] = call_errors  # failed calls: unknown, not "no data"
    out["m1_largest_other_gaps"] = sorted(other_gaps, key=lambda g: -g["gap_minutes"])[:20]
    out["ticks"] = tick_depth(mt5, now)
    return out


TICK_SEARCH_FROM = datetime(2005, 1, 1, tzinfo=timezone.utc)


def tick_depth(mt5: object, now: datetime) -> dict:
    """First tick the terminal returns at or after 2005-01-01, checked against the day before it.

    Review r1 F2: one mid-month hour cannot locate the first tick day, so the month search is
    kept only as a labelled supplement and no longer starts from the M1-derived year."""
    out: dict = {}
    first = mt5.copy_ticks_from(SYMBOL, TICK_SEARCH_FROM, 1, mt5.COPY_TICKS_ALL)
    if first is None:
        out["first_tick"] = "UNKNOWN"
        out["first_tick_call_error"] = list(mt5.last_error())
    elif not len(first):
        out["first_tick"] = None
    else:
        t = int(first["time"][0])
        out["first_tick_as_if_utc"] = as_if_utc(t)
        before = mt5.copy_ticks_range(SYMBOL, datetime.fromtimestamp(t - 86400, tz=timezone.utc),
                                      datetime.fromtimestamp(t, tz=timezone.utc), mt5.COPY_TICKS_ALL)
        out["ticks_in_day_before_first"] = None if before is None else len(before)  # expected 0
    out["month_sample_search"] = month_sample_search(mt5, TICK_SEARCH_FROM.year, now)
    return out


def month_sample_search(mt5: object, from_year: int, now: datetime) -> dict:
    """Supplementary: binary search over months on one mid-month weekday hour."""
    months = []
    y, m = from_year, 1
    while (y, m) <= (now.year, now.month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    def has_ticks(ym: tuple[int, int]) -> int | None:
        day = datetime(ym[0], ym[1], 15, 12, tzinfo=timezone.utc)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        ticks = mt5.copy_ticks_range(SYMBOL, day, day + timedelta(hours=1), mt5.COPY_TICKS_ALL)
        return None if ticks is None else len(ticks)  # None: the call failed (F3)

    lo, hi, probes = 0, len(months) - 1, []
    latest = has_ticks(months[-1]) if months else 0
    if latest is None:
        return {"first_month_with_ticks": "UNKNOWN", "call_error": list(mt5.last_error())}
    if not latest:
        return {"first_month_with_ticks": None, "note": "no ticks found even in the current month"}
    while lo < hi:
        mid = (lo + hi) // 2
        n = has_ticks(months[mid])
        if n is None:
            return {"first_month_with_ticks": "UNKNOWN", "probes": probes,
                    "call_error": {"month": f"{months[mid][0]}-{months[mid][1]:02d}", "error": list(mt5.last_error())}}
        probes.append({"month": f"{months[mid][0]}-{months[mid][1]:02d}", "ticks_in_hour": n})
        if n:
            hi = mid
        else:
            lo = mid + 1
    first = months[lo]
    return {"first_month_with_ticks": f"{first[0]}-{first[1]:02d}", "probes": probes,
            "method": "supplementary binary search on one mid-month weekday hour; assumes contiguous "
                      "history and cannot locate the first day"}


# ---- Orchestration -----------------------------------------------------------------------------
def run(mt5: object, now: datetime, samples: int = 3, interval: float = 20.0, history: bool = True) -> tuple[int, dict]:
    report: dict = {"probe_started_bangkok": now.isoformat(timespec="seconds"), "symbol": SYMBOL}
    try:
        check_expiry(now)
    except Refused as exc:
        report["refused"] = str(exc)
        return 2, report
    if not mt5.initialize():
        report["refused"] = f"initialize failed: {mt5.last_error()}"
        return 3, report
    try:
        info = mt5.account_info()
        try:
            check_account(info, mt5.ACCOUNT_TRADE_MODE_DEMO)
        except Refused as exc:
            report["refused"] = str(exc)
            return 2, report
        report["ac01_connection"] = connection_facts(mt5, info)
        report["ac03_symbol_spec"] = symbol_spec(mt5)
        report["ac04_time"] = time_samples(mt5, samples, interval)
        if history:
            report["ac05_dst"] = dst_study(mt5)
            report["ac06_history"] = history_depth(mt5, datetime.now(timezone.utc))
        return 0, report
    finally:
        mt5.shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="JSON result path, outside the repository")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--interval", type=float, default=20.0)
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args(argv)
    import MetaTrader5 as mt5

    code, report = run(mt5, datetime.now(BANGKOK), args.samples, args.interval, not args.no_history)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({"exit": code, "refused": report.get("refused"), "out": args.out}))
    return code


if __name__ == "__main__":
    sys.exit(main())
