"""
Groq Whisper Large v3 Turbo Transcriber
Sử dụng Groq API (~0.04 USD/giờ audio), tốc độ siêu nhanh.
Nếu chưa có key, tự động chuyển sang FreeSpeechTranscriber chép lời thật.
"""

import os
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment
from engines.transcribe.free_speech import FreeSpeechTranscriber

logger = logging.getLogger("taio.transcribe.groq_turbo")


class GroqTurboTranscriber:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = "whisper-large-v3-turbo"
        self.free_fallback = FreeSpeechTranscriber()

    def transcribe(self, audio_file_path: str, language: str = "en") -> Transcript:
        transcript = Transcript(
            title=os.path.basename(audio_file_path),
            media_path=audio_file_path,
            source_language=language
        )

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Không tìm thấy file audio: {audio_file_path}")

        # Kiểm tra nếu API key rỗng hoặc là placeholder
        if not self.api_key or "your_groq_api_key" in self.api_key or len(self.api_key) < 15:
            logger.info("Chưa có GROQ_API_KEY hợp lệ. Kích hoạt FreeSpeechTranscriber chép lời thật...")
            return self.free_fallback.transcribe(audio_file_path, language=language)

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

            segments_data = getattr(res, "segments", [])
            for idx, seg in enumerate(segments_data):
                segment = TranscriptSegment(
                    id=idx + 1,
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", 0.0)),
                    original_text=seg.get("text", "").strip()
                )
                transcript.add_segment(segment)

            if not transcript.segments and hasattr(res, "text"):
                transcript.add_segment(TranscriptSegment(
                    id=1,
                    start=0.0,
                    end=5.0,
                    original_text=res.text.strip()
                ))

            return transcript

        except Exception as e:
            logger.warning(f"Groq Whisper API gặp lỗi ({e}). Chuyển sang FreeSpeechTranscriber...")
            return self.free_fallback.transcribe(audio_file_path, language=language)
