import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

YFINANCE_SYMBOLS = {
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "USDJPY=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/USD": "GBPUSD=X",
    "AUD/USD": "AUDUSD=X",
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "NIKKEI": "^N225",
}

# In-memory failure cache: {symbol: (failure_count, last_failure_timestamp)}
# Prevents retrying known-broken tickers for FAILURE_COOLDOWN seconds
_FAILURE_CACHE: Dict[str, tuple] = {}
FAILURE_COOLDOWN = 600  # 10 minutes
MAX_FAILURES_BEFORE_CACHE = 2


def _is_symbol_blacklisted(symbol: str) -> bool:
    """Check if symbol recently failed — skip to avoid wasted time."""
    entry = _FAILURE_CACHE.get(symbol)
    if not entry:
        return False
    failures, last_ts = entry
    if failures >= MAX_FAILURES_BEFORE_CACHE:
        if time.time() - last_ts < FAILURE_COOLDOWN:
            return True
        # Cooldown expired — reset
        _FAILURE_CACHE.pop(symbol, None)
    return False


def _record_failure(symbol: str) -> None:
    entry = _FAILURE_CACHE.get(symbol, (0, 0))
    _FAILURE_CACHE[symbol] = (entry[0] + 1, time.time())


def _record_success(symbol: str) -> None:
    _FAILURE_CACHE.pop(symbol, None)

INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "1h",  # yfinance ไม่มี 4h → ดึง 1h แล้วคำนวณเอง
    "1d": "1d",
    "1w": "1wk",
}

PERIOD_MAP = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "1h": "730d",
    "4h": "730d",
    "1d": "2y",
    "1w": "5y",
}


class YFinanceFallback:
    async def get_candles(
        self,
        pair: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        symbol = YFINANCE_SYMBOLS.get(pair, pair.replace("/", "") + "=X")

        # Skip if recently blacklisted (deleted/broken ticker)
        if _is_symbol_blacklisted(symbol):
            logger.debug(f"[yfinance] {symbol} blacklisted — skipping")
            return []

        try:
            import yfinance as yf

            interval = INTERVAL_MAP.get(timeframe, "1h")
            period = PERIOD_MAP.get(timeframe, "730d")

            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                logger.warning(f"[yfinance] No data for {pair} {timeframe}")
                _record_failure(symbol)
                return []

            df = df.tail(limit)
            candles = []

            for idx, row in df.iterrows():
                candles.append({
                    "pair": pair,
                    "timeframe": timeframe,
                    "open_time": idx.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row.get("Volume", 0)),
                })

            if timeframe == "4h" and interval == "1h":
                candles = self._resample_to_4h(candles)

            _record_success(symbol)
            logger.info(f"[yfinance] {pair} {timeframe}: {len(candles)} candles")
            return candles

        except ImportError:
            logger.error("[yfinance] yfinance not installed")
            return []
        except Exception as e:
            _record_failure(symbol)
            logger.error(f"[yfinance] Error: {e}")
            return []

    def _resample_to_4h(self, candles_1h: List[Dict]) -> List[Dict]:
        if not candles_1h:
            return []

        result = []
        chunk = []
        for c in candles_1h:
            chunk.append(c)
            if len(chunk) == 4:
                result.append({
                    "pair": chunk[0]["pair"],
                    "timeframe": "4h",
                    "open_time": chunk[0]["open_time"],
                    "open": chunk[0]["open"],
                    "high": max(x["high"] for x in chunk),
                    "low": min(x["low"] for x in chunk),
                    "close": chunk[-1]["close"],
                    "volume": sum(x["volume"] for x in chunk),
                })
                chunk = []

        return result

    async def get_realtime_price(self, pair: str) -> Optional[Dict[str, Any]]:
        try:
            import yfinance as yf

            symbol = YFINANCE_SYMBOLS.get(pair, pair.replace("/", "") + "=X")
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            return {
                "pair": pair,
                "price": float(info.last_price),
                "previous_close": float(info.previous_close),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"[yfinance] Realtime price error: {e}")
            return None

    async def get_correlation_data(self) -> Dict[str, List[Dict]]:
        symbols = {"DXY": "DXY", "VIX": "VIX", "NIKKEI": "NIKKEI"}
        result = {}
        for name, pair in symbols.items():
            candles = await self.get_candles(pair, "1d", 60)
            result[name] = candles
        return result
