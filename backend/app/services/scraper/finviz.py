import logging
from typing import List

from bs4 import BeautifulSoup

from app.services.scraper.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)


class FinvizScraper(BaseScraper):
    source_name = "finviz"
    base_url = "https://finviz.com"

    async def scrape(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        url = f"{self.base_url}/forex.ashx"
        html = await self.fetch(url)
        if not html:
            return items

        soup = BeautifulSoup(html, "lxml")

        items.extend(self._parse_heatmap(soup))
        items.extend(self._parse_news(soup))

        logger.info(f"[finviz] Scraped {len(items)} items")
        return items

    def _parse_heatmap(self, soup: BeautifulSoup) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        tables = soup.select("table.t-home-table, table[class*='forex']")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) < 3:
                    continue

                pair_text = cells[0].get_text(strip=True).upper()
                pair_normalized = ""
                for target in ["EUR/USD", "USD/JPY", "EUR/JPY"]:
                    if target.replace("/", "") in pair_text or target in pair_text:
                        pair_normalized = target
                        break

                if not pair_normalized:
                    continue

                price = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                change = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                items.append(
                    ScrapedItem(
                        source=self.source_name,
                        title=f"{pair_normalized} Heatmap: {price} ({change})",
                        content=f"Price: {price}, Change: {change}",
                        currency=self.detect_currency(pair_normalized),
                        pair=pair_normalized,
                        impact_level="low",
                        url=f"{self.base_url}/forex.ashx",
                        raw_data={"price": price, "change": change, "type": "heatmap"},
                    )
                )

        return items

    def _parse_news(self, soup: BeautifulSoup) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        news_rows = soup.select(".news-link-left a, table.t-home-table a[href*='news']")
        for link_el in news_rows[:15]:
            try:
                title = link_el.get_text(strip=True)
                if not self.is_relevant_currency(title):
                    continue

                href = link_el.get("href", "")
                link = href if href.startswith("http") else f"{self.base_url}/{href}"

                items.append(
                    ScrapedItem(
                        source=self.source_name,
                        title=title,
                        content=title,
                        currency=self.detect_currency(title),
                        pair=self.detect_pair(title),
                        impact_level="low",
                        url=link,
                        raw_data={"type": "news"},
                    )
                )
            except Exception as e:
                logger.debug(f"[finviz] Parse news error: {e}")
                continue

        return items
