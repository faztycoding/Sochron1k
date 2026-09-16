from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .models import AccountSnapshot, CommandIntent, ContractSpec, MarketSnapshot, TradeMode


class PreflightDenied(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PreflightPolicy:
    account_ref: str
    server: str
    symbol: str
    currency: str
    margin_mode: str
    max_price_age_seconds: float = 5.0


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PreflightDenied("INVALID_TIME", f"{field} must be timezone-aware")


def validate_preflight(
    policy: PreflightPolicy,
    account: AccountSnapshot,
    contract: ContractSpec,
    market: MarketSnapshot,
    intent: CommandIntent,
    *,
    now: datetime | None = None,
) -> None:
    checked_at = now or datetime.now(UTC)
    _aware(checked_at, "now")
    _aware(account.checked_at, "account.checked_at")
    _aware(market.event_time, "market.event_time")
    _aware(market.received_time, "market.received_time")

    if account.trade_mode is not TradeMode.DEMO:
        raise PreflightDenied("NON_DEMO_ACCOUNT", "only an MT5 Demo account is permitted")
    expected = {
        "account_ref": (account.account_ref, policy.account_ref),
        "server": (account.server, policy.server),
        "currency": (account.currency, policy.currency),
        "margin_mode": (account.margin_mode, policy.margin_mode),
    }
    for field, (actual, configured) in expected.items():
        if actual != configured:
            raise PreflightDenied(
                "IDENTITY_MISMATCH", f"{field} does not match configured Demo identity"
            )
    if not account.can_trade:
        raise PreflightDenied("TRADING_DISABLED", "MT5 reports trading is not permitted")
    if intent.account_ref != account.account_ref:
        raise PreflightDenied("COMMAND_ACCOUNT_MISMATCH", "command targets another account")
    if (
        contract.symbol != policy.symbol
        or market.symbol != policy.symbol
        or intent.symbol != policy.symbol
    ):
        raise PreflightDenied("SYMBOL_MISMATCH", "symbol does not match configured Demo symbol")
    if not market.market_open:
        raise PreflightDenied("MARKET_CLOSED", "market is not expected to be open")
    if market.received_time < market.event_time:
        raise PreflightDenied("INVALID_TIME", "received time predates event time")
    age = (checked_at - market.received_time.astimezone(UTC)).total_seconds()
    if age < 0:
        raise PreflightDenied("INVALID_TIME", "market data is from the future")
    if age > policy.max_price_age_seconds:
        raise PreflightDenied(
            "STALE_PRICE", f"market data age {age:.3f}s exceeds the allowed threshold"
        )
    if intent.expires_at <= checked_at:
        raise PreflightDenied("EXPIRED_COMMAND", "command has expired")
    if intent.side.value == "buy" and intent.stop_loss >= intent.requested_entry:
        raise PreflightDenied("INVALID_STOP", "buy stop loss must be below entry")
    if intent.side.value == "sell" and intent.stop_loss <= intent.requested_entry:
        raise PreflightDenied("INVALID_STOP", "sell stop loss must be above entry")
