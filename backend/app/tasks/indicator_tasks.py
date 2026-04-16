import asyncio
import logging
from typing import Any, Dict

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(
    name="app.tasks.indicator_tasks.compute_all_indicators",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def compute_all_indicators(self) -> Dict[str, Any]:
    logger.info("[task] Computing all indicators")

    async def _do():
        from app.services.indicators.engine import IndicatorEngine

        engine = IndicatorEngine()
        try:
            results = await engine.compute_all_pairs()
            summary = {}
            for pair, tf_data in results.items():
                summary[pair] = {
                    tf: {
                        "rsi": data.get("rsi"),
                        "adx": data.get("adx"),
                        "macd_hist": data.get("macd_hist"),
                    }
                    for tf, data in tf_data.items()
                    if isinstance(data, dict)
                }
            return {"computed": len(results), "summary": summary}
        finally:
            await engine.close()

    try:
        return _run_async(_do())
    except Exception as exc:
        logger.error(f"[task] compute_all_indicators failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.indicator_tasks.refresh_price_cache")
def refresh_price_cache() -> Dict[str, Any]:
    logger.info("[task] Refreshing price cache")

    async def _do():
        from app.services.price.manager import PriceManager

        pm = PriceManager()
        try:
            prices = await pm.get_realtime_prices()
            return {"updated": len(prices), "pairs": list(prices.keys())}
        finally:
            await pm.close()

    return _run_async(_do())
