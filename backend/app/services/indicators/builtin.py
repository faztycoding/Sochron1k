import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _to_df(candles: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    return df


def calc_ema(closes: pd.Series, period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return float(closes.ewm(span=period, adjust=False).mean().iloc[-1])


def calc_sma(closes: pd.Series, period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return float(closes.rolling(window=period).mean().iloc[-1])


def calc_rsi(closes: pd.Series, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    if np.isnan(val) or np.isinf(val):
        if loss.iloc[-1] == 0 and gain.iloc[-1] > 0:
            return 100.0
        elif gain.iloc[-1] == 0 and loss.iloc[-1] > 0:
            return 0.0
        return None
    return float(val)


def calc_macd(
    closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, Optional[float]]:
    if len(closes) < slow + signal:
        return {"macd_line": None, "macd_signal": None, "macd_hist": None}
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd_line": float(macd_line.iloc[-1]),
        "macd_signal": float(signal_line.iloc[-1]),
        "macd_hist": float(histogram.iloc[-1]),
    }


def calc_adx(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    if len(df) < period * 2:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    mask = plus_dm < minus_dm
    plus_dm[mask] = 0
    minus_dm[~mask] = 0

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=period).mean()

    val = adx.iloc[-1]
    return float(val) if not np.isnan(val) else None


def calc_stochastic(
    df: pd.DataFrame, k_period: int = 14, d_period: int = 3, smooth: int = 3
) -> Dict[str, Optional[float]]:
    if len(df) < k_period + d_period:
        return {"stoch_k": None, "stoch_d": None}
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    raw_k = 100 * (df["close"] - low_min) / (high_max - low_min)
    k = raw_k.rolling(window=smooth).mean()
    d = k.rolling(window=d_period).mean()
    return {
        "stoch_k": float(k.iloc[-1]) if not np.isnan(k.iloc[-1]) else None,
        "stoch_d": float(d.iloc[-1]) if not np.isnan(d.iloc[-1]) else None,
    }


def calc_cci(df: pd.DataFrame, period: int = 20) -> Optional[float]:
    if len(df) < period:
        return None
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma) / (0.015 * mad)
    val = cci.iloc[-1]
    return float(val) if not np.isnan(val) else None


def calc_bollinger(
    closes: pd.Series, period: int = 20, std_dev: float = 2.0
) -> Dict[str, Optional[float]]:
    if len(closes) < period:
        return {"bb_upper": None, "bb_middle": None, "bb_lower": None}
    sma = closes.rolling(window=period).mean()
    std = closes.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return {
        "bb_upper": float(upper.iloc[-1]),
        "bb_middle": float(sma.iloc[-1]),
        "bb_lower": float(lower.iloc[-1]),
    }


def calc_atr(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    if len(df) < period + 1:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    val = atr.iloc[-1]
    return float(val) if not np.isnan(val) else None


def calc_keltner(
    df: pd.DataFrame, period: int = 20, multiplier: float = 1.5
) -> Dict[str, Optional[float]]:
    if len(df) < period + 1:
        return {"keltner_upper": None, "keltner_lower": None}
    ema_val = df["close"].ewm(span=period, adjust=False).mean()
    atr_val = calc_atr(df, period)
    if atr_val is None:
        return {"keltner_upper": None, "keltner_lower": None}
    mid = float(ema_val.iloc[-1])
    return {
        "keltner_upper": mid + multiplier * atr_val,
        "keltner_lower": mid - multiplier * atr_val,
    }


def calc_obv(df: pd.DataFrame) -> Optional[float]:
    if len(df) < 2:
        return None
    close, volume = df["close"], df["volume"]
    direction = np.sign(close.diff())
    obv = (direction * volume).cumsum()
    val = obv.iloc[-1]
    return float(val) if not np.isnan(val) else None


def compute_all_builtin(candles: List[Dict]) -> Dict[str, Any]:
    df = _to_df(candles)
    if len(df) < 30:
        logger.warning(f"[indicators] Only {len(df)} candles — need 30+")
        return {}

    closes = df["close"]

    result = {
        # Trend
        "ema_9": calc_ema(closes, 9),
        "ema_21": calc_ema(closes, 21),
        "ema_50": calc_ema(closes, 50),
        "ema_200": calc_ema(closes, 200),
        "sma_50": calc_sma(closes, 50),
        "sma_200": calc_sma(closes, 200),
        "adx": calc_adx(df),
        # Oscillators
        "rsi": calc_rsi(closes),
        "cci": calc_cci(df),
        # Volatility
        "atr": calc_atr(df),
        # Volume
        "obv": calc_obv(df),
    }

    result.update(calc_macd(closes))
    result.update(calc_stochastic(df))
    result.update(calc_bollinger(closes))
    result.update(calc_keltner(df))

    count = sum(1 for v in result.values() if v is not None)
    logger.info(f"[indicators] Computed {count}/{len(result)} built-in indicators")
    return result
