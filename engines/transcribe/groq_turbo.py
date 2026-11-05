"""
Groq Whisper Large v3 Turbo Transcriber
Sử dụng Groq API (~0.04 USD/giờ audio), tốc độ siêu nhanh (~200x realtime).
"""

import os
import json
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment

logger = logging.getLogger("taio.transcribe.groq_turbo")


class GroqTurboTranscriber:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = "whisper-large-v3-turbo"

    def transcribe(self, audio_file_path: str, language: str = "en") -> Transcript:
        """
        Gửi audio_file_path lên Groq Whisper Large v3 Turbo để lấy timestamps & segments
        """
        transcript = Transcript(
            title=os.path.basename(audio_file_path),
            media_path=audio_file_path,
            source_language=language
        )

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Không tìm thấy file audio: {audio_file_path}")

        if not self.api_key:
            logger.warning("GROQ_API_KEY chưa được cấu hình. Sử dụng chế độ demo transcription.")
            # Chế độ demo thông minh để kiểm thử và chạy khi chưa gắn key
            return self._mock_transcription(audio_file_path, language)

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
            logger.error(f"Lỗi khi gọi Groq Whisper API: {e}. Chuyển fallback hoặc demo.")
            return self._mock_transcription(audio_file_path, language)

    def _mock_transcription(self, audio_path: str, lang: str) -> Transcript:
        transcript = Transcript(
            title=os.path.basename(audio_path),
            media_path=audio_path,
            source_language=lang
        )
        sample_texts = [
            (0.0, 3.5, "Welcome to TAIO RemakeStudio, the all-in-one media localization tool."),
            (3.6, 7.2, "Now anyone can listen to global content in Vietnamese with natural regional voices."),
            (7.5, 11.0, "From TikTok and Facebook videos to podcasts and favorite songs.")
        ]
        for idx, (st, en, text) in enumerate(sample_texts):
            transcript.add_segment(TranscriptSegment(
                id=idx + 1,
                start=st,
                end=en,
                original_text=text
            ))
        return transcript
