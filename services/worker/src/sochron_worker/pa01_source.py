"""Bounded local sources for PA01 decisions; no network or execution authority."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .native_source import PRICE_TEXT, NativeArchiveSource, SourceUnavailable, _json
from .pa01_aggregation import AggregationUnavailable, aggregate_native_m1
from .pa01_envelope import (
    EnvelopeUnavailable,
    PA01DecisionEnvelope,
    PA01PolicyEvidence,
    build_pa01_decision_envelope,
)
from .sync_config import SyncConfigInvalid, private_bytes

MAX_POLICY_BYTES = 16_384
SIGNAL_LIFETIME_SECONDS = 30


class PA01SourceUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_SOURCE_UNAVAILABLE")


class PolicyFileSource:
    """Read one stable owner-only policy observation contract."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> PA01PolicyEvidence:
        try:
            raw = private_bytes(self.path, MAX_POLICY_BYTES).decode("utf-8")
            data = _json(raw, MAX_POLICY_BYTES)
            spread = data.get("spread_price")
            if not isinstance(spread, str) or len(spread) > 40 or not PRICE_TEXT.fullmatch(spread):
                raise ValueError("exact spread string required")
            data["spread_price"] = Decimal(spread)
            return PA01PolicyEvidence.model_validate(data)
        except SyncConfigInvalid, ValueError, TypeError, RecursionError:
            raise PA01SourceUnavailable() from None


class PA01DecisionSource:
    """Build at most one envelope for the newest unseen closed M5 bar."""

    def __init__(
        self,
        archive: NativeArchiveSource,
        policy: PolicyFileSource,
        code_hash: str,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if (
            not isinstance(code_hash, str)
            or len(code_hash) != 64
            or any(char not in "0123456789abcdef" for char in code_hash)
        ):
            raise PA01SourceUnavailable()
        self.archive, self.policy, self.code_hash = archive, policy, code_hash
        self._now = utc_now

    def next(self, last_formed_at: datetime | None) -> PA01DecisionEnvelope | None:
        try:
            if last_formed_at is not None and (
                not isinstance(last_formed_at, datetime)
                or last_formed_at.tzinfo is None
                or last_formed_at.utcoffset() is None
            ):
                raise PA01SourceUnavailable()
            now = self._now()
            if now.tzinfo is None or now.utcoffset() is None:
                raise PA01SourceUnavailable()
            now = now.astimezone(UTC)
            policy = self.policy.read()
            if not (
                policy.cutoff_utc
                <= now
                <= policy.cutoff_utc + timedelta(seconds=SIGNAL_LIFETIME_SECONDS)
            ):
                raise PA01SourceUnavailable()
            rows = self.archive.read_pa01(policy.cutoff_utc)
            if not rows:
                return None
            aggregation = aggregate_native_m1(rows, cutoff_utc=policy.cutoff_utc)
            if not aggregation.m5_bars:
                return None
            formed = aggregation.m5_bars[-1].close_time_utc
            if last_formed_at is not None and formed <= last_formed_at.astimezone(UTC):
                return None
            envelope = build_pa01_decision_envelope(aggregation, policy, code_hash=self.code_hash)
            if envelope.signal.formed_at != formed:
                raise PA01SourceUnavailable()
            return envelope
        except PA01SourceUnavailable:
            raise
        except SourceUnavailable, AggregationUnavailable, EnvelopeUnavailable:
            raise PA01SourceUnavailable() from None
        except ValueError, TypeError, KeyError, ArithmeticError, OverflowError, RecursionError:
            raise PA01SourceUnavailable() from None
