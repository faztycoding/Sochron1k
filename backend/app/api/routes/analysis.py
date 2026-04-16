import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas.analysis import AnalysisRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["วิเคราะห์"])

TARGET_PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"]


@router.post("/{pair}/run", summary="รันวิเคราะห์ 5-layer เต็มรูปแบบ")
async def run_analysis(
    pair: str,
    timeframe: str = Query("1h"),
    consecutive_losses: int = Query(0, ge=0),
    daily_loss_pct: float = Query(0.0, ge=0),
) -> Dict[str, Any]:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(400, f"คู่เงินที่รองรับ: {TARGET_PAIRS}")

    from app.services.analysis.brain import AnalysisBrain
    brain = AnalysisBrain()
    try:
        return await brain.analyze(pair, timeframe, consecutive_losses, daily_loss_pct)
    except Exception as e:
        logger.error(f"[analysis] Error: {e}")
        raise HTTPException(500, f"วิเคราะห์ล้มเหลว: {str(e)}")


@router.get("/all/run", summary="วิเคราะห์ทุกคู่เงินพร้อมกัน")
async def run_all_analysis() -> Dict[str, Any]:
    from app.services.analysis.brain import AnalysisBrain
    brain = AnalysisBrain()
    try:
        return await brain.analyze_all_pairs()
    except Exception as e:
        logger.error(f"[analysis] All pairs error: {e}")
        raise HTTPException(500, str(e))


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
