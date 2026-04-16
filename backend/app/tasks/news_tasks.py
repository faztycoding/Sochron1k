import asyncio
import json
import logging
from typing import Any, Dict

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(
    name="app.tasks.news_tasks.scrape_source",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def scrape_source(self, source_name: str) -> Dict[str, Any]:
    logger.info(f"[task] Scraping source: {source_name}")

    async def _do_scrape():
        from app.services.scraper.manager import ScraperManager

        manager = ScraperManager()
        try:
            items = await manager.scrape_source(source_name)
            return {
                "source": source_name,
                "count": len(items),
                "items": [
                    {
                        "title": i.title,
                        "currency": i.currency,
                        "pair": i.pair,
                        "impact": i.impact_level,
                    }
                    for i in items[:20]
                ],
            }
        finally:
            await manager.close_all()

    try:
        return _run_async(_do_scrape())
    except Exception as exc:
        logger.error(f"[task] scrape_source({source_name}) failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.news_tasks.run_full_pipeline",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def run_full_pipeline(self) -> Dict[str, Any]:
    logger.info("[task] Running full news pipeline")

    async def _do_pipeline():
        from app.services.news_pipeline import NewsPipeline

        pipeline = NewsPipeline()
        try:
            return await pipeline.run_full_pipeline()
        finally:
            await pipeline.close()

    try:
        return _run_async(_do_pipeline())
    except Exception as exc:
        logger.error(f"[task] full_pipeline failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.news_tasks.scrape_urgent_check")
def scrape_urgent_check() -> Dict[str, Any]:
    logger.info("[task] Urgent news check (Forex Factory only)")

    async def _do_urgent():
        from app.services.ai.gemini import GeminiService
        from app.services.scraper.forex_factory import ForexFactoryScraper

        scraper = ForexFactoryScraper()
        gemini = GeminiService()

        try:
            items = await scraper.scrape()
            high_impact = [i for i in items if i.impact_level == "high"]

            urgent = []
            for item in high_impact[:5]:
                analysis = await gemini.analyze_news(
                    source=item.source,
                    title=item.title,
                    content=item.content,
                    raw_data=item.raw_data,
                )
                if analysis.get("is_urgent"):
                    urgent.append({
                        "title": item.title,
                        "currency": item.currency,
                        "pair": item.pair,
                        "score": analysis.get("sentiment_score", 0),
                    })

            return {"urgent_count": len(urgent), "urgent_items": urgent}
        finally:
            await scraper.close()

    return _run_async(_do_urgent())
