"""World-class news pipeline with fail-closed analysis + pre-AI filter + semantic dedup.

Flow:
  1. Scrape all sources (ScraperManager)
  2. Pre-AI filter (drop blogs, low-impact regional data)
  3. Semantic dedup (Gemini embeddings, cosine similarity)
  4. Chain-of-Thought analysis (Gemini structured output)
  5. Post-AI filter (hide low confidence/impact)
  6. Thai translation (Claude — only for items passing filter)
  7. Risk meter enrichment + countdown
  8. Cache to Redis + persist to DB
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.ai.claude import ClaudeService
from app.services.ai.dedup import SemanticDeduplicator
from app.services.ai.gemini import GeminiService
from app.services.ai.news_filter import filter_pre_ai, should_show_in_ui
from app.services.ai.risk_meter import compute_risk_meter
from app.services.scraper.base import ScrapedItem
from app.services.scraper.manager import ScraperManager

logger = logging.getLogger(__name__)


class NewsPipeline:
    def __init__(self):
        self._scraper_manager = ScraperManager()
        self._gemini = GeminiService()
        self._claude = ClaudeService()
        self._dedup = SemanticDeduplicator(self._gemini)
        self._settings = get_settings()

    async def run_full_pipeline(self) -> Dict[str, Any]:
        start_time = datetime.now(tz=timezone.utc)
        logger.info("[pipeline] Starting world-class news pipeline...")

        # ============================================================
        # STEP 1: Scrape all sources
        # ============================================================
        scraped_items, scraper_status = await self._scraper_manager.scrape_all()
        logger.info(f"[pipeline] Step 1 (scrape): {len(scraped_items)} items")

        # ============================================================
        # STEP 2: Pre-AI filter (drop obvious noise before AI)
        # ============================================================
        filtered_items = filter_pre_ai(scraped_items)
        logger.info(
            f"[pipeline] Step 2 (pre-filter): {len(filtered_items)}/"
            f"{len(scraped_items)} items"
        )

        if not filtered_items:
            return self._empty_result(start_time, scraper_status, len(scraped_items))

        # ============================================================
        # STEP 3: Semantic dedup (embed + cluster similar news)
        # ============================================================
        deduped_items = await self._dedup.deduplicate(filtered_items)
        logger.info(
            f"[pipeline] Step 3 (semantic dedup): {len(deduped_items)}/"
            f"{len(filtered_items)} unique items"
        )

        # ============================================================
        # STEP 3.5: Priority ranking + cap for API quota respect
        # ============================================================
        # Sort by (impact, recency) — highest impact first, so we spend
        # our Gemini quota on what matters most.
        deduped_items = self._prioritize_items(deduped_items)

        # Cap to max items per run (respect free tier quota: 20/day for gemini-2.5-flash)
        max_per_run = self._settings.NEWS_MAX_ANALYSIS_PER_RUN
        if len(deduped_items) > max_per_run:
            logger.info(
                f"[pipeline] Capping to top {max_per_run}/{len(deduped_items)} "
                f"highest-priority items (API quota respect)"
            )
            deduped_items = deduped_items[:max_per_run]

        # ============================================================
        # STEP 4-6: AI analysis + post-filter + translation (per item)
        # ============================================================
        processed_items = []
        urgent_items = []
        stats = {"analyzed": 0, "hidden_low_conf": 0, "failed": 0}

        for idx, item in enumerate(deduped_items):
            try:
                # Step 4: Gemini CoT analysis (returns None on failure)
                analysis = await self._gemini.analyze_news(
                    source=item.source,
                    title=item.title,
                    content=item.content,
                    raw_data=item.raw_data,
                )

                if analysis is None:
                    stats["failed"] += 1
                    continue  # Fail-closed: skip items with no analysis

                # Step 5: Post-AI filter (hide low-confidence / low-impact)
                if not should_show_in_ui(analysis):
                    stats["hidden_low_conf"] += 1
                    continue

                # Step 6: Build processed result (translation happens here)
                processed = await self._build_result(item, analysis)
                processed_items.append(processed)
                stats["analyzed"] += 1

                if processed.get("is_urgent") or analysis.get("is_urgent"):
                    urgent_items.append(processed)

                # Throttle: 150ms between items (avoid rate limit)
                if idx < len(deduped_items) - 1:
                    await asyncio.sleep(0.15)

            except Exception as e:
                logger.error(f"[pipeline] Error processing '{item.title[:50]}': {e}")
                stats["failed"] += 1

        # ============================================================
        # STEP 7: Cache to Redis
        # ============================================================
        saved_count = await self._cache_results(processed_items)

        end_time = datetime.now(tz=timezone.utc)
        duration = (end_time - start_time).total_seconds()

        result = {
            "success": True,
            "scraped_total": len(scraped_items),
            "filtered_total": len(filtered_items),
            "deduped_total": len(deduped_items),
            "processed_total": len(processed_items),
            "urgent_count": len(urgent_items),
            "saved_count": saved_count,
            "scraper_status": scraper_status,
            "duration_seconds": round(duration, 2),
            "timestamp": start_time.isoformat(),
            "urgent_items": urgent_items[:5],
            "stats": stats,
        }

        logger.info(
            f"[pipeline] Complete in {duration:.1f}s: "
            f"{len(scraped_items)} scraped → "
            f"{len(filtered_items)} filtered → "
            f"{len(deduped_items)} deduped → "
            f"{len(processed_items)} shown "
            f"(hidden {stats['hidden_low_conf']} low-conf, {stats['failed']} failed)"
        )

        return result

    async def _build_result(
        self, item: ScrapedItem, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build final news item dict from scraped + analysis + translation + risk."""
        result = self._item_to_dict(item)

        # Copy analysis fields
        result["sentiment_score"] = analysis.get("sentiment_score", 0.0)
        result["impact_level"] = analysis.get("impact_level", item.impact_level)
        result["impact_score"] = analysis.get("impact_score", 1)
        result["category"] = analysis.get("category", "sentiment")
        result["sentiment"] = analysis.get("sentiment", {})
        result["expected_volatility_pips"] = analysis.get("expected_volatility_pips", 0)
        result["time_horizon"] = analysis.get("time_horizon", "short")
        result["surprise_factor"] = analysis.get("surprise_factor", 0.0)
        result["actionability"] = analysis.get("actionability", "watch")
        result["confidence"] = analysis.get("confidence", 0.0)
        result["summary_original"] = analysis.get("summary", "")
        result["key_takeaway"] = analysis.get("key_takeaway", "")
        result["key_numbers"] = analysis.get("key_numbers", {})
        result["is_urgent"] = analysis.get("is_urgent", False)
        # NEW: reasoning + trade_setup + similar_events (from CoT schema)
        result["reasoning"] = analysis.get("reasoning", {})
        result["trade_setup"] = analysis.get("trade_setup", {})
        result["similar_events"] = analysis.get("similar_events", [])

        # Override pair if AI found relevant ones
        if analysis.get("relevant_pairs"):
            result["pair"] = analysis["relevant_pairs"][0]
            result["relevant_pairs"] = analysis["relevant_pairs"]

        # Compute risk meter (countdown, warning zone)
        result["risk_meter"] = compute_risk_meter(
            impact_score=result["impact_score"],
            confidence=result["confidence"],
            event_time=item.event_time,
            actionability=result["actionability"],
        )

        # Translate to Thai (parallelized)
        title_th, summary_th, takeaway_th = await self._translate_trio(
            item.title,
            analysis.get("summary", ""),
            analysis.get("key_takeaway", ""),
        )
        result["title_th"] = title_th
        result["summary_th"] = summary_th
        result["key_takeaway_th"] = takeaway_th

        return result

    async def _translate_trio(
        self, title: str, summary: str, takeaway: str
    ) -> tuple:
        """Translate title + summary + takeaway in parallel."""
        tasks = []
        tasks.append(self._claude.translate_to_thai(title))
        if summary:
            tasks.append(self._claude.translate_to_thai(summary))
        else:
            tasks.append(asyncio.sleep(0, result=""))
        if takeaway:
            tasks.append(self._claude.translate_to_thai(takeaway))
        else:
            tasks.append(asyncio.sleep(0, result=""))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Handle exceptions
        cleaned = []
        for r in results:
            if isinstance(r, Exception):
                cleaned.append("")
            else:
                cleaned.append(r)
        return cleaned[0], cleaned[1], cleaned[2]

    def _prioritize_items(self, items: List[ScrapedItem]) -> List[ScrapedItem]:
        """Sort items by priority: high-impact first, then recent.

        Scoring:
          - FF high impact: 100
          - FF medium impact: 50
          - Reuters/Bloomberg (tier-1 wires): 40
          - Priority keywords (NFP, CPI, Fed, ECB, BOJ, rate): +30
          - Urgent flag from scraper: +20
        """
        priority_keywords = [
            "nfp", "non-farm", "cpi", "ppi", "gdp", "fed", "fomc", "powell",
            "ecb", "lagarde", "boj", "ueda", "boe", "bailey", "rate decision",
            "rate hike", "rate cut", "intervention", "emergency", "crisis",
        ]

        def score(item: ScrapedItem) -> float:
            s = 0.0
            source = (item.source or "").lower()
            title_lower = (item.title or "").lower()

            # Base source score
            if source in ("forex_factory", "forex_factory_xml"):
                if item.impact_level == "high":
                    s += 100
                elif item.impact_level == "medium":
                    s += 50
                else:
                    s += 10
            elif source in ("reuters", "bloomberg"):
                s += 40
            elif source == "investing":
                s += 30
            elif source == "finviz":
                s += 25
            else:
                s += 15

            # Priority keyword bonus
            for kw in priority_keywords:
                if kw in title_lower:
                    s += 30
                    break

            # Impact multiplier
            if item.impact_level == "high":
                s *= 1.5
            elif item.impact_level == "medium":
                s *= 1.2

            return s

        return sorted(items, key=score, reverse=True)

    def _item_to_dict(self, item: ScrapedItem) -> Dict[str, Any]:
        return {
            "source": item.source,
            "title_original": item.title,
            "title_th": "",
            "content": item.content,
            "summary_original": "",
            "summary_th": "",
            "currency": item.currency,
            "pair": item.pair,
            "impact_level": item.impact_level,
            "sentiment_score": 0.0,
            "event_time": item.event_time,
            "url": item.url,
            "raw_data": item.raw_data,
            "is_urgent": False,
            "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _empty_result(
        self, start_time: datetime, scraper_status: Any, scraped_total: int
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "scraped_total": scraped_total,
            "filtered_total": 0,
            "deduped_total": 0,
            "processed_total": 0,
            "urgent_count": 0,
            "saved_count": 0,
            "scraper_status": scraper_status,
            "duration_seconds": 0,
            "timestamp": start_time.isoformat(),
            "urgent_items": [],
            "stats": {"analyzed": 0, "hidden_low_conf": 0, "failed": 0},
        }

    async def _cache_results(self, items: List[Dict[str, Any]]) -> int:
        if not items:
            return 0

        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(
                self._settings.REDIS_URL, decode_responses=True
            )

            pipe = r.pipeline()
            for item in items:
                key = f"news:{item['source']}:{hash(item['title_original'])}"
                pipe.setex(
                    key, 3600, json.dumps(item, ensure_ascii=False, default=str)
                )

            latest_keys = [
                f"news:{item['source']}:{hash(item['title_original'])}"
                for item in items
            ]
            pipe.delete("news:latest_keys")
            if latest_keys:
                pipe.rpush("news:latest_keys", *latest_keys)
                pipe.expire("news:latest_keys", 3600)

            await pipe.execute()
            await r.aclose()

            logger.info(f"[pipeline] Cached {len(items)} items to Redis")
            return len(items)

        except Exception as e:
            logger.error(f"[pipeline] Redis cache error: {e}")
            return 0

    async def close(self) -> None:
        await self._scraper_manager.close_all()
