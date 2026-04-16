"""Unit tests for Phase 4: Analysis Brain components"""
import pytest
from unittest.mock import patch


# ── Kill Switch ──
# Kill switch calls get_current_session() which may trigger dead_zone,
# so we mock it for clean isolated testing.

class TestKillSwitch:
    def _eval(self, **kwargs):
        from app.services.analysis.kill_switch import evaluate_kill_switch
        defaults = {
            "news_data": {},
            "indicators": {},
            "regime_data": {},
            "pair": "EUR/USD",
            "price": 1.085,
            "consecutive_losses": 0,
            "daily_loss_pct": 0.0,
            "scraper_failures": 0,
        }
        defaults.update(kwargs)
        # Mock dead zone and session to avoid time-dependent flakiness
        with patch("app.services.analysis.signal_generator.get_current_session", return_value={"session": "London", "is_dead_zone": False}):
            return evaluate_kill_switch(**defaults)

    def test_all_clear(self):
        r = self._eval()
        assert r["kill_switch_active"] is False
        assert r["trigger_count"] == 0

    def test_high_impact_news(self):
        r = self._eval(news_data={"high_impact_soon": True})
        assert r["kill_switch_active"] is True
        assert any(t["condition"] == "high_impact_news" for t in r["triggers"])

    def test_extreme_volatility(self):
        r = self._eval(indicators={"session_vol_index": 4.0})
        assert r["kill_switch_active"] is True
        assert any(t["condition"] == "extreme_volatility" for t in r["triggers"])

    def test_consecutive_losses(self):
        r = self._eval(consecutive_losses=3)
        assert r["kill_switch_active"] is True
        assert any(t["condition"] == "consecutive_losses" for t in r["triggers"])

    def test_daily_loss_limit(self):
        r = self._eval(daily_loss_pct=6.0)
        assert r["kill_switch_active"] is True
        assert any(t["condition"] == "daily_loss_limit" for t in r["triggers"])

    def test_scraper_failures(self):
        r = self._eval(scraper_failures=3)
        assert r["kill_switch_active"] is True
        assert any(t["condition"] == "data_insufficient" for t in r["triggers"])

    def test_multiple_triggers(self):
        r = self._eval(
            news_data={"high_impact_soon": True},
            consecutive_losses=5,
            daily_loss_pct=7.0,
        )
        assert r["kill_switch_active"] is True
        assert r["trigger_count"] >= 3

    def test_below_thresholds(self):
        r = self._eval(
            indicators={"session_vol_index": 2.0},
            consecutive_losses=2,
            daily_loss_pct=4.0,
            scraper_failures=1,
        )
        assert r["kill_switch_active"] is False


# ── Regime Detection ──
# detect_regime takes a dict of indicators, not keyword args

class TestRegimeDetection:
    def test_trending_regime(self):
        from app.services.analysis.regime import detect_regime
        r = detect_regime({"adx": 35, "atr": 0.002, "session_vol_index": 1.5})
        assert r["regime"] in ["trending", "volatile"]
        assert 0 <= r["regime_score"] <= 1

    def test_sideways_regime(self):
        from app.services.analysis.regime import detect_regime
        r = detect_regime({"adx": 15, "atr": 0.001, "session_vol_index": 0.8})
        assert r["regime"] == "sideways"

    def test_volatile_regime(self):
        from app.services.analysis.regime import detect_regime
        r = detect_regime({"adx": 20, "session_vol_index": 3.0})
        assert r["regime"] == "volatile"

    def test_squeeze_detection(self):
        from app.services.analysis.regime import detect_regime
        r = detect_regime({
            "adx": 18,
            "bb_upper": 1.090, "bb_lower": 1.085,
            "keltner_upper": 1.092, "keltner_lower": 1.083,
        })
        assert r["is_squeeze"] is True

    def test_empty_indicators(self):
        from app.services.analysis.regime import detect_regime
        r = detect_regime({})
        assert r["regime"] == "sideways"
        assert r["regime_score"] == 0.5


# ── News Sentiment ──

class TestNewsSentiment:
    def test_score_with_items(self):
        from app.services.analysis.sentiment import score_news_sentiment
        items = [
            {"impact_level": "high", "sentiment_score": 0.8, "scraped_at": "2025-01-01T12:00:00"},
            {"impact_level": "low", "sentiment_score": -0.2, "scraped_at": "2025-01-01T11:00:00"},
        ]
        r = score_news_sentiment(items, pair="EUR/USD")
        assert "news_score" in r
        assert "sentiment" in r
        assert 0 <= r["news_score"] <= 1

    def test_score_empty(self):
        from app.services.analysis.sentiment import score_news_sentiment
        r = score_news_sentiment([], pair="EUR/USD")
        assert r["news_score"] == 0.5
        assert r["sentiment"] == "neutral"


# ── Self-Diagnosis ──
# run_all_diagnostics is the real function name

class TestDiagnosis:
    def test_basic_run(self):
        from app.services.analysis.diagnosis import run_all_diagnostics
        r = run_all_diagnostics(
            indicators={"rsi": 50, "atr": 0.001, "ema_9": 1.085, "adx": 25, "macd_hist": 0.0001, "ema_21": 1.084},
            news_data={"news_count": 3, "sentiment": "neutral", "high_impact_soon": False},
            correlation_data={"correlation_score": 0.7},
            regime_data={"regime": "trending"},
            risk_gate={},
            pair="EUR/USD",
            price=1.085,
        )
        assert "diagnostics" in r
        assert "overall_health" in r
        assert isinstance(r["diagnostics"], list)
        assert r["overall_health"] in ["HEALTHY", "WARNING", "ERROR", "CRITICAL"]

    def test_missing_indicators(self):
        from app.services.analysis.diagnosis import run_all_diagnostics
        r = run_all_diagnostics(
            indicators={},
            news_data={"news_count": 0, "sentiment": "neutral"},
            correlation_data={},
            regime_data={},
            risk_gate={},
            pair="EUR/USD",
            price=1.085,
        )
        assert r["issues"] > 0


# ── Signal Generator ──

class TestSignalGenerator:
    def test_current_session(self):
        from app.services.analysis.signal_generator import get_current_session
        s = get_current_session()
        assert "session" in s
        assert "is_dead_zone" in s
        assert isinstance(s["is_dead_zone"], bool)
        assert 0 <= s["utc_hour"] < 24

    def test_session_info_fields(self):
        from app.services.analysis.signal_generator import get_current_session
        s = get_current_session()
        assert "thai_hour" in s
        assert s["thai_hour"] == (s["utc_hour"] + 7) % 24


# ── Correlation ──

class TestCorrelation:
    def test_boj_risk_safe(self):
        from app.services.analysis.correlation import check_boj_risk
        r = check_boj_risk("USD/JPY", 145.0)
        assert "risk" in r
        assert r["risk"] in ["LOW", "MEDIUM", "HIGH"]

    def test_boj_risk_danger_zone(self):
        from app.services.analysis.correlation import check_boj_risk
        r = check_boj_risk("USD/JPY", 160.0)
        assert r["risk"] == "HIGH"

    def test_non_jpy_pair(self):
        from app.services.analysis.correlation import check_boj_risk
        r = check_boj_risk("EUR/USD", 1.085)
        assert r["risk"] == "LOW"
