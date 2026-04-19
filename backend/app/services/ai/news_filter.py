"""Pre-AI news filtering layer.

Drops noise BEFORE sending to Gemini — saves tokens + reduces UI clutter.
Rules:
  1. Blacklist sources: TradingView, BabyPips blogs (educational content)
  2. Blacklist events: minor regional data (Rightmove HPI, etc.)
  3. Blacklist keywords: "opinion", "my view", "chart pattern", etc.
  4. Forex Factory: drop impact="low"
"""
import logging
import re
from typing import List

from app.services.scraper.base import ScrapedItem

logger = logging.getLogger(__name__)

# ============================================================
# BLACKLISTS
# ============================================================

# Sources that are pure educational/analysis blogs → always drop
BLACKLISTED_SOURCES = {
    "tradingview",  # Chart analysis blogs
    "babypips",     # Educational content
}

# Event name substrings that indicate low-impact regional data
# (case-insensitive match on title)
LOW_IMPACT_EVENT_PATTERNS = [
    r"rightmove.*hpi",
    r"tertiary industry",
    r"current account.*adjustment",
    r"preliminary.*gfk",
    r"m3 money supply",
    r"prelim.*flash",  # preliminary flash estimates often pre-announced
    r"leading index",
    r"producer inflation",  # less impactful than CPI
    r"housing starts",
    r"building permits",
    r"existing home sales",
    r"new home sales",
    r"pending home sales",
    r"construction spending",
    r"factory orders",
    r"wholesale inventories",
    r"business inventories",
    r"chicago pmi",  # regional, less impact than ISM
    r"philadelphia fed",  # regional
    r"kansas fed",  # regional
    r"richmond fed",  # regional
    r"empire state",  # regional (NY Fed)
    r"dallas fed",  # regional
]

# Keywords in title/content indicating opinion/blog (not event)
BLOG_KEYWORDS = [
    "opinion",
    "my view",
    "i think",
    "my analysis",
    "chart pattern",
    "idea trading",
    "trading idea",
    "setup of the day",
    "weekly outlook",
    "daily outlook",
    "technical analysis",
    "forecast and analysis",
    "price action",
    "support and resistance",
    "fibonacci",
    "elliott wave",
    "harmonic pattern",
    "smart money concept",
    "liquidity sweep",
    "order block",
    "fair value gap",
    "break of structure",
    "change of character",
]

# High-value events that should ALWAYS pass (even if above patterns match)
PRIORITY_EVENTS = [
    "nfp",
    "non-farm",
    "non farm",
    "cpi",
    "core cpi",
    "pce",
    "core pce",
    "gdp",
    "retail sales",
    "ism manufacturing",
    "ism services",
    "unemployment rate",
    "unemployment claims",
    "jobless claims",
    "average earnings",
    "wage growth",
    "fed rate",
    "federal funds",
    "fomc",
    "powell",
    "ecb rate",
    "lagarde",
    "boj",
    "ueda",
    "boe",
    "bailey",
    "rba",
    "rate decision",
    "rate hike",
    "rate cut",
    "rate hold",
    "rate pause",
    "interest rate",
    "monetary policy",
    "press conference",
    "minutes",  # FOMC minutes, ECB minutes
    "trade balance",
    "current account",
    "ppi",
    "import prices",
    "consumer confidence",
    "michigan sentiment",
    "zew",
    "ifo",
    "sentix",
    "pmi manufacturing",
    "pmi services",
    "pmi composite",
    "hpi",  # House price index (national only)
]


def _is_blog_content(title: str, content: str) -> bool:
    """Check if item is a blog/educational post (not an event)."""
    text = f"{title} {content[:500]}".lower()
    # Must match blog keyword AND not be a priority event
    for kw in BLOG_KEYWORDS:
        if kw in text:
            # Check if it mentions a priority event that overrides
            if any(priority in text for priority in PRIORITY_EVENTS):
                return False
            return True
    return False


def _is_low_impact_event(title: str) -> bool:
    """Check if title matches a low-impact regional data pattern."""
    title_lower = title.lower()
    for pattern in LOW_IMPACT_EVENT_PATTERNS:
        if re.search(pattern, title_lower):
            return True
    return False


def _is_priority_event(title: str, content: str) -> bool:
    """Check if item mentions a high-value event that must pass."""
    text = f"{title} {content[:300]}".lower()
    return any(kw in text for kw in PRIORITY_EVENTS)


def filter_pre_ai(items: List[ScrapedItem]) -> List[ScrapedItem]:
    """Filter scraped items BEFORE sending to Gemini.

    Drops:
      - Blacklisted sources (TradingView, BabyPips)
      - Forex Factory low-impact events (unless priority)
      - Blog/opinion content
      - Low-impact regional data (unless priority)

    Returns filtered list. Logs stats for monitoring.
    """
    if not items:
        return []

    kept: List[ScrapedItem] = []
    dropped_stats = {
        "blacklisted_source": 0,
        "blog_content": 0,
        "low_impact_event": 0,
        "ff_low_impact": 0,
    }

    for item in items:
        source_lower = (item.source or "").lower()

        # Rule 1: Drop blacklisted sources entirely
        if source_lower in BLACKLISTED_SOURCES:
            dropped_stats["blacklisted_source"] += 1
            continue

        # Rule 2: Forex Factory explicit low-impact → drop (unless priority)
        if source_lower in ("forex_factory", "forex_factory_xml"):
            if item.impact_level == "low" and not _is_priority_event(item.title, item.content):
                dropped_stats["ff_low_impact"] += 1
                continue

        # Rule 3: Blog/opinion content → drop
        if _is_blog_content(item.title, item.content):
            dropped_stats["blog_content"] += 1
            continue

        # Rule 4: Low-impact regional data → drop (unless priority)
        if _is_low_impact_event(item.title) and not _is_priority_event(item.title, item.content):
            dropped_stats["low_impact_event"] += 1
            continue

        kept.append(item)

    total_dropped = sum(dropped_stats.values())
    logger.info(
        f"[news_filter] Kept {len(kept)}/{len(items)} items "
        f"(dropped {total_dropped}: "
        f"{dropped_stats['blacklisted_source']} blacklisted, "
        f"{dropped_stats['blog_content']} blogs, "
        f"{dropped_stats['ff_low_impact']} FF-low, "
        f"{dropped_stats['low_impact_event']} low-regional)"
    )
    return kept


def should_show_in_ui(analysis: dict) -> bool:
    """Post-AI filter: hide analysis that's unreliable/low-impact.

    Rules:
      - confidence < 0.5 → hide (uncertain)
      - impact_score < 2 → hide (noise)
      - actionability == "ignore" → hide
      - category == "technical_blog" → hide
    """
    if not analysis:
        return False

    confidence = analysis.get("confidence", 0.0)
    impact_score = analysis.get("impact_score", 0)
    actionability = analysis.get("actionability", "")
    category = analysis.get("category", "")

    if confidence < 0.5:
        return False
    if impact_score < 2:
        return False
    if actionability == "ignore":
        return False
    if category == "technical_blog":
        return False

    return True
