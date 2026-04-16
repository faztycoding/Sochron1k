import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas.trade import TradeCreate, TradeUpdate, TradeResponse, TradeListResponse
from app.services.journal import (
    create_trade, get_trade, update_trade, list_trades, delete_trade,
    get_win_rate, get_accuracy, get_overview,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trades", tags=["บันทึกเทรด"])


@router.post("", summary="บันทึกเทรดใหม่", response_model=TradeResponse)
async def create(data: TradeCreate, db: AsyncSession = Depends(get_db)):
    try:
        trade = await create_trade(db, data.model_dump())
        return trade
    except Exception as e:
        logger.error(f"[trades] Create error: {e}")
        raise HTTPException(500, str(e))


@router.get("", summary="ดูรายการเทรด", response_model=TradeListResponse)
async def list_all(
    pair: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    pair_clean = pair.upper().replace("-", "/") if pair else None
    return await list_trades(db, pair_clean, status, result, page, per_page)


@router.get("/stats/winrate", summary="Win Rate รวม/แยก pair")
async def winrate(
    pair: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    pair_clean = pair.upper().replace("-", "/") if pair else None
    return await get_win_rate(db, pair_clean)


@router.get("/stats/accuracy", summary="ความแม่นระบบ vs ผลจริง")
async def accuracy(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await get_accuracy(db)


@router.get("/stats/overview", summary="ภาพรวมทั้งหมด")
async def overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await get_overview(db)


@router.get("/{trade_id}", summary="ดูเทรดเดียว", response_model=TradeResponse)
async def get_one(trade_id: int, db: AsyncSession = Depends(get_db)):
    trade = await get_trade(db, trade_id)
    if not trade:
        raise HTTPException(404, "ไม่พบเทรดนี้")
    return trade


@router.put("/{trade_id}", summary="อัพเดทเทรด (ปิด/แก้ไข)", response_model=TradeResponse)
async def update(trade_id: int, data: TradeUpdate, db: AsyncSession = Depends(get_db)):
    trade = await update_trade(db, trade_id, data.model_dump(exclude_unset=True))
    if not trade:
        raise HTTPException(404, "ไม่พบเทรดนี้")
    return trade


@router.delete("/{trade_id}", summary="ลบเทรด")
async def delete(trade_id: int, db: AsyncSession = Depends(get_db)):
    ok = await delete_trade(db, trade_id)
    if not ok:
        raise HTTPException(404, "ไม่พบเทรดนี้")
    return {"message": f"ลบเทรด #{trade_id} สำเร็จ"}
