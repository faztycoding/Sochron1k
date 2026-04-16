import logging
from typing import List

from bs4 import BeautifulSoup

from app.services.scraper.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)


class TradingViewScraper(BaseScraper):
    source_name = "tradingview"
    base_url = "https://www.tradingview.com"

    IDEA_URLS = [
        "/symbols/EURUSD/ideas/",
        "/symbols/USDJPY/ideas/",
        "/symbols/EURJPY/ideas/",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        for path in self.IDEA_URLS:
            url = f"{self.base_url}{path}"
            html = await self.fetch(url)
            if not html:
                continue

            pair = "EUR/USD"
            if "USDJPY" in path:
                pair = "USD/JPY"
            elif "EURJPY" in path:
                pair = "EUR/JPY"

            soup = BeautifulSoup(html, "lxml")
            idea_cards = soup.select(
                ".tv-widget-idea, .idea-card, [class*='ideaCard'], [class*='IdeaCard']"
            )

            for card in idea_cards[:8]:
                try:
                    title_el = card.select_one(
                        ".tv-widget-idea__title, [class*='title'], h2, h3"
                    )
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)

                    desc_el = card.select_one(
                        ".tv-widget-idea__description, [class*='description'], p"
                    )
                    description = desc_el.get_text(strip=True) if desc_el else ""

                    link_el = card.select_one("a[href]")
                    link = ""
                    if link_el:
                        href = link_el.get("href", "")
                        link = href if href.startswith("http") else f"{self.base_url}{href}"

                    author_el = card.select_one(
                        ".tv-widget-idea__author, [class*='author']"
                    )
                    author = author_el.get_text(strip=True) if author_el else ""

                    items.append(
                        ScrapedItem(
                            source=self.source_name,
                            title=title,
                            content=description,
                            currency=self.detect_currency(pair),
                            pair=pair,
                            impact_level="low",
                            url=link,
                            raw_data={"author": author, "pair_page": path},
                        )
                    )
                except Exception as e:
                    logger.debug(f"[tradingview] Parse error: {e}")
                    continue

        logger.info(f"[tradingview] Scraped {len(items)} ideas")
        return items
