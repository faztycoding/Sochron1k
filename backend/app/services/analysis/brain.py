"""Analysis Brain — Full 5-layer pipeline orchestrator"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import get_settings
from app.services.analysis.correlation import check_boj_risk, check_correlations
from app.services.analysis.diagnosis import adjust_confidence, run_all_diagnostics
from app.services.analysis.kill_switch import evaluate_kill_switch
from app.services.analysis.regime import detect_regime
from app.services.analysis.sentiment import get_cached_news, score_news_sentiment
from app.services.analysis.signal_generator import (
    compute_final_confidence,
    compute_risk_gate,
    compute_technical_score,
    determine_direction,
    get_current_session,
)

logger = logging.getLogger(__name__)

from app.config import TARGET_PAIRS


class AnalysisBrain:
    def __init__(self):
        self._settings = get_settings()

    async def analyze(
        self,
        pair: str,
        timeframe: str = "1h",
        consecutive_losses: int = 0,
        daily_loss_pct: float = 0.0,
        scraper_failures: int = 0,
    ) -> Dict[str, Any]:
        start = time.time()

        # Get indicator snapshot
        from app.services.indicators.engine import IndicatorEngine
        engine = IndicatorEngine()
        try:
            indicators = await engine.compute_for_pair(pair, timeframe)
        finally:
            await engine.close()

        if "error" in indicators:
            return {"error": indicators["error"], "pair": pair}

        price = indicators.get("latest_price", 0)

        # Layer 1: Market Regime
        regime = detect_regime(indicators)

        # Layer 2: News Sentiment
        news_items = await get_cached_news(self._settings.REDIS_URL, pair)
        news_result = score_news_sentiment(news_items, pair)

        # Layer 3: Technical Confluence
        direction = determine_direction(indicators, news_result.get("sentiment", "neutral"))
        technical = compute_technical_score(indicators, direction)

        # Layer 4: Inter-market Correlation
        market_data = await self._get_market_data()
        pair_closes = await self._get_pair_closes(pair, timeframe)
        correlation = check_correlations(pair, pair_closes, market_data)

        # Layer 5: Risk Gate
        session = get_current_session()
        boj = check_boj_risk(pair, price) if "JPY" in pair else {"risk": "LOW"}
        atr = indicators.get("atr")
        pip_mult = 100 if "JPY" in pair else 10000
        sl_pips = atr * pip_mult * 1.5 if atr else None
        tp_pips = sl_pips * 2 if sl_pips else None

        risk_gate = compute_risk_gate(
            pair, price, atr, sl_pips, tp_pips,
            session, news_result.get("high_impact_soon", False), boj,
        )

        # Confidence
        confidence_data = compute_final_confidence(
            regime["regime_score"],
            news_result["news_score"],
            technical["technical_score"],
            correlation["correlation_score"],
            risk_gate["risk_gate_score"],
        )

        # Self-diagnosis (18 checks)
        duration = time.time() - start
        diagnosis = run_all_diagnostics(
            indicators, news_result, correlation, regime, risk_gate,
            pair, price, duration, consecutive_losses, daily_loss_pct, scraper_failures,
        )

        # Adjust confidence based on diagnostics
        adjusted = adjust_confidence(confidence_data["confidence"], diagnosis["diagnostics"])

        # Kill Switch
        kill_switch = evaluate_kill_switch(
            news_result, indicators, regime, pair, price,
            consecutive_losses, daily_loss_pct, scraper_failures,
        )

        # SL/TP suggestion
        entry = price
        sl = price - (atr * 1.5 if direction == "BUY" else -atr * 1.5) if atr else None
        tp = price + (atr * 3.0 if direction == "BUY" else -atr * 3.0) if atr else None

        result = {
            "pair": pair,
            "timeframe": timeframe,
            "direction": direction,
            "confidence": adjusted,
            "original_confidence": confidence_data["confidence"],
            "strength": confidence_data["strength"],
            "recommendation": confidence_data["recommendation"],
            "confidence_breakdown": confidence_data["breakdown"],
            "regime": regime,
            "news": news_result,
            "technical": technical,
            "correlation": correlation,
            "risk_gate": risk_gate,
            "kill_switch": kill_switch,
            "diagnosis": diagnosis,
            "session": session,
            "suggested_entry": round(entry, 5),
            "suggested_sl": round(sl, 5) if sl else None,
            "suggested_tp": round(tp, 5) if tp else None,
            "sl_pips": round(sl_pips, 1) if sl_pips else None,
            "tp_pips": round(tp_pips, 1) if tp_pips else None,
            "risk_reward": round(tp_pips / sl_pips, 2) if sl_pips and tp_pips else None,
            "price": price,
            "indicators_summary": {
                "rsi": indicators.get("rsi"),
                "adx": indicators.get("adx"),
                "macd_hist": indicators.get("macd_hist"),
                "ema_9": indicators.get("ema_9"),
                "ema_21": indicators.get("ema_21"),
                "atr": indicators.get("atr"),
                "z_score": indicators.get("z_score"),
                "currency_strength": indicators.get("currency_strength"),
            },
            "analysis_duration": round(duration, 2),
            "analyzed_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        # Override if kill switch active
        if kill_switch["kill_switch_active"]:
            result["direction"] = "NO_TRADE"
            result["confidence"] = 0.0
            result["strength"] = "KILLED"
            result["recommendation"] = kill_switch["message"]

        logger.info(
            f"[brain] {pair} {timeframe}: {result['direction']} "
            f"conf={result['confidence']:.2f} regime={regime['regime']} "
            f"({duration:.1f}s)"
        )

        return result

    async def analyze_all_pairs(self) -> Dict[str, Any]:
        results = {}
        for pair in TARGET_PAIRS:
            results[pair] = await self.analyze(pair)
        return results

    async def _get_market_data(self) -> Dict[str, list]:
        try:
            from app.services.price.yfinance_fallback import YFinanceFallback
            yf = YFinanceFallback()
            data = {}
            for symbol in ["DXY", "VIX", "NIKKEI"]:
                candles = await yf.get_candles(symbol, "1d", 30)
                data[symbol] = [float(c["close"]) for c in candles]
            return data
        except Exception as e:
            logger.debug(f"[brain] Market data error: {e}")
            return {}

    async def _get_pair_closes(self, pair: str, tf: str) -> list:
        try:
            from app.services.price.manager import PriceManager
            pm = PriceManager()
            candles = await pm.get_candles(pair, tf, 30)
            await pm.close()
            return [float(c["close"]) for c in candles]
        except Exception:
            return []
