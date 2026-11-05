"""
DeepSeek Translation Engine (Dự phòng cho Gemini)
"""

import os
import json
import logging
from typing import Optional
from engines.models import Transcript

logger = logging.getLogger("taio.translate.deepseek")


class DeepSeekTranslator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = "https://api.deepseek.com/v1"

    def translate_transcript(self, transcript: Transcript, target_lang: str = "vi") -> Transcript:
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY không có. Giữ nguyên text hoặc dùng fallback.")
            for seg in transcript.segments:
                if not seg.translated_text:
                    seg.translated_text = f"[DeepSeek] {seg.original_text}"
            return transcript

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            segments_payload = [
                {"id": s.id, "text": s.original_text, "duration": round(s.duration, 2)}
                for s in transcript.segments
            ]

            prompt = f"Dịch các câu sau sang tiếng Việt ngắn gọn, tự nhiên, khớp nhịp video. JSON mảng: [{{\"id\": 1, \"translated\": \"...\"}}]\n{json.dumps(segments_payload, ensure_ascii=False)}"

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a specialized video subtitle translator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            raw = response.choices[0].message.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]

            parsed = json.loads(raw.strip())
            trans_map = {item["id"]: item.get("translated", "") for item in parsed}
            for seg in transcript.segments:
                if seg.id in trans_map:
                    seg.translated_text = trans_map[seg.id]

            return transcript
        except Exception as e:
            logger.error(f"DeepSeek translation error: {e}")
            return transcript
