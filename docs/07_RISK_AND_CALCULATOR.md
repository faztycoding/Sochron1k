# SOCHRON1K — Risk Management & Trade Calculator

## Trade Calculator — User Input

```
คู่เงิน:           [EUR/USD ▼]
ทิศทาง:           [BUY / SELL]

═══ ข้อมูลพอร์ต ═══
ต้นทุนในพอร์ต:     [___] USD
ความเสี่ยงต่อไม้:   [1-2% ▼]

═══ เป้าหมาย ═══
TP (pips):         [___] หรือ จำนวนเงิน [___]
SL (pips):         [___] หรือ [อัตโนมัติ]
จำนวน Lot:        [___] หรือ [คำนวณให้]
ระยะเวลา:         [___] ชม. หรือ [วิเคราะห์ให้]
เป้า pips:        [1000-2000]
```

## Auto SL/TP Logic

```python
def calculate_auto_sl(pair, direction, timeframe="1H"):
    atr = get_atr(pair, period=14, timeframe=timeframe)
    regime = detect_market_regime(pair)

    if regime == "volatile":
        sl_multiplier = 2.5   # wider in volatile market
    elif regime == "trending":
        sl_multiplier = 1.5
    else:  # sideways
        sl_multiplier = 1.0

    sl_pips = atr * sl_multiplier

    # BOJ zone → widen SL
    if "JPY" in pair:
        price = get_current_price(pair)
        if is_near_psychological_level(price, threshold=100):
            sl_pips *= 1.5

    return round(sl_pips, 1)


def calculate_auto_tp(sl_pips, min_rr=2.0, target_pips=None):
    if target_pips:
        return target_pips
    return round(sl_pips * min_rr, 1)  # minimum R:R = 1:2


def calculate_lot_size(balance, risk_pct, sl_pips, pair):
    risk_amount = balance * (risk_pct / 100)
    pip_value = get_pip_value(pair, lot_size=1.0)
    lot_size = risk_amount / (sl_pips * pip_value)
    return round(lot_size, 2)
```

## Position Size Rules (ทุน 30,000 THB ≈ $830)

| Rule | Description |
|---|---|
| **Max risk per trade** | 2% ($16.60) |
| **Max open positions** | 2 |
| **Max total exposure** | 5% ($41.50) |
| **3 consecutive losses** | STOP 24 hours (cool-down) |
| **Daily loss limit** | 5% → Kill Switch |

## Pip Value Reference

| Pair | Pip Value (1 standard lot) | Pip Value (0.01 lot) |
|---|---|---|
| EUR/USD | $10/pip | $0.10/pip |
| USD/JPY | ~$6.70/pip (varies) | ~$0.067/pip |
| EUR/JPY | ~$6.70/pip (varies) | ~$0.067/pip |

## ตัวอย่างการคำนวณ

```
ทุน:        $830
ความเสี่ยง:  1% = $8.30
คู่เงิน:     EUR/USD
SL:         50 pips (ATR-based)
Pip value:  $0.10/pip (0.01 lot)

Lot size = $8.30 / (50 × $10) = 0.0166 → 0.02 lot
TP (R:R 1:2) = 100 pips
Potential profit = 100 × $0.20 = $20
```

---

## Trade Journal Flow

```
1. User เทรดจริงตาม recommendation
2. บันทึกเทรดในแอพ: entry, SL, TP, lot, direction
3. เมื่อปิดเทรด → report: exit price, P/L, status
4. ระบบอัตโนมัติ:
   - Link trade → analysis ที่ generate สัญญาณ
   - Update was_correct + actual_outcome
   - Recalculate win rate
   - Feed data → future ML training
```

## Win Rate Dashboard

```
═══ Overall ═══
Total: 47 | Wins: 35 | Losses: 12 | Win Rate: 74.5%

═══ Per Pair ═══
EUR/USD:  78% (18/23)  Avg: +38 pips
USD/JPY:  69% (9/13)   Avg: +51 pips
EUR/JPY:  73% (8/11)   Avg: +44 pips

═══ Per Confidence Level ═══
High (>0.75):   85% accuracy
Medium (0.5-0.74): 65% accuracy
Low (<0.50):    45% accuracy  ← ไม่ควรเทรด
```
