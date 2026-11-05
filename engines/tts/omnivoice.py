"""
OmniVoice Engine (k2-fsa, Apache 2.0)
Hỗ trợ 600+ ngôn ngữ quốc tế và nhân bản giọng nói cho Super Admin (Luồng L3).
Gọi qua endpoint chuẩn OpenAI `/v1/audio/speech` (Bearer auth) hoặc Python API trực tiếp.
"""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger("taio.tts.omnivoice")


class OmniVoiceEngine:
    def __init__(
        self,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        voice: str = "en-US-JennyNeural"
    ):
        self.server_url = server_url or os.getenv("OMNIVOICE_SERVER_URL", "http://localhost:8080/v1/audio/speech")
        self.api_key = api_key or os.getenv("OMNIVOICE_API_KEY", "")
        self.voice = voice

    def synthesize(
        self,
        text: str,
        output_path: str,
        speed_multiplier: float = 1.0,
        voice_id: Optional[str] = None,
        prompt_speech_path: Optional[str] = None
    ) -> str:
        """
        Gọi omnivoice-server endpoint chuẩn OpenAI /v1/audio/speech
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        target_voice = voice_id or self.voice

        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": "omnivoice",
            "input": text,
            "voice": target_voice,
            "speed": speed_multiplier,
            "response_format": "mp3"
        }
        if prompt_speech_path:
            payload["prompt_speech"] = prompt_speech_path

        try:
            resp = requests.post(self.server_url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return output_path
            else:
                logger.warning(f"OmniVoice server trả về mã {resp.status_code}: {resp.text}")
                raise RuntimeError(f"OmniVoice error: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Không thể kết nối OmniVoice ({e}). Sử dụng Edge TTS quốc tế fallback.")
            from engines.tts.edge_tts_fallback import EdgeTTSEngine
            return EdgeTTSEngine(voice=target_voice).synthesize(text, output_path, speed_multiplier)
