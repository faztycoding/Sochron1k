import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/price", tags=["ราคา"])

TARGET_PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"]


@router.get("/realtime", summary="ราคาเรียลไทม์ทุกคู่เงิน")
async def get_realtime_prices() -> Dict[str, Any]:
    from app.services.price.manager import PriceManager

    pm = PriceManager()
    try:
        prices = await pm.get_realtime_prices()
        return {"prices": prices, "count": len(prices)}
    except Exception as e:
        logger.error(f"[price] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pm.close()


@router.get("/candles/{pair}", summary="ดึงแท่งเทียน OHLCV")
async def get_candles(
    pair: str,
    timeframe: str = Query("1h", description="1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(200, ge=10, le=1000),
) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(status_code=400, detail=f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    from app.services.price.manager import PriceManager

    pm = PriceManager()
    try:
        candles = await pm.get_candles(pair, timeframe, limit)
        return {
            "pair": pair,
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles,
        }
    except Exception as e:
        logger.error(f"[price] Candles error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pm.close()


@router.get("/quote/{pair}", summary="ราคาละเอียดพร้อม change %")
async def get_quote(pair: str) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(status_code=400, detail=f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    from app.services.price.twelve_data import TwelveDataService

    td = TwelveDataService()
    try:
        quote = await td.get_quote(pair)
        if not quote:
            from app.services.price.yfinance_fallback import YFinanceFallback
            yf = YFinanceFallback()
            quote = await yf.get_realtime_price(pair)

        if not quote:
            raise HTTPException(status_code=404, detail=f"ไม่พบราคา {pair}")
        return quote
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[price] Quote error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await td.close()
