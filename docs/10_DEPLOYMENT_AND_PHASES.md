# SOCHRON1K — Deployment, Budget & Implementation Phases

## VPS Recommendation

| Provider | Plan | Spec | ราคา/เดือน |
|---|---|---|---|
| **Hetzner** (แนะนำ) | CX22 | 2 vCPU, 4GB RAM, 40GB NVMe | ~€4.35 (~175 THB) |
| DigitalOcean | Basic | 2 vCPU, 4GB RAM, 80GB SSD | ~$24 (~840 THB) |
| Vultr | Cloud | 2 vCPU, 4GB RAM, 80GB SSD | ~$24 (~840 THB) |

> **แนะนำ Hetzner CX22** — ถูกสุด, server ยุโรป, specs เพียงพอ

---

## Docker Compose Services

```yaml
services:
  backend:       # FastAPI + Uvicorn
  celery-worker: # Background tasks (scraping, analysis)
  celery-beat:   # Scheduled jobs
  frontend:      # Next.js SSR
  postgres:      # TimescaleDB (PG16 + timescale)
  redis:         # Cache + PubSub + Celery broker
  caddy:         # Reverse proxy, auto HTTPS
```

## Celery Beat Schedule

| Task | Schedule | Notes |
|---|---|---|
| scrape_forex_factory | ทุก 30 นาที | Playwright |
| scrape_investing | ทุก 1 ชม. | httpx |
| scrape_tradingview | ทุก 2 ชม. | httpx |
| scrape_babypips | ทุก 2 ชม. | httpx |
| scrape_finviz | ทุก 1 ชม. | httpx |
| analyze_all_pairs | ทุก 1 ชม. (5 นาทีหลัง scrape) | 3 pairs |
| update_ohlcv | ทุก 5 นาที | price data |
| cleanup | ตี 3 ทุกวัน | delete old records |
| health_check | ทุก 10 นาที | system monitoring |

Plus **event-driven triggers** — ข่าว HIGH IMPACT → immediate analysis

---

## Budget Breakdown

### Monthly

| Item | THB/เดือน |
|---|---|
| Hetzner VPS CX22 | ~175 |
| Domain | ~35 (420/year ÷ 12) |
| Claude Haiku API | ~35-100 |
| Gemini API | 0 (free) |
| Twelve Data API | 0 (free) |
| **Total** | **~245-310** |

### One-time

| Item | THB |
|---|---|
| Domain (.com) | ~420 |
| VPS first month | ~175 |
| **Total** | **~595** |

### Trading Capital

```
30,000 THB - 3,720 (1yr running) - 600 (setup) = ~25,680 THB (~$713)
```

---

## Implementation Phases

### Phase 1: Foundation (สัปดาห์ 1-2)
- [ ] Project structure (Python backend + Next.js frontend)
- [ ] Docker Compose + PostgreSQL + TimescaleDB + Redis
- [ ] Database migrations (Alembic)
- [ ] FastAPI skeleton + health check
- [ ] Next.js skeleton + TailwindCSS + shadcn/ui
- [ ] `.env.example` configuration
- [ ] Basic CI setup

### Phase 2: Data Pipeline (สัปดาห์ 3-4)
- [ ] Web scraping engine — Forex Factory (Playwright)
- [ ] Web scraping — Investing.com, TradingView, BabyPips, Finviz
- [ ] Gemini integration — summarize + sentiment
- [ ] Claude Haiku integration — translate Thai
- [ ] Celery Beat scheduling
- [ ] News API endpoints
- [ ] News WebSocket push
- [ ] Scraper fallback (RSS feeds)

### Phase 3: Indicators & Price Feed (สัปดาห์ 5-6)
- [ ] Twelve Data API integration (REST + WebSocket)
- [ ] yfinance fallback
- [ ] TimescaleDB OHLCV storage
- [ ] TA-Lib indicators (trend, oscillator, volatility)
- [ ] Custom indicators (currency strength, Z-score, etc.)
- [ ] Indicator API endpoints
- [ ] Redis price cache

