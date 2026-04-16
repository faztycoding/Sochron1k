from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Float, Index, String
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OHLCVCandle(Base):
    __tablename__ = "ohlcv_candles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    open_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        Index("idx_ohlcv_pair_tf_time", "pair", "timeframe", open_time.desc()),
        Index("idx_ohlcv_time", open_time.desc()),
    )


class IndicatorSnapshot(Base):
    __tablename__ = "indicator_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    # Trend
    ema_9: Mapped[Optional[float]] = mapped_column(Float)
    ema_21: Mapped[Optional[float]] = mapped_column(Float)
    ema_50: Mapped[Optional[float]] = mapped_column(Float)
    ema_200: Mapped[Optional[float]] = mapped_column(Float)
    sma_50: Mapped[Optional[float]] = mapped_column(Float)
    sma_200: Mapped[Optional[float]] = mapped_column(Float)
    adx: Mapped[Optional[float]] = mapped_column(Float)
    macd_line: Mapped[Optional[float]] = mapped_column(Float)
    macd_signal: Mapped[Optional[float]] = mapped_column(Float)
    macd_hist: Mapped[Optional[float]] = mapped_column(Float)

    # Oscillators
    rsi: Mapped[Optional[float]] = mapped_column(Float)
    stoch_k: Mapped[Optional[float]] = mapped_column(Float)
    stoch_d: Mapped[Optional[float]] = mapped_column(Float)
    cci: Mapped[Optional[float]] = mapped_column(Float)

    # Volatility
    bb_upper: Mapped[Optional[float]] = mapped_column(Float)
    bb_middle: Mapped[Optional[float]] = mapped_column(Float)
    bb_lower: Mapped[Optional[float]] = mapped_column(Float)
    atr: Mapped[Optional[float]] = mapped_column(Float)
    keltner_upper: Mapped[Optional[float]] = mapped_column(Float)
    keltner_lower: Mapped[Optional[float]] = mapped_column(Float)

    # Volume
    obv: Mapped[Optional[float]] = mapped_column(Float)

    # Custom
    currency_strength: Mapped[Optional[float]] = mapped_column(Float)
    z_score: Mapped[Optional[float]] = mapped_column(Float)
    session_vol_index: Mapped[Optional[float]] = mapped_column(Float)
    correlation_divergence: Mapped[Optional[float]] = mapped_column(Float)
    liquidity_spike: Mapped[Optional[float]] = mapped_column(Float)
    multi_tf_confluence: Mapped[Optional[float]] = mapped_column(Float)
    news_impact_score: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        Index("idx_snapshot_pair_tf", "pair", "timeframe", calculated_at.desc()),
    )
