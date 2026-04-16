from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Float, ForeignKey, Index, String, Text
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("analyses.id"))
    pair: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)

    account_balance: Mapped[float] = mapped_column(Float, nullable=False)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    sl_price: Mapped[Optional[float]] = mapped_column(Float)
    tp_price: Mapped[Optional[float]] = mapped_column(Float)
    target_pips: Mapped[Optional[float]] = mapped_column(Float)
    target_hours: Mapped[Optional[float]] = mapped_column(Float)

    exit_price: Mapped[Optional[float]] = mapped_column(Float)
    actual_pips: Mapped[Optional[float]] = mapped_column(Float)
    profit_loss: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="open")

    opened_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    user_notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_trades_pair_status", "pair", "status"),
    )
