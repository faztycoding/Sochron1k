# SOCHRON1K — System Architecture & Tech Stack

> **ทุน:** 30,000 THB | **คู่เงิน:** EUR/USD, USD/JPY, EUR/JPY
> **เป้า:** 1,000–2,000 pips | Win Rate สูงสุด | VPS 24/7

---

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│                 FRONTEND (Next.js 15 + TS)            │
│  Dashboard | Realtime Charts | Analysis | Journal     │
│                    │ REST + WebSocket                  │
└────────────────────┼─────────────────────────────────┘
                     │
┌────────────────────┼─────────────────────────────────┐
│              BACKEND (Python FastAPI)                  │
│                                                        │
│  ┌────────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ Scraping   │ │ AI Layer │ │ Indicator Engine     │ │
│  │ Engine     │ │ Gemini + │ │ TA-Lib + Custom      │ │
│  │ Playwright │ │ Claude   │ │ NumPy/Pandas         │ │
│  └─────┬──────┘ └────┬─────┘ └──────────┬──────────┘ │
│        └──────────────┴─────────────────┘             │
│                       │                                │
│        ┌──────────────┴──────────────┐                │
│        │   ANALYSIS CORE (BRAIN)     │                │
│        │   5-Layer Confirmation      │                │
│        │   Signal Generator          │                │
│        └──────────────┬──────────────┘                │
│                       │                                │
│  ┌──────────┐ ┌───────┴──────┐ ┌───────────────────┐ │
│  │ Celery   │ │ Risk Manager │ │ Trade Journal     │ │
│  │ Workers  │ │ Calculator   │ │ Win Rate Tracker  │ │
│  └──────────┘ └──────────────┘ └───────────────────┘ │
└────────────────────┼─────────────────────────────────┘
                     │
┌────────────────────┼─────────────────────────────────┐
│               DATA LAYER                              │
│  PostgreSQL 16    │  TimescaleDB    │  Redis 7        │
│  (Main DB)        │  (Price OHLCV)  │  (Cache/PubSub) │
└──────────────────────────────────────────────────────┘
```

---

## Tech Stack — เลือกภาษาที่ดีที่สุดสำหรับแต่ละงาน

| Component | Technology | เหตุผล |
|---|---|---|
| **Backend API** | **Python 3.12 + FastAPI** | Async, เร็ว, ecosystem data science/ML ดีที่สุด |
| **Web Scraping** | **Playwright** (JS sites) + **httpx + BS4** (static) | Playwright รองรับ dynamic rendering |
| **AI News Scan** | **Google Gemini 2.0 Flash** | ฟรี 15 RPM, context window ใหญ่ |
| **AI Thai Translation** | **Claude 3.5 Haiku** | คุณภาพภาษาไทยดี, ราคาถูก |
| **Indicators** | **TA-Lib** (C-based) + **pandas-ta** + **NumPy** | TA-Lib เร็วสุด, pandas-ta ครบ |
| **Frontend** | **Next.js 15 + TypeScript + TailwindCSS + shadcn/ui** | SSR, real-time WS, UI สวย |
| **Charts** | **TradingView Lightweight Charts v4** | ฟรี, open-source, production-grade |
| **Price Feed** | **Twelve Data API** (free) + **yfinance** fallback | WebSocket real-time ฟรี |
| **Main DB** | **PostgreSQL 16** | ACID, JSON, mature |
| **Time-series** | **TimescaleDB** (PG extension) | OHLCV query เร็ว |
| **Cache/Queue** | **Redis 7** | Pub/Sub real-time, Celery broker |
| **Task Queue** | **Celery + Celery Beat** | Scheduled scraping, background jobs |
| **Deployment** | **Docker Compose** on VPS | Reproducible |
| **Reverse Proxy** | **Caddy** | Auto HTTPS |
| **ML (future)** | **Scikit-learn + XGBoost** | Market regime detection |

---

## API Keys Required

| Service | Cost | Notes |
|---|---|---|
| Gemini 2.0 Flash | **ฟรี** (15 RPM, 1M tokens/day) | เพียงพอ |
| Claude 3.5 Haiku | ~$1-3/เดือน | แปลไทยอย่างเดียว |
| Twelve Data | **ฟรี** (800 calls/day) | 3 pairs + DXY |

---

## Design Principles

1. **Event-Driven** — ข่าวสำคัญเข้า → trigger analysis ทันที
2. **Multi-Layer Confirmation** — ทุกสัญญาณต้อง confirm 4-5 ชั้น
3. **Fail-Safe** — ทุก module มี fallback
4. **Self-Diagnosing** — ระบบตรวจสอบตัวเองหลังทุกการวิเคราะห์
5. **Data-Driven** — เก็บทุกอย่างเพื่อ train model ในอนาคต
