import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import get_settings, TARGET_PAIRS
from app.services.indicators.builtin import compute_all_builtin
from app.services.indicators.custom import compute_all_custom
from app.services.price.manager import PriceManager

logger = logging.getLogger(__name__)
ANALYSIS_TIMEFRAMES = ["1h", "4h", "1d"]


class IndicatorEngine:
    def __init__(self):
        self._settings = get_settings()
        self._price_manager = PriceManager()

    async def compute_for_pair(
        self,
        pair: str,
        timeframe: str = "1h",
    ) -> Dict[str, Any]:
        # Check indicator cache first (15 min TTL)
        cached = await self._get_cached_snapshot(pair, timeframe)
        if cached and "latest_price" in cached:
            logger.info(f"[engine] Cache hit: {pair} {timeframe}")
            return cached

        raw_candles = await self._price_manager.get_candles(pair, timeframe)
        if not raw_candles:
            logger.warning(f"[engine] No candles for {pair} {timeframe}")
            return {"error": f"ไม่มีข้อมูลราคา {pair} {timeframe}"}

        # Sort oldest→newest for indicator calculations
        candles = sorted(raw_candles, key=lambda c: c.get("open_time", ""))

        # Built-in indicators
        builtin = compute_all_builtin(candles)

        # Custom indicators
        all_pair_candles = {}
        for p in TARGET_PAIRS:
            pc = await self._price_manager.get_candles(p, timeframe, 100)
            if pc:
                all_pair_candles[p] = sorted(pc, key=lambda c: c.get("open_time", ""))

        dxy_closes = await self._get_dxy_closes()
        news_sentiments = await self._get_recent_sentiments(pair)

        # Multi-TF EMA data
        ema_multi_tf = await self._get_multi_tf_emas(pair)

        custom = compute_all_custom(
            pair=pair,
            candles=candles,
            all_pair_candles=all_pair_candles,
            dxy_closes=dxy_closes,
            news_sentiments=news_sentiments,
            ema_data_multi_tf=ema_multi_tf,
        )

        result = {
            "pair": pair,
            "timeframe": timeframe,
            "calculated_at": datetime.now(tz=timezone.utc).isoformat(),
            "candle_count": len(candles),
            "latest_price": float(candles[-1]["close"]),
            **builtin,
            **custom,
        }

        await self._cache_snapshot(pair, timeframe, result)

        return result

    async def compute_all_pairs(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for pair in TARGET_PAIRS:
            results[pair] = {}
            for tf in ANALYSIS_TIMEFRAMES:
                snapshot = await self.compute_for_pair(pair, tf)
                results[pair][tf] = snapshot
        return results

    async def get_quick_summary(self, pair: str) -> Dict[str, Any]:
        snapshot = await self.compute_for_pair(pair, "1h")
        if "error" in snapshot:
            return snapshot

        rsi = snapshot.get("rsi")
        adx = snapshot.get("adx")
        macd_hist = snapshot.get("macd_hist")
        bb_upper = snapshot.get("bb_upper")
        bb_lower = snapshot.get("bb_lower")
        price = snapshot.get("latest_price", 0)
        z_score = snapshot.get("z_score")
        confluence = snapshot.get("multi_tf_confluence", 0)

        signals = []

        # RSI
        if rsi is not None:
            if rsi > 70:
                signals.append({"name": "RSI", "signal": "overbought", "value": rsi, "bias": "bearish"})
            elif rsi < 30:
                signals.append({"name": "RSI", "signal": "oversold", "value": rsi, "bias": "bullish"})

        # MACD
        if macd_hist is not None:
            bias = "bullish" if macd_hist > 0 else "bearish"
            signals.append({"name": "MACD", "signal": "momentum", "value": macd_hist, "bias": bias})

        # ADX (trend strength)
        if adx is not None:
            strength = "trending" if adx > 25 else "ranging"
            signals.append({"name": "ADX", "signal": strength, "value": adx, "bias": "neutral"})

        # BB
        if bb_upper and bb_lower and price:
            if price >= bb_upper:
                signals.append({"name": "Bollinger", "signal": "upper_band", "value": price, "bias": "bearish"})
            elif price <= bb_lower:
                signals.append({"name": "Bollinger", "signal": "lower_band", "value": price, "bias": "bullish"})

        # Z-Score
        if z_score is not None:
            if z_score > 2.0:
                signals.append({"name": "Z-Score", "signal": "overbought", "value": z_score, "bias": "bearish"})
            elif z_score < -2.0:
                signals.append({"name": "Z-Score", "signal": "oversold", "value": z_score, "bias": "bullish"})

        # Multi-TF Confluence
        if abs(confluence) > 50:
            bias = "bullish" if confluence > 0 else "bearish"
            signals.append({"name": "Multi-TF", "signal": "aligned", "value": confluence, "bias": bias})

        bullish = sum(1 for s in signals if s["bias"] == "bullish")
        bearish = sum(1 for s in signals if s["bias"] == "bearish")
        overall = "bullish" if bullish > bearish else "bearish" if bearish > bullish else "neutral"

        return {
            "pair": pair,
            "overall_bias": overall,
            "bullish_signals": bullish,
            "bearish_signals": bearish,
            "signals": signals,
            "snapshot": snapshot,
        }

    async def _get_dxy_closes(self) -> List[float]:
        try:
            from app.services.price.yfinance_fallback import YFinanceFallback

            yf = YFinanceFallback()
            candles = await yf.get_candles("DXY", "1d", 30)
            return [float(c["close"]) for c in candles]
        except Exception:
            return []

    async def _get_recent_sentiments(self, pair: str) -> List[float]:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            keys = await r.lrange("news:latest_keys", 0, -1)
            sentiments = []
            for key in keys[:50]:
                data = await r.get(key)
                if data:
                    item = json.loads(data)
                    if item.get("pair") == pair:
                        score = item.get("sentiment_score", 0)
                        if score != 0:
                            sentiments.append(score)
            await r.aclose()
            return sentiments
        except Exception:
            return []

    async def _get_multi_tf_emas(self, pair: str) -> Dict[str, Dict]:
        ema_data = {}
        for tf in ANALYSIS_TIMEFRAMES:
            cached = await self._get_cached_snapshot(pair, tf)
            if cached:
                ema_data[tf] = {
                    "ema_9": cached.get("ema_9"),
                    "ema_21": cached.get("ema_21"),
                    "ema_50": cached.get("ema_50"),
                }
            else:
                raw = await self._price_manager.get_candles(pair, tf, 60)
                if raw:
                    candles = sorted(raw, key=lambda c: c.get("open_time", ""))
                    builtin = compute_all_builtin(candles)
                    ema_data[tf] = {
                        "ema_9": builtin.get("ema_9"),
                        "ema_21": builtin.get("ema_21"),
                        "ema_50": builtin.get("ema_50"),
                    }
        return ema_data

    async def _cache_snapshot(
        self, pair: str, timeframe: str, data: Dict
    ) -> None:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            key = f"indicators:{pair}:{timeframe}"
            await r.setex(key, 900, json.dumps(data, default=str))
            await r.aclose()
        except Exception as e:
            logger.debug(f"[engine] Cache error: {e}")

    async def _get_cached_snapshot(
        self, pair: str, timeframe: str
    ) -> Optional[Dict]:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)
            data = await r.get(f"indicators:{pair}:{timeframe}")
            await r.aclose()
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def close(self) -> None:
        await self._price_manager.close()
