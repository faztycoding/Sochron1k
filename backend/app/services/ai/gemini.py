"""World-class Forex news analyst via Gemini 2.5 Flash.

Uses Chain-of-Thought reasoning + structured response schema + fail-closed design.
No mock data leaks to UI — returns None on failure so caller can filter out.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# ============================================================
# WORLD-CLASS ANALYSIS PROMPT (Chain-of-Thought + Self-Eval)
# ============================================================
GEMINI_SCAN_PROMPT = """You are a senior Forex analyst at a bulge-bracket bank (Goldman Sachs / JP Morgan FX desk). You have 15+ years trading spot FX. Your task: analyze news for professional traders who act on your call.

Target pairs: EUR/USD, USD/JPY, EUR/JPY, GBP/USD, AUD/USD

===== REASONING FRAMEWORK (think step-by-step) =====

You MUST reason through these 6 steps in order. Each step's answer informs the next.

STEP 1 — EVENT CLASSIFICATION
- What type of event is this? (central_bank | economic_data | geopolitical | commodity | sentiment | technical_blog)
- Is this ACTIONABLE news for FX traders, or just background noise?
- Red flag: blog post / educational content / "my chart pattern" → category="technical_blog", impact=low, STOP analysis

STEP 2 — HISTORICAL PRECEDENT
- Recall: when similar events happened before, what was the typical pip move on major pairs?
- Example templates:
  * NFP beat +50k: EUR/USD -40 to -80 pips in first 30 min
  * Fed 25bp hike (expected): minimal reaction, priced in
  * Fed 25bp hike (hawkish surprise): DXY +1% = EUR/USD -80-120 pips
  * ECB dovish pivot: EUR/USD -60-100 pips
  * BOJ intervention: USD/JPY -200-400 pips instantly

STEP 3 — CURRENT MARKET BIAS
- What's the prevailing narrative? (dollar strength, risk-on/off, carry trade)
- Does this news confirm or contradict consensus?
- If contradicts → larger move. If confirms → small move.

STEP 4 — VOLATILITY FORECAST
- Predict pip range per pair (use Step 2 as anchor)
- Time window: instant (<5min), short (<4h), medium (<3d), long (>3d)
- Directional bias per currency (must be consistent with sentiment scores)

STEP 5 — TRADE SETUP (if tradeable)
- Entry: market or specific level (e.g., "sell rallies to 1.0850")
- Stop loss: invalidation level (based on ATR or news-driven structure)
- Take profit: realistic target (R:R ≥ 1.5:1)
- Warning zone: avoid trading X minutes before/after high-impact release

STEP 6 — SELF-EVALUATION (CRITICAL)
- Confidence: 0.0-1.0. Be honest. If you can't name 2 historical precedents → confidence ≤ 0.5
- Red flags that should LOWER confidence:
  * Vague headlines without numbers ("Fed official speaks")
  * Non-FX news (equities, crypto, stock picks)
  * Blog/analysis post (not breaking event)
  * Missing forecast vs actual
- If confidence < 0.5: set actionability="ignore", no trade setup

===== FILTERING RULES =====

SET impact_level="low" and confidence<0.3 IF:
- Source is TradingView/BabyPips and content is chart analysis (not event)
- Event is "Rightmove HPI", "Tertiary Industry Activity", minor regional data
- Headline contains: "opinion", "my view", "I think", "chart pattern"
- Content is educational (explaining indicators, courses, tutorials)

KEEP only if:
- Central bank action/speech (Fed, ECB, BOJ, BOE, RBA)
- High-impact data: NFP, CPI, GDP, Retail Sales, PMI, Unemployment, Rate Decision
- Geopolitical: war, sanctions, elections, policy shifts
- Commodity shocks: oil spike, gold breakout
- Breaking crisis: bank failures, currency crises

===== FEW-SHOT EXAMPLES =====

EXAMPLE 1 (HIGH IMPACT, CLEAR):
Input: "Fed raises rates 50bp, more than expected 25bp. Powell: 'We're not done.'"
Reasoning: Central bank hawkish surprise → DXY strong bid → EUR/USD/all USD pairs move fast
Output: impact_score=5, confidence=0.92, USD=bullish, EUR=bearish, expected_volatility_pips=120, actionability=tradable, trade_setup={{direction:"sell", pair:"EUR/USD", entry_zone:"market", sl_pips:40, tp_pips:80, rr:2.0}}

EXAMPLE 2 (LOW IMPACT, FILTER OUT):
Input: "Liquidity Sweep Reversal - Bullish Recovery in Play" (TradingView blog)
Reasoning: Chart analysis blog, not event → technical_blog category, no market impact
Output: impact_score=1, confidence=0.1, category="technical_blog", actionability="ignore", all sentiments neutral, expected_volatility_pips=0

EXAMPLE 3 (MEDIUM IMPACT, NUANCED):
Input: "German ZEW Economic Sentiment 45.2 vs forecast 42.0"
Reasoning: Slight beat, moderate EUR support, but ZEW is sentiment gauge not hard data. Short-term only.
Output: impact_score=3, confidence=0.75, EUR=bullish, USD=neutral, expected_volatility_pips=25, actionability="watch", time_horizon="short"

===== OUTPUT REQUIREMENTS =====

Return ONLY valid JSON matching the schema exactly. No markdown, no code fences, no extra text.

