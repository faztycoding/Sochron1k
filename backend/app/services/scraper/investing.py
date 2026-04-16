import logging
from typing import List

from bs4 import BeautifulSoup

from app.services.scraper.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)


class InvestingScraper(BaseScraper):
    source_name = "investing"
    base_url = "https://www.investing.com"

    URLS = [
        "/news/forex-news",
        "/currencies/eur-usd-news",
        "/currencies/usd-jpy-news",
        "/currencies/eur-jpy-news",
    ]

    async def scrape(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        for path in self.URLS:
            url = f"{self.base_url}{path}"
            html = await self.fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            articles = soup.select("article[data-test='article-item'], .articleItem, .js-article-item")

            for article in articles[:10]:
                try:
                    title_el = article.select_one("a.title, a[data-test='article-title-link'], .articleItem__title a")
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    if not self.is_relevant_currency(title):
                        continue

                    link = title_el.get("href", "")
                    if link and not link.startswith("http"):
                        link = f"{self.base_url}{link}"

                    summary_el = article.select_one("p, .articleItem__text")
                    summary = summary_el.get_text(strip=True) if summary_el else ""

                    date_el = article.select_one("time, .articleItem__time, [data-test='article-publish-date']")
                    date_str = date_el.get("datetime", "") if date_el else ""

                    pair = self.detect_pair(title + " " + summary)
                    currency = self.detect_currency(title + " " + summary)

                    items.append(
                        ScrapedItem(
                            source=self.source_name,
                            title=title,
                            content=summary,
                            currency=currency,
                            pair=pair,
                            impact_level="medium",
                            event_time=date_str or None,
                            url=link,
                            raw_data={"path": path},
                        )
                    )
                except Exception as e:
                    logger.debug(f"[investing] Parse error: {e}")
                    continue

        logger.info(f"[investing] Scraped {len(items)} articles")
        return items
