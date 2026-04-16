# 🏦 SOCHRON1K — Forex Analysis & Signal System

> ระบบวิเคราะห์ Forex อัจฉริยะสำหรับ EUR/USD, USD/JPY, EUR/JPY
> Web scraping + AI + Technical Indicators + Risk Management

## Features

- **News Scraping** — 5 เว็บไซต์หลัก (Forex Factory, Investing.com, TradingView, BabyPips, Finviz)
- **AI Pipeline** — Gemini สรุปข่าว + Claude Haiku แปลไทย
- **Technical Indicators** — 15+ indicators (TA-Lib + custom)
- **Real-time Charts** — TradingView Lightweight Charts
- **5-Layer Signal Logic** — Market Regime → News → Technical → Correlation → Risk Gate
- **Trade Calculator** — Auto SL/TP, lot sizing, R:R optimization
- **Trade Journal** — Win rate tracking per pair
- **Self-Diagnosis** — 18 automated checks after every analysis
- **24/7 on VPS** — Docker Compose deployment

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 15 + TypeScript + TailwindCSS + shadcn/ui |
| Charts | TradingView Lightweight Charts v4 |
| Database | PostgreSQL 16 + TimescaleDB |
| Cache | Redis 7 |
| Tasks | Celery + Celery Beat |
| AI | Gemini 2.0 Flash + Claude 3.5 Haiku |
| Scraping | Playwright + httpx + BeautifulSoup4 |
| Deploy | Docker Compose + Caddy |

## Currency Pairs

| Pair | Primary Strategy |
|---|---|
| EUR/USD | London Open Breakout + Trend Following |
| USD/JPY | Trend Following + Mean Reversion (Z-Score) |
| EUR/JPY | Momentum + Range Trading |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/faztycoding/Sochron1k.git
cd Sochron1k

# 2. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run with Docker
docker compose up -d

# 4. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## Documentation

See `docs/` folder:
- `01_ARCHITECTURE.md` — System design & tech stack
- `02_PROJECT_STRUCTURE.md` — File structure
- `03_DATABASE.md` — Database schema
- `04_SCRAPING_AND_AI.md` — Web scraping & AI pipeline
- `05_INDICATORS.md` — Technical indicators
- `06_SIGNAL_LOGIC.md` — 5-layer signal generation
- `07_RISK_AND_CALCULATOR.md` — Risk management
- `08_SELF_DIAGNOSIS.md` — Error detection
- `09_API_AND_FRONTEND.md` — API endpoints & UI
- `10_DEPLOYMENT_AND_PHASES.md` — Deployment & phases

## License

Private — All rights reserved.
