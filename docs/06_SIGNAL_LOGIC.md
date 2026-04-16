# SOCHRON1K — Analysis & Signal Logic (High Win Rate)

## Multi-Layer Confirmation System

> **หลักการ:** ไม่มีสัญญาณใดควรใช้คนเดียว — ต้องผ่านอย่างน้อย 4-5 ชั้น

```
┌────────────────────────────────────────────────────────┐
│                  ANALYSIS PIPELINE                       │
│                                                          │
│  Layer 1: MARKET REGIME DETECTION                       │
│  ├─ ADX > 25 → Trending (ใช้ trend strategy)             │
│  ├─ ADX < 20 + BB squeeze → Sideways (mean reversion)   │
│  └─ ATR spike > 2x avg → Volatile (ระวัง/หยุด)           │
│           ↓                                              │
│  Layer 2: NEWS SENTIMENT FILTER                         │
│  ├─ Aggregate sentiment from 5 sources                  │
│  ├─ High impact news within 1hr → PAUSE                 │
│  ├─ Strong bullish (>0.5) → favor BUY                   │
│  └─ Strong bearish (<-0.5) → favor SELL                 │
│           ↓                                              │
│  Layer 3: TECHNICAL INDICATOR CONFLUENCE                │
│  ├─ EMA alignment (9>21>50>200 = strong uptrend)        │
│  ├─ RSI not overbought for BUY signals                  │
│  ├─ MACD histogram matches direction                    │
│  ├─ Multi-timeframe check (1H + 4H + 1D agree)         │
│  └─ Score: agreements / total indicators                │
│           ↓                                              │
│  Layer 4: INTER-MARKET CORRELATION                      │
│  ├─ DXY direction confirms? (USD pairs)                 │
│  ├─ EUR/USD vs USD/CHF divergence                       │
│  ├─ VIX check (JPY safe-haven)                          │
│  ├─ Nikkei/S&P direction (JPY pairs)                    │
│  └─ Currency Strength Index confirms?                   │
│           ↓                                              │
│  Layer 5: RISK GATE                                     │
│  ├─ R:R ratio >= 1:2?                                   │
│  ├─ ATR-based SL within range?                          │
│  ├─ Active trading session?                             │
│  ├─ No BOJ intervention zone? (JPY)                     │
│  └─ No high-impact news next 60 min?                    │
│           ↓                                              │
│  ═══════════════════════════════════════                 │
│  FINAL SIGNAL + CONFIDENCE SCORE                        │
│  ═══════════════════════════════════════                 │
└────────────────────────────────────────────────────────┘
```

## Confidence Scoring

```python
confidence = (
    regime_score     * 0.15 +
    news_score       * 0.25 +
    technical_score  * 0.35 +
    correlation_score * 0.15 +
    risk_gate_score  * 0.10
)

# Signal Rules:
# confidence >= 0.75 → STRONG SIGNAL (แนะนำเทรด)
# confidence 0.50-0.74 → MODERATE (เทรดได้ ระวัง)
# confidence < 0.50 → WEAK / NO TRADE
```

## Time-of-Day Rules (เวลาไทย GMT+7)

| เวลา | Session | Action |
|---|---|---|
| 07:00-08:00 | Tokyo Fix | JPY spike เล็กๆ ทุกเช้า |
| 08:00-14:00 | Asian | Low vol, range trading OK for EUR/JPY |
| 14:00-15:00 | London Open | EUR high vol → Breakout strategy |
| 15:00-19:00 | London | Best for EUR/USD trend |
| 19:00-22:00 | NY Overlap | HIGHEST vol → Best for ALL pairs |
| 22:00-01:00 | NY | USD pairs still active |
| 01:00-07:00 | Dead Zone | **AVOID** — low liquidity, whipsaws |

## Key Correlations to Monitor

| Correlation | Logic |
|---|---|
| **USD vs DXY** | DXY up → USD strong → EUR/USD down, USD/JPY up |
| **EUR/USD vs USD/CHF** | ~100% negative correlation — confirm signals |
| **JPY vs VIX** | VIX up → JPY strong (safe-haven flow) |
| **JPY vs Nikkei** | Nikkei down → JPY strong |
| **EUR/USD vs GBP/USD** | ~80% positive — cross-confirm |

## BOJ Intervention Logic (Hard-coded Safety)

```python
BOJ_DANGER_ZONES = {
    "USD/JPY": [150.00, 155.00, 160.00],
    "EUR/JPY": [165.00, 170.00],
}

def check_boj_risk(pair, price):
    zones = BOJ_DANGER_ZONES.get(pair, [])
    for zone in zones:
        if abs(price - zone) < 1.0:  # within 100 pips
            return {
                "risk": "HIGH",
                "message": f"ใกล้ BOJ intervention zone {zone}",
                "action": "widen SL 1.5x or AVOID"
            }
    return {"risk": "LOW"}
```

## Kill Switch Conditions

ระบบจะ **หยุดให้สัญญาณ** เมื่อ:

1. High-impact news ในอีก 30 นาที
2. ATR > 3x ค่าเฉลี่ย 20 วัน (extreme volatility)
3. ผู้ใช้ขาดทุนติดต่อกัน 3 ครั้ง (cool-down 24 ชม.)
4. Daily loss > 5% ของทุน
5. JPY อยู่ใน BOJ intervention zone
6. ตลาดอยู่ในช่วง Dead Zone (01:00-07:00)
7. Scraper ล้มเหลว > 2 sources (data ไม่เพียงพอ)
