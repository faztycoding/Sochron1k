"""Per-candle indicator series for chart overlays.

Unlike `builtin.compute_all_builtin` (which returns the latest scalar value),
these functions return the full time-series aligned with the input candles,
so the frontend can draw them as lines or histograms.

Returns:
    {
        "candles": [...],          # original OHLCV list
        "ema_9": [...],            # same length, nulls during warmup
        "ema_21": [...],
        "ema_50": [...],
        "bb_upper": [...],
        "bb_middle": [...],
        "bb_lower": [...],
        "rsi": [...],
        "macd_line": [...],
        "macd_signal": [...],
        "macd_hist": [...],
    }
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _finite_or_none(val: float) -> Optional[float]:
    if val is None or pd.isna(val) or np.isinf(val):
        return None
    return float(val)


def _series_to_list(s: pd.Series) -> List[Optional[float]]:
    return [_finite_or_none(v) for v in s.tolist()]


def compute_series(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aligned indicator series from a list of OHLCV candles.

    Expects candles sorted oldest → newest. If fewer than ~30 candles,
    many series will be all-null (which the frontend should handle).
    """
    if not candles:
        return {"candles": [], "count": 0}

    df = pd.DataFrame(candles)
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    closes = df["close"]

    out: Dict[str, Any] = {
        "candles": df.to_dict(orient="records"),
        "count": len(df),
    }

    # --- EMAs (trend) ---
    for period in (9, 21, 50, 200):
        ema = closes.ewm(span=period, adjust=False).mean()
        # Null out warmup (first `period-1` values are not meaningful)
        ema.iloc[: period - 1] = np.nan
        out[f"ema_{period}"] = _series_to_list(ema)

    # --- SMA ---
    for period in (50, 200):
        sma = closes.rolling(window=period).mean()
        out[f"sma_{period}"] = _series_to_list(sma)

    # --- Bollinger Bands (20, 2σ) ---
    bb_period = 20
    bb_std = 2.0
    bb_mid = closes.rolling(window=bb_period).mean()
    bb_sd = closes.rolling(window=bb_period).std()
    out["bb_upper"] = _series_to_list(bb_mid + bb_std * bb_sd)
    out["bb_middle"] = _series_to_list(bb_mid)
    out["bb_lower"] = _series_to_list(bb_mid - bb_std * bb_sd)

    # --- RSI (14) ---
    rsi_period = 14
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # When loss==0 and gain>0 → 100; gain==0 and loss>0 → 0
    rsi = rsi.where(~((loss == 0) & (gain > 0)), 100.0)
    rsi = rsi.where(~((gain == 0) & (loss > 0)), 0.0)
    out["rsi"] = _series_to_list(rsi)

    # --- MACD (12, 26, 9) ---
    ema_fast = closes.ewm(span=12, adjust=False).mean()
    ema_slow = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    # First 25 values aren't reliable; null them
    for s in (macd_line, macd_signal, macd_hist):
        s.iloc[:25] = np.nan
    out["macd_line"] = _series_to_list(macd_line)
    out["macd_signal"] = _series_to_list(macd_signal)
    out["macd_hist"] = _series_to_list(macd_hist)

    # --- ATR (14) for SL/TP overlays ---
    if len(df) >= 15:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14).mean()
        out["atr"] = _series_to_list(atr)
    else:
        out["atr"] = [None] * len(df)

    return out
