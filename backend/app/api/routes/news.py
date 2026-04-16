from fastapi import APIRouter

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
async def get_news():
    return {"message": "ข่าวล่าสุด — coming in Phase 2"}


@router.post("/refresh")
async def refresh_news():
    return {"message": "อัพเดทข่าว — coming in Phase 2"}
