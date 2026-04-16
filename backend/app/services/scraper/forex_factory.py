import logging
from datetime import datetime
from typing import List, Optional

from app.services.scraper.base import BaseScraper, ScrapedItem, TARGET_CURRENCIES

logger = logging.getLogger(__name__)


class ForexFactoryScraper(BaseScraper):
    source_name = "forex_factory"
    base_url = "https://www.forexfactory.com"
    use_playwright = True

    async def scrape(self) -> List[ScrapedItem]:
        items: List[ScrapedItem] = []
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                await page.goto(
                    f"{self.base_url}/calendar",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await page.wait_for_timeout(3000)

                rows = await page.query_selector_all("tr.calendar__row")
                current_date = ""

                for row in rows:
                    try:
                        item = await self._parse_calendar_row(row, current_date)
                        if item:
                            date_cell = await row.query_selector(".calendar__date")
                            if date_cell:
                                new_date = (await date_cell.inner_text()).strip()
                                if new_date:
                                    current_date = new_date
                            items.append(item)
                    except Exception as e:
                        logger.debug(f"Skipping row: {e}")
                        continue

                await browser.close()

        except ImportError:
            logger.error("Playwright not installed — using fallback")
            items = await self._fallback_xml()
        except Exception as e:
            logger.error(f"[forex_factory] Scrape failed: {e}")
            items = await self._fallback_xml()

        logger.info(f"[forex_factory] Scraped {len(items)} events")
        return items

    async def _parse_calendar_row(
        self, row, current_date: str
    ) -> Optional[ScrapedItem]:
        currency_el = await row.query_selector(".calendar__currency")
        if not currency_el:
            return None

        currency = (await currency_el.inner_text()).strip().upper()
        if currency not in TARGET_CURRENCIES:
            return None

        impact_el = await row.query_selector(".calendar__impact span")
        impact = "low"
        if impact_el:
            impact_class = await impact_el.get_attribute("class") or ""
            if "high" in impact_class:
                impact = "high"
            elif "medium" in impact_class or "moderate" in impact_class:
                impact = "medium"

        event_el = await row.query_selector(".calendar__event")
        event_title = (await event_el.inner_text()).strip() if event_el else "Unknown"

        actual_el = await row.query_selector(".calendar__actual")
        forecast_el = await row.query_selector(".calendar__forecast")
        previous_el = await row.query_selector(".calendar__previous")

        actual = (await actual_el.inner_text()).strip() if actual_el else ""
        forecast = (await forecast_el.inner_text()).strip() if forecast_el else ""
        previous = (await previous_el.inner_text()).strip() if previous_el else ""

        time_el = await row.query_selector(".calendar__time")
        event_time = (await time_el.inner_text()).strip() if time_el else ""

        content = f"Currency: {currency} | Event: {event_title}"
        if actual:
            content += f" | Actual: {actual}"
        if forecast:
            content += f" | Forecast: {forecast}"
        if previous:
            content += f" | Previous: {previous}"

        pair = self._match_pair(currency)

        return ScrapedItem(
            source=self.source_name,
            title=event_title,
            content=content,
            currency=currency,
            pair=pair,
            impact_level=impact,
            event_time=f"{current_date} {event_time}".strip() if event_time else None,
            url=f"{self.base_url}/calendar",
            raw_data={
                "actual": actual,
                "forecast": forecast,
                "previous": previous,
                "currency": currency,
                "impact": impact,
            },
        )

    def _match_pair(self, currency: str) -> str:
        pair_map = {
            "EUR": "EUR/USD",
            "USD": "USD/JPY",
            "JPY": "USD/JPY",
        }
        return pair_map.get(currency, "")

    async def _fallback_xml(self) -> List[ScrapedItem]:
        logger.info("[forex_factory] Using XML calendar fallback")
        items: List[ScrapedItem] = []
        try:
            import xml.etree.ElementTree as ET

            html = await self.fetch("https://nfs.faireconomy.media/ff_calendar_thisweek.xml")
            if not html:
                return items

            root = ET.fromstring(html)
            for event in root.findall(".//event"):
                currency = (event.findtext("country") or "").strip().upper()
                if currency not in TARGET_CURRENCIES:
                    continue

                title = event.findtext("title") or "Unknown"
                impact = (event.findtext("impact") or "low").strip().lower()
                if impact not in ("high", "medium", "low"):
                    impact = "low"

                actual = event.findtext("actual") or ""
                forecast = event.findtext("forecast") or ""
                previous = event.findtext("previous") or ""
                date_str = event.findtext("date") or ""
                time_str = event.findtext("time") or ""

                content = f"Currency: {currency} | Event: {title}"
                if actual:
                    content += f" | Actual: {actual}"
                if forecast:
                    content += f" | Forecast: {forecast}"

                items.append(
                    ScrapedItem(
                        source="forex_factory_xml",
                        title=title,
                        content=content,
                        currency=currency,
                        pair=self._match_pair(currency),
                        impact_level=impact,
                        event_time=f"{date_str} {time_str}".strip() or None,
                        url="https://www.forexfactory.com/calendar",
                        raw_data={
                            "actual": actual,
                            "forecast": forecast,
                            "previous": previous,
                        },
                    )
                )
        except Exception as e:
            logger.error(f"[forex_factory] XML fallback failed: {e}")

        return items
