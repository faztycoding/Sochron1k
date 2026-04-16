import asyncio
import logging
from typing import Dict, List, Tuple

from app.services.scraper.babypips import BabyPipsScraper
from app.services.scraper.base import BaseScraper, ScrapedItem
from app.services.scraper.fallback_rss import RSSFallbackScraper
from app.services.scraper.finviz import FinvizScraper
from app.services.scraper.forex_factory import ForexFactoryScraper
from app.services.scraper.investing import InvestingScraper
from app.services.scraper.tradingview import TradingViewScraper

logger = logging.getLogger(__name__)


class ScraperManager:
    def __init__(self):
        self._scrapers: Dict[str, BaseScraper] = {
            "forex_factory": ForexFactoryScraper(),
            "investing": InvestingScraper(),
            "tradingview": TradingViewScraper(),
            "babypips": BabyPipsScraper(),
            "finviz": FinvizScraper(),
        }
        self._fallback = RSSFallbackScraper()

    async def scrape_all(self) -> Tuple[List[ScrapedItem], Dict[str, str]]:
        results: List[ScrapedItem] = []
        status: Dict[str, str] = {}

        tasks = {
            name: asyncio.create_task(self._safe_scrape(name, scraper))
            for name, scraper in self._scrapers.items()
        }

        for name, task in tasks.items():
            try:
                items = await task
                results.extend(items)
                status[name] = f"สำเร็จ ({len(items)} รายการ)"
            except Exception as e:
                logger.error(f"[manager] {name} failed: {e}")
                status[name] = f"ล้มเหลว: {str(e)[:100]}"

        if not results:
            logger.warning("[manager] All scrapers failed — using RSS fallback")
            try:
                fallback_items = await self._fallback.scrape()
                results.extend(fallback_items)
                status["rss_fallback"] = f"สำเร็จ ({len(fallback_items)} รายการ)"
            except Exception as e:
                status["rss_fallback"] = f"ล้มเหลว: {str(e)[:100]}"

        logger.info(f"[manager] Total scraped: {len(results)} items from {len(status)} sources")
        return results, status

    async def scrape_source(self, source_name: str) -> List[ScrapedItem]:
        scraper = self._scrapers.get(source_name)
        if not scraper:
            raise ValueError(f"Unknown source: {source_name}")
        return await scraper.scrape()

    async def _safe_scrape(self, name: str, scraper: BaseScraper) -> List[ScrapedItem]:
        try:
            items = await scraper.scrape()
            return items
        except Exception as e:
            logger.error(f"[{name}] Scrape error: {e}")
            if name == "forex_factory":
                logger.info(f"[{name}] Attempting RSS fallback")
                return await self._fallback.scrape()
            return []

    async def close_all(self) -> None:
        for scraper in self._scrapers.values():
            await scraper.close()
        await self._fallback.close()
