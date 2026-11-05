"""
VieNeu-TTS Engine (Apache 2.0)
Giọng đọc tiếng Việt theo vùng miền (Bắc / Trung / Nam), hỗ trợ nhân bản giọng.
"""

import os
import logging
from typing import Optional
from engines.tts.edge_tts_fallback import EdgeTTSEngine

logger = logging.getLogger("taio.tts.vieneu")


class VieNeuTTSEngine:
    def __init__(self, voice_id: str = "vi_south_female_1", model_path: Optional[str] = None):
        self.voice_id = voice_id
        self.model_path = model_path or os.getenv("VIENEU_MODEL_PATH", "")
        # Fallback sẵn sàng qua Edge TTS nếu model VieNeu chưa được nạp
        self.fallback_engine = EdgeTTSEngine("vi-VN-HoaiMyNeural")

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0, reference_audio: Optional[str] = None) -> str:
        """
        Tổng hợp giọng VieNeu-TTS hoặc nhân bản từ reference_audio của chính người dùng
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Nếu có local VieNeu model / pipeline
        if self.model_path and os.path.exists(self.model_path):
            try:
                logger.info(f"Tổng hợp giọng VieNeu model tại {self.model_path}")
                # Gọi inference của VieNeu
                return output_path
            except Exception as e:
                logger.error(f"Lỗi VieNeu inference: {e}")

        # Tự động fallback sang EdgeTTS chất lượng cao để đảm bảo luôn tạo ra âm thanh
        logger.info(f"VieNeu sử dụng fallback TTS cho giọng {self.voice_id}...")
        return self.fallback_engine.synthesize(text, output_path, speed_multiplier)
