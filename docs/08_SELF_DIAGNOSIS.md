# SOCHRON1K — Self-Diagnosis & Error Detection

## Diagnostic Checks (รันหลังทุกการวิเคราะห์)

### Data Quality
| Check | Logic | Severity |
|---|---|---|
| `is_price_data_stale` | ข้อมูลราคาเก่าเกิน 5 นาที | error |
| `is_news_data_stale` | ข่าวอัพเดทล่าสุดเกิน 3 ชม. | warning |
| `has_missing_indicators` | มี indicator คำนวณไม่ได้ | error |

### Logic Contradictions
| Check | Logic | Severity |
|---|---|---|
| `news_vs_technical_conflict` | ข่าว bullish แต่ technical bearish | warning |
| `multi_tf_disagreement` | 1H = BUY แต่ 4H = SELL | warning |
| `correlation_anomaly` | DXY ไม่สอดคล้อง EUR/USD | warning |

### Risk Warnings
| Check | Logic | Severity |
|---|---|---|
| `sl_too_tight` | SL < 1 ATR | warning |
| `sl_too_wide` | SL > 3 ATR | warning |
| `rr_ratio_too_low` | R:R < 1:1.5 | error |
| `near_psychological_level` | ใกล้เลขกลม (150.00, 1.1000) | warning |
| `high_impact_news_soon` | ข่าวแรงใน 60 นาที | critical |
| `outside_trading_hours` | Dead Zone 01:00-07:00 | warning |
| `consecutive_losses` | ขาดทุนติดกัน >= 3 | critical |

### Market Conditions
| Check | Logic | Severity |
|---|---|---|
| `extreme_volatility` | ATR > 2x avg | critical |
| `low_liquidity_warning` | Volume ต่ำผิดปกติ | warning |
| `boj_intervention_risk` | JPY ใกล้ zone แทรกแซง | critical |

### System Health
| Check | Logic | Severity |
|---|---|---|
| `scraper_failures` | Scraper fail > 2 sources | error |
| `api_rate_limit_warning` | API calls ใกล้ limit | warning |
| `analysis_took_too_long` | วิเคราะห์นาน > 30 วินาที | warning |

## Output Example

```json
{
  "analysis_id": 123,
  "diagnostics": [
    {
      "check": "news_vs_technical_conflict",
      "severity": "warning",
      "message": "ข่าว Bullish (0.6) แต่ RSI Overbought (78) — อาจเป็นจุดสูงสุด",
      "recommendation": "ลด confidence 15% หรือรอ RSI < 70"
    },
    {
      "check": "high_impact_news_soon",
      "severity": "critical",
      "message": "FOMC Rate Decision ในอีก 45 นาที",
      "recommendation": "PAUSE — รอหลังข่าว 30 นาที"
    }
  ],
  "overall_health": "WARNING",
  "adjusted_confidence": 0.55
}
```

## Confidence Adjustment Rules

```python
def adjust_confidence(base_confidence, diagnostics):
    adjusted = base_confidence

    for d in diagnostics:
        if d.severity == "critical":
            adjusted *= 0.5     # ลดครึ่ง
        elif d.severity == "error":
            adjusted *= 0.8     # ลด 20%
        elif d.severity == "warning":
            adjusted *= 0.9     # ลด 10%

    return max(0.0, min(1.0, adjusted))
```
