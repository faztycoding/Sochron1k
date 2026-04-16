from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.models.schemas.common import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    await db.execute(text("SELECT 1"))
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=settings.APP_ENV,
    )
