import json
import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings, TARGET_PAIRS
from app.services.price.twelve_data import TwelveDataService
from app.services.price.yfinance_fallback import YFinanceFallback

logger = logging.getLogger(__name__)

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]


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
        # 1. Try Redis cache first (check freshness)
        cached = await self._get_cached_candles(pair, timeframe)
        if cached and len(cached) >= min(limit, 50):
            # Verify cache is recent (not stale data from hours ago)
            try:
                from datetime import datetime, timezone, timedelta
                latest = cached[0].get("open_time", "")
                if latest:
                    latest_dt = datetime.fromisoformat(latest.replace(" ", "T"))
                    max_age = {"1m": 5, "5m": 15, "15m": 30, "1h": 120, "4h": 480, "1d": 2880}
                    max_minutes = max_age.get(timeframe, 120)
                    if (datetime.now(tz=timezone.utc).replace(tzinfo=None) - latest_dt) > timedelta(minutes=max_minutes):
                        logger.warning(f"[price] Cache stale: {pair} {timeframe} latest={latest}")
                        cached = None
            except Exception:
                pass

        if cached and len(cached) >= min(limit, 50):
            logger.info(f"[price] Cache hit: {pair} {timeframe} ({len(cached)} candles)")
            return cached[:limit]

        # 2. Twelve Data (primary)
        candles = await self._twelve.get_candles(pair, timeframe, limit)
        if candles:
            await self._cache_candles(pair, timeframe, candles)
            return candles

        # 3. Return stale cache if API failed
        if cached:
            logger.warning(f"[price] API failed, returning stale cache for {pair} {timeframe}")
            return cached[:limit]

        # 4. yfinance (last resort)
        logger.info(f"[price] Falling back to yfinance for {pair} {timeframe}")
        candles = await self._yfinance.get_candles(pair, timeframe, limit)
        if candles:
            await self._cache_candles(pair, timeframe, candles)
        return candles

    async def get_realtime_prices(self) -> Dict[str, Any]:
        prices = {}
        for pair in TARGET_PAIRS:
            # Try cache first (60s TTL)
            cached = await self._get_cached_price(pair)
            if cached:
                prices[pair] = cached
                continue

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

    def _cache_ttl(self, timeframe: str) -> int:
        """Shorter TTL for shorter timeframes to keep data fresh."""
        return {
            "1m": 60,       # 1 min
            "5m": 120,      # 2 min
            "15m": 300,     # 5 min
            "1h": 600,      # 10 min
            "4h": 1800,     # 30 min
            "1d": 3600,     # 1 hour
        }.get(timeframe, 600)

    async def _cache_candles(
        self, pair: str, timeframe: str, candles: List[Dict]
    ) -> None:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            key = f"candles:{pair}:{timeframe}"
            await r.setex(
                key,
                self._cache_ttl(timeframe),
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
            await r.setex(f"price:{pair}", 10, json.dumps(data, default=str))
            await r.aclose()
        except Exception:
            pass

    async def _get_cached_price(self, pair: str) -> Optional[Dict]:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            data = await r.get(f"price:{pair}")
            await r.aclose()
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def close(self) -> None:
        await self._twelve.close()
