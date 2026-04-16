import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

TARGET_PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"]
TARGET_CURRENCIES = ["EUR", "USD", "JPY"]


@dataclass
class ScrapedItem:
    source: str
    title: str
    content: str = ""
    currency: str = ""
    pair: str = ""
    impact_level: str = "low"
    event_time: Optional[str] = None
    url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._last_request: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str) -> None:
        async with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0)
            elapsed = now - last
            delay = random.uniform(self._min_delay, self._max_delay)
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"Rate limit: waiting {wait_time:.1f}s for {domain}")
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()


rate_limiter = RateLimiter()


def get_random_ua() -> str:
    return random.choice(USER_AGENTS)


def get_default_headers() -> Dict[str, str]:
    return {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }


class BaseScraper(ABC):
    source_name: str = "unknown"
    base_url: str = ""
    use_playwright: bool = False

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=get_default_headers(),
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def fetch(self, url: str) -> Optional[str]:
        domain = url.split("/")[2]
        await rate_limiter.wait(domain)
        try:
            client = await self.get_client()
            client.headers.update({"User-Agent": get_random_ua()})
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"[{self.source_name}] HTTP {e.response.status_code}: {url}")
            return None
        except httpx.RequestError as e:
            logger.error(f"[{self.source_name}] Request error: {e}")
            return None

    @abstractmethod
    async def scrape(self) -> List[ScrapedItem]:
        ...

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def is_relevant_currency(self, text: str) -> bool:
        text_upper = text.upper()
        return any(c in text_upper for c in TARGET_CURRENCIES)

    def detect_pair(self, text: str) -> str:
        text_upper = text.upper()
        for pair in TARGET_PAIRS:
            normalized = pair.replace("/", "")
            if pair in text_upper or normalized in text_upper:
                return pair
        return ""

    def detect_currency(self, text: str) -> str:
        text_upper = text.upper()
        found = [c for c in TARGET_CURRENCIES if c in text_upper]
        return ",".join(found) if found else ""
