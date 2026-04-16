"""Unit tests for Phase 3: Built-in indicators"""
import numpy as np
import pandas as pd
import pytest

from app.services.indicators.builtin import (
    calc_ema, calc_sma, calc_rsi, calc_macd, calc_adx,
    calc_stochastic, calc_cci, calc_bollinger, calc_atr,
    calc_keltner, calc_obv, compute_all_builtin,
)


def _make_closes(n=50, start=1.08, step=0.0001):
    """Generate realistic close prices"""
    np.random.seed(42)
    noise = np.random.randn(n) * 0.001
    return pd.Series([start + i * step + noise[i] for i in range(n)])


def _make_ohlcv_df(n=50, start=100.0):
    """Generate realistic OHLCV DataFrame"""
    np.random.seed(42)
    data = []
    price = start
    for _ in range(n):
        change = np.random.randn() * 0.5
        o = price
        c = price + change
        h = max(o, c) + abs(np.random.randn() * 0.2)
        l = min(o, c) - abs(np.random.randn() * 0.2)
        v = abs(np.random.randn() * 1000) + 100
        data.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
        price = c
    return pd.DataFrame(data)


def _make_candle_dicts(n=50, start=1.085):
    """Generate candle dicts for compute_all_builtin"""
    np.random.seed(42)
    candles = []
    price = start
    for _ in range(n):
        change = np.random.randn() * 0.001
        o = price
        c = price + change
        h = max(o, c) + abs(np.random.randn() * 0.0003)
        l = min(o, c) - abs(np.random.randn() * 0.0003)
        v = abs(np.random.randn() * 1000) + 100
        candles.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
        price = c
    return candles


# ── EMA ──

class TestEMA:
    def test_basic(self):
        closes = _make_closes(20)
        result = calc_ema(closes, 9)
        assert result is not None
        assert isinstance(result, float)

    def test_too_short(self):
        closes = _make_closes(5)
        assert calc_ema(closes, 9) is None

    def test_exact_minimum(self):
        closes = _make_closes(9)
        assert calc_ema(closes, 9) is not None

    def test_different_periods(self):
        closes = _make_closes(50)
        ema9 = calc_ema(closes, 9)
        ema21 = calc_ema(closes, 21)
        assert ema9 is not None
        assert ema21 is not None
        assert ema9 != ema21


# ── SMA ──

class TestSMA:
    def test_basic(self):
        closes = _make_closes(30)
        result = calc_sma(closes, 20)
        assert result is not None

    def test_too_short(self):
        closes = _make_closes(10)
        assert calc_sma(closes, 20) is None

    def test_matches_manual(self):
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = calc_sma(closes, 5)
        assert result == pytest.approx(3.0)


# ── RSI ──

class TestRSI:
    def test_normal_range(self):
        closes = _make_closes(30)
        result = calc_rsi(closes)
        assert result is not None
        assert 0 <= result <= 100

    def test_too_short(self):
        closes = _make_closes(10)
        assert calc_rsi(closes) is None

    def test_all_up(self):
        closes = pd.Series(range(1, 20), dtype=float)
        result = calc_rsi(closes)
        assert result == 100.0

    def test_all_down(self):
        closes = pd.Series(range(20, 1, -1), dtype=float)
        result = calc_rsi(closes)
        assert result == 0.0


# ── MACD ──

class TestMACD:
    def test_basic(self):
        closes = _make_closes(50)
        result = calc_macd(closes)
        assert result["macd_line"] is not None
        assert result["macd_signal"] is not None
        assert result["macd_hist"] is not None

    def test_too_short(self):
        closes = _make_closes(20)
        result = calc_macd(closes)
        assert result["macd_line"] is None


# ── ADX ──

class TestADX:
    def test_basic(self):
        df = _make_ohlcv_df(50)
        result = calc_adx(df)
        assert result is not None
        assert result >= 0

    def test_too_short(self):
        df = _make_ohlcv_df(10)
        assert calc_adx(df) is None


# ── Stochastic ──

class TestStochastic:
    def test_basic(self):
        df = _make_ohlcv_df(30)
        result = calc_stochastic(df)
        assert result["stoch_k"] is not None
        assert result["stoch_d"] is not None
        assert 0 <= result["stoch_k"] <= 100

    def test_too_short(self):
        df = _make_ohlcv_df(5)
        result = calc_stochastic(df)
        assert result["stoch_k"] is None


# ── CCI ──

class TestCCI:
    def test_basic(self):
        df = _make_ohlcv_df(30)
        result = calc_cci(df)
        assert result is not None

    def test_too_short(self):
        df = _make_ohlcv_df(10)
        assert calc_cci(df) is None


# ── Bollinger Bands ──

class TestBollinger:
    def test_basic(self):
        closes = _make_closes(30)
        result = calc_bollinger(closes)
        assert result["bb_upper"] is not None
        assert result["bb_middle"] is not None
        assert result["bb_lower"] is not None
        assert result["bb_upper"] > result["bb_middle"] > result["bb_lower"]

    def test_too_short(self):
        closes = _make_closes(10)
        result = calc_bollinger(closes)
        assert result["bb_upper"] is None


# ── ATR ──

class TestATR:
    def test_basic(self):
        df = _make_ohlcv_df(30)
        result = calc_atr(df)
        assert result is not None
        assert result > 0

    def test_too_short(self):
        df = _make_ohlcv_df(10)
        assert calc_atr(df) is None


# ── Keltner ──

class TestKeltner:
    def test_basic(self):
        df = _make_ohlcv_df(30)
        result = calc_keltner(df)
        assert result["keltner_upper"] is not None
        assert result["keltner_lower"] is not None
        assert result["keltner_upper"] > result["keltner_lower"]

    def test_too_short(self):
        df = _make_ohlcv_df(10)
        result = calc_keltner(df)
        assert result["keltner_upper"] is None


# ── OBV ──

class TestOBV:
    def test_basic(self):
        df = _make_ohlcv_df(30)
        result = calc_obv(df)
        assert result is not None

    def test_too_short(self):
        df = _make_ohlcv_df(1)
        assert calc_obv(df) is None


# ── compute_all_builtin ──

class TestComputeAll:
    def test_basic(self):
        candles = _make_candle_dicts(50)
        result = compute_all_builtin(candles)
        assert isinstance(result, dict)
        assert "rsi" in result
        assert "ema_9" in result
        assert "macd_line" in result
        assert "bb_upper" in result
        assert "atr" in result

    def test_too_few_candles(self):
        candles = _make_candle_dicts(10)
        result = compute_all_builtin(candles)
        assert result == {}

    def test_all_keys_present(self):
        candles = _make_candle_dicts(250)
        result = compute_all_builtin(candles)
        expected_keys = [
            "ema_9", "ema_21", "ema_50", "sma_50", "adx", "rsi",
            "macd_line", "macd_signal", "macd_hist",
            "stoch_k", "stoch_d", "cci",
            "bb_upper", "bb_middle", "bb_lower",
            "atr", "keltner_upper", "keltner_lower", "obv",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
