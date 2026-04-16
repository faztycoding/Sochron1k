from fastapi import APIRouter

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
async def get_trades():
    return {"message": "บันทึกการเทรด — coming in Phase 6"}


@router.get("/stats")
async def get_trade_stats():
    return {"message": "สถิติ win rate — coming in Phase 6"}
