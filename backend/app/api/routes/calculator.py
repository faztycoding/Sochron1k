import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.models.schemas.trade import CalculateRequest, AutoSLTPRequest
from app.services.calculator import calculate_position, auto_sl_tp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calculate", tags=["คำนวณ"])

TARGET_PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"]


@router.post("", summary="คำนวณ position size + SL/TP")
async def calculate(req: CalculateRequest) -> Dict[str, Any]:
    pair = req.pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(400, f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    return calculate_position(
        pair=pair,
        direction=req.direction,
        account_balance=req.account_balance,
        risk_percent=req.risk_percent,
        entry_price=req.entry_price,
        sl_price=req.sl_price,
        tp_price=req.tp_price,
        sl_pips=req.sl_pips,
        tp_pips=req.tp_pips,
    )


@router.post("/auto-sl", summary="Auto SL/TP จาก ATR")
async def auto_sltp(req: AutoSLTPRequest) -> Dict[str, Any]:
    pair = req.pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(400, f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    try:
        return await auto_sl_tp(pair, req.direction, req.entry_price, req.timeframe)
    except Exception as e:
        logger.error(f"[auto-sl] Error: {e}")
        raise HTTPException(500, f"คำนวณ SL/TP ล้มเหลว: {str(e)}")
