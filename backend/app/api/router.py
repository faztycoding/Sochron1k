from fastapi import APIRouter

from app.api.routes import analysis, health, indicators, news, price, trades, ws

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(news.router)
api_router.include_router(price.router)
api_router.include_router(indicators.router)
api_router.include_router(analysis.router)
api_router.include_router(trades.router)
api_router.include_router(ws.router)
