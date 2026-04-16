import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.models.schemas.news import (
    NewsFilter,
    NewsListResponse,
    NewsPipelineResult,
    ScraperStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["ข่าว"])


@router.get("", summary="ดึงข่าวล่าสุดจาก Cache")
async def get_news(
    pair: Optional[str] = Query(None, description="คู่สกุลเงิน เช่น EUR/USD"),
    source: Optional[str] = Query(None, description="แหล่งข่าว เช่น forex_factory"),
    impact: Optional[str] = Query(None, description="ระดับผลกระทบ: high/medium/low"),
    limit: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

        keys = await r.lrange("news:latest_keys", 0, -1)
        if not keys:
            return {"items": [], "total": 0, "message": "ยังไม่มีข่าว — กดอัพเดทข่าวก่อน"}

        items = []
        for key in keys:
            data = await r.get(key)
            if data:
                item = json.loads(data)
                if pair and item.get("pair") != pair:
                    continue
                if source and item.get("source") != source:
                    continue
                if impact and item.get("impact_level") != impact:
                    continue
                items.append(item)

        await r.aclose()

        items.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)
        items = items[:limit]

        return {"items": items, "total": len(items)}

    except Exception as e:
        logger.error(f"[news] Get news error: {e}")
        return {"items": [], "total": 0, "error": str(e)}


@router.post("/refresh", summary="อัพเดทข่าวจากทุกแหล่ง + AI วิเคราะห์")
async def refresh_news() -> NewsPipelineResult:
    from app.services.news_pipeline import NewsPipeline

    pipeline = NewsPipeline()
    try:
        result = await pipeline.run_full_pipeline()
        return NewsPipelineResult(**result)
    except Exception as e:
        logger.error(f"[news] Refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"อัพเดทข่าวล้มเหลว: {str(e)}")
    finally:
        await pipeline.close()


@router.post("/refresh/{source_name}", summary="อัพเดทข่าวจากแหล่งเดียว")
async def refresh_source(source_name: str) -> Dict[str, Any]:
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[news] Refresh {source_name} error: {e}")
        raise HTTPException(status_code=500, detail=f"ดึงข่าวล้มเหลว: {str(e)}")
    finally:
        await manager.close_all()


@router.get("/sources", summary="ดูสถานะ scrapers ทั้งหมด")
async def get_scraper_status() -> List[Dict[str, str]]:
    sources = [
        {"source": "forex_factory", "method": "Playwright", "frequency": "ทุก 3 นาที"},
        {"source": "investing", "method": "httpx + BS4", "frequency": "ทุก 1 ชม."},
        {"source": "tradingview", "method": "httpx + BS4", "frequency": "ทุก 2 ชม."},
        {"source": "babypips", "method": "httpx + BS4", "frequency": "ทุก 2 ชม."},
        {"source": "finviz", "method": "httpx + BS4", "frequency": "ทุก 1 ชม."},
        {"source": "rss_fallback", "method": "RSS/XML", "frequency": "เมื่อ scraper หลักล้มเหลว"},
    ]
    return sources


@router.get("/urgent", summary="ข่าวด่วนที่ส่งผลต่อตลาด")
async def get_urgent_news(
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        keys = await r.lrange("news:latest_keys", 0, -1)

        urgent = []
        for key in keys:
            data = await r.get(key)
            if data:
                item = json.loads(data)
                if item.get("is_urgent") or item.get("impact_level") == "high":
                    urgent.append(item)

        await r.aclose()
        urgent.sort(key=lambda x: abs(x.get("sentiment_score", 0)), reverse=True)
        return {"urgent_items": urgent[:10], "total": len(urgent)}

    except Exception as e:
        logger.error(f"[news] Urgent news error: {e}")
        return {"urgent_items": [], "total": 0}
