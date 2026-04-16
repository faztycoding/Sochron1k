"""Layer 1: Market Regime Detection — ADX + ATR + BB Squeeze"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

REGIME_TRENDING = "trending"
REGIME_SIDEWAYS = "sideways"
REGIME_VOLATILE = "volatile"


def detect_regime(indicators: Dict[str, Any]) -> Dict[str, Any]:
    adx = indicators.get("adx")
    atr = indicators.get("atr")
    session_vol = indicators.get("session_vol_index")
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    keltner_upper = indicators.get("keltner_upper")
    keltner_lower = indicators.get("keltner_lower")

    regime = REGIME_SIDEWAYS
    score = 0.5
    details = []

    # ADX check
    if adx is not None:
        if adx > 25:
            regime = REGIME_TRENDING
            score = min(1.0, 0.5 + (adx - 25) / 50)
            details.append(f"ADX={adx:.1f} → เทรนด์ชัดเจน")
        elif adx < 20:
            regime = REGIME_SIDEWAYS
            score = 0.3 + adx / 100
            details.append(f"ADX={adx:.1f} → ตลาด sideways")
        else:
            score = 0.5
            details.append(f"ADX={adx:.1f} → เทรนด์เริ่มก่อตัว")

    # ATR spike → extreme volatility
    if session_vol is not None and session_vol > 2.0:
        regime = REGIME_VOLATILE
        score *= 0.5
        details.append(f"Session Vol={session_vol:.2f}x → ผันผวนผิดปกติ!")
    elif session_vol is not None and session_vol > 1.5:
        details.append(f"Session Vol={session_vol:.2f}x → ผันผวนสูง")

    # Bollinger-Keltner squeeze
    is_squeeze = False
    if all(v is not None for v in [bb_upper, bb_lower, keltner_upper, keltner_lower]):
        bb_width = bb_upper - bb_lower
        kelt_width = keltner_upper - keltner_lower
        if kelt_width > 0 and bb_width < kelt_width:
            is_squeeze = True
            if regime == REGIME_SIDEWAYS:
                details.append("BB Squeeze → พร้อม breakout")
                score = max(score, 0.6)

    # Determine recommended strategy
    strategy = _get_strategy_for_regime(regime, is_squeeze)

    return {
        "regime": regime,
        "regime_score": round(score, 4),
        "is_squeeze": is_squeeze,
        "details": details,
        "recommended_strategy": strategy,
    }


def _get_strategy_for_regime(regime: str, is_squeeze: bool) -> str:
    if regime == REGIME_VOLATILE:
        return "AVOID หรือลด lot size 50%"
    if regime == REGIME_TRENDING:
        return "Trend Following (EMA crossover + ADX)"
    if is_squeeze:
        return "รอ Breakout (BB Squeeze → expansion)"
    return "Mean Reversion (BB bounce + Z-Score)"
