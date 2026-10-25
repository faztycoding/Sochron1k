"""SPIKE-002: read-only re-measure on the VPS (throwaway spike code).

Contract: docs/contracts/SPIKE-002-vps-remeasure.md (v1.2). Packages: D-022, SPIKE-002 only.
The probe never sends, modifies or checks orders, and reads only the calls in ALLOWED_CALLS.
Every Authorization value comes from the command line; nothing is built in.

Run on the VPS from the repository root (temporary uv environment, D-022), one line:
  uv run --no-project --python 3.12.15 --with MetaTrader5==5.0.6231 --with numpy==2.5.4
    --with tzdata==2026.5 python spikes/SPIKE-002/probe.py --server <server>
    --login-suffix <last 4 digits> --valid-until <ISO 8601 with offset> --clock-sync "<w32tm lines>"

Success: one JSON object on stdout, exit 0. Refusal: one line on stderr, exit 2 for arguments,
authorization or account (checked before any symbol or history call), exit 3 when the terminal
cannot be used (initialize failed, not logged in, MetaTrader5 missing).

Post-cutoff rule (contract Invariants): the M1 search never asks for a range at or after
CUTOFF_UTC, no tick timestamp, price or count is reported, and the only post-cutoff value is
first_tick_utc at day precision, which the owner accepted with the contract.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from importlib import metadata
from typing import Callable

SYMBOL = "XAUUSDm"
UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
CUTOFF_UTC = datetime(2025, 1, 1, tzinfo=UTC)  # research.model.HOLDOUT_CUTOFF_UTC
M1_SEARCH_FROM = datetime(2005, 1, 1, tzinfo=UTC)
TICK_SEARCH_FROM = datetime(2005, 1, 1, tzinfo=UTC)
UNLIMITED_MAXBARS = 100_000_000  # terminal_info().maxbars for "Unlimited" (SPIKE-001 runs 2-4)
SAMPLES = 5
INTERVAL_S = 20
MIN_ADVANCES = 3
HOUR_MS = 3_600_000
TOLERANCE_MS = 120_000  # same tolerance as SPIKE-001 and timebase.classify_offset
PACKAGES = ("MetaTrader5", "numpy", "tzdata")
NOT_INSTALLED = "not installed"
UNKNOWN = "UNKNOWN"

ALLOWED_CALLS = frozenset({
    "initialize", "shutdown", "last_error", "version", "terminal_info", "account_info",
    "symbol_info", "symbol_info_tick", "copy_rates_range", "copy_rates_from_pos",
    "copy_ticks_range", "copy_ticks_from",
})

SPEC_FIELDS = (
    "digits", "point", "trade_contract_size", "volume_min", "volume_step", "volume_max",
    "trade_stops_level", "filling_mode", "swap_long", "swap_short", "swap_rollover3days",
    "spread_float",
)


@dataclass(frozen=True)
class Authorization:
    server: str
    login_suffix: str
    valid_until: datetime


@dataclass(frozen=True)
class Sample:
    machine_ms: int
    tick_msc: int | None


class Refused(Exception):
    """Exit 2: arguments, authorization or account do not match the contract."""


class Unavailable(Exception):
    """Exit 3: the terminal cannot be used."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # argparse would print usage and exit; refuse instead
        raise Refused(f"arguments: {message}")


def utc_now() -> datetime:
    return datetime.now(UTC)


def epoch_ms(moment: datetime) -> int:
    return (moment - EPOCH) // timedelta(milliseconds=1)


def parse_arguments(argv: list[str] | None) -> tuple[Authorization, str]:
    parser = _ArgumentParser(prog="probe.py", description="SPIKE-002 read-only re-measure")
    parser.add_argument("--server", required=True)
    parser.add_argument("--login-suffix", required=True)
    parser.add_argument("--valid-until", required=True)
    parser.add_argument("--clock-sync", required=True)
    args = parser.parse_args(argv)
    server = args.server.strip()
    if not server:
        raise Refused("arguments: --server is empty")
    if not re.fullmatch(r"[0-9]{4}", args.login_suffix):
        raise Refused("arguments: --login-suffix must be exactly 4 digits")
    try:
        valid_until = datetime.fromisoformat(args.valid_until)
    except ValueError:
        raise Refused("arguments: --valid-until is not ISO 8601") from None
    if valid_until.tzinfo is None or valid_until.utcoffset() is None:
        raise Refused("arguments: --valid-until needs a UTC offset")
    clock_sync = args.clock_sync.strip()
    if not clock_sync:
        raise Refused("arguments: --clock-sync is empty")
    return Authorization(server, args.login_suffix, valid_until), clock_sync


