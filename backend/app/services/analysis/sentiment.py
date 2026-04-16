"""Layer 2: News Sentiment Filter"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def score_news_sentiment(
    news_items: List[Dict[str, Any]],
    pair: str,
) -> Dict[str, Any]:
    if not news_items:
        return {
            "news_score": 0.5,
            "sentiment": "neutral",
            "high_impact_soon": False,
            "should_pause": False,
            "details": ["ไม่มีข่าวที่เกี่ยวข้อง"],
        }

    relevant = [n for n in news_items if n.get("pair") == pair or not n.get("pair")]
    if not relevant:
        relevant = news_items

    scores = []
    high_impact_count = 0
    has_upcoming_high = False
    details = []

    now = datetime.now(tz=timezone.utc)

    for item in relevant[:20]:
        sentiment = item.get("sentiment_score", 0.0)
        impact = item.get("impact_level", "low")
        is_urgent = item.get("is_urgent", False)

        weight = 1.0
        if impact == "high":
            weight = 3.0
            high_impact_count += 1
        elif impact == "medium":
            weight = 2.0

        if is_urgent:
            weight *= 1.5

        # Time decay — ข่าวเก่ามีน้ำหนักน้อย
        event_time = item.get("event_time")
        if event_time:
            try:
                if isinstance(event_time, str):
                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                        try:
                            et = datetime.strptime(event_time[:19], fmt)
                            hours_diff = abs((now - et).total_seconds()) / 3600
                            if hours_diff < 1:
                                weight *= 2.0
                                if impact == "high":
                                    has_upcoming_high = True
                            elif hours_diff > 12:
                                weight *= 0.5
                            break
                        except ValueError:
                            continue
            except Exception:
                pass

        scores.append(sentiment * weight)

    if not scores:
        return {
            "news_score": 0.5,
            "sentiment": "neutral",
            "high_impact_soon": False,
            "should_pause": False,
            "details": ["ไม่มีข่าวที่เกี่ยวข้อง"],
        }

    avg_score = sum(scores) / sum(abs(s) for s in scores) if any(scores) else 0
    # Normalize to 0-1
    normalized = (avg_score + 1) / 2  # -1..+1 → 0..1

    if avg_score > 0.5:
        sentiment = "bullish"
        details.append(f"ข่าว Bullish (score={avg_score:.2f})")
    elif avg_score < -0.5:
        sentiment = "bearish"
        details.append(f"ข่าว Bearish (score={avg_score:.2f})")
    else:
        sentiment = "neutral"
        details.append(f"ข่าว Neutral (score={avg_score:.2f})")

    should_pause = has_upcoming_high
    if should_pause:
        details.append("⚠️ ข่าว High Impact ภายใน 1 ชม. → PAUSE")

    details.append(f"ข่าวทั้งหมด {len(relevant)} | High Impact: {high_impact_count}")

    return {
        "news_score": round(normalized, 4),
        "raw_sentiment": round(avg_score, 4),
        "sentiment": sentiment,
        "high_impact_soon": has_upcoming_high,
        "high_impact_count": high_impact_count,
        "should_pause": should_pause,
        "news_count": len(relevant),
        "details": details,
    }


async def get_cached_news(redis_url: str, pair: str) -> List[Dict]:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(redis_url, decode_responses=True)
        keys = await r.lrange("news:latest_keys", 0, -1)
        items = []
        for key in keys:
            data = await r.get(key)
            if data:
                item = json.loads(data)
                if item.get("pair") == pair or not item.get("pair"):
                    items.append(item)
        await r.aclose()
        return items
    except Exception as e:
        logger.error(f"[sentiment] Redis error: {e}")
        return []