### Phase 4: Analysis Brain (สัปดาห์ 7-8)
- [ ] Market Regime Detection (ADX + ATR)
- [ ] News Sentiment scoring
- [ ] Inter-market Correlation checks (DXY, VIX)
- [ ] Multi-layer signal generator
- [ ] Confidence scoring system
- [ ] Self-diagnosis checks (18 checks)
- [ ] Kill Switch logic
- [ ] Analysis API endpoints

### Phase 5: Frontend — Dashboard & Charts (สัปดาห์ 9-10)
- [ ] Dashboard page (price cards, news feed, quick signals)
- [ ] Real-time chart (TradingView Lightweight Charts)
- [ ] Indicator overlays on chart
- [ ] WebSocket integration (prices + news + analysis)
- [ ] Signal panel with confidence meter
- [ ] Thai language UI

### Phase 6: Trade Calculator & Journal (สัปดาห์ 11-12)
- [ ] Trade Calculator UI + backend logic
- [ ] Auto SL/TP calculation
- [ ] Position size calculator
- [ ] Trade Journal CRUD
- [ ] Win Rate dashboard
- [ ] System accuracy tracking
- [ ] Training data collection

### Phase 7: Testing & Hardening (สัปดาห์ 13-14)
- [ ] Unit tests (scrapers, indicators, analysis)
- [ ] Integration tests (full pipeline)
- [ ] Backtesting validation (historical data)
- [ ] Stress test (concurrent WebSocket)
- [ ] Security review (API keys, rate limiting)
- [ ] Error handling & logging

### Phase 8: Deployment (สัปดาห์ 15)
- [ ] VPS provisioning (Hetzner)
- [ ] Docker Compose deploy
- [ ] Caddy HTTPS setup
- [ ] Domain configuration
- [ ] Monitoring setup
- [ ] Documentation

### Phase 9: Live Testing (สัปดาห์ 16+)
- [ ] Paper trading — ทดสอบระบบกับตลาดจริงแต่ไม่ลงเงิน
- [ ] เก็บ data 2-4 สัปดาห์ เพื่อวัด win rate จริง
- [ ] ปรับจูน confidence weights
- [ ] ปรับ indicator parameters
- [ ] เมื่อ win rate > 65% → เริ่มเทรดจริงด้วยเงินน้อยก่อน

---

## Risk & Limitations (ต้องรู้)

### สิ่งที่ระบบทำได้
- ✅ สรุปข่าว + sentiment analysis
- ✅ วิเคราะห์ technical indicators หลายชั้น
- ✅ คำนวณ risk management อัตโนมัติ
- ✅ เก็บ data เพื่อ training model ในอนาคต
- ✅ Self-diagnosis หาข้อผิดพลาด
- ✅ Win rate tracking

### สิ่งที่ต้องระวัง
- ⚠️ **Win Rate 100% เป็นไปไม่ได้** — เป้า realistic คือ 60-75%
- ⚠️ **Black Swan Events** — เหตุการณ์ที่คาดไม่ถึง (สงคราม, วิกฤต)
- ⚠️ **Web Scraping เปราะบาง** — เว็บเปลี่ยน layout = scraper พัง ต้อง maintain
- ⚠️ **BOJ Intervention** — ทำให้ JPY pairs เคลื่อนไหวผิดปกติ
- ⚠️ **Slippage** — ราคาจริงอาจต่างจากที่วิเคราะห์
- ⚠️ **Overfitting** — ระวังระบบดีบน backtest แต่แย่บน live
- ⚠️ **Spread/Swap costs** — กินกำไรถ้าเทรดบ่อย

### แนวทางลด risk
1. **Paper trade ก่อนอย่างน้อย 2-4 สัปดาห์**
2. **เริ่มด้วย lot เล็กสุด (0.01)**
3. **อย่า risk เกิน 2% per trade**
4. **เชื่อ Kill Switch เสมอ — ถ้าระบบบอกหยุด ให้หยุด**
5. **Review win rate ทุกสัปดาห์ — ถ้าต่ำกว่า 50% ให้หยุดและปรับ**
