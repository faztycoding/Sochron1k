"""Backtesting strategies.

Each strategy implements a `generate_signal(df, i)` method that returns
a signal dict for candle index `i` given the full DataFrame of OHLCV.

The engine then uses this to open/close simulated positions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class BaseStrategy:
    """Base class for all backtesting strategies.

    Returning a signal dict:
        {"direction": "BUY" | "SELL" | None, "reason": str}
    None means no action (hold).
    """

    name: str = "base"
    display_name: str = "Base Strategy"
    description: str = "Override this class"
    params: Dict[str, Any] = {}

    def __init__(self, **params: Any) -> None:
        # Merge user params over defaults
        self.params = {**self.params, **params}

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Precompute indicator columns once for the whole series (fast)."""
        return df

    def generate_signal(self, df: pd.DataFrame, i: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class EMAcrossoverStrategy(BaseStrategy):
    """Classic fast/slow EMA crossover.

    BUY  when fast EMA crosses above slow EMA
    SELL when fast EMA crosses below slow EMA
    """

    name = "ema_crossover"
    display_name = "EMA Crossover"
    description = "ซื้อเมื่อ EMA เร็วตัด EMA ช้าขึ้น; ขายเมื่อตัดลง"
    params = {"fast": 9, "slow": 21}

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema_fast"] = df["close"].ewm(span=self.params["fast"], adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.params["slow"], adjust=False).mean()
        return df

    def generate_signal(self, df: pd.DataFrame, i: int) -> Optional[Dict[str, Any]]:
        if i < self.params["slow"] + 1:
            return None
        fast_now = df["ema_fast"].iloc[i]
        slow_now = df["ema_slow"].iloc[i]
        fast_prev = df["ema_fast"].iloc[i - 1]
        slow_prev = df["ema_slow"].iloc[i - 1]
        if fast_prev <= slow_prev and fast_now > slow_now:
            return {"direction": "BUY", "reason": f"EMA{self.params['fast']} ตัด EMA{self.params['slow']} ขึ้น"}
        if fast_prev >= slow_prev and fast_now < slow_now:
            return {"direction": "SELL", "reason": f"EMA{self.params['fast']} ตัด EMA{self.params['slow']} ลง"}
        return None


class RSIReversionStrategy(BaseStrategy):
    """Mean-reversion on RSI extremes.

    BUY  when RSI crosses back above oversold line (30)
    SELL when RSI crosses back below overbought line (70)
    """

    name = "rsi_reversion"
    display_name = "RSI Mean Reversion"
    description = "ซื้อเมื่อ RSI เด้งจาก oversold; ขายเมื่อ RSI ตกจาก overbought"
    params = {"period": 14, "oversold": 30, "overbought": 70}

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=self.params["period"]).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=self.params["period"]).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    def generate_signal(self, df: pd.DataFrame, i: int) -> Optional[Dict[str, Any]]:
        if i < self.params["period"] + 1:
            return None
        rsi_now = df["rsi"].iloc[i]
        rsi_prev = df["rsi"].iloc[i - 1]
        if pd.isna(rsi_now) or pd.isna(rsi_prev):
            return None
        if rsi_prev < self.params["oversold"] <= rsi_now:
            return {"direction": "BUY", "reason": f"RSI เด้งจาก {rsi_prev:.1f} → {rsi_now:.1f}"}
        if rsi_prev > self.params["overbought"] >= rsi_now:
            return {"direction": "SELL", "reason": f"RSI ตกจาก {rsi_prev:.1f} → {rsi_now:.1f}"}
        return None


class MACDSignalStrategy(BaseStrategy):
    """MACD histogram zero-line crossover."""

    name = "macd_signal"
    display_name = "MACD Signal Cross"
    description = "ซื้อเมื่อ MACD histogram ข้าม 0 ขึ้น; ขายเมื่อข้ามลง"
    params = {"fast": 12, "slow": 26, "signal": 9}

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ema_fast = df["close"].ewm(span=self.params["fast"], adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.params["slow"], adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.params["signal"], adjust=False).mean()
        df["macd_hist"] = macd_line - signal_line
        return df

    def generate_signal(self, df: pd.DataFrame, i: int) -> Optional[Dict[str, Any]]:
        warmup = self.params["slow"] + self.params["signal"]
        if i < warmup + 1:
            return None
        hist_now = df["macd_hist"].iloc[i]
        hist_prev = df["macd_hist"].iloc[i - 1]
        if pd.isna(hist_now) or pd.isna(hist_prev):
            return None
        if hist_prev <= 0 < hist_now:
            return {"direction": "BUY", "reason": f"MACD histogram ข้าม 0 ขึ้น ({hist_now:.5f})"}
        if hist_prev >= 0 > hist_now:
            return {"direction": "SELL", "reason": f"MACD histogram ข้าม 0 ลง ({hist_now:.5f})"}
        return None


STRATEGIES: Dict[str, type[BaseStrategy]] = {
    EMAcrossoverStrategy.name: EMAcrossoverStrategy,
    RSIReversionStrategy.name: RSIReversionStrategy,
    MACDSignalStrategy.name: MACDSignalStrategy,
}


def list_strategies() -> List[Dict[str, Any]]:
    """Return metadata for all registered strategies (for frontend dropdown)."""
    out = []
    for name, cls in STRATEGIES.items():
        default = cls()
        out.append({
            "name": cls.name,
            "display_name": cls.display_name,
            "description": cls.description,
            "default_params": default.params,
        })
    return out
