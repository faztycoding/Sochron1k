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
    "GBP/USD": "GBP/USD",
    "AUD/USD": "AUD/USD",
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
    MAX_CALLS_PER_MIN = 54  # Plan is 55/min — leave 1 credit headroom

    def __init__(self):
        self._settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _check_rate_limit(self, credits: int = 1) -> bool:
        """Return True if we have enough credits left, False if rate limited.

        Twelve Data counts credits per SYMBOL, not per HTTP call. A batch
        /quote with N symbols consumes N credits even though it's 1 HTTP call.
        """
        import time
        now = time.time()
        TwelveDataService._call_times = [t for t in TwelveDataService._call_times if t > now - 60]
        if len(TwelveDataService._call_times) + credits > self.MAX_CALLS_PER_MIN:
            logger.warning(
                f"[twelve_data] Rate limit hit: {len(TwelveDataService._call_times)}+{credits}"
                f" would exceed {self.MAX_CALLS_PER_MIN}/min"
            )
            return False
        for _ in range(credits):
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

    def _parse_quote_row(self, pair: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single TwelveData /quote row into our PriceData shape."""
        price = float(data.get("close", 0) or 0) or float(data.get("price", 0) or 0)
        prev_close = float(data.get("previous_close", 0) or 0)
        day_open = float(data.get("open", 0) or 0)
        day_high = float(data.get("high", 0) or 0)
        day_low = float(data.get("low", 0) or 0)

        is_jpy = "JPY" in pair
        spread_pips = 1.5 if is_jpy else 0.00015
        bid = round(price - spread_pips / 2, 5 if not is_jpy else 3)
        ask = round(price + spread_pips / 2, 5 if not is_jpy else 3)

        return {
            "pair": pair,
            "price": price,
            "bid": bid,
            "ask": ask,
            "spread": round((ask - bid) * (100 if is_jpy else 10000), 1),
            "previous_close": prev_close,
            "change": float(data.get("change", 0) or 0),
            "percent_change": float(data.get("percent_change", 0) or 0),
            "day_open": day_open,
            "day_high": day_high,
            "day_low": day_low,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    async def get_realtime_prices_batch(
        self, pairs: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Batch-fetch all pairs in ONE API call.

        TwelveData /quote accepts comma-separated symbols and returns a
        dict-of-quotes — 1 API credit total instead of N. Critical for
        staying under 50 calls/min rate limit while polling every ~2s.
        """
        if not self._settings.TWELVE_DATA_API_KEY or not pairs:
            return {}
        if not self._check_rate_limit(credits=len(pairs)):
            return {}

        symbols = ",".join(PAIR_MAP.get(p, p) for p in pairs)
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.BASE_URL}/quote",
                params={
                    "symbol": symbols,
                    "apikey": self._settings.TWELVE_DATA_API_KEY,
                },
            )
            response.raise_for_status()
            raw = response.json()

            # Single-symbol response is a flat dict; multi-symbol is dict-of-dicts
            out: Dict[str, Dict[str, Any]] = {}
            if len(pairs) == 1:
                out[pairs[0]] = self._parse_quote_row(pairs[0], raw)
            else:
                for pair in pairs:
                    symbol = PAIR_MAP.get(pair, pair)
                    row = raw.get(symbol) or raw.get(pair)
                    if row and isinstance(row, dict) and not row.get("code"):
                        out[pair] = self._parse_quote_row(pair, row)
            return out
        except Exception as e:
            logger.error(f"[twelve_data] Batch quote error: {e}")
            return {}

    async def get_realtime_price(self, pair: str) -> Optional[Dict[str, Any]]:
        """Single-pair convenience wrapper — prefer batch for N>1."""
        result = await self.get_realtime_prices_batch([pair])
        return result.get(pair)

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
