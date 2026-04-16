from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NewsItemResponse(BaseModel):
    id: int
    source: str
    currency: str
    pair: Optional[str] = None
    title_original: str
    title_th: Optional[str] = None
    summary_original: Optional[str] = None
    summary_th: Optional[str] = None
    impact_level: str
    sentiment_score: Optional[float] = None
    event_time: Optional[datetime] = None
    scraped_at: datetime

    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    items: List[NewsItemResponse]
    total: int
    page: int = 1
    per_page: int = 20


class NewsPipelineResult(BaseModel):
    success: bool
    scraped_total: int
    processed_total: int
    urgent_count: int
    saved_count: int
    scraper_status: Dict[str, str]
    duration_seconds: float
    timestamp: str
    urgent_items: List[Dict[str, Any]] = []


class NewsFilter(BaseModel):
    pair: Optional[str] = None
    source: Optional[str] = None
    impact_level: Optional[str] = None
    currency: Optional[str] = None
    limit: int = Field(default=20, le=100, ge=1)
    offset: int = Field(default=0, ge=0)


class ScraperStatusResponse(BaseModel):
    source: str
    status: str
    last_run: Optional[str] = None
    item_count: int = 0
