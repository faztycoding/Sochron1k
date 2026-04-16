from fastapi import APIRouter

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{pair}")
async def get_analysis(pair: str):
    return {"pair": pair, "message": "ผลวิเคราะห์ — coming in Phase 4"}


@router.post("/{pair}/run")
async def run_analysis(pair: str):
    return {"pair": pair, "message": "รันวิเคราะห์ — coming in Phase 4"}
