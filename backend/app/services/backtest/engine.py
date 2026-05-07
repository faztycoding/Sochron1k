"""Backtest engine — replays historical candles and simulates trades.

Execution model (intentionally simple but realistic):
  - One position at a time
  - Entry: at candle close when strategy signals BUY/SELL
  - Exit: SL or TP hit intra-candle (worst-case SL wins on gap), OR
    opposite signal on the next bar (closes current position and opens opposite)
  - Position size: fixed-risk per trade (risk_percent of equity on SL distance)
  - Spread and commission are modeled as a flat pip cost per round-trip

Output: BacktestResult with equity curve, trade list, and summary stats
(win rate, profit factor, max drawdown, Sharpe, Sortino, CAGR).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.services.backtest.strategies import BaseStrategy

logger = logging.getLogger(__name__)


def _pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair else 0.0001


def _pip_multiplier(pair: str) -> float:
    """Multiply a price diff by this to get pip count."""
    return 100.0 if "JPY" in pair else 10000.0


@dataclass
class SimTrade:
    entry_time: str
    exit_time: Optional[str]
    direction: str                 # "BUY" or "SELL"
    entry_price: float
    exit_price: Optional[float]
    sl_price: float
    tp_price: float
    lot_size: float
    pips: Optional[float] = None   # positive = profit, negative = loss
    pnl: Optional[float] = None    # in account currency (USD base assumed)
    reason_in: str = ""
    reason_out: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    pair: str
    timeframe: str
    strategy: str
    params: Dict[str, Any]
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win_pips: float
    avg_loss_pips: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe: float
    sortino: float
    total_pips: float
    equity_curve: List[Dict[str, Any]]   # [{time, equity}]
    trades: List[Dict[str, Any]]
    start: str
    end: str
    candle_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BacktestEngine:
    """Simulate a strategy against historical candles."""

    def __init__(
        self,
        pair: str,
        candles: List[Dict[str, Any]],
        strategy: BaseStrategy,
        *,
        initial_balance: float = 1000.0,
        risk_percent: float = 1.0,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 3.0,
        spread_pips: float = 1.5,       # cost per round-trip
        commission_pips: float = 0.0,
    ) -> None:
        self.pair = pair
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.risk_percent = risk_percent
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.spread_pips = spread_pips
        self.commission_pips = commission_pips

        # Normalize candles to DataFrame sorted oldest→newest
        df = pd.DataFrame(candles)
        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["close"]).copy()
        if "open_time" in df.columns:
            df["open_time"] = pd.to_datetime(df["open_time"])
            df = df.sort_values("open_time").reset_index(drop=True)
        self.df = df

        # ATR for SL/TP sizing
        if len(df) >= 15:
            high, low, close = df["high"], df["low"], df["close"]
            tr = pd.concat(
                [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
                axis=1,
            ).max(axis=1)
            self.df["atr"] = tr.rolling(14).mean()
        else:
            self.df["atr"] = np.nan

    # ---------- position sizing ----------

    def _lot_for_risk(self, equity: float, sl_price_distance: float) -> float:
        """Return lot size (std lot = 100k units) so that stop-loss costs exactly
        `risk_percent` of equity.
        """
        pip_size = _pip_size(self.pair)
        if sl_price_distance <= 0 or pip_size <= 0:
            return 0.0
        pip_dist = sl_price_distance / pip_size
        # Pip value per std lot in quote currency
        # For USD-quoted pairs, 1 std lot * 1 pip = $10
        # For JPY-quoted, $1000 / USDJPY ≈ $6.5 at 150
        pip_value_per_lot = 10.0 if "JPY" not in self.pair else 1000.0 / max(self.df["close"].iloc[-1], 1.0)
        risk_amount = equity * (self.risk_percent / 100.0)
        raw_lot = risk_amount / (pip_dist * pip_value_per_lot)
        # Round to micro-lot (0.01) and clamp
        return max(0.01, round(raw_lot, 2))

    def _pip_value_for_lot(self, lot: float) -> float:
        if "JPY" in self.pair:
            return lot * (1000.0 / max(self.df["close"].iloc[-1], 1.0))
        return lot * 10.0

    # ---------- simulation ----------

    def run(self) -> BacktestResult:
        df = self.strategy.prepare(self.df)
        equity = self.initial_balance
        equity_curve: List[Dict[str, Any]] = []
        trades: List[SimTrade] = []
        open_trade: Optional[SimTrade] = None

        pip_size = _pip_size(self.pair)
        pip_mult = _pip_multiplier(self.pair)
        spread_cost_price = self.spread_pips * pip_size
        comm_cost_price = self.commission_pips * pip_size

        n = len(df)
        for i in range(n):
            row = df.iloc[i]
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            t = row.get("open_time")
            t_str = t.isoformat() if isinstance(t, (pd.Timestamp, datetime)) else str(t)

            # --- 1. Check if existing open trade hit SL/TP this bar ---
            if open_trade is not None:
                exit_price: Optional[float] = None
                reason_out = ""
                if open_trade.direction == "BUY":
                    # If bar range covers both SL and TP, assume pessimistic SL-first
                    if low <= open_trade.sl_price:
                        exit_price = open_trade.sl_price
                        reason_out = "SL hit"
                    elif high >= open_trade.tp_price:
                        exit_price = open_trade.tp_price
                        reason_out = "TP hit"
                else:  # SELL
                    if high >= open_trade.sl_price:
                        exit_price = open_trade.sl_price
                        reason_out = "SL hit"
                    elif low <= open_trade.tp_price:
                        exit_price = open_trade.tp_price
                        reason_out = "TP hit"

                if exit_price is not None:
                    # Apply spread + commission cost (in price units, paid at exit)
                    if open_trade.direction == "BUY":
                        exit_price -= spread_cost_price + comm_cost_price
                        raw_diff = exit_price - open_trade.entry_price
                    else:
                        exit_price += spread_cost_price + comm_cost_price
                        raw_diff = open_trade.entry_price - exit_price
                    pips = raw_diff * pip_mult
                    pnl = pips * self._pip_value_for_lot(open_trade.lot_size)
                    open_trade.exit_time = t_str
                    open_trade.exit_price = round(exit_price, 5)
                    open_trade.pips = round(pips, 1)
                    open_trade.pnl = round(pnl, 2)
                    open_trade.reason_out = reason_out
                    equity += pnl
                    trades.append(open_trade)
                    open_trade = None

            # --- 2. Strategy signal for this bar ---
            sig = self.strategy.generate_signal(df, i)

            # Opposite-signal exit (still in trade after SL/TP check)
            if open_trade is not None and sig is not None:
                is_flip = (
                    open_trade.direction == "BUY" and sig["direction"] == "SELL"
                ) or (
                    open_trade.direction == "SELL" and sig["direction"] == "BUY"
                )
                if is_flip:
                    exit_price = close
                    if open_trade.direction == "BUY":
                        exit_price -= spread_cost_price + comm_cost_price
                        raw_diff = exit_price - open_trade.entry_price
                    else:
                        exit_price += spread_cost_price + comm_cost_price
                        raw_diff = open_trade.entry_price - exit_price
                    pips = raw_diff * pip_mult
                    pnl = pips * self._pip_value_for_lot(open_trade.lot_size)
                    open_trade.exit_time = t_str
                    open_trade.exit_price = round(exit_price, 5)
                    open_trade.pips = round(pips, 1)
                    open_trade.pnl = round(pnl, 2)
                    open_trade.reason_out = "Opposite signal"
                    equity += pnl
                    trades.append(open_trade)
                    open_trade = None

            # --- 3. Open new position on fresh signal ---
            if open_trade is None and sig is not None and sig["direction"] in ("BUY", "SELL"):
                atr_val = float(row["atr"]) if not pd.isna(row.get("atr")) else pip_size * 25
                sl_dist = atr_val * self.sl_atr_mult
                tp_dist = atr_val * self.tp_atr_mult
                if sig["direction"] == "BUY":
                    entry = close + spread_cost_price  # pay spread on entry
                    sl = entry - sl_dist
                    tp = entry + tp_dist
                else:
                    entry = close - spread_cost_price
                    sl = entry + sl_dist
                    tp = entry - tp_dist

                lot = self._lot_for_risk(equity, sl_dist)
                if lot > 0:
                    open_trade = SimTrade(
                        entry_time=t_str,
                        exit_time=None,
                        direction=sig["direction"],
                        entry_price=round(entry, 5),
                        exit_price=None,
                        sl_price=round(sl, 5),
                        tp_price=round(tp, 5),
                        lot_size=lot,
                        reason_in=sig.get("reason", ""),
                    )

            equity_curve.append({"time": t_str, "equity": round(equity, 2)})

        # Close any trade still open at the end of data
        if open_trade is not None:
            last = df.iloc[-1]
            exit_price = float(last["close"])
            if open_trade.direction == "BUY":
                raw_diff = exit_price - open_trade.entry_price
            else:
                raw_diff = open_trade.entry_price - exit_price
            pips = raw_diff * pip_mult
            pnl = pips * self._pip_value_for_lot(open_trade.lot_size)
            t = last.get("open_time")
            open_trade.exit_time = t.isoformat() if isinstance(t, (pd.Timestamp, datetime)) else str(t)
            open_trade.exit_price = round(exit_price, 5)
            open_trade.pips = round(pips, 1)
            open_trade.pnl = round(pnl, 2)
            open_trade.reason_out = "End of backtest"
            equity += pnl
            trades.append(open_trade)

        return self._summarize(equity_curve, trades, equity)

    def _summarize(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[SimTrade],
        final_equity: float,
    ) -> BacktestResult:
        n_trades = len(trades)
        wins = [t for t in trades if (t.pnl or 0) > 0]
        losses = [t for t in trades if (t.pnl or 0) <= 0]

        total_pips = round(sum((t.pips or 0) for t in trades), 1)
        avg_win_pips = round(np.mean([t.pips for t in wins]) if wins else 0.0, 1)
        avg_loss_pips = round(np.mean([t.pips for t in losses]) if losses else 0.0, 1)

        gross_profit = sum((t.pnl or 0) for t in wins)
        gross_loss = abs(sum((t.pnl or 0) for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (
            round(gross_profit, 2) if gross_profit > 0 else 0.0
        )

        # Max drawdown (from equity curve)
        curve = np.array([p["equity"] for p in equity_curve])
        max_dd = 0.0
        if len(curve) > 1:
            running_max = np.maximum.accumulate(curve)
            drawdowns = (curve - running_max) / running_max
            max_dd = float(drawdowns.min()) * 100

        # Daily-ish returns for Sharpe/Sortino (use equity-curve diffs)
        sharpe = 0.0
        sortino = 0.0
        if len(curve) > 2:
            rets = np.diff(curve) / curve[:-1]
            if rets.std() > 0:
                sharpe = float(rets.mean() / rets.std() * math.sqrt(252))
            downside = rets[rets < 0]
            if len(downside) > 0 and downside.std() > 0:
                sortino = float(rets.mean() / downside.std() * math.sqrt(252))

        start_row = self.df.iloc[0]
        end_row = self.df.iloc[-1]
        start_t = start_row.get("open_time")
        end_t = end_row.get("open_time")

        return BacktestResult(
            pair=self.pair,
            timeframe=str(self.df.get("timeframe", "")),
            strategy=self.strategy.name,
            params=self.strategy.params,
            initial_balance=round(self.initial_balance, 2),
            final_balance=round(final_equity, 2),
            total_return_pct=round((final_equity / self.initial_balance - 1) * 100, 2),
            total_trades=n_trades,
            wins=len(wins),
            losses=len(losses),
            win_rate=round(len(wins) / n_trades * 100, 1) if n_trades else 0.0,
            avg_win_pips=avg_win_pips,
            avg_loss_pips=avg_loss_pips,
            profit_factor=profit_factor,
            max_drawdown_pct=round(max_dd, 2),
            sharpe=round(sharpe, 2),
            sortino=round(sortino, 2),
            total_pips=total_pips,
            equity_curve=equity_curve,
            trades=[t.to_dict() for t in trades],
            start=start_t.isoformat() if isinstance(start_t, (pd.Timestamp, datetime)) else str(start_t),
            end=end_t.isoformat() if isinstance(end_t, (pd.Timestamp, datetime)) else str(end_t),
            candle_count=len(self.df),
        )
