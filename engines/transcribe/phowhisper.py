"""
VinAIResearch/PhoWhisper Engine
Tối ưu hóa đặc biệt cho tiếng Việt đa vùng miền.
"""

import os
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment
from engines.errors import EngineUnavailable, EngineFailed
from engines.demo import is_demo_mode, get_demo_transcript
from engines.transcribe.groq_large_v3 import GroqLargeV3Transcriber

logger = logging.getLogger("taio.transcribe.phowhisper")


class PhoWhisperTranscriber:
    def __init__(self, model_name: str = "vinai/phowhisper-medium"):
        self.model_name = model_name
        self.groq_fallback = GroqLargeV3Transcriber()

    def transcribe(self, audio_file_path: str, language: str = "vi") -> Transcript:
        transcript = Transcript(
            title=os.path.basename(audio_file_path),
            media_path=audio_file_path,
            source_language=language
        )

        try:
            import torch
            from transformers import pipeline

            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=device,
                return_timestamps=True
            )
            result = pipe(audio_file_path)

            chunks = result.get("chunks", [])
            for idx, chunk in enumerate(chunks):
                ts = chunk.get("timestamp", (0.0, 5.0))
                st = ts[0] if ts[0] is not None else 0.0
                en = ts[1] if ts[1] is not None else st + 3.0
                transcript.add_segment(TranscriptSegment(
                    id=idx + 1,
                    start=float(st),
                    end=float(en),
                    original_text=chunk.get("text", "").strip()
                ))

            return transcript
        except Exception as e:
            logger.info(f"PhoWhisper local không khả dụng ({e}). Dự phòng sang Groq Whisper...")
            try:
                return self.groq_fallback.transcribe(audio_file_path, language="vi")
            except Exception as ge:
                if is_demo_mode():
                    return get_demo_transcript(lang="vi")
                raise EngineUnavailable(
                    "PhoWhisper / Groq Whisper",
                    f"Cả PhoWhisper local và Groq đều không khả dụng: {ge}",
                    setup_hint="Thêm GROQ_API_KEY vào .env để sử dụng chép lời."
                )