def check_expiry(now: datetime, auth: Authorization) -> None:
    if now > auth.valid_until:
        raise Refused(f"authorization expired at {auth.valid_until.isoformat()}")


def mask_login(login: object) -> str:
    return "****" + str(login)[-4:]


def check_account(info: object, demo_mode: object, auth: Authorization) -> None:
    """Stop unless the logged-in account is the authorized Demo account with trading disabled."""
    if info is None:
        raise Unavailable("terminal is not logged in to an account")
    if getattr(info, "server", None) != auth.server:
        raise Refused("account server is not the authorized server")
    login = str(getattr(info, "login", ""))
    if len(login) <= 4 or not login.endswith(auth.login_suffix):
        raise Refused(f"account {mask_login(login)} is not the authorized account")
    if demo_mode is None or getattr(info, "trade_mode", None) != demo_mode:
        raise Refused(f"account trade mode {getattr(info, 'trade_mode', None)} is not Demo")
    if getattr(info, "trade_allowed", None) is not False:
        raise Refused("account_info().trade_allowed is not false: log in with the investor password")


# ---- time: freshness and offset, judged separately (architecture 13a) -------------------------
def take_samples(mt5: object, now: Callable[[], datetime], sleep: Callable[[float], object],
                 samples: int = SAMPLES, interval: float = INTERVAL_S) -> list[Sample]:
    out = []
    for i in range(samples):
        if i:
            sleep(interval)
        machine_ms = epoch_ms(now())
        tick = mt5.symbol_info_tick(SYMBOL)
        msc = getattr(tick, "time_msc", None) if tick is not None else None
        out.append(Sample(machine_ms, None if msc is None else int(msc)))
    return out


def market_open(samples: list[Sample], started: datetime) -> bool:
    """Ticks advance in at least MIN_ADVANCES steps and the run day is Monday-Friday (UTC).

    The offset is not used here, so a shifted clock reads as "open and shifted", not "closed"."""
    advances = sum(1 for a, b in zip(samples, samples[1:])
                   if a.tick_msc is not None and b.tick_msc is not None and b.tick_msc > a.tick_msc)
    return started.astimezone(UTC).weekday() < 5 and advances >= MIN_ADVANCES


def offsets_ms(samples: list[Sample]) -> list[int | None]:
    return [None if s.tick_msc is None else s.tick_msc - s.machine_ms for s in samples]


