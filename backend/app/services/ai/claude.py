import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

CLAUDE_TRANSLATE_PROMPT = """คุณเป็นนักแปลข่าว Forex มืออาชีพ แปลข้อความต่อไปนี้เป็นภาษาไทย:

กฎ:
- ใช้ศัพท์เทคนิคที่เทรดเดอร์ไทยคุ้นเคย (เช่น อัตราดอกเบี้ย, ดัชนี, เงินเฟ้อ, GDP)
- เก็บตัวเลข เปอร์เซ็นต์ และชื่อเฉพาะ (Fed, BOJ, ECB, NFP) ไว้ตามเดิม
- ใช้คำว่า 'ดอลลาร์' แทน USD, 'ยูโร' แทน EUR เมื่อเป็นกลางข้อความ
- กระชับ เข้าใจง่าย เป็นธรรมชาติ
- ห้ามเพิ่มข้อความที่ไม่มีในต้นฉบับ
- ห้ามใส่คำอธิบายหรือคำนำเพิ่มเติม

ข้อความ: {text}

แปลเป็นภาษาไทยเท่านั้น:"""


class ClaudeService:
    def __init__(self):
        self._settings = get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._settings.CLAUDE_API_KEY)
        return self._client

    async def translate_to_thai(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        if not self._settings.CLAUDE_API_KEY:
            logger.warning("[claude] No API key — returning original text")
            return f"[รอแปล] {text[:200]}"

        prompt = CLAUDE_TRANSLATE_PROMPT.format(text=text[:3000])

        try:
            client = self._get_client()
            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            result = message.content[0].text.strip()
            logger.info(f"[claude] Translated: {text[:40]}... → {result[:40]}...")
            return result

        except Exception as e:
            logger.error(f"[claude] Translation error: {e}")
            return f"[แปลไม่สำเร็จ] {text[:200]}"

    async def translate_title_and_summary(
        self, title: str, summary: str
    ) -> tuple:
        title_th = await self.translate_to_thai(title)
        summary_th = await self.translate_to_thai(summary) if summary else ""
        return title_th, summary_th
