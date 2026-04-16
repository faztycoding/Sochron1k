"""Kill Switch — 7 conditions to halt signals"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def evaluate_kill_switch(
    news_data: Dict[str, Any],
    indicators: Dict[str, Any],
    regime_data: Dict[str, Any],
    pair: str,
    price: float,
    consecutive_losses: int = 0,
    daily_loss_pct: float = 0.0,
    scraper_failures: int = 0,
) -> Dict[str, Any]:
    triggers: List[Dict[str, str]] = []
    active = False

    # 1. High-impact news within 30 min
    if news_data.get("high_impact_soon"):
        triggers.append({
            "condition": "high_impact_news",
            "message": "ข่าว High Impact ในอีก 30 นาที",
            "action": "PAUSE จนกว่าจะผ่านไป 30 นาทีหลังข่าว",
        })
        active = True

    # 2. ATR > 3x average (extreme volatility)
    svi = indicators.get("session_vol_index")
    if svi is not None and svi > 3.0:
        triggers.append({
            "condition": "extreme_volatility",
            "message": f"ATR สูงกว่าปกติ {svi:.1f}x (>3x)",
            "action": "หยุดเทรด — ตลาดผันผวนรุนแรง",
        })
        active = True

    # 3. Consecutive losses >= 3
    if consecutive_losses >= 3:
        triggers.append({
            "condition": "consecutive_losses",
            "message": f"ขาดทุนติดกัน {consecutive_losses} ครั้ง",
            "action": "Cool-down 24 ชม. — ทบทวน strategy",
        })
        active = True

    # 4. Daily loss > 5%
    if daily_loss_pct > 5.0:
        triggers.append({
            "condition": "daily_loss_limit",
            "message": f"ขาดทุนวันนี้ {daily_loss_pct:.1f}% (>5%)",
            "action": "หยุดเทรดวันนี้",
        })
        active = True

    # 5. BOJ intervention zone
    if "JPY" in pair:
        from app.services.analysis.correlation import check_boj_risk
        boj = check_boj_risk(pair, price)
        if boj["risk"] == "HIGH":
            triggers.append({
                "condition": "boj_intervention",
                "message": boj["message"],
                "action": boj.get("action", "AVOID"),
            })
            active = True

    # 6. Dead Zone (01:00-07:00 TH)
    from app.services.analysis.signal_generator import get_current_session
    session = get_current_session()
    if session.get("is_dead_zone"):
        triggers.append({
            "condition": "dead_zone",
            "message": "ตลาดอยู่ใน Dead Zone (01:00-07:00 TH)",
            "action": "ไม่เทรด — สภาพคล่องต่ำ, whipsaw risk สูง",
        })
        active = True

    # 7. Scraper failures > 2 sources
    if scraper_failures > 2:
        triggers.append({
            "condition": "data_insufficient",
            "message": f"Scraper ล้มเหลว {scraper_failures} sources",
            "action": "ข้อมูลไม่เพียงพอ — หยุดให้สัญญาณ",
        })
        active = True

    return {
        "kill_switch_active": active,
        "triggers": triggers,
        "trigger_count": len(triggers),
        "message": "🛑 Kill Switch ACTIVE — หยุดให้สัญญาณ" if active else "✅ ระบบปกติ",
    }
