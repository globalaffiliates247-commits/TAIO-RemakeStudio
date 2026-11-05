"""
Gemini Flash Translation Engine
Sử dụng mô hình Gemini 1.5/2.0 Flash để dịch ngữ cảnh, giữ nhịp điệu và khớp mốc thời gian.
"""

import os
import json
import logging
from typing import Optional
from engines.models import Transcript

logger = logging.getLogger("taio.translate.gemini")


class GeminiTranslator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-1.5-flash"

    def translate_transcript(self, transcript: Transcript, target_lang: str = "vi") -> Transcript:
        """
        Dịch toàn bộ Transcript sang target_lang, cập nhật translated_text cho từng segment.
        """
        if not transcript.segments:
            return transcript

        transcript.target_language = target_lang

        if not self.api_key:
            logger.warning("GEMINI_API_KEY chưa được cấu hình. Sử dụng bản dịch mẫu/tự động.")
            return self._auto_translate_fallback(transcript, target_lang)

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
            logger.error(f"Lỗi khi gọi Gemini Translation API: {e}. Sử dụng fallback.")
            return self._auto_translate_fallback(transcript, target_lang)

    def _auto_translate_fallback(self, transcript: Transcript, target_lang: str) -> Transcript:
        """Fallback dịch mẫu khi không có Gemini API key"""
        translations = {
            "Welcome to TAIO RemakeStudio, the all-in-one media localization tool.": "Chào mừng đến với TAIO RemakeStudio, công cụ bản địa hóa video toàn diện.",
            "Now anyone can listen to global content in Vietnamese with natural regional voices.": "Giờ đây ai cũng có thể nghe nội dung quốc tế bằng tiếng Việt với giọng đọc quê hương thân thuộc.",
            "From TikTok and Facebook videos to podcasts and favorite songs.": "Từ video TikTok, Facebook Reels đến các bài hát và podcast yêu thích."
        }
        for seg in transcript.segments:
            if not seg.translated_text:
                seg.translated_text = translations.get(seg.original_text, f"[Dịch Tiếng Việt] {seg.original_text}")
        return transcript
