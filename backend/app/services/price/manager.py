import json
import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.price.twelve_data import TwelveDataService
from app.services.price.yfinance_fallback import YFinanceFallback

logger = logging.getLogger(__name__)

TARGET_PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"]
TIMEFRAMES = ["1h", "4h", "1d"]


class PriceManager:
    def __init__(self):
        self._settings = get_settings()
        self._twelve = TwelveDataService()
        self._yfinance = YFinanceFallback()

    async def get_candles(
        self,
        pair: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        # Twelve Data (primary)
        candles = await self._twelve.get_candles(pair, timeframe, limit)
        if candles:
            await self._cache_candles(pair, timeframe, candles)
            return candles

        # yfinance (fallback)
        logger.info(f"[price] Falling back to yfinance for {pair} {timeframe}")
        candles = await self._yfinance.get_candles(pair, timeframe, limit)
        if candles:
            await self._cache_candles(pair, timeframe, candles)
        return candles

    async def get_realtime_prices(self) -> Dict[str, Any]:
        prices = {}
        for pair in TARGET_PAIRS:
            price_data = await self._twelve.get_realtime_price(pair)
            if not price_data:
                price_data = await self._yfinance.get_realtime_price(pair)
            if price_data:
                prices[pair] = price_data
                await self._cache_price(pair, price_data)
        return prices

    async def get_all_candles(self) -> Dict[str, Dict[str, List]]:
        result = {}
        for pair in TARGET_PAIRS:
            result[pair] = {}
            for tf in TIMEFRAMES:
                cached = await self._get_cached_candles(pair, tf)
                if cached:
                    result[pair][tf] = cached
                else:
                    candles = await self.get_candles(pair, tf)
                    result[pair][tf] = candles
        return result

    async def _cache_candles(
        self, pair: str, timeframe: str, candles: List[Dict]
    ) -> None:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            key = f"candles:{pair}:{timeframe}"
            await r.setex(
                key,
                1800,  # 30 min cache
                json.dumps(candles[-200:], default=str),
            )
            await r.aclose()
        except Exception as e:
            logger.debug(f"[price] Cache write error: {e}")

    async def _get_cached_candles(
        self, pair: str, timeframe: str
    ) -> Optional[List[Dict]]:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            key = f"candles:{pair}:{timeframe}"
            data = await r.get(key)
            await r.aclose()
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def _cache_price(self, pair: str, data: Dict) -> None:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            await r.setex(f"price:{pair}", 60, json.dumps(data, default=str))
            await r.aclose()
        except Exception:
            pass

    async def close(self) -> None:
        await self._twelve.close()
