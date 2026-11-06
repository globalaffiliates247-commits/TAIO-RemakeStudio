"""
SYSTRAN/faster-whisper local engine (Cấp 2)
Chạy trên máy người dùng, 0đ chi phí API, hỗ trợ mọi ngôn ngữ.
Tích hợp sẵn Silero VAD để lọc khoảng lặng và tạp âm chính xác.
"""

import os
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment
from engines.errors import EngineUnavailable, EngineFailed

logger = logging.getLogger("taio.transcribe.faster_whisper")


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size

    def transcribe(self, audio_file_path: str, language: Optional[str] = None) -> Transcript:
        logger.info(f"Chạy faster-whisper local ({self.model_size}) kèm Silero VAD...")
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise EngineUnavailable(
                "faster_whisper_local",
                "Thư viện faster-whisper chưa được cài đặt",
                setup_hint="Cài đặt qua pip: pip install faster-whisper"
            )

        if not os.path.exists(audio_file_path):
            raise EngineFailed("faster_whisper_local", f"Tệp âm thanh không tồn tại: {audio_file_path}")

        try:
            model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            # Bật Silero VAD để cắt bỏ khoảng lặng chính xác
            segments, info = model.transcribe(
                audio_file_path,
                language=language if language and language != "auto" else None,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            detected_lang = info.language if info and hasattr(info, "language") else (language or "vi")
            transcript = Transcript(
                title=os.path.basename(audio_file_path),
                media_path=audio_file_path,
                source_language=detected_lang
            )

            for idx, seg in enumerate(segments):
                text_clean = seg.text.strip()
                if text_clean:
                    transcript.add_segment(TranscriptSegment(
                        id=idx + 1,
                        start=seg.start,
                        end=seg.end,
                        original_text=text_clean
                    ))

            if not transcript.segments:
                raise EngineFailed("faster_whisper_local", "Không tìm thấy nội dung giọng nói trong tệp âm thanh.")

            return transcript
        except Exception as e:
            logger.error(f"Lỗi thực thi faster-whisper local: {e}")
            if isinstance(e, (EngineUnavailable, EngineFailed)):
                raise e
            raise EngineFailed("faster_whisper_local", str(e))