Source: {source}
Title: {title}
Content: {content}
Raw data: {raw_data}

Now reason through all 6 steps internally, then output the JSON."""


# ============================================================
# STRUCTURED RESPONSE SCHEMA (Gemini response_schema)
# ============================================================
# Using JSON Schema (OpenAPI 3.0 subset) — Gemini validates output
GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant_pairs": {"type": "array", "items": {"type": "string"}},
        "impact_level": {"type": "string", "enum": ["high", "medium", "low"]},
        "impact_score": {"type": "integer", "minimum": 1, "maximum": 5},
        "category": {
            "type": "string",
            "enum": [
                "central_bank", "economic_data", "geopolitical",
                "corporate", "commodity", "sentiment", "technical_blog",
            ],
        },
        "sentiment": {
            "type": "object",
            "properties": {
                "EUR": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                "USD": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                "JPY": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                "GBP": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                "AUD": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
            },
        },
        "sentiment_score": {"type": "number", "minimum": -1.0, "maximum": 1.0},
        "key_numbers": {
            "type": "object",
            "properties": {
                "actual": {"type": "string"},
                "forecast": {"type": "string"},
                "previous": {"type": "string"},
            },
        },
        "expected_volatility_pips": {"type": "integer", "minimum": 0, "maximum": 500},
        "time_horizon": {
            "type": "string",
            "enum": ["instant", "short", "medium", "long"],
        },
        "surprise_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "actionability": {"type": "string", "enum": ["tradable", "watch", "ignore"]},
        "summary": {"type": "string"},
        "key_takeaway": {"type": "string"},
        "is_urgent": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        # NEW: Reasoning chain (6 steps)
        "reasoning": {
            "type": "object",
            "properties": {
                "step1_classification": {"type": "string"},
                "step2_historical_precedent": {"type": "string"},
                "step3_market_bias": {"type": "string"},
                "step4_volatility_forecast": {"type": "string"},
                "step5_trade_setup_logic": {"type": "string"},
                "step6_self_eval": {"type": "string"},
            },
        },
        # NEW: Concrete trade setup
        "trade_setup": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["buy", "sell", "avoid", "wait"],
                },
                "pair": {"type": "string"},
                "entry_type": {"type": "string", "enum": ["market", "limit", "stop"]},
                "entry_zone": {"type": "string"},
                "sl_pips": {"type": "integer", "minimum": 0, "maximum": 200},
                "tp_pips": {"type": "integer", "minimum": 0, "maximum": 500},
                "risk_reward": {"type": "number", "minimum": 0.0, "maximum": 10.0},
                "style": {"type": "string", "enum": ["scalp", "intraday", "swing"]},
                "warning_minutes": {"type": "integer", "minimum": 0, "maximum": 60},
            },
        },
        # NEW: Similar historical events
        "similar_events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "event": {"type": "string"},
                    "date_approx": {"type": "string"},
                    "pair_impact": {"type": "string"},
                    "pips_moved": {"type": "integer"},
                    "time_to_peak": {"type": "string"},
                },
            },
        },
    },
    "required": [
        "impact_level", "impact_score", "category",
        "sentiment", "sentiment_score", "expected_volatility_pips",
        "actionability", "summary", "key_takeaway",
        "is_urgent", "confidence",
    ],
}


class GeminiService:
    def __init__(self):
        self._settings = get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._settings.GEMINI_API_KEY)
        return self._client

    async def analyze_news(
        self,
        source: str,
        title: str,
        content: str,
        raw_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze news with Chain-of-Thought reasoning.

        Returns None on failure (fail-closed) — caller MUST filter out None results.
        This prevents mock/pending data from leaking into UI.
        """
        if not self._settings.GEMINI_API_KEY:
            logger.warning("[gemini] No API key — skipping analysis (fail-closed)")
            return None

        prompt = GEMINI_SCAN_PROMPT.format(
            source=source,
            title=title,
            content=content[:2000],
            raw_data=json.dumps(raw_data or {}, ensure_ascii=False)[:1000],
        )

        try:
            client = self._get_client()
            # Use structured response schema — Gemini validates output automatically
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": GEMINI_RESPONSE_SCHEMA,
                    "temperature": 0.3,  # Lower = more consistent reasoning
                },
            )

            text = response.text.strip()
            result = json.loads(text)

            # Sanity checks — fail-closed if AI returned garbage
            if not result.get("category"):
                logger.warning(f"[gemini] Missing category for: {title[:50]}")
                return None

            confidence = result.get("confidence", 0.0)
            logger.info(
                f"[gemini] Analyzed: {title[:50]} → "
                f"impact={result.get('impact_level')}/{result.get('impact_score')} "
                f"conf={confidence:.2f} pips={result.get('expected_volatility_pips', 0)}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[gemini] JSON parse error for '{title[:50]}': {e}")
            return None
        except Exception as e:
            logger.error(f"[gemini] API error for '{title[:50]}': {e}")
            return None

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for semantic deduplication.

        Returns None on failure.
        """
        if not self._settings.GEMINI_API_KEY or not text:
            return None

        try:
            client = self._get_client()
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text[:2000],
            )
            # google-genai returns embeddings in response.embeddings
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
            return None
        except Exception as e:
            logger.debug(f"[gemini] Embedding error: {e}")
            return None
