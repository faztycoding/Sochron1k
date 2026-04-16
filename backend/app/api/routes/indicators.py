import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.models.schemas.indicators import (
    CurrencyStrengthResponse,
    IndicatorSnapshotResponse,
    QuickSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/indicators", tags=["อินดิเคเตอร์"])

from app.config import TARGET_PAIRS
VALID_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]


@router.get("/{pair}", summary="คำนวณอินดิเคเตอร์ทั้งหมดสำหรับคู่เงิน")
async def get_indicators(
    pair: str,
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(status_code=400, detail=f"คู่เงินที่รองรับ: {TARGET_PAIRS}")
    if timeframe not in VALID_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"Timeframe ที่รองรับ: {VALID_TIMEFRAMES}")

    from app.services.indicators.engine import IndicatorEngine

    engine = IndicatorEngine()
    try:
        result = await engine.compute_for_pair(pair, timeframe)
        return result
    except Exception as e:
        logger.error(f"[indicators] Error: {e}")
        raise HTTPException(status_code=500, detail=f"คำนวณล้มเหลว: {str(e)}")
    finally:
        await engine.close()


@router.get("/{pair}/summary", summary="สรุปสัญญาณเร็วสำหรับคู่เงิน")
async def get_quick_summary(pair: str) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(status_code=400, detail=f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    from app.services.indicators.engine import IndicatorEngine

    engine = IndicatorEngine()
    try:
        return await engine.get_quick_summary(pair)
    except Exception as e:
        logger.error(f"[indicators] Summary error: {e}")
        raise HTTPException(status_code=500, detail=f"คำนวณล้มเหลว: {str(e)}")
    finally:
        await engine.close()


@router.get("/all/snapshot", summary="สแนปชอตอินดิเคเตอร์ทุกคู่เงิน")
async def get_all_indicators() -> Dict[str, Any]:
    from app.services.indicators.engine import IndicatorEngine

    engine = IndicatorEngine()
    try:
        return await engine.compute_all_pairs()
    except Exception as e:
        logger.error(f"[indicators] All pairs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await engine.close()


@router.get("/strength/currencies", summary="ดูความแข็งแกร่งสกุลเงิน")
async def get_currency_strength() -> Dict[str, Any]:
    from app.services.indicators.custom import calc_currency_strength
    from app.services.price.manager import PriceManager

    pm = PriceManager()
    try:
        pair_candles = {}
        for pair in TARGET_PAIRS:
            candles = await pm.get_candles(pair, "1h", 50)
            if candles:
                pair_candles[pair] = sorted(candles, key=lambda c: c.get("open_time", ""))

        strength = calc_currency_strength(pair_candles)
        return {
            "currencies": strength,
            "strongest": max(strength, key=strength.get) if strength else None,
            "weakest": min(strength, key=strength.get) if strength else None,
        }
    except Exception as e:
        logger.error(f"[indicators] Strength error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pm.close()
