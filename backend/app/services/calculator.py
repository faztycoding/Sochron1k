"""Trade Calculator — Position size, SL/TP, Risk management"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default FX rates — used when client doesn't supply fx_rate_to_usd.
# In production the frontend should pull the live rate (/price/realtime for
# USDJPY, plus a THB rate from a cached endpoint).
DEFAULT_FX_TO_USD = {
    "USD": 1.0,
    "THB": 1.0 / 36.0,   # ~36 THB per USD (conservative; overridable)
    "EUR": 1.08,
    "GBP": 1.26,
    "JPY": 1.0 / 150.0,
}

# pip_size is fixed per quote currency. pip_value_per_lot in USD depends on
# the current USD/JPY rate for JPY-quoted pairs — caller can override.
PIP_SIZES = {
    "EUR/USD": 0.0001,
    "GBP/USD": 0.0001,
    "AUD/USD": 0.0001,
    "USD/JPY": 0.01,
    "EUR/JPY": 0.01,
    "GBP/JPY": 0.01,
}


def _pip_size(pair: str) -> float:
    return PIP_SIZES.get(pair, 0.01 if "JPY" in pair else 0.0001)


def _pip_value_per_lot_usd(pair: str, usd_jpy_rate: float = 150.0) -> float:
    """USD value of 1 pip on 1 standard lot (100k units).

    - USD-quoted pairs (EUR/USD, GBP/USD, AUD/USD): always exactly $10/pip
    - JPY-quoted pairs: ¥1000 / current USDJPY rate
    """
    if pair.endswith("/USD"):
        return 10.0
    if pair.endswith("/JPY"):
        return 1000.0 / max(usd_jpy_rate, 1.0)
    # Fallback for unsupported pairs
    return 10.0


def get_pip_info(pair: str, usd_jpy_rate: float = 150.0) -> Dict[str, float]:
    return {
        "pip_size": _pip_size(pair),
        "pip_value_per_lot": _pip_value_per_lot_usd(pair, usd_jpy_rate),
    }


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
    account_currency: str = "USD",
    fx_rate_to_usd: Optional[float] = None,
    usd_jpy_rate: float = 150.0,
) -> Dict[str, Any]:
    # Normalize currency/rate
    ccy = account_currency.upper()
    rate = fx_rate_to_usd if fx_rate_to_usd and fx_rate_to_usd > 0 else DEFAULT_FX_TO_USD.get(ccy, 1.0)
    balance_usd = account_balance * rate

    info = get_pip_info(pair, usd_jpy_rate)
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

    # Risk — compute in USD (pip values are USD-denominated).
    # Lot size uses the USD-equivalent balance so all currencies see equal risk.
    risk_amount_usd = balance_usd * (risk_percent / 100)
    pip_value = info["pip_value_per_lot"]
    lot_size = risk_amount_usd / (sl_pips_calc * pip_value) if sl_pips_calc > 0 else 0.01
    lot_size = round(max(0.01, lot_size), 2)

    # Potential profit in USD
    potential_profit_usd = tp_pips_calc * pip_value * lot_size

    # Convert back to account currency for display
    # (rate is "1 ccy unit = X USD" → divide USD by rate to get ccy amount)
    risk_amount_local = risk_amount_usd / rate if rate > 0 else risk_amount_usd
    potential_profit_local = potential_profit_usd / rate if rate > 0 else potential_profit_usd

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
    if lot_size > 1.0 and balance_usd < 10000:
        warnings.append("⚠️ Lot size สูงเมื่อเทียบกับทุน — ระวัง margin call")
    if balance_usd < 100:
        warnings.append(f"⚠️ ทุน < $100 USD ({account_balance:.0f} {ccy}) — ใช้บัญชี Cent/Micro")

    return {
        "pair": pair,
        "direction": direction,
        "entry_price": round(entry_price, 5),
        "sl_price": round(sl_price, 5),
        "tp_price": round(tp_price, 5),
        "sl_pips": round(sl_pips_calc, 1),
        "tp_pips": round(tp_pips_calc, 1),
        "lot_size": lot_size,
        "risk_amount": round(risk_amount_usd, 2),
        "potential_profit": round(potential_profit_usd, 2),
        "risk_reward": risk_reward,
        "pip_value": round(pip_value, 4),
        "warnings": warnings,
        "account_currency": ccy,
        "fx_rate_to_usd": round(rate, 6),
        "risk_amount_local": round(risk_amount_local, 2),
        "potential_profit_local": round(potential_profit_local, 2),
        "balance_usd": round(balance_usd, 2),
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
