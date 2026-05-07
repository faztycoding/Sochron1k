"""Pydantic schemas for the backtest API."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy: str = Field(..., description="strategy name, e.g. ema_crossover")
    timeframe: str = Field("1h", description="1m, 5m, 15m, 1h, 4h, 1d")
    lookback: int = Field(500, ge=50, le=5000, description="จำนวนแท่งเทียนย้อนหลัง")
    initial_balance: float = Field(1000.0, gt=0)
    risk_percent: float = Field(1.0, ge=0.1, le=10.0)
    sl_atr_mult: float = Field(1.5, ge=0.5, le=5.0)
    tp_atr_mult: float = Field(3.0, ge=0.5, le=10.0)
    spread_pips: float = Field(1.5, ge=0, le=10)
    commission_pips: float = Field(0.0, ge=0, le=10)
    params: Optional[Dict[str, Any]] = Field(default=None, description="strategy-specific overrides")


class TradeRow(BaseModel):
    entry_time: str
    exit_time: Optional[str]
    direction: str
    entry_price: float
    exit_price: Optional[float]
    sl_price: float
    tp_price: float
    lot_size: float
    pips: Optional[float]
    pnl: Optional[float]
    reason_in: str
    reason_out: str


class BacktestResponse(BaseModel):
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
    equity_curve: List[Dict[str, Any]]
    trades: List[TradeRow]
    start: str
    end: str
    candle_count: int


class StrategyMetadata(BaseModel):
    name: str
    display_name: str
    description: str
    default_params: Dict[str, Any]
