"""Risk meter + countdown calculator for news events.

Produces a structured risk assessment:
  - risk_score (0-100): how risky to trade around this news
  - opportunity_score (0-100): how strong the trading opportunity is
  - warning_active: bool — should UI show "DON'T TRADE NOW"
  - warning_minutes_left: countdown until safe to trade
  - trade_freeze: bool — pre/post news blackout window
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Pre-news blackout window by impact score (minutes before event)
PRE_NEWS_BLACKOUT_MIN = {
    5: 15,  # Critical event: avoid 15 min before
    4: 10,  # High impact: avoid 10 min before
    3: 5,   # Medium impact: avoid 5 min before
    2: 0,   # Low impact: no blackout
    1: 0,
}

# Post-news blackout window (volatility still high right after)
POST_NEWS_BLACKOUT_MIN = {
    5: 30,
    4: 20,
    3: 10,
    2: 0,
    1: 0,
}


def _parse_event_time(event_time_str: Optional[str]) -> Optional[datetime]:
    """Parse event_time string (best-effort) to datetime (UTC).

    Handles formats:
      - ISO 8601: "2026-04-19T22:00:00Z"
      - Forex Factory: "Mon Apr 19 04-19-2026 10:45pm"
      - Just time: "10:45pm"
    """
    if not event_time_str:
        return None

    s = event_time_str.strip()

    # Try ISO 8601
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        pass

    # Try Forex Factory format: "04-19-2026 10:45pm"
    # Extract MM-DD-YYYY + time
    match = re.search(r"(\d{2}-\d{2}-\d{4})\s+(\d{1,2}:\d{2}(?:am|pm)?)", s, re.IGNORECASE)
    if match:
        date_str, time_str = match.groups()
        for fmt in ("%m-%d-%Y %I:%M%p", "%m-%d-%Y %I:%M"):
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


def compute_risk_meter(
    impact_score: int,
    confidence: float,
    event_time: Optional[str] = None,
    actionability: str = "watch",
) -> Dict[str, Any]:
    """Compute risk meter + countdown for a news event.

    Returns dict with:
      - risk_score: 0-100 (higher = more dangerous to trade)
      - opportunity_score: 0-100 (higher = better trading opportunity)
      - warning_active: bool (trade freeze zone)
      - warning_minutes_left: int (minutes until safe, or 0 if not active)
      - minutes_to_event: int (negative = past, 0 = now, positive = future)
      - trade_freeze: bool (should UI disable trade buttons)
      - message_th: Thai user-facing message
    """
    # Risk: scales with impact, dampened by low confidence
    risk_score = min(100, int(impact_score * 20 * (0.5 + confidence / 2)))

    # Opportunity: scales with impact AND confidence AND actionability
    opp_multiplier = {"tradable": 1.0, "watch": 0.6, "ignore": 0.1}.get(actionability, 0.5)
    opportunity_score = min(100, int(impact_score * 20 * confidence * opp_multiplier))

    # Compute countdown if event_time available
    now = datetime.now(tz=timezone.utc)
    event_dt = _parse_event_time(event_time)
    minutes_to_event = None
    warning_active = False
    warning_minutes_left = 0
    trade_freeze = False

    if event_dt:
        delta = event_dt - now
        minutes_to_event = int(delta.total_seconds() / 60)

        pre_window = PRE_NEWS_BLACKOUT_MIN.get(impact_score, 0)
        post_window = POST_NEWS_BLACKOUT_MIN.get(impact_score, 0)

        # Active warning: within pre-news window before OR within post-news window after
        if -post_window <= minutes_to_event <= pre_window:
            warning_active = True
            trade_freeze = True
            if minutes_to_event > 0:
                warning_minutes_left = minutes_to_event
            else:
                # Past event — count down through post-news blackout
                warning_minutes_left = post_window + minutes_to_event

    # Thai message
    message_th = _build_thai_message(
        impact_score=impact_score,
        confidence=confidence,
        minutes_to_event=minutes_to_event,
        warning_active=warning_active,
        actionability=actionability,
    )

    return {
        "risk_score": risk_score,
        "opportunity_score": opportunity_score,
        "warning_active": warning_active,
        "warning_minutes_left": max(0, warning_minutes_left),
        "minutes_to_event": minutes_to_event,
        "trade_freeze": trade_freeze,
        "message_th": message_th,
    }


def _build_thai_message(
    impact_score: int,
    confidence: float,
    minutes_to_event: Optional[int],
    warning_active: bool,
    actionability: str,
) -> str:
    """Build user-facing Thai message based on risk state."""
    if warning_active:
        if minutes_to_event is not None and minutes_to_event > 0:
            return f"⚠️ อย่าเทรด {minutes_to_event} นาทีก่อนข่าว — ความผันผวนสูง"
        elif minutes_to_event is not None and minutes_to_event <= 0:
            post_min = abs(minutes_to_event)
            return f"⏱ ข่าวเพิ่งออก {post_min} นาทีที่แล้ว — รอให้ราคานิ่งก่อน"
        return "⚠️ โซนอันตราย — หลีกเลี่ยงการเทรด"

    if actionability == "ignore":
        return "🚫 ข่าวนี้ไม่ส่งผลต่อตลาด"

    if minutes_to_event is not None and minutes_to_event > 0:
        if minutes_to_event < 60:
            return f"⏰ ข่าวออกใน {minutes_to_event} นาที"
        hours = minutes_to_event // 60
        return f"📅 ข่าวออกใน {hours} ชั่วโมง"

    if impact_score >= 4 and confidence >= 0.7:
        return "✅ โอกาสเทรดที่ดี — มั่นใจสูง"
    if impact_score >= 3:
        return "👀 ติดตามอย่างใกล้ชิด"

    return "ℹ️ ข้อมูลประกอบการตัดสินใจ"
