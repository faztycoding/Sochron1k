import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calc_currency_strength(
    pair_candles: Dict[str, List[Dict]],
) -> Dict[str, float]:
    """คำนวณ Currency Strength Index จาก basket ของคู่เงิน"""
    strength = {"EUR": 0.0, "USD": 0.0, "JPY": 0.0}

    for pair, candles in pair_candles.items():
        if len(candles) < 2:
            continue

        latest = float(candles[-1]["close"])
        prev = float(candles[-2]["close"])
        if prev == 0:
            continue

        pct_change = ((latest - prev) / prev) * 100

        # EUR/USD: EUR up → EUR strong, USD weak
        if pair == "EUR/USD":
            strength["EUR"] += pct_change
            strength["USD"] -= pct_change
        # USD/JPY: USD up → USD strong, JPY weak
        elif pair == "USD/JPY":
            strength["USD"] += pct_change
            strength["JPY"] -= pct_change
        # EUR/JPY: EUR up → EUR strong, JPY weak
        elif pair == "EUR/JPY":
            strength["EUR"] += pct_change
            strength["JPY"] -= pct_change

    total = sum(abs(v) for v in strength.values())
    if total > 0:
        strength = {k: round(v / total * 100, 2) for k, v in strength.items()}

    return strength


def calc_z_score(closes: List[float], period: int = 20) -> Optional[float]:
    """Z-Score = (price - SMA) / StdDev — mean reversion signal"""
    if len(closes) < period:
        return None

    series = pd.Series(closes[-period:])
    mean = series.mean()
    std = series.std()
    if std == 0:
        return 0.0

    z = (closes[-1] - mean) / std
    return round(float(z), 4)


def calc_session_volatility_index(
    candles: List[Dict],
    session_hours: int = 4,
) -> Optional[float]:
    """Session Vol Index = ATR ปัจจุบัน / ATR เฉลี่ย → >1.5 ผิดปกติ"""
    if len(candles) < 50:
        return None

    df = pd.DataFrame(candles)
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift(1)).abs()
    tr3 = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    current_atr = tr.iloc[-session_hours:].mean()
    avg_atr = tr.mean()

    if avg_atr == 0:
        return None

    return round(float(current_atr / avg_atr), 4)


def calc_correlation_divergence(
    pair_closes: List[float],
    dxy_closes: List[float],
    period: int = 20,
) -> Optional[float]:
    """EUR/USD vs DXY correlation break → divergence = false breakout signal"""
    if len(pair_closes) < period or len(dxy_closes) < period:
        return None

    pair_series = pd.Series(pair_closes[-period:])
    dxy_series = pd.Series(dxy_closes[-period:])

    correlation = pair_series.corr(dxy_series)
    # EUR/USD normally negative corr with DXY
    # divergence = when correlation breaks (goes positive)
    return round(float(correlation), 4)


def calc_liquidity_spike(
    candles: List[Dict],
    vol_threshold: float = 2.0,
) -> Optional[float]:
    """Volume spike + price reversal = ดักจุด MM กวาด SL"""
    if len(candles) < 30:
        return None

    df = pd.DataFrame(candles)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")

    avg_vol = df["volume"].iloc[-30:-1].mean()
    if avg_vol == 0:
        return 0.0

    latest_vol = float(df["volume"].iloc[-1])
    vol_ratio = latest_vol / avg_vol

    # Price reversal check: wick > body
    last = df.iloc[-1]
    body = abs(last["close"] - last["open"]) if "open" in df.columns else 0
    wick = (last["high"] - last["low"]) - body

    spike_score = 0.0
    if vol_ratio >= vol_threshold:
        spike_score = vol_ratio
        if body > 0 and wick / body > 2:
            spike_score *= 1.5  # reversal signal boost

    return round(spike_score, 4)


def calc_multi_tf_confluence(
    ema_data: Dict[str, Dict[str, Optional[float]]],
) -> float:
    """EMA alignment across 1H + 4H + 1D → +-100 score"""
    score = 0.0
    timeframes = ["1h", "4h", "1d"]
    weight = {"1h": 1.0, "4h": 2.0, "1d": 3.0}

    for tf in timeframes:
        tf_data = ema_data.get(tf, {})
        ema9 = tf_data.get("ema_9")
        ema21 = tf_data.get("ema_21")
        ema50 = tf_data.get("ema_50")

        if ema9 is None or ema21 is None or ema50 is None:
            continue

        w = weight[tf]
        # Bullish alignment: EMA9 > EMA21 > EMA50
        if ema9 > ema21 > ema50:
            score += 33.3 * w
        # Bearish alignment: EMA9 < EMA21 < EMA50
        elif ema9 < ema21 < ema50:
            score -= 33.3 * w

    max_score = sum(33.3 * w for w in weight.values())
    if max_score > 0:
        score = (score / max_score) * 100

    return round(score, 2)


def calc_news_impact_score(
    news_sentiments: List[float],
    hours: int = 24,
) -> float:
    """Weighted average of sentiment scores from recent news"""
    if not news_sentiments:
        return 0.0

    n = len(news_sentiments)
    weights = [1.0 / (i + 1) for i in range(n)]
    total_weight = sum(weights)

    weighted_sum = sum(s * w for s, w in zip(news_sentiments, weights))
    return round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0


def compute_all_custom(
    pair: str,
    candles: List[Dict],
    all_pair_candles: Optional[Dict[str, List[Dict]]] = None,
    dxy_closes: Optional[List[float]] = None,
    news_sentiments: Optional[List[float]] = None,
    ema_data_multi_tf: Optional[Dict[str, Dict]] = None,
) -> Dict[str, Any]:
    closes = [float(c["close"]) for c in candles if c.get("close")]

    result = {
        "z_score": calc_z_score(closes),
        "session_vol_index": calc_session_volatility_index(candles),
        "liquidity_spike": calc_liquidity_spike(candles),
        "news_impact_score": calc_news_impact_score(news_sentiments or []),
    }

    if all_pair_candles:
        cs = calc_currency_strength(all_pair_candles)
        base, quote = pair.split("/") if "/" in pair else (pair[:3], pair[3:])
        result["currency_strength"] = cs.get(base, 0) - cs.get(quote, 0)

    if dxy_closes and closes:
        result["correlation_divergence"] = calc_correlation_divergence(
            closes, dxy_closes
        )

    if ema_data_multi_tf:
        result["multi_tf_confluence"] = calc_multi_tf_confluence(ema_data_multi_tf)

    count = sum(1 for v in result.values() if v is not None)
    logger.info(f"[custom] Computed {count}/{len(result)} custom indicators for {pair}")
    return result
