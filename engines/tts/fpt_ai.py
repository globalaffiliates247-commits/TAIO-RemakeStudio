"""
FPT.AI Text-To-Speech API Integration
Hỗ trợ giọng chuẩn VTV: Ban Mai (Bắc), Thu Dung (Nam), Mỹ An (Trung)...
"""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger("taio.tts.fpt_ai")


class FptAITTSEngine:
    def __init__(self, api_key: Optional[str] = None, voice: str = "banmai"):
        self.api_key = api_key or os.getenv("FPT_AI_API_KEY", "")
        self.voice = voice
        self.api_url = "https://api.fpt.ai/hmi/tts/v5"

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> str:
        if not self.api_key:
            logger.warning("FPT_AI_API_KEY không có. Dùng fallback engine.")
            from engines.tts.edge_tts_fallback import EdgeTTSEngine
            return EdgeTTSEngine().synthesize(text, output_path, speed_multiplier)

        try:
            headers = {
                "api-key": self.api_key,
                "voice": self.voice,
                "speed": str(speed_multiplier)
            }
            resp = requests.post(self.api_url, data=text.encode("utf-8"), headers=headers, timeout=15)
            data = resp.json()
            if data.get("error") == 0 and "async" in data:
                audio_url = data["async"]
                # Tải audio từ url
                audio_data = requests.get(audio_url, timeout=30).content
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                return output_path
            else:
                raise RuntimeError(f"FPT.AI error: {data.get('message')}")
        except Exception as e:
            logger.error(f"FPT.AI TTS thất bại: {e}")
            from engines.tts.edge_tts_fallback import EdgeTTSEngine
            return EdgeTTSEngine().synthesize(text, output_path, speed_multiplier)