def whole_seconds(ms: int | None) -> int | None:
    if ms is None:
        return None
    return int((Decimal(ms) / 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def offset_class_s(offsets: list[int | None], is_open: bool) -> int | None:
    """Nearest multiple of 3600 s when every sample lies within TOLERANCE_MS of it, else None."""
    if not is_open or not offsets or any(o is None for o in offsets):
        return None
    hours = (offsets[0] + HOUR_MS // 2) // HOUR_MS
    target = hours * HOUR_MS
    if all(abs(o - target) <= TOLERANCE_MS for o in offsets):
        return hours * 3600
    return None


# ---- identity, spec, history ------------------------------------------------------------------
def terminal_path_kind(term: object) -> str | None:
    path, data_path = getattr(term, "path", None), getattr(term, "data_path", None)
    if not path or not data_path:
        return None
    same = os.path.normcase(os.path.normpath(path)) == os.path.normcase(os.path.normpath(data_path))
    return "portable" if same else "installed"


def identity(info: object, term: object) -> dict:
    return {
        "company": getattr(info, "company", None),
        "server": getattr(info, "server", None),
        "trade_mode": getattr(info, "trade_mode", None),
        "currency": getattr(info, "currency", None),
        "leverage": getattr(info, "leverage", None),
        "login_masked": mask_login(getattr(info, "login", "")),
        "trade_allowed": getattr(info, "trade_allowed", None),
        "terminal_build": getattr(term, "build", None),
        "terminal_path_kind": terminal_path_kind(term),
    }


def symbol_spec(mt5: object) -> dict:
    sym = mt5.symbol_info(SYMBOL)
    return {field: (getattr(sym, field, None) if sym is not None else None) for field in SPEC_FIELDS}


def _months_before_cutoff():
    y, m = M1_SEARCH_FROM.year, M1_SEARCH_FROM.month
    while True:
        start = datetime(y, m, 1, tzinfo=UTC)
        if start >= CUTOFF_UTC:
            return
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        yield start, min(datetime(y, m, 1, tzinfo=UTC), CUTOFF_UTC)


def first_m1_utc(mt5: object, maxbars: object) -> str | None:
    """Day of the first M1 bar before the cutoff (raw time read as UTC: rule version "1", offset 0).

    UNKNOWN when maxbars is not Unlimited or a month request failed before the first data;
    None when no M1 bar exists before the cutoff (for example history not loaded yet).
    A range with no data can still return the earliest bar the terminal holds (SPIKE-001 round 2),
    so bars outside the requested range are dropped."""
    if maxbars != UNLIMITED_MAXBARS:
        return UNKNOWN
    for start, end in _months_before_cutoff():
        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, start, end)
        if rates is None:
            return UNKNOWN
        lo, hi = epoch_ms(start) // 1000, epoch_ms(end) // 1000
        inside = [int(t) for t in rates["time"] if lo <= int(t) < hi]
        if inside:
            return datetime.fromtimestamp(min(inside), tz=UTC).date().isoformat()
    return None


def first_tick_utc(mt5: object) -> str | None:
    """Day of the first tick at or after 2005-01-01: the one accepted post-cutoff value, day only."""
    ticks = mt5.copy_ticks_from(SYMBOL, TICK_SEARCH_FROM, 1, mt5.COPY_TICKS_ALL)
    if ticks is None:
        return UNKNOWN
    if not len(ticks):
        return None
    return datetime.fromtimestamp(int(ticks["time"][0]), tz=UTC).date().isoformat()


def package_versions() -> dict:
    out = {}
    for name in PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = NOT_INSTALLED
    out["python"] = platform.python_version()
    return out


# ---- orchestration ----------------------------------------------------------------------------
def run(mt5: object, auth: Authorization, clock_sync: str, now: Callable[[], datetime] = utc_now,
        sleep: Callable[[float], object] = time.sleep) -> tuple[int, dict | None, str]:
    started = now()
    try:
        check_expiry(started, auth)
    except Refused as exc:
        return 2, None, str(exc)
    if not mt5.initialize():
        return 3, None, f"initialize failed: {mt5.last_error()}"
    try:
        info = mt5.account_info()
        check_account(info, getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None), auth)
        term = mt5.terminal_info()
        samples = take_samples(mt5, now, sleep)
        is_open = market_open(samples, started)
        offsets = offsets_ms(samples)
        maxbars = getattr(term, "maxbars", None)
        report = {
            "identity": identity(info, term),
            "spec": symbol_spec(mt5),
            "time": {
                "market_open": is_open,
                "offset_samples_s": [whole_seconds(o) for o in offsets],
                "offset_class_s": offset_class_s(offsets, is_open),
                "clock_sync": clock_sync,
            },
            "history": {
                "maxbars": maxbars,
                "first_m1_utc": first_m1_utc(mt5, maxbars),
                "first_tick_utc": first_tick_utc(mt5),
            },
            "packages": package_versions(),
            "run": {"started_utc": started.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")},
        }
        return 0, report, ""
    except Refused as exc:
        return 2, None, str(exc)
    except Unavailable as exc:
        return 3, None, str(exc)
    finally:
        mt5.shutdown()


def main(argv: list[str] | None = None, now: Callable[[], datetime] = utc_now,
         sleep: Callable[[float], object] = time.sleep) -> int:
    try:
        auth, clock_sync = parse_arguments(argv)
        check_expiry(now(), auth)
    except Refused as exc:
        print(f"REFUSED (exit 2): {exc}", file=sys.stderr)
        return 2
    try:
        import MetaTrader5 as mt5  # only after the argument and expiry checks
    except ModuleNotFoundError:
        print("REFUSED (exit 3): MetaTrader5 is not installed in this environment (see D-022)",
              file=sys.stderr)
        return 3
    code, report, message = run(mt5, auth, clock_sync, now, sleep)
    if code:
        print(f"REFUSED (exit {code}): {message}", file=sys.stderr)
        return code
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
