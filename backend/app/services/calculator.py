"""Trade Calculator — Position size, SL/TP, Risk management"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PIP_VALUES = {
    "EUR/USD": {"pip_size": 0.0001, "pip_value_per_lot": 10.0},
    "USD/JPY": {"pip_size": 0.01, "pip_value_per_lot": 1000 / 150},
    "EUR/JPY": {"pip_size": 0.01, "pip_value_per_lot": 1000 / 150},
}


def get_pip_info(pair: str) -> Dict[str, float]:
    return PIP_VALUES.get(pair, {"pip_size": 0.0001, "pip_value_per_lot": 10.0})


def price_to_pips(pair: str, price_diff: float) -> float:
    info = get_pip_info(pair)
    return abs(price_diff) / info["pip_size"]


def pips_to_price(pair: str, pips: float) -> float:
    info = get_pip_info(pair)
    return pips * info["pip_size"]


def calculate_position(
    pair: str,
    direction: str,
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    sl_price: Optional[float] = None,
    tp_price: Optional[float] = None,
    sl_pips: Optional[float] = None,
    tp_pips: Optional[float] = None,
) -> Dict[str, Any]:
    info = get_pip_info(pair)
    warnings: List[str] = []

    # Determine SL
    if sl_price is not None:
        sl_pips_calc = price_to_pips(pair, entry_price - sl_price) if direction == "BUY" \
            else price_to_pips(pair, sl_price - entry_price)
    elif sl_pips is not None:
        sl_pips_calc = sl_pips
        if direction == "BUY":
            sl_price = entry_price - pips_to_price(pair, sl_pips)
        else:
            sl_price = entry_price + pips_to_price(pair, sl_pips)
    else:
        sl_pips_calc = 30.0
        warnings.append("ไม่ได้กำหนด SL — ใช้ default 30 pips")
        if direction == "BUY":
            sl_price = entry_price - pips_to_price(pair, 30)
        else:
            sl_price = entry_price + pips_to_price(pair, 30)

    # Determine TP
    if tp_price is not None:
        tp_pips_calc = price_to_pips(pair, tp_price - entry_price) if direction == "BUY" \
            else price_to_pips(pair, entry_price - tp_price)
    elif tp_pips is not None:
        tp_pips_calc = tp_pips
        if direction == "BUY":
            tp_price = entry_price + pips_to_price(pair, tp_pips)
        else:
            tp_price = entry_price - pips_to_price(pair, tp_pips)
    else:
        tp_pips_calc = sl_pips_calc * 2
        warnings.append("ไม่ได้กำหนด TP — ใช้ R:R 1:2")
        if direction == "BUY":
            tp_price = entry_price + pips_to_price(pair, tp_pips_calc)
        else:
            tp_price = entry_price - pips_to_price(pair, tp_pips_calc)

    # Risk
    risk_amount = account_balance * (risk_percent / 100)
    pip_value = info["pip_value_per_lot"]
    lot_size = risk_amount / (sl_pips_calc * pip_value) if sl_pips_calc > 0 else 0.01
    lot_size = round(max(0.01, lot_size), 2)

    # Potential profit
    potential_profit = tp_pips_calc * pip_value * lot_size

    # R:R
    risk_reward = round(tp_pips_calc / sl_pips_calc, 2) if sl_pips_calc > 0 else 0

    # Warnings
    if risk_percent > 5:
        warnings.append("⚠️ ความเสี่ยงสูงเกิน 5% — แนะนำ 1-2%")
    if sl_pips_calc < 10:
        warnings.append("⚠️ SL แคบมาก (<10 pips) — เสี่ยง stop-out")
    if sl_pips_calc > 100:
        warnings.append("⚠️ SL กว้างมาก (>100 pips) — ทบทวน position size")
    if risk_reward < 1.5:
        warnings.append("⚠️ R:R ต่ำ (<1.5) — แนะนำ R:R >= 2.0")
    if lot_size > 1.0 and account_balance < 10000:
        warnings.append("⚠️ Lot size สูงเมื่อเทียบกับทุน — ระวัง margin call")

    return {
        "pair": pair,
        "direction": direction,
        "entry_price": round(entry_price, 5),
        "sl_price": round(sl_price, 5),
        "tp_price": round(tp_price, 5),
        "sl_pips": round(sl_pips_calc, 1),
        "tp_pips": round(tp_pips_calc, 1),
        "lot_size": lot_size,
        "risk_amount": round(risk_amount, 2),
        "potential_profit": round(potential_profit, 2),
        "risk_reward": risk_reward,
        "pip_value": round(pip_value, 4),
        "warnings": warnings,
    }


async def auto_sl_tp(
    pair: str,
    direction: str,
    entry_price: float,
    timeframe: str = "1h",
) -> Dict[str, Any]:
    """Auto SL/TP based on ATR"""
    from app.services.indicators.engine import IndicatorEngine

    engine = IndicatorEngine()
    try:
        indicators = await engine.compute_for_pair(pair, timeframe)
    finally:
        await engine.close()

    atr = indicators.get("atr")
    if not atr:
        atr = pips_to_price(pair, 25)

    sl_dist = atr * 1.5
    tp_dist = atr * 3.0

    if direction == "BUY":
        sl_price = entry_price - sl_dist
        tp_price = entry_price + tp_dist
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - tp_dist

    sl_p = price_to_pips(pair, sl_dist)
    tp_p = price_to_pips(pair, tp_dist)

    return {
        "pair": pair,
        "direction": direction,
        "entry_price": round(entry_price, 5),
        "sl_price": round(sl_price, 5),
        "tp_price": round(tp_price, 5),
        "sl_pips": round(sl_p, 1),
        "tp_pips": round(tp_p, 1),
        "atr_used": round(atr, 6),
        "risk_reward": round(tp_p / sl_p, 2) if sl_p > 0 else 0,
        "method": "ATR-based",
    }
