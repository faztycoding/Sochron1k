"""Unit tests for Phase 6: Trade Calculator"""
import pytest

from app.services.calculator import (
    calculate_position, price_to_pips, pips_to_price, get_pip_info,
)


class TestPipConversions:
    def test_eurusd_pip_size(self):
        info = get_pip_info("EUR/USD")
        assert info["pip_size"] == 0.0001

    def test_usdjpy_pip_size(self):
        info = get_pip_info("USD/JPY")
        assert info["pip_size"] == 0.01

    def test_price_to_pips_eurusd(self):
        assert price_to_pips("EUR/USD", 0.003) == pytest.approx(30.0)

    def test_price_to_pips_usdjpy(self):
        assert price_to_pips("USD/JPY", 0.30) == pytest.approx(30.0)

    def test_pips_to_price_eurusd(self):
        assert pips_to_price("EUR/USD", 30) == pytest.approx(0.003)

    def test_pips_to_price_usdjpy(self):
        assert pips_to_price("USD/JPY", 30) == pytest.approx(0.30)

    def test_roundtrip(self):
        for pair in ["EUR/USD", "USD/JPY", "EUR/JPY"]:
            pips = 25.0
            price = pips_to_price(pair, pips)
            back = price_to_pips(pair, price)
            assert back == pytest.approx(pips)


class TestPositionCalculator:
    def test_basic_buy(self):
        r = calculate_position("EUR/USD", "BUY", 1000, 2, 1.08500)
        assert r["lot_size"] > 0
        assert r["risk_reward"] > 0
        assert r["sl_price"] < 1.08500
        assert r["tp_price"] > 1.08500
        assert r["risk_amount"] == pytest.approx(20.0)

    def test_basic_sell(self):
        r = calculate_position("EUR/USD", "SELL", 1000, 2, 1.08500)
        assert r["sl_price"] > 1.08500
        assert r["tp_price"] < 1.08500

    def test_custom_sl_tp(self):
        r = calculate_position(
            "EUR/USD", "BUY", 1000, 2, 1.08500,
            sl_price=1.08200, tp_price=1.09100,
        )
        assert r["sl_pips"] == pytest.approx(30.0)
        assert r["tp_pips"] == pytest.approx(60.0)
        assert r["risk_reward"] == pytest.approx(2.0)

    def test_sl_pips_input(self):
        r = calculate_position(
            "USD/JPY", "BUY", 500, 1, 150.000,
            sl_pips=20, tp_pips=40,
        )
        assert r["sl_pips"] == pytest.approx(20.0)
        assert r["tp_pips"] == pytest.approx(40.0)
        assert r["sl_price"] == pytest.approx(149.800, abs=0.01)

    def test_warnings_high_risk(self):
        r = calculate_position("EUR/USD", "BUY", 1000, 8, 1.08500)
        warnings = " ".join(r["warnings"])
        assert "5%" in warnings

    def test_warnings_low_rr(self):
        r = calculate_position(
            "EUR/USD", "BUY", 1000, 2, 1.08500,
            sl_pips=30, tp_pips=20,
        )
        assert r["risk_reward"] < 1.5
        warnings = " ".join(r["warnings"])
        assert "R:R" in warnings

    def test_default_sl_tp(self):
        r = calculate_position("EUR/USD", "BUY", 1000, 2, 1.08500)
        assert r["sl_pips"] == pytest.approx(30.0)
        assert r["tp_pips"] == pytest.approx(60.0)
        assert any("default" in w for w in r["warnings"])

    def test_min_lot_size(self):
        r = calculate_position("EUR/USD", "BUY", 10, 0.5, 1.08500, sl_pips=100)
        assert r["lot_size"] >= 0.01

    def test_jpy_pair(self):
        r = calculate_position("USD/JPY", "SELL", 1000, 2, 150.000, sl_pips=30, tp_pips=60)
        assert r["pair"] == "USD/JPY"
        assert r["sl_price"] > 150.0
        assert r["tp_price"] < 150.0

    def test_all_pairs(self):
        for pair in ["EUR/USD", "USD/JPY", "EUR/JPY"]:
            r = calculate_position(pair, "BUY", 1000, 2, 1.08500 if "JPY" not in pair else 150.0)
            assert r["lot_size"] > 0
            assert r["risk_reward"] > 0
