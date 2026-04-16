import json
import logging
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_SCAN_PROMPT = """You are a world-class Forex news analyst (Bloomberg/Reuters-level). Analyze this news for professional traders.

Target pairs: EUR/USD, USD/JPY, EUR/JPY, GBP/USD, AUD/USD
Target currencies: EUR, USD, JPY, GBP, AUD

RATING CRITERIA (world-class standard):
- impact_score (1-5): 1=background noise, 2=minor, 3=moderate, 4=high-impact, 5=market-moving critical event
- category: "central_bank" | "economic_data" | "geopolitical" | "corporate" | "commodity" | "sentiment" | "technical"
- expected_volatility_pips: estimated pip movement on major pair (e.g. 30 for 30 pips, 100 for 100 pips)
- time_horizon: "instant" (minutes) | "short" (hours) | "medium" (days) | "long" (weeks)
- surprise_factor (0-1): 0=expected, 1=huge surprise vs forecast
- actionability: "tradable" | "watch" | "ignore" — can a trader act on this?

Return ONLY valid JSON (no markdown, no code fences):
{{
  "relevant_pairs": ["EUR/USD"],
  "impact_level": "high|medium|low",
  "impact_score": 1-5,
  "category": "central_bank|economic_data|geopolitical|corporate|commodity|sentiment|technical",
  "sentiment": {{
    "EUR": "bullish|bearish|neutral",
    "USD": "bullish|bearish|neutral",
    "JPY": "bullish|bearish|neutral",
    "GBP": "bullish|bearish|neutral",
    "AUD": "bullish|bearish|neutral"
  }},
  "sentiment_score": -1.0 to +1.0,
  "key_numbers": {{
    "actual": "",
    "forecast": "",
    "previous": ""
  }},
  "expected_volatility_pips": 0-200,
  "time_horizon": "instant|short|medium|long",
  "surprise_factor": 0.0-1.0,
  "actionability": "tradable|watch|ignore",
  "summary": "2-3 sentences on market impact in English",
  "key_takeaway": "One-sentence trading implication in English",
  "is_urgent": true|false,
  "confidence": 0.0-1.0
}}

Source: {source}
Title: {title}
Content: {content}
Raw data: {raw_data}"""


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
    ) -> Dict[str, Any]:
        if not self._settings.GEMINI_API_KEY:
            logger.warning("[gemini] No API key — returning mock analysis")
            return self._mock_response(title)

        prompt = GEMINI_SCAN_PROMPT.format(
            source=source,
            title=title,
            content=content[:2000],
            raw_data=json.dumps(raw_data or {}, ensure_ascii=False)[:1000],
        )

        try:
            client = self._get_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            result = json.loads(text)
            logger.info(f"[gemini] Analyzed: {title[:50]} → score={result.get('sentiment_score', 0)}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[gemini] JSON parse error: {e}")
            return self._mock_response(title)
        except Exception as e:
            logger.error(f"[gemini] API error: {e}")
            return self._mock_response(title)

    def _mock_response(self, title: str) -> Dict[str, Any]:
        return {
            "relevant_pairs": [],
            "impact_level": "low",
            "impact_score": 1,
            "category": "sentiment",
            "sentiment": {
                "EUR": "neutral", "USD": "neutral", "JPY": "neutral",
                "GBP": "neutral", "AUD": "neutral",
            },
            "sentiment_score": 0.0,
            "key_numbers": {"actual": "", "forecast": "", "previous": ""},
            "expected_volatility_pips": 0,
            "time_horizon": "short",
            "surprise_factor": 0.0,
            "actionability": "watch",
            "summary": f"[Mock] Analysis pending for: {title[:100]}",
            "key_takeaway": "Analysis pending",
            "is_urgent": False,
            "confidence": 0.0,
        }
