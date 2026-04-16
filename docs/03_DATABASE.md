# SOCHRON1K — Database Architecture

## PostgreSQL Tables

### news_items — ข่าวที่ scrape มา

```sql
CREATE TABLE news_items (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,        -- 'forex_factory', 'investing', etc.
    currency        VARCHAR(10) NOT NULL,         -- 'USD', 'EUR', 'JPY'
    pair            VARCHAR(10),                  -- 'EUR/USD' or NULL
    title_original  TEXT NOT NULL,
    title_th        TEXT,                         -- Claude Haiku translated
    summary_original TEXT,
    summary_th      TEXT,
    impact_level    VARCHAR(10) NOT NULL,         -- 'high', 'medium', 'low'
    sentiment_score FLOAT,                        -- -1.0 (bearish) to +1.0 (bullish)
    event_time      TIMESTAMPTZ,
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    raw_data        JSONB
);
CREATE INDEX idx_news_pair_time ON news_items(pair, event_time DESC);
CREATE INDEX idx_news_impact ON news_items(impact_level, event_time DESC);
```

### analyses — ผลวิเคราะห์

```sql
CREATE TABLE analyses (
    id              BIGSERIAL PRIMARY KEY,
    pair            VARCHAR(10) NOT NULL,
    timeframe       VARCHAR(10) NOT NULL,         -- '1H', '4H', '1D'
    direction       VARCHAR(10) NOT NULL,         -- 'BUY', 'SELL', 'NEUTRAL'
    confidence      FLOAT NOT NULL,               -- 0.0 - 1.0

    -- Component scores
    trend_score     FLOAT,
    news_score      FLOAT,
    indicator_score FLOAT,
    correlation_score FLOAT,
    regime          VARCHAR(20),                  -- 'trending_up','trending_down','sideways','volatile'

    indicators_data JSONB NOT NULL,               -- {"rsi":45,"adx":30,...}

    -- Recommendations
    suggested_entry FLOAT,
    suggested_sl    FLOAT,
    suggested_tp    FLOAT,
    suggested_lots  FLOAT,
    risk_reward     FLOAT,

    analysis_summary_th TEXT,
    errors_found    JSONB,                        -- self-diagnosis
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    -- Validation (filled after trade)
    was_correct     BOOLEAN,
    actual_outcome  FLOAT
);
CREATE INDEX idx_analysis_pair_time ON analyses(pair, created_at DESC);
```

### trades — บันทึกเทรดจริง

```sql
CREATE TABLE trades (
    id              BIGSERIAL PRIMARY KEY,
    analysis_id     BIGINT REFERENCES analyses(id),
    pair            VARCHAR(10) NOT NULL,
    direction       VARCHAR(10) NOT NULL,

    -- User input
    account_balance FLOAT NOT NULL,
    lot_size        FLOAT NOT NULL,
    entry_price     FLOAT NOT NULL,
    sl_price        FLOAT,
    tp_price        FLOAT,
    target_pips     FLOAT,
    target_hours    FLOAT,

    -- Result (user reports)
    exit_price      FLOAT,
    actual_pips     FLOAT,
    profit_loss     FLOAT,
    status          VARCHAR(20) DEFAULT 'open',   -- 'open','win','loss','breakeven','cancelled'

    opened_at       TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    user_notes      TEXT
);
CREATE INDEX idx_trades_pair_status ON trades(pair, status);
```

### system_diagnostics — error detection

```sql
CREATE TABLE system_diagnostics (
    id              BIGSERIAL PRIMARY KEY,
    analysis_id     BIGINT REFERENCES analyses(id),
    diagnostic_type VARCHAR(50) NOT NULL,
    severity        VARCHAR(10) NOT NULL,         -- 'warning','error','critical'
    message         TEXT NOT NULL,
    details         JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Win Rate View

```sql
CREATE VIEW v_winrate_by_pair AS
SELECT
    pair,
    COUNT(*) FILTER (WHERE status IN ('win','loss','breakeven')) AS total_trades,
    COUNT(*) FILTER (WHERE status = 'win') AS wins,
    COUNT(*) FILTER (WHERE status = 'loss') AS losses,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE status IN ('win','loss')), 0) * 100, 2
    ) AS win_rate_pct,
    ROUND(AVG(actual_pips) FILTER (WHERE status IN ('win','loss'))::NUMERIC, 2) AS avg_pips,
    ROUND(SUM(profit_loss) FILTER (WHERE status IN ('win','loss'))::NUMERIC, 2) AS total_pnl
FROM trades GROUP BY pair;
```

---

## TimescaleDB — Price OHLCV

```sql
CREATE TABLE price_ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    pair        VARCHAR(10) NOT NULL,
    timeframe   VARCHAR(10) NOT NULL,
    open        FLOAT NOT NULL,
    high        FLOAT NOT NULL,
    low         FLOAT NOT NULL,
    close       FLOAT NOT NULL,
    volume      FLOAT
);
SELECT create_hypertable('price_ohlcv', 'time');
CREATE INDEX idx_price_pair_tf ON price_ohlcv(pair, timeframe, time DESC);
```

---

## Redis Cache Structure

```
# Prices (TTL: 5s)
price:EUR/USD     → {"bid":1.1050,"ask":1.1052,"time":"..."}
price:USD/JPY     → {"bid":149.50,"ask":149.52,"time":"..."}
price:EUR/JPY     → {"bid":165.20,"ask":165.23,"time":"..."}

# News (TTL: 30min)
news:latest       → [serialized news list]
news:high_impact  → [high impact only]

# Analysis (TTL: 10min)
analysis:EUR/USD  → {serialized analysis}

# Scraper state
scraper:last_run:{source}  → timestamp
scraper:status:{source}    → "ok" | "error"

# Pub/Sub channels
channel:price_update   → real-time price broadcasts
channel:news_alert     → breaking news
channel:analysis_ready → new analysis done
```
