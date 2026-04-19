import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
import redis.asyncio as redis

from app.config import get_settings
from app.models.schemas.analysis import AnalysisRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["วิเคราะห์"])

from app.config import TARGET_PAIRS

ANALYSIS_CACHE_TTL = 45  # seconds — balance between freshness and API load


async def _get_cached_analysis(pair: str, timeframe: str) -> Dict[str, Any] | None:
    try:
        settings = get_settings()
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"analysis:{pair}:{timeframe}"
        raw = await client.get(key)
        await client.close()
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"[analysis] cache read error: {e}")
    return None


async def _set_cached_analysis(pair: str, timeframe: str, result: Dict[str, Any]) -> None:
    try:
        settings = get_settings()
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"analysis:{pair}:{timeframe}"
        await client.setex(key, ANALYSIS_CACHE_TTL, json.dumps(result, default=str))
        await client.close()
    except Exception as e:
        logger.debug(f"[analysis] cache write error: {e}")


@router.post("/{pair}/run", summary="รันวิเคราะห์ 5-layer เต็มรูปแบบ")
async def run_analysis(
    pair: str,
    timeframe: str = Query("1h"),
    consecutive_losses: int = Query(0, ge=0),
    daily_loss_pct: float = Query(0.0, ge=0),
    force_refresh: bool = Query(False, description="ข้าม cache บังคับรันใหม่"),
) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(400, f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    # Check cache first (only when inputs are default — avoid stale for custom risk params)
    if not force_refresh and consecutive_losses == 0 and daily_loss_pct == 0.0:
        cached = await _get_cached_analysis(pair, timeframe)
        if cached:
            cached["_cache"] = "hit"
            return cached

    from app.services.analysis.brain import AnalysisBrain
    brain = AnalysisBrain()
    try:
        result = await brain.analyze(pair, timeframe, consecutive_losses, daily_loss_pct)
        if "error" not in result and consecutive_losses == 0 and daily_loss_pct == 0.0:
            await _set_cached_analysis(pair, timeframe, result)
        result["_cache"] = "miss"
        return result
    except Exception as e:
        logger.error(f"[analysis] Error: {e}")
        raise HTTPException(500, f"วิเคราะห์ล้มเหลว: {str(e)}")


@router.get("/all/run", summary="วิเคราะห์ทุกคู่เงินพร้อมกัน")
async def run_all_analysis(force_refresh: bool = Query(False)) -> Dict[str, Any]:
    from app.services.analysis.brain import AnalysisBrain

    # Try cache first for all pairs
    results: Dict[str, Any] = {}
    uncached_pairs = []
    if not force_refresh:
        for pair in TARGET_PAIRS:
            cached = await _get_cached_analysis(pair, "1h")
            if cached:
                cached["_cache"] = "hit"
                results[pair] = cached
            else:
                uncached_pairs.append(pair)
    else:
        uncached_pairs = list(TARGET_PAIRS)

    # Run analysis only for uncached pairs (in parallel)
    if uncached_pairs:
        import asyncio
        brain = AnalysisBrain()
        try:
            tasks = [brain.analyze(p) for p in uncached_pairs]
            analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
            for pair, result in zip(uncached_pairs, analysis_results):
                if isinstance(result, Exception):
                    logger.error(f"[analysis] {pair}: {result}")
                    results[pair] = {"error": str(result), "pair": pair}
                else:
                    if "error" not in result:
                        await _set_cached_analysis(pair, "1h", result)
                    result["_cache"] = "miss"
                    results[pair] = result
        except Exception as e:
            logger.error(f"[analysis] All pairs error: {e}")
            raise HTTPException(500, str(e))

    return results


@router.get("/{pair}/kill-switch", summary="ตรวจสอบ Kill Switch")
async def check_kill_switch(
    pair: str,
    consecutive_losses: int = Query(0),
    daily_loss_pct: float = Query(0.0),
) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(400, f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    from app.services.analysis.kill_switch import evaluate_kill_switch
    from app.services.analysis.sentiment import get_cached_news, score_news_sentiment
    from app.services.analysis.signal_generator import get_current_session
    from app.services.indicators.engine import IndicatorEngine
    from app.config import get_settings

    settings = get_settings()
    engine = IndicatorEngine()
    try:
        indicators = await engine.compute_for_pair(pair, "1h")
        news_items = await get_cached_news(settings.REDIS_URL, pair)
        news = score_news_sentiment(news_items, pair)
        price = indicators.get("latest_price", 0)
        regime = {"regime": indicators.get("regime", "unknown")}

        return evaluate_kill_switch(
            news, indicators, regime, pair, price,
            consecutive_losses, daily_loss_pct,
        )
    except Exception as e:
        logger.error(f"[kill-switch] Error: {e}")
        raise HTTPException(500, str(e))
    finally:
        await engine.close()


@router.get("/{pair}/diagnosis", summary="Self-diagnosis 18 checks")
async def run_diagnosis(pair: str) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(400, f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    from app.services.analysis.brain import AnalysisBrain
    brain = AnalysisBrain()
    try:
        result = await brain.analyze(pair)
        return {
            "pair": pair,
            "diagnosis": result.get("diagnosis"),
            "kill_switch": result.get("kill_switch"),
            "confidence": result.get("confidence"),
            "regime": result.get("regime"),
        }
    except Exception as e:
        logger.error(f"[diagnosis] Error: {e}")
        raise HTTPException(500, str(e))


@router.get("/session/current", summary="ดู session ปัจจุบัน")
async def get_session() -> Dict[str, Any]:
    from app.services.analysis.signal_generator import get_current_session
    return get_current_session()
