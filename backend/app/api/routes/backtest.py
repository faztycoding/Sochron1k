"""Backtest API — validate strategies on historical candles."""
import logging

from fastapi import APIRouter, HTTPException

from app.config import TARGET_PAIRS
from app.models.schemas.backtest import BacktestRequest, BacktestResponse, StrategyMetadata
from app.services.backtest import BacktestEngine, STRATEGIES, list_strategies
from app.services.price.manager import PriceManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/strategies", response_model=list[StrategyMetadata], summary="รายการกลยุทธ์ที่ backtest ได้")
async def get_strategies() -> list[StrategyMetadata]:
    return [StrategyMetadata(**s) for s in list_strategies()]


@router.post(
    "/{pair}/run",
    response_model=BacktestResponse,
    summary="รัน backtest สำหรับคู่เงิน",
)
async def run_backtest(pair: str, req: BacktestRequest) -> BacktestResponse:
    pair = pair.upper().replace("-", "/")
    if pair not in TARGET_PAIRS:
        raise HTTPException(status_code=404, detail=f"ไม่รองรับคู่ {pair}")

    if req.strategy not in STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"ไม่มีกลยุทธ์ '{req.strategy}' — ลอง: {list(STRATEGIES.keys())}",
        )

    pm = PriceManager()
    try:
        candles = await pm.get_candles(pair, req.timeframe, req.lookback)
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"ข้อมูลแท่งเทียนน้อยเกินไป ({len(candles) if candles else 0} แท่ง) — ต้องการอย่างน้อย 50",
            )
    finally:
        await pm.close()

    strategy_cls = STRATEGIES[req.strategy]
    strategy = strategy_cls(**(req.params or {}))

    engine = BacktestEngine(
        pair=pair,
        candles=candles,
        strategy=strategy,
        initial_balance=req.initial_balance,
        risk_percent=req.risk_percent,
        sl_atr_mult=req.sl_atr_mult,
        tp_atr_mult=req.tp_atr_mult,
        spread_pips=req.spread_pips,
        commission_pips=req.commission_pips,
    )

    try:
        result = engine.run()
    except Exception as e:
        logger.exception(f"[backtest] Run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    data = result.to_dict()
    data["timeframe"] = req.timeframe
    return BacktestResponse(**data)
