# SOCHRON1K — API Design & Frontend

## REST API Endpoints

```
# ═══ News ═══
GET    /api/v1/news                    → ข่าวล่าสุด
GET    /api/v1/news?pair=EUR/USD       → ข่าวเฉพาะคู่
GET    /api/v1/news?impact=high        → ข่าวแรงเท่านั้น
POST   /api/v1/news/refresh            → บังคับ scrape (ปุ่มอัพเดท)

# ═══ Analysis ═══
GET    /api/v1/analysis/{pair}         → ผลวิเคราะห์ล่าสุด
POST   /api/v1/analysis/{pair}/run     → รันวิเคราะห์ใหม่
GET    /api/v1/analysis/history        → ประวัติ

# ═══ Indicators ═══
GET    /api/v1/indicators/{pair}       → ค่า indicator ล่าสุด
GET    /api/v1/indicators/{pair}/chart → ข้อมูลสำหรับ chart

# ═══ Calculator ═══
POST   /api/v1/calculate               → คำนวณ lot/SL/TP
POST   /api/v1/calculate/auto-sl       → SL อัตโนมัติ

# ═══ Trades ═══
POST   /api/v1/trades                  → บันทึกเทรดใหม่
PUT    /api/v1/trades/{id}             → อัพเดทผลเทรด
GET    /api/v1/trades                  → ดูทั้งหมด

# ═══ Stats ═══
GET    /api/v1/stats/winrate           → Win rate per pair
GET    /api/v1/stats/overview          → ภาพรวม
GET    /api/v1/stats/accuracy          → ความแม่นของระบบ

# ═══ Prices ═══
GET    /api/v1/prices/{pair}/ohlcv     → Historical OHLCV
GET    /api/v1/prices/live             → Latest prices (REST)

# ═══ System ═══
GET    /api/v1/health                  → Health check
GET    /api/v1/diagnostics/latest      → Diagnostic results
```

## WebSocket Endpoints

```
WS /ws/prices     → Real-time prices (all 3 pairs)
WS /ws/news       → Breaking news alerts
WS /ws/analysis   → New analysis notification
```

---

## Frontend Pages

### Page 1: Dashboard (หน้าหลัก)

- **Price Cards** — EUR/USD, USD/JPY, EUR/JPY แบบ real-time พร้อม %change
- **News Feed** — ข่าวล่าสุดเป็นภาษาไทย + ปุ่มอัพเดท + แถบสี impact
- **Currency Strength** — Bar chart USD/EUR/JPY strength
- **Quick Signals** — สรุปว่าแต่ละคู่ BUY/SELL/NEUTRAL + confidence %
- **Win Rate Summary** — ภาพรวมสั้นๆ

### Page 2: Analysis (วิเคราะห์เชิงลึก)

- **Pair Selector** — เลือก EUR/USD, USD/JPY, EUR/JPY
- **Real-time Chart** — TradingView Lightweight Charts
  - Candlestick (1m, 5m, 15m, 1H, 4H, 1D)
  - Toggle: EMA, BB, RSI overlay
  - News markers (high impact = red)
  - Signal markers (BUY = green arrow, SELL = red)
- **Indicator Toggle Panel** — เลือกเปิด/ปิด indicator
- **Signal Panel** — ทิศทาง + confidence meter + สรุปภาษาไทย
- **Diagnostics** — คำเตือนจาก self-diagnosis

### Page 3: Trade Calculator

- **Input Form** — ต้นทุน, TP, SL, lots, ระยะเวลา
- **Auto-calculate** — ระบบคำนวณ lot/SL/TP ให้
- **Result Panel** — แสดงค่าที่คำนวณ + คำเตือน
- **Save to Journal** — บันทึกเทรดไปที่ journal

### Page 4: Trade Journal & Win Rate

- **Trade Table** — filter by pair, status, date range
- **Edit/Update** — แก้ไขผลเทรด
- **Win Rate Charts** — bar chart, line over time
- **Accuracy Comparison** — system accuracy vs user results
- **Export** — CSV/JSON

---

## Real-time Chart Tech

```
TradingView Lightweight Charts v4 (open-source)
├── Candlestick series  → OHLCV from backend REST
├── Line series         → EMA overlays
├── Histogram series    → Volume bars
├── Markers             → News events + signals
└── Real-time updates   → WebSocket price feed
```

ข้อมูลราคา real-time:
- **Primary:** Twelve Data WebSocket (free: 8 symbols)
- **Fallback:** yfinance polling every 15s
- Backend เป็น proxy → ส่งต่อผ่าน WS ไป frontend
