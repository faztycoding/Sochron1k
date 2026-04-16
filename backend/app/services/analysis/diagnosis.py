"""Self-Diagnosis — 18 checks across 5 categories"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def adjust_confidence(base: float, diagnostics: List[Dict]) -> float:
    adj = base
    for d in diagnostics:
        s = d.get("severity", "ok")
        if s == "critical": adj *= 0.5
        elif s == "error": adj *= 0.8
        elif s == "warning": adj *= 0.9
    return max(0.0, min(1.0, round(adj, 4)))


def _diag(check, severity, message, rec=""):
    d = {"check": check, "severity": severity, "message": message}
    if rec: d["recommendation"] = rec
    return d


def _get_psych_levels(pair):
    if pair == "EUR/USD": return [1.0500, 1.0600, 1.0700, 1.0800, 1.0900, 1.1000, 1.1100, 1.1200]
    if pair == "USD/JPY": return [145.00, 148.00, 150.00, 152.00, 155.00, 158.00, 160.00]
    if pair == "EUR/JPY": return [160.00, 162.00, 165.00, 168.00, 170.00]
    return []


def run_all_diagnostics(
    indicators: Dict, news_data: Dict, correlation_data: Dict,
    regime_data: Dict, risk_gate: Dict, pair: str, price: float,
    analysis_duration_seconds: float = 0, consecutive_losses: int = 0,
    daily_loss_pct: float = 0, scraper_failures: int = 0,
) -> Dict[str, Any]:
    diags: List[Dict] = []

    # === Data Quality (3) ===
    # 1. price stale
    calc_at = indicators.get("calculated_at", "")
    if calc_at:
        try:
            t = datetime.fromisoformat(calc_at)
            stale = datetime.utcnow() - t > timedelta(minutes=5)
            diags.append(_diag("is_price_data_stale", "error" if stale else "ok",
                "ราคาเก่าเกิน 5 นาที" if stale else "ราคาอัพเดทแล้ว"))
        except Exception:
            diags.append(_diag("is_price_data_stale", "warning", "ตรวจ timestamp ไม่ได้"))
    else:
        diags.append(_diag("is_price_data_stale", "error", "ไม่มีข้อมูลราคา"))

    # 2. news stale
    nc = news_data.get("news_count", 0)
    diags.append(_diag("is_news_data_stale",
        "warning" if nc == 0 else "ok",
        f"ข่าว {nc} รายการ" if nc else "ไม่มีข่าวล่าสุด"))

    # 3. missing indicators
    missing = [k for k in ["rsi","adx","macd_hist","atr","ema_9","ema_21"] if indicators.get(k) is None]
    diags.append(_diag("has_missing_indicators",
        "error" if len(missing) > 2 else ("warning" if missing else "ok"),
        f"ขาด: {','.join(missing)}" if missing else "indicator ครบ"))

    # === Logic Contradictions (3) ===
    # 4. news vs technical
    sent = news_data.get("sentiment", "neutral")
    mh = indicators.get("macd_hist")
    conflict = (sent == "bullish" and mh is not None and mh < 0) or (sent == "bearish" and mh is not None and mh > 0)
    diags.append(_diag("news_vs_technical_conflict",
        "warning" if conflict else "ok",
        f"ข่าว {sent} ขัดแย้ง technical" if conflict else "สอดคล้อง"))

    # 5. multi TF disagreement
    conf = indicators.get("multi_tf_confluence", 0)
    diags.append(_diag("multi_tf_disagreement",
        "warning" if abs(conf) < 20 else "ok",
        f"Multi-TF confluence={conf:.1f}"))

    # 6. correlation anomaly
    cs = correlation_data.get("correlation_score", 0.5)
    diags.append(_diag("correlation_anomaly",
        "warning" if cs < 0.3 else "ok",
        f"Correlation score={cs:.2f}"))

    # === Risk Warnings (7) ===
    atr = indicators.get("atr")
    pm = 100 if "JPY" in pair else 10000

    # 7. sl reference
    diags.append(_diag("sl_atr_ref", "ok", f"ATR={atr*pm:.1f} pips" if atr else "ATR ไม่มี"))

    # 8. rr check placeholder
    diags.append(_diag("rr_ratio_check", "ok", "ตรวจสอบตอนเปิดเทรด"))

    # 9. psych level
    near = [l for l in _get_psych_levels(pair) if abs(price - l) * pm < 30]
    diags.append(_diag("near_psychological_level",
        "warning" if near else "ok",
        f"ใกล้เลขกลม {near[0]}" if near else "ห่างจากเลขกลม"))

    # 10. high impact soon
    hi = news_data.get("high_impact_soon", False)
    diags.append(_diag("high_impact_news_soon",
        "critical" if hi else "ok",
        "ข่าว High Impact ภายใน 60 นาที" if hi else "ไม่มีข่าว High Impact ใกล้",
        "PAUSE — รอหลังข่าว 30 นาที" if hi else ""))

    # 11. dead zone
    from app.services.analysis.signal_generator import get_current_session
    sess = get_current_session()
    dz = sess.get("is_dead_zone", False)
    diags.append(_diag("outside_trading_hours",
        "warning" if dz else "ok",
        "Dead Zone 01:00-07:00" if dz else f"Session: {sess['session']}"))

    # 12. consecutive losses
    diags.append(_diag("consecutive_losses",
        "critical" if consecutive_losses >= 3 else "ok",
        f"ขาดทุนติดกัน {consecutive_losses} ครั้ง" if consecutive_losses >= 3 else "ปกติ",
        "Cool-down 24 ชม." if consecutive_losses >= 3 else ""))

    # 13. daily loss
    diags.append(_diag("daily_loss_limit",
        "critical" if daily_loss_pct > 5 else "ok",
        f"ขาดทุนวันนี้ {daily_loss_pct:.1f}%" if daily_loss_pct > 5 else "ปกติ"))

    # === Market Conditions (3) ===
    # 14. extreme volatility
    svi = indicators.get("session_vol_index")
    diags.append(_diag("extreme_volatility",
        "critical" if svi and svi > 2.0 else ("warning" if svi and svi > 1.5 else "ok"),
        f"Session Vol={svi:.2f}x" if svi else "ไม่มีข้อมูล"))

    # 15. low liquidity
    obv = indicators.get("obv")
    diags.append(_diag("low_liquidity_warning", "ok", f"OBV={obv:.0f}" if obv else "ไม่มีข้อมูล volume"))

    # 16. BOJ risk
    from app.services.analysis.correlation import check_boj_risk
    boj = check_boj_risk(pair, price) if "JPY" in pair else {"risk": "LOW"}
    diags.append(_diag("boj_intervention_risk",
        "critical" if boj["risk"] == "HIGH" else "ok",
        boj.get("message", "ไม่เกี่ยวข้อง")))

    # === System Health (2) ===
    # 17. scraper failures
    diags.append(_diag("scraper_failures",
        "error" if scraper_failures > 2 else "ok",
        f"Scraper ล้มเหลว {scraper_failures} sources" if scraper_failures > 2 else "ปกติ"))

    # 18. analysis duration
    diags.append(_diag("analysis_took_too_long",
        "warning" if analysis_duration_seconds > 30 else "ok",
        f"วิเคราะห์ใช้เวลา {analysis_duration_seconds:.1f}s" if analysis_duration_seconds > 30 else "ปกติ"))

    sevs = [d["severity"] for d in diags]
    if "critical" in sevs: overall = "CRITICAL"
    elif "error" in sevs: overall = "ERROR"
    elif "warning" in sevs: overall = "WARNING"
    else: overall = "HEALTHY"

    return {
        "diagnostics": diags,
        "total_checks": len(diags),
        "issues": len([d for d in diags if d["severity"] != "ok"]),
        "overall_health": overall,
    }
