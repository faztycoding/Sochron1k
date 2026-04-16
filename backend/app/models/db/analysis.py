from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Float, Index, String, Text
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    trend_score: Mapped[Optional[float]] = mapped_column(Float)
    news_score: Mapped[Optional[float]] = mapped_column(Float)
    indicator_score: Mapped[Optional[float]] = mapped_column(Float)
    correlation_score: Mapped[Optional[float]] = mapped_column(Float)
    regime: Mapped[Optional[str]] = mapped_column(String(20))

    indicators_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    suggested_entry: Mapped[Optional[float]] = mapped_column(Float)
    suggested_sl: Mapped[Optional[float]] = mapped_column(Float)
    suggested_tp: Mapped[Optional[float]] = mapped_column(Float)
    suggested_lots: Mapped[Optional[float]] = mapped_column(Float)
    risk_reward: Mapped[Optional[float]] = mapped_column(Float)

    analysis_summary_th: Mapped[Optional[str]] = mapped_column(Text)
    errors_found: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    was_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    actual_outcome: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        Index("idx_analysis_pair_time", "pair", created_at.desc()),
    )
