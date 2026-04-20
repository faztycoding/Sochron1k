import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.security import SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def _prefetch_candles():
    """Background task: pre-fetch candles for all pairs/timeframes.

    Rate-limit aware: waits 8s between calls so it consumes ~7 credits/min,
    fitting inside the ~17 credits/min headroom left by the realtime poll.
    Skips quickly if TwelveData is momentarily rate-limited — the manager
    returns [] and we move on. Prefers higher timeframes first since they
    feed the analysis page immediately.
    """
    import asyncio
    from app.config import TARGET_PAIRS
    from app.services.price.manager import PriceManager

    # Higher timeframes first — they're what analysis page hits first
    ordered_tfs = ["1h", "4h", "1d", "15m", "5m", "1m"]

    await asyncio.sleep(15)  # let realtime poll establish baseline first
    pm = PriceManager()
    try:
        for tf in ordered_tfs:
            for pair in TARGET_PAIRS:
                try:
                    candles = await pm.get_candles(pair, tf, 200)
                    if candles:
                        logger.info(f"[prefetch] {pair} {tf}: {len(candles)} candles")
                except Exception as e:
                    logger.debug(f"[prefetch] {pair} {tf} failed: {e}")
                await asyncio.sleep(8)  # ~7 credits/min — leaves room for realtime poll
    finally:
        await pm.close()
    logger.info("[prefetch] Done — all timeframes cached")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    # startup
    settings = get_settings()
    logger.info(f"Sochron1k API starting — env={settings.APP_ENV}")
    prefetch_task = asyncio.create_task(_prefetch_candles())

    # Start WebSocket price stream (0 credits)
    from app.services.price.ws_stream import PriceStream
    stream = PriceStream()
    await stream.start()

    yield
    # shutdown
    prefetch_task.cancel()
    await stream.stop()
    # Close shared Redis pool
    try:
        from app.services.price.manager import close_redis_pool
        await close_redis_pool()
    except Exception:
        pass
    logger.info("Sochron1k API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Sochron1k API",
        description="ระบบวิเคราะห์ Forex อัจฉริยะ",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )

    # Middleware (order: last added = outermost = first executed)
    # 1. Inner: ErrorHandler → SecurityHeaders → RateLimit
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst=20)
    # 2. Outermost: CORS must be last so it handles OPTIONS preflight first
    cors_origins = settings.cors_origins_list
    if settings.DEBUG:
        cors_origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not settings.DEBUG,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
