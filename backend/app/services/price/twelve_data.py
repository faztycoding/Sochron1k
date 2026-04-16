import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PAIR_MAP = {
    "EUR/USD": "EUR/USD",
    "USD/JPY": "USD/JPY",
    "EUR/JPY": "EUR/JPY",
}

TIMEFRAME_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1day",
    "1w": "1week",
}


class TwelveDataService:
    BASE_URL = "https://api.twelvedata.com"
    _call_times: list = []
    MAX_CALLS_PER_MIN = 50  # Crow 55 plan: stay under 55 limit

    def __init__(self):
        self._settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _check_rate_limit(self) -> bool:
        """Return True if we can make a call, False if rate limited."""
        import time
        now = time.time()
        TwelveDataService._call_times = [t for t in TwelveDataService._call_times if t > now - 60]
        if len(TwelveDataService._call_times) >= self.MAX_CALLS_PER_MIN:
            logger.warning(f"[twelve_data] Rate limit: {len(TwelveDataService._call_times)}/{self.MAX_CALLS_PER_MIN} calls in last 60s")
            return False
        TwelveDataService._call_times.append(now)
        return True

    async def get_candles(
        self,
        pair: str,
        timeframe: str = "1h",
        outputsize: int = 500,
    ) -> List[Dict[str, Any]]:
        if not self._settings.TWELVE_DATA_API_KEY:
            logger.warning("[twelve_data] No API key — using yfinance fallback")
            return []

        if not self._check_rate_limit():
            return []

        symbol = PAIR_MAP.get(pair, pair)
        interval = TIMEFRAME_MAP.get(timeframe, timeframe)

        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/time_series",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "outputsize": outputsize,
                    "apikey": self._settings.TWELVE_DATA_API_KEY,
                    "format": "JSON",
                    "timezone": "UTC",
                },
            )
            response.raise_for_status()
            data = response.json()

            if "values" not in data:
                logger.error(f"[twelve_data] No values: {data.get('message', 'unknown error')}")
                return []

            candles = []
            for v in data["values"]:
                candles.append({
                    "pair": pair,
                    "timeframe": timeframe,
                    "open_time": v["datetime"],
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                    "volume": float(v.get("volume", 0)),
                })

            logger.info(f"[twelve_data] {pair} {timeframe}: {len(candles)} candles")
            return candles

        except Exception as e:
            logger.error(f"[twelve_data] API error: {e}")
            return []

    async def get_realtime_price(self, pair: str) -> Optional[Dict[str, Any]]:
        if not self._settings.TWELVE_DATA_API_KEY:
            return None

        if not self._check_rate_limit():
            return None

        symbol = PAIR_MAP.get(pair, pair)
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.BASE_URL}/price",
                params={
                    "symbol": symbol,
                    "apikey": self._settings.TWELVE_DATA_API_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()

            return {
                "pair": pair,
                "price": float(data.get("price", 0)),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"[twelve_data] Price error: {e}")
            return None

    async def get_quote(self, pair: str) -> Optional[Dict[str, Any]]:
        if not self._settings.TWELVE_DATA_API_KEY:
            return None

        if not self._check_rate_limit():
            return None

        symbol = PAIR_MAP.get(pair, pair)
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.BASE_URL}/quote",
                params={
                    "symbol": symbol,
                    "apikey": self._settings.TWELVE_DATA_API_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()

            return {
                "pair": pair,
                "open": float(data.get("open", 0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "close": float(data.get("close", 0)),
                "previous_close": float(data.get("previous_close", 0)),
                "change": float(data.get("change", 0)),
                "percent_change": float(data.get("percent_change", 0)),
                "volume": float(data.get("volume", 0)),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"[twelve_data] Quote error: {e}")
            return None

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
