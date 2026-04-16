"""Trade Journal Service — CRUD + Win Rate + Accuracy"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.trade import Trade

logger = logging.getLogger(__name__)


async def create_trade(db: AsyncSession, data: Dict[str, Any]) -> Trade:
    trade = Trade(**data)
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    logger.info(f"[journal] Created trade #{trade.id} {trade.pair} {trade.direction}")
    return trade


async def get_trade(db: AsyncSession, trade_id: int) -> Optional[Trade]:
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    return result.scalar_one_or_none()


async def update_trade(db: AsyncSession, trade_id: int, data: Dict[str, Any]) -> Optional[Trade]:
    trade = await get_trade(db, trade_id)
    if not trade:
        return None

    for key, val in data.items():
        if val is not None and hasattr(trade, key):
            setattr(trade, key, val)

    # Auto-compute when closing
    if data.get("exit_price") and trade.entry_price:
        pip_mult = 100 if "JPY" in trade.pair else 10000
        diff = trade.exit_price - trade.entry_price
        if trade.direction == "SELL":
            diff = -diff
        trade.actual_pips = round(diff * pip_mult, 1)
        trade.result = "win" if diff > 0 else "loss"

        if trade.status != "closed":
            trade.status = "closed"
            trade.closed_at = datetime.utcnow()

        # System accuracy
        if trade.system_direction:
            trade.system_correct = (
                (trade.system_direction == "BUY" and diff > 0) or
                (trade.system_direction == "SELL" and diff < 0)
            )

        # Actual R:R
        if trade.sl_pips and trade.sl_pips > 0:
            trade.risk_reward_actual = round(abs(trade.actual_pips) / trade.sl_pips, 2)

    await db.commit()
    await db.refresh(trade)
    return trade


async def list_trades(
    db: AsyncSession,
    pair: Optional[str] = None,
    status: Optional[str] = None,
    result: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    query = select(Trade)
    count_query = select(func.count()).select_from(Trade)

    if pair:
        query = query.where(Trade.pair == pair)
        count_query = count_query.where(Trade.pair == pair)
    if status:
        query = query.where(Trade.status == status)
        count_query = count_query.where(Trade.status == status)
    if result:
        query = query.where(Trade.result == result)
        count_query = count_query.where(Trade.result == result)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Trade.opened_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()

    return {"items": rows, "total": total, "page": page, "per_page": per_page}


async def delete_trade(db: AsyncSession, trade_id: int) -> bool:
    trade = await get_trade(db, trade_id)
    if not trade:
        return False
    await db.delete(trade)
    await db.commit()
    return True


# ── Stats ──

async def get_win_rate(db: AsyncSession, pair: Optional[str] = None) -> Dict[str, Any]:
    base = select(Trade).where(Trade.status == "closed")
    if pair:
        base = base.where(Trade.pair == pair)

    rows = (await db.execute(base)).scalars().all()

    if not rows:
        return _empty_winrate()

    wins = [t for t in rows if t.result == "win"]
    losses = [t for t in rows if t.result == "loss"]

    win_pips = [t.actual_pips for t in wins if t.actual_pips is not None]
    loss_pips = [abs(t.actual_pips) for t in losses if t.actual_pips is not None]

    avg_win = sum(win_pips) / len(win_pips) if win_pips else 0
    avg_loss = sum(loss_pips) / len(loss_pips) if loss_pips else 0
    total_pips = sum(t.actual_pips for t in rows if t.actual_pips is not None)

    all_pips = [t.actual_pips for t in rows if t.actual_pips is not None]
    best = max(all_pips) if all_pips else 0
    worst = min(all_pips) if all_pips else 0

    total_profit = sum(p for p in win_pips)
    total_loss_val = sum(p for p in loss_pips)
    profit_factor = round(total_profit / total_loss_val, 2) if total_loss_val > 0 else 0

    # By pair
    by_pair: Dict[str, Dict[str, Any]] = {}
    for t in rows:
        p = t.pair
        if p not in by_pair:
            by_pair[p] = {"wins": 0, "losses": 0, "total_pips": 0}
        if t.result == "win":
            by_pair[p]["wins"] += 1
        elif t.result == "loss":
            by_pair[p]["losses"] += 1
        if t.actual_pips:
            by_pair[p]["total_pips"] += t.actual_pips

    for p in by_pair:
        total_p = by_pair[p]["wins"] + by_pair[p]["losses"]
        by_pair[p]["win_rate"] = round(by_pair[p]["wins"] / total_p * 100, 1) if total_p > 0 else 0
        by_pair[p]["total_pips"] = round(by_pair[p]["total_pips"], 1)

    return {
        "total_trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
        "avg_profit_pips": round(avg_win, 1),
        "avg_loss_pips": round(avg_loss, 1),
        "profit_factor": profit_factor,
        "best_trade_pips": round(best, 1),
        "worst_trade_pips": round(worst, 1),
        "total_pips": round(total_pips, 1),
        "by_pair": by_pair,
    }


async def get_accuracy(db: AsyncSession) -> Dict[str, Any]:
    rows = (await db.execute(
        select(Trade).where(and_(Trade.status == "closed", Trade.system_direction.isnot(None)))
    )).scalars().all()

    if not rows:
        return {"total_signals": 0, "correct_signals": 0, "accuracy": 0, "by_pair": {}, "by_regime": {}, "by_confidence_tier": {}}

    correct = [t for t in rows if t.system_correct]

    # By pair
    by_pair: Dict[str, Dict[str, Any]] = {}
    for t in rows:
        p = t.pair
        if p not in by_pair:
            by_pair[p] = {"total": 0, "correct": 0}
        by_pair[p]["total"] += 1
        if t.system_correct:
            by_pair[p]["correct"] += 1
    for p in by_pair:
        by_pair[p]["accuracy"] = round(by_pair[p]["correct"] / by_pair[p]["total"] * 100, 1)

    # By regime
    by_regime: Dict[str, Dict[str, Any]] = {}
    for t in rows:
        r = t.system_regime or "unknown"
        if r not in by_regime:
            by_regime[r] = {"total": 0, "correct": 0}
        by_regime[r]["total"] += 1
        if t.system_correct:
            by_regime[r]["correct"] += 1
    for r in by_regime:
        by_regime[r]["accuracy"] = round(by_regime[r]["correct"] / by_regime[r]["total"] * 100, 1)

    # By confidence tier
    tiers = {"high_75+": lambda c: c and c >= 0.75, "mid_50-75": lambda c: c and 0.50 <= c < 0.75, "low_<50": lambda c: c is None or c < 0.50}
    by_conf: Dict[str, Dict[str, Any]] = {}
    for tier_name, check in tiers.items():
        tier_trades = [t for t in rows if check(t.system_confidence)]
        tier_correct = [t for t in tier_trades if t.system_correct]
        by_conf[tier_name] = {
            "total": len(tier_trades),
            "correct": len(tier_correct),
            "accuracy": round(len(tier_correct) / len(tier_trades) * 100, 1) if tier_trades else 0,
        }

    return {
        "total_signals": len(rows),
        "correct_signals": len(correct),
        "accuracy": round(len(correct) / len(rows) * 100, 1),
        "by_pair": by_pair,
        "by_regime": by_regime,
        "by_confidence_tier": by_conf,
    }


async def get_overview(db: AsyncSession) -> Dict[str, Any]:
    all_trades = (await db.execute(select(Trade))).scalars().all()
    closed = [t for t in all_trades if t.status == "closed"]
    open_trades = [t for t in all_trades if t.status == "open"]

    today = datetime.utcnow().date()
    today_trades = [t for t in closed if t.closed_at and t.closed_at.date() == today]
    today_pips = sum(t.actual_pips for t in today_trades if t.actual_pips) if today_trades else 0

    wins = [t for t in closed if t.result == "win"]
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0
    total_pips = sum(t.actual_pips for t in closed if t.actual_pips) or 0

    # Profit factor
    win_sum = sum(t.actual_pips for t in wins if t.actual_pips and t.actual_pips > 0)
    loss_sum = sum(abs(t.actual_pips) for t in closed if t.actual_pips and t.actual_pips < 0)
    profit_factor = round(win_sum / loss_sum, 2) if loss_sum > 0 else 0

    # System accuracy
    with_sys = [t for t in closed if t.system_direction]
    sys_correct = [t for t in with_sys if t.system_correct]
    accuracy = round(len(sys_correct) / len(with_sys) * 100, 1) if with_sys else 0

    # Best/worst pair
    pair_pips: Dict[str, float] = {}
    for t in closed:
        if t.actual_pips:
            pair_pips[t.pair] = pair_pips.get(t.pair, 0) + t.actual_pips

    best_pair = max(pair_pips, key=pair_pips.get) if pair_pips else None
    worst_pair = min(pair_pips, key=pair_pips.get) if pair_pips else None

    # Avg confidence
    confs = [t.system_confidence for t in closed if t.system_confidence is not None]
    avg_conf = round(sum(confs) / len(confs), 2) if confs else 0

    # Consecutive
    sorted_trades = sorted(closed, key=lambda t: t.closed_at or datetime.min)
    c_wins = c_losses = max_wins = max_losses = 0
    for t in sorted_trades:
        if t.result == "win":
            c_wins += 1
            c_losses = 0
            max_wins = max(max_wins, c_wins)
        elif t.result == "loss":
            c_losses += 1
            c_wins = 0
            max_losses = max(max_losses, c_losses)

    return {
        "total_trades": len(all_trades),
        "open_trades": len(open_trades),
        "win_rate": win_rate,
        "total_pips": round(total_pips, 1),
        "profit_factor": profit_factor,
        "system_accuracy": accuracy,
        "best_pair": best_pair,
        "worst_pair": worst_pair,
        "avg_confidence": avg_conf,
        "consecutive_wins": max_wins,
        "consecutive_losses": max_losses,
        "today_trades": len(today_trades),
        "today_pips": round(today_pips, 1),
    }


def _empty_winrate():
    return {
        "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
        "avg_profit_pips": 0, "avg_loss_pips": 0, "profit_factor": 0,
        "best_trade_pips": 0, "worst_trade_pips": 0, "total_pips": 0,
        "by_pair": {},
    }
