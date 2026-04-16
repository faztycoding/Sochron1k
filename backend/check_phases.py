#!/usr/bin/env python3
"""Phase 2/3/4 verification script"""
import sys
sys.path.insert(0, '.')

def check(label, fn):
    try:
        fn()
        print(f"  OK  {label}")
        return True
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        return False

total = 0
passed = 0

print("=" * 60)
print("PHASE 2: Data Pipeline")
print("=" * 60)

def p2_scrapers():
    from app.services.scraper.base import BaseScraper, ScrapedItem
    from app.services.scraper.forex_factory import ForexFactoryScraper
    from app.services.scraper.investing import InvestingScraper
    from app.services.scraper.tradingview import TradingViewScraper
    from app.services.scraper.babypips import BabyPipsScraper
    from app.services.scraper.finviz import FinvizScraper
    from app.services.scraper.fallback_rss import RSSFallbackScraper
    from app.services.scraper.manager import ScraperManager

def p2_ai():
    from app.services.ai.gemini import GeminiService
    from app.services.ai.claude import ClaudeService

def p2_pipeline():
    from app.services.news_pipeline import NewsPipeline

def p2_celery():
    from app.tasks.celery_app import celery_app
    from app.tasks.news_tasks import scrape_source, run_full_pipeline

def p2_schemas():
    from app.models.schemas.news import NewsItemResponse, NewsPipelineResult, NewsFilter

def p2_api():
    from app.api.routes.news import router
    from app.api.routes.ws import router as wr

for label, fn in [
    ("Scrapers (7)", p2_scrapers),
    ("AI (Gemini+Claude)", p2_ai),
    ("News Pipeline", p2_pipeline),
    ("Celery Tasks", p2_celery),
    ("News Schemas", p2_schemas),
    ("News + WS API", p2_api),
]:
    total += 1
    if check(label, fn): passed += 1

print()
print("=" * 60)
print("PHASE 3: Indicators & Price")
print("=" * 60)

def p3_price():
    from app.services.price.twelve_data import TwelveDataService
    from app.services.price.yfinance_fallback import YFinanceFallback
    from app.services.price.manager import PriceManager

def p3_builtin():
    from app.services.indicators.builtin import compute_all_builtin, calc_rsi, calc_macd

def p3_custom():
    from app.services.indicators.custom import compute_all_custom, calc_z_score, calc_currency_strength

def p3_engine():
    from app.services.indicators.engine import IndicatorEngine

def p3_schemas():
    from app.models.schemas.indicators import IndicatorSnapshotResponse, QuickSummaryResponse

def p3_api():
    from app.api.routes.price import router
    from app.api.routes.indicators import router as ir

def p3_db():
    from app.models.db.price import OHLCVCandle, IndicatorSnapshot

def p3_math():
    import pandas as pd
    import numpy as np
    from app.services.indicators.builtin import calc_rsi, calc_ema, calc_macd, calc_bollinger
    s = pd.Series([1.08 + i*0.001 for i in range(50)])
    rsi_val = calc_rsi(s)
    assert rsi_val is not None, "RSI returned None"
    assert rsi_val == 100.0, f"RSI for all-gain should be 100, got {rsi_val}"
    assert calc_ema(s, 9) is not None, "EMA returned None"
    m = calc_macd(s)
    assert m["macd_line"] is not None, "MACD returned None"
    b = calc_bollinger(s)
    assert b["bb_upper"] is not None, "BB returned None"

for label, fn in [
    ("Price Services (3)", p3_price),
    ("Built-in Indicators", p3_builtin),
    ("Custom Indicators", p3_custom),
    ("Indicator Engine", p3_engine),
    ("Indicator Schemas", p3_schemas),
    ("Price + Indicator API", p3_api),
    ("DB Models (OHLCV)", p3_db),
    ("Math Validation", p3_math),
]:
    total += 1
    if check(label, fn): passed += 1

print()
print("=" * 60)
print("PHASE 4: Analysis Brain")
print("=" * 60)

def p4_regime():
    from app.services.analysis.regime import detect_regime
    r = detect_regime({"adx": 30, "atr": 0.001, "session_vol_index": 1.2, "bb_upper": 1.09, "bb_lower": 1.07, "keltner_upper": 1.095, "keltner_lower": 1.065})
    assert r["regime"] == "trending", f"Expected trending, got {r['regime']}"

def p4_sentiment():
    from app.services.analysis.sentiment import score_news_sentiment
    r = score_news_sentiment([], "EUR/USD")
    assert r["news_score"] == 0.5

def p4_correlation():
    from app.services.analysis.correlation import check_correlations, check_boj_risk
    boj = check_boj_risk("USD/JPY", 149.50)
    assert boj["risk"] == "HIGH", f"Expected HIGH near 150, got {boj['risk']}"
    boj2 = check_boj_risk("USD/JPY", 145.00)
    assert boj2["risk"] == "LOW"

def p4_signal():
    from app.services.analysis.signal_generator import compute_final_confidence, get_current_session
    c = compute_final_confidence(0.8, 0.7, 0.9, 0.6, 0.8)
    assert 0 <= c["confidence"] <= 1
    s = get_current_session()
    assert "session" in s

def p4_diagnosis():
    from app.services.analysis.diagnosis import run_all_diagnostics, adjust_confidence
    r = run_all_diagnostics(
        {"calculated_at": "2020-01-01T00:00:00", "rsi": 50, "adx": 25, "macd_hist": 0.001, "atr": 0.001, "ema_9": 1.08, "ema_21": 1.07, "multi_tf_confluence": 50, "session_vol_index": 1.0, "obv": 1000},
        {"news_count": 5, "sentiment": "neutral", "high_impact_soon": False},
        {"correlation_score": 0.5},
        {"regime": "trending"},
        {},
        "EUR/USD", 1.0850,
    )
    assert r["total_checks"] == 18, f"Expected 18 checks, got {r['total_checks']}"
    a = adjust_confidence(0.8, [{"severity": "critical"}])
    assert a == 0.4, f"Expected 0.4, got {a}"

def p4_killswitch():
    from app.services.analysis.kill_switch import evaluate_kill_switch
    ks = evaluate_kill_switch(
        {"high_impact_soon": True}, {}, {}, "EUR/USD", 1.0850,
    )
    assert ks["kill_switch_active"] == True

def p4_brain():
    from app.services.analysis.brain import AnalysisBrain

def p4_api():
    from app.api.routes.analysis import router
    routes = [r.path for r in router.routes]
    assert "/{pair}/run" in routes or any("run" in str(r) for r in routes)

def p4_schemas():
    from app.models.schemas.analysis import AnalysisRequest, AnalysisResponse, KillSwitchResult

for label, fn in [
    ("Market Regime", p4_regime),
    ("Sentiment Scoring", p4_sentiment),
    ("Correlation + BOJ", p4_correlation),
    ("Signal + Confidence", p4_signal),
    ("Diagnosis (18 checks)", p4_diagnosis),
    ("Kill Switch (7 conds)", p4_killswitch),
    ("Brain Orchestrator", p4_brain),
    ("Analysis API", p4_api),
    ("Analysis Schemas", p4_schemas),
]:
    total += 1
    if check(label, fn): passed += 1

print()
print("=" * 60)
print(f"TOTAL: {passed}/{total} passed")
if passed == total:
    print("ALL PHASES VERIFIED")
else:
    print(f"FAILURES: {total - passed}")
print("=" * 60)
