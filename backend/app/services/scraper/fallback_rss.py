import logging
import xml.etree.ElementTree as ET
from typing import List

from app.services.scraper.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "investing_rss": "https://www.investing.com/rss/news.rss",
    "babypips_rss": "https://www.babypips.com/feed",
    "tradingview_rss": "https://www.tradingview.com/feed/",
    "fxstreet_rss": "https://www.fxstreet.com/rss",
}


class RSSFallbackScraper(BaseScraper):
    source_name = "rss_fallback"

    async def scrape(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        for feed_name, feed_url in RSS_FEEDS.items():
            try:
                feed_items = await self._parse_feed(feed_name, feed_url)
                items.extend(feed_items)
            except Exception as e:
                logger.error(f"[rss] Failed to parse {feed_name}: {e}")
                continue

        logger.info(f"[rss_fallback] Scraped {len(items)} items total")
        return items

    async def _parse_feed(self, feed_name: str, url: str) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []

        xml_text = await self.fetch(url)
        if not xml_text:
            return items

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"[rss] XML parse error for {feed_name}: {e}")
            return items

        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0 format
        for item in root.findall(".//item"):
            parsed = self._parse_rss_item(item, feed_name)
            if parsed:
                items.append(parsed)

        # Atom format
        for entry in root.findall(".//atom:entry", ns):
            parsed = self._parse_atom_entry(entry, ns, feed_name)
            if parsed:
                items.append(parsed)

        return items[:15]

    def _parse_rss_item(self, item, feed_name: str) -> ScrapedItem:
        title = item.findtext("title") or ""
        if not self.is_relevant_currency(title):
            return None

        description = item.findtext("description") or ""
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate") or ""

        combined = title + " " + description
        return ScrapedItem(
            source=feed_name,
            title=title,
            content=description[:500],
            currency=self.detect_currency(combined),
            pair=self.detect_pair(combined),
            impact_level="low",
            event_time=pub_date or None,
            url=link,
            raw_data={"feed": feed_name, "type": "rss"},
        )

    def _parse_atom_entry(self, entry, ns: dict, feed_name: str) -> ScrapedItem:
        title_el = entry.find("atom:title", ns)
        title = title_el.text if title_el is not None else ""
        if not self.is_relevant_currency(title):
            return None

        summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
        summary = summary_el.text if summary_el is not None else ""

        link_el = entry.find("atom:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""

        updated_el = entry.find("atom:updated", ns)
        updated = updated_el.text if updated_el is not None else ""

        combined = title + " " + summary
        return ScrapedItem(
            source=feed_name,
            title=title,
            content=summary[:500],
            currency=self.detect_currency(combined),
            pair=self.detect_pair(combined),
            impact_level="low",
            event_time=updated or None,
            url=link,
            raw_data={"feed": feed_name, "type": "atom"},
        )
