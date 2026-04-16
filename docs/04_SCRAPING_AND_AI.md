# SOCHRON1K — Web Scraping & AI Pipeline

## Scraping Strategy per Website

| Website | Method | Target Data | Frequency |
|---|---|---|---|
| **Forex Factory** | Playwright (JS) | Economic Calendar, impact levels, actual/forecast | ทุก 1-3 นาที |
| **Investing.com** | httpx + BS4 | News articles, Technical Summary | ทุก 1 ชม. |
| **TradingView** | httpx + BS4 | Ideas/analysis posts per pair | ทุก 2 ชม. |
| **BabyPips** | httpx + BS4 | Market analysis, educational | ทุก 2 ชม. |
| **Finviz** | httpx + BS4 | Currency Heatmap, strength | ทุก 1 ชม. |

## Scraping Pipeline Flow

```
1. Celery Beat → trigger scraping task
2. For each source (parallel asyncio.gather):
   a. Check robots.txt
   b. Scrape with appropriate method
   c. Extract structured data
   d. → Gemini: summarize + sentiment score
   e. → Claude Haiku: translate to Thai
   f. → Save to DB + Cache in Redis
3. If HIGH IMPACT news found:
   a. Push via WebSocket (breaking news alert)
   b. Trigger immediate analysis for affected pairs
4. Log scraper health
```

## Anti-Block Measures

- Random delays 2-5s between requests
- User-Agent rotation
- Playwright stealth mode for Forex Factory
- Respect robots.txt
- Rate limit: max 1 req/5s per domain

## Fallback Plan (if blocked)

| Site | Fallback |
|---|---|
| Forex Factory | XML calendar feed |
| Investing.com | RSS feed |
| TradingView | Ideas RSS |
| BabyPips | RSS feed |
| Finviz | FXCM API or OANDA sentiment |

---

## AI Pipeline

### Gemini 2.0 Flash — News Scanner & Summarizer

```python
GEMINI_SCAN_PROMPT = """
You are a professional Forex analyst. Analyze scraped news from {source}:

Extract:
1. Relevance: relevant to EUR/USD, USD/JPY, EUR/JPY? (which pair)
2. Impact Level: high / medium / low
3. Sentiment: bullish / bearish / neutral per affected currency
4. Sentiment Score: -1.0 to +1.0
5. Key Numbers: actual vs forecast vs previous
6. Summary: 2-3 sentences on market impact
7. Urgency: breaking/urgent? yes/no

Raw data: {raw_scraped_data}

Respond in JSON.
"""
```

### Claude 3.5 Haiku — Thai Translator

```python
CLAUDE_TRANSLATE_PROMPT = """
แปลข้อความต่อไปนี้เป็นภาษาไทย สำหรับเทรดเดอร์ Forex:
- ใช้ศัพท์เทคนิคที่เทรดเดอร์ไทยคุ้นเคย
- เก็บตัวเลขและชื่อเฉพาะไว้ตามเดิม
- กระชับ เข้าใจง่าย

ข้อความ: {english_text}
"""
```

### Pipeline

```
Raw HTML → Gemini (extract + summarize + sentiment)
         → Claude Haiku (translate Thai)
         → Store DB (both EN + TH)
         → If urgent → WebSocket push + trigger analysis
```
