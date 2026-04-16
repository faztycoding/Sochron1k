import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.ai.claude import ClaudeService
from app.services.ai.gemini import GeminiService
from app.services.scraper.base import ScrapedItem
from app.services.scraper.manager import ScraperManager

logger = logging.getLogger(__name__)


class NewsPipeline:
    def __init__(self):
        self._scraper_manager = ScraperManager()
        self._gemini = GeminiService()
        self._claude = ClaudeService()
        self._settings = get_settings()

    async def run_full_pipeline(self) -> Dict[str, Any]:
        start_time = datetime.utcnow()

        logger.info("[pipeline] Starting full news pipeline...")

        # Step 1: Scrape all sources
        scraped_items, scraper_status = await self._scraper_manager.scrape_all()
        logger.info(f"[pipeline] Step 1 done: {len(scraped_items)} items scraped")

        # Step 2: AI analysis + translation
        processed_items = []
        urgent_items = []

        for item in scraped_items:
            try:
                processed = await self._process_item(item)
                processed_items.append(processed)

                if processed.get("is_urgent"):
                    urgent_items.append(processed)
            except Exception as e:
                logger.error(f"[pipeline] Process error for '{item.title[:50]}': {e}")
                processed_items.append(self._item_to_dict(item))

        # Step 3: Save to DB (via Redis cache first for speed)
        saved_count = await self._cache_results(processed_items)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        result = {
            "success": True,
            "scraped_total": len(scraped_items),
            "processed_total": len(processed_items),
            "urgent_count": len(urgent_items),
            "saved_count": saved_count,
            "scraper_status": scraper_status,
            "duration_seconds": round(duration, 2),
            "timestamp": start_time.isoformat(),
            "urgent_items": urgent_items[:5],
        }

        logger.info(
            f"[pipeline] Complete: {len(processed_items)} items, "
            f"{len(urgent_items)} urgent, {duration:.1f}s"
        )

        return result

    async def _process_item(self, item: ScrapedItem) -> Dict[str, Any]:
        result = self._item_to_dict(item)

        # Gemini analysis
        analysis = await self._gemini.analyze_news(
            source=item.source,
            title=item.title,
            content=item.content,
            raw_data=item.raw_data,
        )

        result["sentiment_score"] = analysis.get("sentiment_score", 0.0)
        result["impact_level"] = analysis.get("impact_level", item.impact_level)
        result["summary_original"] = analysis.get("summary", item.content[:300])
        result["is_urgent"] = analysis.get("is_urgent", False)
        result["ai_analysis"] = analysis

        # Claude translation
        title_th, summary_th = await self._claude.translate_title_and_summary(
            item.title,
            analysis.get("summary", item.content[:300]),
        )
        result["title_th"] = title_th
        result["summary_th"] = summary_th

        if analysis.get("relevant_pairs"):
            result["pair"] = analysis["relevant_pairs"][0]

        return result

    def _item_to_dict(self, item: ScrapedItem) -> Dict[str, Any]:
        return {
            "source": item.source,
            "title_original": item.title,
            "title_th": "",
            "content": item.content,
            "summary_original": item.content[:300],
            "summary_th": "",
            "currency": item.currency,
            "pair": item.pair,
            "impact_level": item.impact_level,
            "sentiment_score": 0.0,
            "event_time": item.event_time,
            "url": item.url,
            "raw_data": item.raw_data,
            "is_urgent": False,
            "scraped_at": datetime.utcnow().isoformat(),
        }

    async def _cache_results(self, items: List[Dict[str, Any]]) -> int:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._settings.REDIS_URL, decode_responses=True)

            pipe = r.pipeline()
            for item in items:
                key = f"news:{item['source']}:{hash(item['title_original'])}"
                pipe.setex(key, 3600, json.dumps(item, ensure_ascii=False, default=str))

            # Also store latest news list
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
