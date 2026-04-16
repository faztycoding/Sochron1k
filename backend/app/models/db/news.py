from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Float, Index, String, Text
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    pair: Mapped[Optional[str]] = mapped_column(String(10))
    title_original: Mapped[str] = mapped_column(Text, nullable=False)
    title_th: Mapped[Optional[str]] = mapped_column(Text)
    summary_original: Mapped[Optional[str]] = mapped_column(Text)
    summary_th: Mapped[Optional[str]] = mapped_column(Text)
    impact_level: Mapped[str] = mapped_column(String(10), nullable=False)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    event_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_news_pair_time", "pair", scraped_at.desc()),
        Index("idx_news_impact", "impact_level", scraped_at.desc()),
    )
