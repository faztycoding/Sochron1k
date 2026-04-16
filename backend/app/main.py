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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    settings = get_settings()
    logger.info(f"Sochron1k API starting — env={settings.APP_ENV}")
    yield
    # shutdown
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

    # Middleware (order: last added = first executed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst=20)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)

    app.include_router(api_router)

    return app


app = create_app()
