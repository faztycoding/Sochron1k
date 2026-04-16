"""5-Layer Analysis Pipeline + Confidence Scoring"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# เวลาไทย (GMT+7)
TRADING_SESSIONS = {
    "tokyo_fix": (0, 1),      # 07:00-08:00 TH → 00:00-01:00 UTC
    "asian": (1, 7),           # 08:00-14:00 TH
    "london_open": (7, 8),     # 14:00-15:00 TH
    "london": (8, 12),         # 15:00-19:00 TH
    "ny_overlap": (12, 15),    # 19:00-22:00 TH
    "ny": (15, 18),            # 22:00-01:00 TH
    "dead_zone": (18, 24),     # 01:00-07:00 TH
}


def get_current_session() -> Dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    hour = now.hour

    for session, (start, end) in TRADING_SESSIONS.items():
        if start <= hour < end:
            is_dead = session == "dead_zone"
            return {
                "session": session,
                "is_dead_zone": is_dead,
                "utc_hour": hour,
                "thai_hour": (hour + 7) % 24,
            }

    return {"session": "unknown", "is_dead_zone": False, "utc_hour": hour, "thai_hour": (hour + 7) % 24}


def compute_technical_score(indicators: Dict[str, Any], direction: str) -> Dict[str, Any]:
    """Layer 3: Technical Indicator Confluence"""
    agreements = 0
    total = 0
    signals = []

    is_buy = direction == "BUY"

    # EMA alignment
    ema9 = indicators.get("ema_9")
    ema21 = indicators.get("ema_21")
    ema50 = indicators.get("ema_50")
    ema200 = indicators.get("ema_200")

    if all(v is not None for v in [ema9, ema21, ema50]):
        total += 1
        if is_buy and ema9 > ema21 > ema50:
            agreements += 1
            signals.append("EMA alignment bullish ✓")
        elif not is_buy and ema9 < ema21 < ema50:
            agreements += 1
            signals.append("EMA alignment bearish ✓")
        else:
            signals.append("EMA ไม่ align")

    # RSI
    rsi = indicators.get("rsi")
    if rsi is not None:
        total += 1
        if is_buy and rsi < 70:
            agreements += 1
            signals.append(f"RSI={rsi:.1f} ไม่ overbought ✓")
        elif not is_buy and rsi > 30:
            agreements += 1
            signals.append(f"RSI={rsi:.1f} ไม่ oversold ✓")
        else:
            signals.append(f"RSI={rsi:.1f} ⚠️")

    # MACD
    macd_hist = indicators.get("macd_hist")
    if macd_hist is not None:
        total += 1
        if (is_buy and macd_hist > 0) or (not is_buy and macd_hist < 0):
            agreements += 1
            signals.append(f"MACD hist={macd_hist:.5f} ยืนยัน ✓")
        else:
            signals.append(f"MACD hist={macd_hist:.5f} ขัดแย้ง")

    # Multi-TF
    confluence = indicators.get("multi_tf_confluence", 0)
    if confluence != 0:
        total += 1
        if (is_buy and confluence > 30) or (not is_buy and confluence < -30):
            agreements += 1
            signals.append(f"Multi-TF={confluence:.1f} ยืนยัน ✓")
        else:
            signals.append(f"Multi-TF={confluence:.1f} ไม่ยืนยัน")

    # Stochastic
    stoch_k = indicators.get("stoch_k")
    if stoch_k is not None:
        total += 1
        if (is_buy and stoch_k < 80) or (not is_buy and stoch_k > 20):
            agreements += 1
            signals.append(f"Stoch K={stoch_k:.1f} ✓")

    score = agreements / total if total > 0 else 0.5

    return {
        "technical_score": round(score, 4),
        "agreements": agreements,
        "total_checks": total,
        "signals": signals,
    }


def compute_risk_gate(
    pair: str,
    price: float,
    atr: Optional[float],
    sl_pips: Optional[float],
    tp_pips: Optional[float],
    session: Dict[str, Any],
    high_impact_soon: bool,
    boj_risk: Dict[str, Any],
) -> Dict[str, Any]:
    """Layer 5: Risk Gate"""
    passes = 0
    total = 0
    details = []

    # R:R ratio >= 1:2
    total += 1
    if sl_pips and tp_pips and sl_pips > 0:
        rr = tp_pips / sl_pips
        if rr >= 2.0:
            passes += 1
            details.append(f"R:R = 1:{rr:.1f} ✓")
        elif rr >= 1.5:
            passes += 0.5
            details.append(f"R:R = 1:{rr:.1f} พอได้")
        else:
            details.append(f"R:R = 1:{rr:.1f} ✗ ต่ำเกินไป")
    else:
        passes += 0.5
        details.append("R:R ยังไม่ได้คำนวณ")

    # ATR-based SL check
    if atr and sl_pips:
        total += 1
        pip_mult = 100 if "JPY" in pair else 10000
        atr_pips = atr * pip_mult
        if 1.0 * atr_pips <= sl_pips <= 3.0 * atr_pips:
            passes += 1
            details.append(f"SL={sl_pips:.0f} อยู่ใน ATR range ✓")
        else:
            details.append(f"SL={sl_pips:.0f} นอก ATR range (ATR={atr_pips:.0f})")

    # Active session check
    total += 1
    if not session.get("is_dead_zone"):
        passes += 1
        details.append(f"Session: {session.get('session')} ✓")
    else:
        details.append("Dead Zone (01:00-07:00) ✗ → AVOID")

    # BOJ check
    if "JPY" in pair:
        total += 1
        if boj_risk.get("risk") == "LOW":
            passes += 1
            details.append("BOJ risk: LOW ✓")
        else:
            details.append(f"BOJ risk: HIGH ✗ — {boj_risk.get('message', '')}")

    # High impact news check
    total += 1
    if not high_impact_soon:
        passes += 1
        details.append("ไม่มีข่าว High Impact ใกล้ ✓")
    else:
        details.append("⚠️ ข่าว High Impact ภายใน 60 นาที → PAUSE")

    score = passes / total if total > 0 else 0.5

    return {
        "risk_gate_score": round(score, 4),
        "passes": passes,
        "total_checks": total,
        "details": details,
    }


def determine_direction(indicators: Dict[str, Any], news_sentiment: str) -> str:
    bullish = 0
    bearish = 0

    ema9 = indicators.get("ema_9")
    ema21 = indicators.get("ema_21")
    if ema9 and ema21:
        if ema9 > ema21:
            bullish += 1
        else:
            bearish += 1

    macd_hist = indicators.get("macd_hist")
    if macd_hist is not None:
        if macd_hist > 0:
            bullish += 1
        else:
            bearish += 1

    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi < 50:
            bearish += 1
        else:
            bullish += 1

    if news_sentiment == "bullish":
        bullish += 1
    elif news_sentiment == "bearish":
        bearish += 1

    return "BUY" if bullish > bearish else "SELL"


def compute_final_confidence(
    regime_score: float,
    news_score: float,
    technical_score: float,
    correlation_score: float,
    risk_gate_score: float,
) -> Dict[str, Any]:
    confidence = (
        regime_score * 0.15
        + news_score * 0.25
        + technical_score * 0.35
        + correlation_score * 0.15
        + risk_gate_score * 0.10
    )

    confidence = max(0.0, min(1.0, confidence))

    if confidence >= 0.75:
        strength = "STRONG"
        recommendation = "แนะนำเทรด — สัญญาณชัดเจน"
    elif confidence >= 0.50:
        strength = "MODERATE"
        recommendation = "เทรดได้แต่ระวัง — ลด lot size"
    else:
        strength = "WEAK"
        recommendation = "ไม่แนะนำเทรด — สัญญาณไม่ชัด"

    return {
        "confidence": round(confidence, 4),
        "strength": strength,
        "recommendation": recommendation,
        "breakdown": {
            "regime": round(regime_score * 0.15, 4),
            "news": round(news_score * 0.25, 4),
            "technical": round(technical_score * 0.35, 4),
            "correlation": round(correlation_score * 0.15, 4),
            "risk_gate": round(risk_gate_score * 0.10, 4),
        },
    }
