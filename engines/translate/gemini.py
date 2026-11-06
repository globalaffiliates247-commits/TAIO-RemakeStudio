"""
Gemini Flash Translation Engine
Sử dụng mô hình Gemini 1.5/2.0 Flash để dịch ngữ cảnh, giữ nhịp điệu và khớp mốc thời gian.
Theo chuẩn v0.3: Không chứa dữ liệu giả ngầm.
"""

import os
import json
import logging
from typing import Optional
from engines.models import Transcript
from engines.errors import EngineUnavailable, EngineFailed
from engines.demo import is_demo_mode

logger = logging.getLogger("taio.translate.gemini")


class GeminiTranslator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-1.5-flash"

    def translate_transcript(self, transcript: Transcript, target_lang: str = "vi") -> Transcript:
        if not transcript.segments:
            return transcript

        transcript.target_language = target_lang

        if not self.api_key or "your_gemini_api_key" in self.api_key or len(self.api_key.strip()) < 15:
            if is_demo_mode():
                logger.info("DEMO_MODE=1: Gán bản dịch demo.")
                for s in transcript.segments:
                    s.translated_text = f"[Demo Dịch] {s.original_text}"
                return transcript
            raise EngineUnavailable(
                "Gemini Flash",
                "Chưa cấu hình GEMINI_API_KEY",
                setup_hint="Thêm GEMINI_API_KEY vào file .env rồi khởi động lại."
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

            segments_payload = [
                {"id": s.id, "text": s.original_text, "duration": round(s.duration, 2)}
                for s in transcript.segments
            ]

            prompt = f"""Bạn là chuyên gia dịch thuật video của TAIO.
Hãy dịch các câu sau sang tiếng Việt ({target_lang}) sao cho:
1. Ngắn gọn, tự nhiên, gần gũi với người Việt.
2. Khớp với khoảng thời lượng (duration) để người lồng tiếng nói kịp.
3. Xuất ra định dạng JSON mảng các đối tượng {{"id": number, "translated": "chuỗi dịch"}}. Không thêm markdown thừa.

Dữ liệu đầu vào:
{json.dumps(segments_payload, ensure_ascii=False)}
"""
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]

            parsed = json.loads(clean_text.strip())
            trans_map = {item["id"]: item.get("translated", "") for item in parsed}

            for seg in transcript.segments:
                if seg.id in trans_map:
                    seg.translated_text = trans_map[seg.id]
                else:
                    seg.translated_text = seg.original_text

            return transcript

        except Exception as e:
            logger.error(f"Lỗi khi gọi Gemini Translation API: {e}")
            raise EngineFailed("Gemini Flash", str(e))
