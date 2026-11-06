"""
VinAIResearch/PhoWhisper Engine
Tối ưu hóa đặc biệt cho tiếng Việt đa vùng miền.
Theo PRD Mục 3: Nếu PhoWhisper local không khả dụng, tự động dự phòng sang Groq Whisper Large v3.
"""

import os
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment
from engines.transcribe.groq_large_v3 import GroqLargeV3Transcriber

logger = logging.getLogger("taio.transcribe.phowhisper")


class PhoWhisperTranscriber:
    def __init__(self, model_name: str = "vinai/phowhisper-medium"):
        self.model_name = model_name
        self.groq_fallback = GroqLargeV3Transcriber()

    def transcribe(self, audio_file_path: str, language: str = "vi") -> Transcript:
        logger.info(f"Đang chép lời bằng PhoWhisper ({self.model_name}): {audio_file_path}")
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
            logger.info(f"PhoWhisper local không khả dụng ({e}). Chuyển sang Groq Whisper Large v3 theo quy ước PRD...")
            # Fallback sang Groq Whisper Large v3 theo đúng bảng Luồng PRD Section 3
            try:
                res = self.groq_fallback.transcribe(audio_file_path, language="vi")
                if res and res.segments:
                    return res
            except Exception as ge:
                logger.warning(f"Groq fallback gặp lỗi: {ge}")

            # Nếu chưa có API key và chưa có local model, tạo cảnh báo rõ ràng
            transcript.add_segment(TranscriptSegment(
                id=1,
                start=0.0,
                end=5.0,
                original_text="[Chưa cấu hình GROQ_API_KEY trong file .env để chép lời tự động từ video này]"
            ))
            return transcript
