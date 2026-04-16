# SOCHRON1K — Technical Indicators Engine

## Built-in Indicators (TA-Lib / pandas-ta)

| Category | Indicator | Params | Usage |
|---|---|---|---|
| **Trend** | EMA | (9, 21, 50, 200) | Direction, crossover signals |
| **Trend** | SMA | (50, 200) | Golden/Death cross |
| **Trend** | ADX | (14) | Trend strength (>25 = trending) |
| **Trend** | MACD | (12, 26, 9) | Momentum & trend |
| **Oscillator** | RSI | (14) | Overbought(>70) / Oversold(<30) |
| **Oscillator** | Stochastic | (14, 3, 3) | Short-term reversal |
| **Oscillator** | CCI | (20) | Cycle detection |
| **Volatility** | Bollinger Bands | (20, 2) | Squeeze, mean reversion |
| **Volatility** | ATR | (14) | Dynamic SL/TP calculation |
| **Volatility** | Keltner Channel | (20) | BB-Keltner squeeze |
| **Volume** | OBV | — | Volume confirmation |

## Custom Indicators (สร้างเอง)

| Indicator | Logic | Purpose |
|---|---|---|
| **Currency Strength Index** | % change of USD/EUR/JPY from basket of pairs | ดูว่าสกุลไหนแข็ง/อ่อนจริง |
| **News Impact Score** | Weighted avg of sentiment from last 24h news | Fundamental overlay |
| **Multi-TF Confluence** | EMA alignment across 1H + 4H + 1D | High-probability entries |
| **Session Volatility Index** | ATR ratio: current session vs avg | ตลาดปกติหรือผิดปกติ |
| **Z-Score (20)** | (price - SMA) / StdDev | Mean reversion signal (JPY) |
| **Correlation Divergence** | EUR/USD vs DXY correlation break | False breakout detection |
| **Liquidity Spike Detector** | Volume spike + price reversal | ดักจุด MM กวาด SL |

## Indicator Engine (Pseudo-code)

```python
def run_indicators(pair: str, timeframe: str) -> IndicatorSnapshot:
    candles = get_candles(pair, timeframe, lookback=500)

    result = {
        # Trend
        "ema_9": ta.ema(candles.close, 9),
        "ema_21": ta.ema(candles.close, 21),
        "ema_50": ta.ema(candles.close, 50),
        "ema_200": ta.ema(candles.close, 200),
        "adx": ta.adx(candles, 14),
        "macd": ta.macd(candles.close, 12, 26, 9),

        # Oscillators
        "rsi": ta.rsi(candles.close, 14),
        "stochastic": ta.stoch(candles, 14, 3, 3),

        # Volatility
        "bollinger": ta.bbands(candles.close, 20, 2),
        "atr": ta.atr(candles, 14),

        # Custom
        "currency_strength": calc_currency_strength(pair),
        "z_score": calc_z_score(candles.close, 20),
        "session_vol_index": calc_session_volatility(),
        "correlation_div": calc_correlation_divergence(pair),
    }

    save_snapshot(pair, timeframe, result)
    return result
```

## Per-Pair Strategy Mapping

| Pair | Primary Strategy | Secondary | Key Filter |
|---|---|---|---|
| **EUR/USD** | London Open Breakout (14:00-15:00 TH) | EMA Crossover + ADX | DXY correlation |
| **USD/JPY** | Trend Following (NY session) | Mean Reversion (Z-Score) | VIX + Nikkei, BOJ zone |
| **EUR/JPY** | Momentum (strongest trend EUR vs JPY) | Range trading (Asian) | Currency Strength diff |
