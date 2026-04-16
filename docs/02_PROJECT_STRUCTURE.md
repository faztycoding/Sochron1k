# SOCHRON1K — Project Structure

```
Sochron1k/
├── backend/                          # Python FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # Settings & env vars
│   │   ├── dependencies.py           # Dependency injection
│   │   │
│   │   ├── api/                      # API Layer
│   │   │   ├── routes/
│   │   │   │   ├── news.py           # GET/POST /news
│   │   │   │   ├── analysis.py       # GET/POST /analysis/{pair}
│   │   │   │   ├── indicators.py     # GET /indicators/{pair}
│   │   │   │   ├── trade.py          # CRUD /trades
│   │   │   │   ├── calculator.py     # POST /calculate
│   │   │   │   └── stats.py          # GET /winrate, /stats
│   │   │   └── websockets/
│   │   │       ├── price_feed.py     # WS real-time prices
│   │   │       └── news_alert.py     # WS breaking news
│   │   │
│   │   ├── core/                     # Business Logic
│   │   │   ├── scraper/              # Web Scraping Engine
│   │   │   │   ├── base.py           # Abstract scraper
│   │   │   │   ├── forex_factory.py  # Playwright
│   │   │   │   ├── investing_com.py  # httpx + BS4
│   │   │   │   ├── tradingview.py    # httpx + BS4
│   │   │   │   ├── babypips.py       # httpx + BS4
│   │   │   │   ├── finviz.py         # httpx + BS4
│   │   │   │   └── scheduler.py      # Orchestrator
│   │   │   │
│   │   │   ├── ai/                   # AI Pipeline
│   │   │   │   ├── gemini_client.py  # Scan & summarize news
│   │   │   │   ├── claude_client.py  # Translate to Thai
│   │   │   │   ├── prompts.py        # Prompt templates
│   │   │   │   └── pipeline.py       # scrape → summarize → translate
│   │   │   │
│   │   │   ├── indicators/           # Technical Indicators
│   │   │   │   ├── trend.py          # EMA, SMA, ADX, MACD
│   │   │   │   ├── oscillators.py    # RSI, Stochastic, CCI
│   │   │   │   ├── volatility.py     # BB, ATR, Keltner
│   │   │   │   ├── volume.py         # OBV, VWAP
│   │   │   │   ├── custom.py         # Currency Strength, Z-Score, etc.
│   │   │   │   └── engine.py         # Run all indicators
│   │   │   │
│   │   │   ├── analysis/             # BRAIN — Signal Logic
│   │   │   │   ├── market_regime.py  # Trending/Sideways/Volatile
│   │   │   │   ├── news_sentiment.py # Score news impact
│   │   │   │   ├── correlation.py    # DXY, VIX, cross-market
│   │   │   │   ├── signal_generator.py  # Multi-layer → SIGNAL
│   │   │   │   ├── confidence.py     # Confidence scoring
│   │   │   │   └── self_diagnosis.py # Error detection
│   │   │   │
│   │   │   ├── risk/                 # Risk Management
│   │   │   │   ├── position_size.py  # Lot calculator
│   │   │   │   ├── sl_tp.py          # Auto SL/TP (ATR-based)
│   │   │   │   ├── risk_reward.py    # R:R optimizer
│   │   │   │   └── kill_switch.py    # Emergency stop
│   │   │   │
│   │   │   └── price/                # Price Data
│   │   │       ├── twelve_data.py    # Primary feed
│   │   │       ├── yfinance_feed.py  # Fallback
│   │   │       └── price_cache.py    # Redis cache
│   │   │
│   │   ├── models/
│   │   │   ├── db/                   # SQLAlchemy ORM models
│   │   │   │   ├── news.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── trade.py
│   │   │   │   └── price.py
│   │   │   └── schemas/              # Pydantic API schemas
│   │   │       ├── news.py
│   │   │       ├── analysis.py
│   │   │       ├── trade.py
│   │   │       └── calculator.py
│   │   │
│   │   ├── db/
│   │   │   ├── session.py            # Async SQLAlchemy
│   │   │   └── migrations/           # Alembic
│   │   │
│   │   └── tasks/                    # Celery
│   │       ├── celery_app.py
│   │       ├── scraping_tasks.py
│   │       ├── analysis_tasks.py
│   │       └── cleanup_tasks.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/                         # Next.js 15
│   ├── src/
│   │   ├── app/                      # App Router pages
│   │   │   ├── page.tsx              # Dashboard
│   │   │   ├── analysis/page.tsx     # Analysis + Charts
│   │   │   ├── trade/page.tsx        # Calculator
│   │   │   ├── journal/page.tsx      # Journal + Win Rate
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui
│   │   │   ├── charts/
│   │   │   │   ├── RealtimeChart.tsx # TradingView LWC
│   │   │   │   └── IndicatorOverlay.tsx
│   │   │   ├── news/
│   │   │   │   ├── NewsFeed.tsx
│   │   │   │   └── NewsCard.tsx
│   │   │   ├── analysis/
│   │   │   │   ├── SignalPanel.tsx
│   │   │   │   └── ConfidenceMeter.tsx
│   │   │   └── trade/
│   │   │       ├── TradeCalculator.tsx
│   │   │       └── TradeJournal.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useAnalysis.ts
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── utils.ts
│   │   └── types/index.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── docker-compose.yml
├── Caddyfile
├── .env.example
├── .env                              # gitignored
├── docs/                             # Planning docs
└── README.md
```
