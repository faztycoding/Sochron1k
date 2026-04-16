import logging
from typing import List

from bs4 import BeautifulSoup

from app.services.scraper.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)


class BabyPipsScraper(BaseScraper):
    source_name = "babypips"
    base_url = "https://www.babypips.com"

    URLS = [
        "/news",
        "/news/forex",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        for path in self.URLS:
            url = f"{self.base_url}{path}"
            html = await self.fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            articles = soup.select(
                "article, .article-card, [class*='ArticleCard'], .post-item"
            )

            for article in articles[:10]:
                try:
                    title_el = article.select_one("h2 a, h3 a, .article-title a, a[class*='title']")
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    if not self.is_relevant_currency(title):
                        continue

                    href = title_el.get("href", "")
                    link = href if href.startswith("http") else f"{self.base_url}{href}"

                    excerpt_el = article.select_one("p, .excerpt, [class*='excerpt']")
                    excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ""

                    date_el = article.select_one("time, [class*='date']")
                    date_str = ""
                    if date_el:
                        date_str = date_el.get("datetime", "") or date_el.get_text(strip=True)

                    combined = title + " " + excerpt
                    pair = self.detect_pair(combined)
                    currency = self.detect_currency(combined)

                    items.append(
                        ScrapedItem(
                            source=self.source_name,
                            title=title,
                            content=excerpt,
                            currency=currency,
                            pair=pair,
                            impact_level="low",
                            event_time=date_str or None,
                            url=link,
                            raw_data={"path": path},
                        )
                    )
                except Exception as e:
                    logger.debug(f"[babypips] Parse error: {e}")
                    continue

        logger.info(f"[babypips] Scraped {len(items)} articles")
        return items
