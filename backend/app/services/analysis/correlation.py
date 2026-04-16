"""Layer 4: Inter-market Correlation — DXY, VIX, Nikkei"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CORRELATION_RULES = {
    "EUR/USD": {
        "DXY": {"expected": "negative", "desc": "DXY ↑ → EUR/USD ↓"},
        "VIX": {"expected": "mild_negative", "desc": "VIX ↑ → risk-off → EUR อ่อน"},
    },
    "USD/JPY": {
        "DXY": {"expected": "positive", "desc": "DXY ↑ → USD ↑ → USD/JPY ↑"},
        "VIX": {"expected": "negative", "desc": "VIX ↑ → JPY แข็ง → USD/JPY ↓"},
        "NIKKEI": {"expected": "positive", "desc": "Nikkei ↑ → JPY อ่อน → USD/JPY ↑"},
    },
    "EUR/JPY": {
        "VIX": {"expected": "negative", "desc": "VIX ↑ → JPY แข็ง → EUR/JPY ↓"},
        "NIKKEI": {"expected": "positive", "desc": "Nikkei ↑ → JPY อ่อน → EUR/JPY ↑"},
    },
}

BOJ_DANGER_ZONES = {
    "USD/JPY": [150.00, 155.00, 160.00],
    "EUR/JPY": [165.00, 170.00],
}


def check_correlations(
    pair: str,
    pair_closes: List[float],
    market_data: Dict[str, List[float]],
    period: int = 20,
) -> Dict[str, Any]:
    rules = CORRELATION_RULES.get(pair, {})
    if not rules or not pair_closes:
        return {
            "correlation_score": 0.5,
            "checks": [],
            "details": ["ไม่มีข้อมูล correlation"],
        }

    checks = []
    confirmations = 0
    total = 0

    for market, rule in rules.items():
        market_closes = market_data.get(market, [])
        if len(market_closes) < period or len(pair_closes) < period:
            checks.append({
                "market": market,
                "status": "ไม่มีข้อมูล",
                "confirms": False,
            })
            continue

        total += 1
        corr = float(
            pd.Series(pair_closes[-period:]).corr(pd.Series(market_closes[-period:]))
        )

        expected = rule["expected"]
        confirms = False

        if expected == "negative" and corr < -0.3:
            confirms = True
        elif expected == "positive" and corr > 0.3:
            confirms = True
        elif expected == "mild_negative" and corr < 0:
            confirms = True

        if confirms:
            confirmations += 1

        checks.append({
            "market": market,
            "correlation": round(corr, 4),
            "expected": expected,
            "confirms": confirms,
            "desc": rule["desc"],
        })

    score = confirmations / total if total > 0 else 0.5
    details = [
        f"{c['market']}: corr={c.get('correlation', 'N/A')} ({'✓' if c['confirms'] else '✗'})"
        for c in checks
    ]

    return {
        "correlation_score": round(score, 4),
        "confirmations": confirmations,
        "total_checks": total,
        "checks": checks,
        "details": details,
    }


def check_boj_risk(pair: str, price: float) -> Dict[str, Any]:
    zones = BOJ_DANGER_ZONES.get(pair, [])
    for zone in zones:
        distance_pips = abs(price - zone) * (100 if "JPY" in pair else 10000)
        if distance_pips < 100:
            return {
                "risk": "HIGH",
                "zone": zone,
                "distance_pips": round(distance_pips, 1),
                "message": f"ใกล้ BOJ intervention zone {zone} ({distance_pips:.0f} pips)",
                "action": "widen SL 1.5x หรือ AVOID",
            }
    return {"risk": "LOW", "message": "ไม่มีความเสี่ยง BOJ"}
