from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IndicatorSnapshotResponse(BaseModel):
    pair: str
    timeframe: str
    calculated_at: str
    candle_count: int
    latest_price: float

    # Trend
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    adx: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None

    # Oscillators
    rsi: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    cci: Optional[float] = None

    # Volatility
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None
    keltner_upper: Optional[float] = None
    keltner_lower: Optional[float] = None

    # Volume
    obv: Optional[float] = None

    # Custom
    currency_strength: Optional[float] = None
    z_score: Optional[float] = None
    session_vol_index: Optional[float] = None
    correlation_divergence: Optional[float] = None
    liquidity_spike: Optional[float] = None
    multi_tf_confluence: Optional[float] = None
    news_impact_score: Optional[float] = None


class SignalItem(BaseModel):
    name: str
    signal: str
    value: float
    bias: str


class QuickSummaryResponse(BaseModel):
    pair: str
    overall_bias: str
    bullish_signals: int
    bearish_signals: int
    signals: List[SignalItem]
    snapshot: Dict[str, Any]


class PriceResponse(BaseModel):
    pair: str
    price: float
    timestamp: str
    previous_close: Optional[float] = None


class CandleResponse(BaseModel):
    pair: str
    timeframe: str
    open_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class CurrencyStrengthResponse(BaseModel):
    EUR: float
    USD: float
    JPY: float
