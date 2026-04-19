import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings, TARGET_PAIRS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/price", tags=["ราคา"])


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


@router.get("/performance", summary="ประสิทธิภาพราคา: เปลี่ยนแปลง 1D/3D/1W/1M")
async def get_performance() -> Dict[str, Any]:
    """Calculate price change % over different time periods using candle data."""
    from app.services.price.manager import PriceManager

    pm = PriceManager()
    result = {}

    try:
        for pair in TARGET_PAIRS:
            # Get 1D candles (30 trading days ≈ 1.5 months)
            candles_1d = await pm.get_candles(pair, "1d", 30)
            candles_1h = await pm.get_candles(pair, "1h", 24)

            if not candles_1d:
                result[pair] = {"error": "no data"}
                continue

            # Sort oldest→newest
            candles_1d = sorted(candles_1d, key=lambda c: c.get("open_time", ""))
            candles_1h = sorted(candles_1h, key=lambda c: c.get("open_time", ""))

            current = candles_1d[-1]["close"] if candles_1d else 0
            if candles_1h:
                current = candles_1h[-1]["close"]

            day_high = max(c["high"] for c in candles_1h) if candles_1h else current
            day_low = min(c["low"] for c in candles_1h) if candles_1h else current

            def pct_change(old: float, new: float) -> float:
                if old == 0:
                    return 0
                return round((new - old) / old * 100, 4)

            def pip_change(old: float, new: float, pair: str) -> float:
                mult = 100 if "JPY" in pair else 10000
                return round((new - old) * mult, 1)

            perf: Dict[str, Any] = {
                "price": current,
                "day_high": day_high,
                "day_low": day_low,
                "day_open": candles_1d[-1]["open"] if candles_1d else current,
            }

            # 1D: use 24h rolling from hourly candles (matches TradingView)
            # 3D/1W/1M: use daily candles as before
            if len(candles_1h) >= 24:
                old_1d = candles_1h[-24]["close"] if len(candles_1h) >= 24 else None
                if old_1d:
                    perf["1D"] = {
                        "pct": pct_change(old_1d, current),
                        "pips": pip_change(old_1d, current, pair),
                        "from_price": old_1d,
                    }
                else:
                    perf["1D"] = None
            elif len(candles_1d) > 1:
                old_price = candles_1d[-2]["close"]
                perf["1D"] = {
                    "pct": pct_change(old_price, current),
                    "pips": pip_change(old_price, current, pair),
                    "from_price": old_price,
                }
            else:
                perf["1D"] = None

            # Longer periods use daily candles
            periods = {"3D": 3, "1W": 5, "1M": 22}
            for label, days_back in periods.items():
                if len(candles_1d) > days_back:
                    old_price = candles_1d[-(days_back + 1)]["close"]
                    perf[label] = {
                        "pct": pct_change(old_price, current),
                        "pips": pip_change(old_price, current, pair),
                        "from_price": old_price,
                    }
                else:
                    perf[label] = None

            result[pair] = perf

        return {"performance": result}
    except Exception as e:
        logger.error(f"[price] Performance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pm.close()


@router.get("/stream", summary="SSE real-time price stream (WebSocket-backed)")
async def price_stream(request: Request):
    """Server-Sent Events: backed by Twelve Data WebSocket (0 credits)."""

    async def event_generator():
        from app.services.price.ws_stream import PriceStream
        stream = PriceStream()
        q = stream.subscribe()

        try:
            # Send current snapshot immediately
            if stream.prices:
                data = json.dumps({
                    "prices": stream.prices,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }, default=str)
                yield f"data: {data}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    msg = await asyncio.wait_for(q.get(), timeout=5.0)
                    if msg.get("type") == "price":
                        # Single price update
                        pdata = msg["data"]
                        pair = pdata["pair"]
                        all_prices = dict(stream.prices)
                        all_prices[pair] = pdata
                        data = json.dumps({
                            "prices": all_prices,
                            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                        }, default=str)
                        yield f"data: {data}\n\n"
                    elif msg.get("type") == "prices":
                        # Batch update from REST fallback
                        data = json.dumps({
                            "prices": msg["data"],
                            "timestamp": msg.get("timestamp", datetime.now(tz=timezone.utc).isoformat()),
                        }, default=str)
                        yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
        finally:
            stream.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
