"""
Groq Whisper Large v3 Turbo Transcriber
Sử dụng Groq API (~0.04 USD/giờ audio), tốc độ siêu nhanh (~200x realtime).
Theo chuẩn v0.3: Không chứa dữ liệu giả ngầm. Chỉ chạy demo khi DEMO_MODE=1.
"""

import os
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment
from engines.errors import EngineUnavailable, EngineFailed
from engines.demo import is_demo_mode, get_demo_transcript

logger = logging.getLogger("taio.transcribe.groq_turbo")


class GroqTurboTranscriber:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = "whisper-large-v3-turbo"

    def transcribe(self, audio_file_path: str, language: str = "en") -> Transcript:
        transcript = Transcript(
            title=os.path.basename(audio_file_path),
            media_path=audio_file_path,
            source_language=language
        )

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Không tìm thấy file audio: {audio_file_path}")

        # Kiểm tra API Key hợp lệ
        if not self.api_key or "your_groq_api_key" in self.api_key or len(self.api_key.strip()) < 15:
            if is_demo_mode():
                logger.info("DEMO_MODE=1: Trả về transcript mẫu theo quy định Mục 4.")
                return get_demo_transcript(lang=language)
            raise EngineUnavailable(
                "Groq Whisper",
                "Chưa cấu hình GROQ_API_KEY",
                setup_hint="Thêm GROQ_API_KEY vào file .env rồi khởi động lại."
            )

        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            with open(audio_file_path, "rb") as file:
                res = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_file_path), file.read()),
                    model=self.model,
                    response_format="verbose_json",
                    language=language if language != "auto" else None,
                    temperature=0.0
                )

            # Lấy ngôn ngữ phát hiện nếu có
            detected_lang = getattr(res, "language", language)
            if detected_lang:
                transcript.source_language = detected_lang

            segments_data = getattr(res, "segments", [])
            for idx, seg in enumerate(segments_data):
                segment = TranscriptSegment(
                    id=idx + 1,
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", 0.0)),
                    original_text=seg.get("text", "").strip()
                )
                transcript.add_segment(segment)

            if not transcript.segments and hasattr(res, "text") and res.text:
                transcript.add_segment(TranscriptSegment(
                    id=1,
                    start=0.0,
                    end=5.0,
                    original_text=res.text.strip()
                ))

            return transcript

        except Exception as e:
            logger.error(f"Groq Whisper API lỗi: {e}")
            raise EngineFailed("Groq Whisper", str(e))
