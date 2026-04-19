import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from app.config import get_settings, TARGET_PAIRS
from app.services.price.twelve_data import TwelveDataService
from app.services.price.yfinance_fallback import YFinanceFallback

logger = logging.getLogger(__name__)

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Module-level singleton — shared Redis pool across all PriceManager instances
_redis_pool: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    """Lazy-create a shared async Redis connection with connection pooling."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
            socket_keepalive=True,
        )
    return _redis_pool


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
                # Override change/percent_change with 24h rolling reference
                # (matches TradingView/OANDA convention better than
                # TwelveData's UTC-midnight previous_close)
                await self._adjust_rolling_24h(pair, price_data)
                prices[pair] = price_data
                await self._cache_price(pair, price_data)
        return prices

    async def _adjust_rolling_24h(
        self, pair: str, price_data: Dict[str, Any]
    ) -> None:
        """Recompute change/percent_change using 24h rolling reference.

        Uses 1h candles from 24 hours ago as the "previous" baseline.
        This matches major forex platforms (TradingView, OANDA, Bloomberg)
        better than Twelve Data's daily boundary which can be hours-old.
        """
        try:
            candles_1h = await self._get_cached_candles(pair, "1h")
            if not candles_1h or len(candles_1h) < 24:
                return  # fall back to TwelveData values

            # Sort oldest first, pick candle ~24 hours ago
            candles_sorted = sorted(candles_1h, key=lambda c: c.get("open_time", ""))
            if len(candles_sorted) < 25:
                return
            ref_close = float(candles_sorted[-25]["close"])
            current = float(price_data.get("price", 0))
            if ref_close <= 0 or current <= 0:
                return

            change = current - ref_close
            pct = (change / ref_close) * 100
            price_data["previous_close"] = ref_close
            price_data["change"] = round(change, 5 if "JPY" not in pair else 3)
            price_data["percent_change"] = round(pct, 4)
            price_data["reference_type"] = "24h_rolling"
        except Exception as e:
            logger.debug(f"[price] Rolling 24h adjust error for {pair}: {e}")

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
            r = await _get_redis()
            key = f"candles:{pair}:{timeframe}"
            await r.setex(
                key,
                self._cache_ttl(timeframe),
                json.dumps(candles[-200:], default=str),
            )
        except Exception as e:
            logger.debug(f"[price] Cache write error: {e}")

    async def _get_cached_candles(
        self, pair: str, timeframe: str
    ) -> Optional[List[Dict]]:
        try:
            r = await _get_redis()
            key = f"candles:{pair}:{timeframe}"
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def _cache_price(self, pair: str, data: Dict) -> None:
        try:
            r = await _get_redis()
            await r.setex(f"price:{pair}", 10, json.dumps(data, default=str))
        except Exception:
            pass

    async def _get_cached_price(self, pair: str) -> Optional[Dict]:
        try:
            r = await _get_redis()
            data = await r.get(f"price:{pair}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def close(self) -> None:
        """Close TwelveData client only — Redis pool is shared (don't close)."""
        await self._twelve.close()


async def close_redis_pool() -> None:
    """Call during app shutdown to close the shared Redis pool."""
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.aclose()
        except Exception:
            pass
        _redis_pool = None
