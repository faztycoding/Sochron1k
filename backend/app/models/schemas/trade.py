from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Calculator ──

class CalculateRequest(BaseModel):
    pair: str
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    account_balance: float = Field(..., gt=0)
    risk_percent: float = Field(2.0, gt=0, le=10)
    entry_price: float = Field(..., gt=0)
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    sl_pips: Optional[float] = None
    tp_pips: Optional[float] = None


class CalculateResponse(BaseModel):
    pair: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    sl_pips: float
    tp_pips: float
    lot_size: float
    risk_amount: float
    potential_profit: float
    risk_reward: float
    pip_value: float
    warnings: List[str] = []


class AutoSLTPRequest(BaseModel):
    pair: str
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    entry_price: float = Field(..., gt=0)
    timeframe: str = "1h"


class AutoSLTPResponse(BaseModel):
    pair: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    sl_pips: float
    tp_pips: float
    atr_used: float
    risk_reward: float
    method: str = "ATR-based"


# ── Trade Journal ──

class TradeCreate(BaseModel):
    pair: str
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    timeframe: str = "1h"
    account_balance: float = Field(..., gt=0)
    risk_percent: float = Field(2.0, gt=0, le=10)
    lot_size: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    sl_pips: Optional[float] = None
    tp_pips: Optional[float] = None
    target_pips: Optional[float] = None
    target_hours: Optional[float] = None
    system_confidence: Optional[float] = None
    system_direction: Optional[str] = None
    system_regime: Optional[str] = None
    user_notes: Optional[str] = None


class TradeUpdate(BaseModel):
    exit_price: Optional[float] = None
    actual_pips: Optional[float] = None
    profit_loss: Optional[float] = None
    status: Optional[str] = None
    result: Optional[str] = None
    user_notes: Optional[str] = None


class TradeResponse(BaseModel):
    id: int
    pair: str
    direction: str
    timeframe: str
    account_balance: float
    risk_percent: float
    lot_size: float
    entry_price: float
    sl_price: Optional[float]
    tp_price: Optional[float]
    sl_pips: Optional[float]
    tp_pips: Optional[float]
    exit_price: Optional[float]
    actual_pips: Optional[float]
    profit_loss: Optional[float]
    risk_reward_actual: Optional[float]
    status: str
    result: Optional[str]
    system_confidence: Optional[float]
    system_direction: Optional[str]
    system_regime: Optional[str]
    system_correct: Optional[bool]
    opened_at: datetime
    closed_at: Optional[datetime]
    user_notes: Optional[str]

    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    items: List[TradeResponse]
    total: int
    page: int = 1
    per_page: int = 20


# ── Stats ──

class WinRateResponse(BaseModel):
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_profit_pips: float
    avg_loss_pips: float
    profit_factor: float
    best_trade_pips: float
    worst_trade_pips: float
    total_pips: float
    by_pair: Dict[str, Dict[str, Any]]


class AccuracyResponse(BaseModel):
    total_signals: int
    correct_signals: int
    accuracy: float
    by_pair: Dict[str, Dict[str, Any]]
    by_regime: Dict[str, Dict[str, Any]]
    by_confidence_tier: Dict[str, Dict[str, Any]]


class OverviewResponse(BaseModel):
    total_trades: int
    open_trades: int
    win_rate: float
    total_pips: float
    profit_factor: float
    system_accuracy: float
    best_pair: Optional[str]
    worst_pair: Optional[str]
    avg_confidence: float
    consecutive_wins: int
    consecutive_losses: int
    today_trades: int
    today_pips: float
