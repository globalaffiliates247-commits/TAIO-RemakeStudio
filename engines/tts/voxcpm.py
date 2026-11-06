"""
VoxCPM2 Text-to-Speech Engine
Model ~2B tham số (dưới ngưỡng 15 GB), chạy server GPU qua vLLM-Omni.
Gọi qua endpoint chuẩn OpenAI /v1/audio/speech, hỗ trợ mô tả giọng (voice prompt) theo vùng miền.
"""

import os
import requests
import logging
from typing import Optional
from engines.errors import EngineUnavailable, EngineFailed

logger = logging.getLogger("taio.tts.voxcpm")


class VoxCPMEngine:
    def __init__(
        self,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        voice_prompt: Optional[str] = None
    ):
        self.server_url = server_url or os.getenv("VOXCPM_SERVER_URL", "")
        self.api_key = api_key or os.getenv("VOXCPM_API_KEY", "")
        self.default_prompt = voice_prompt or "Giọng nữ tiếng Việt miền Bắc truyền cảm, tự nhiên, rõ ràng."

    def synthesize(
        self,
        text: str,
        output_path: str,
        speed_multiplier: float = 1.0,
        voice_prompt: Optional[str] = None
    ) -> str:
        if not self.server_url or len(self.server_url.strip()) < 8:
            raise EngineUnavailable(
                "VoxCPM2",
                "Chưa cấu hình VOXCPM_SERVER_URL",
                setup_hint="Chạy server VoxCPM2 bằng vLLM-Omni rồi thêm VOXCPM_SERVER_URL vào file .env."
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        prompt = voice_prompt or self.default_prompt

        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": "voxcpm2",
            "input": text,
            "voice": prompt,
            "speed": speed_multiplier,
            "response_format": "mp3"
        }

        try:
            resp = requests.post(self.server_url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return output_path
            else:
                raise EngineFailed("VoxCPM2", f"Server trả về mã lỗi {resp.status_code}: {resp.text[:120]}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Không thể kết nối đến VoxCPM2 server tại {self.server_url}: {e}")
            raise EngineUnavailable("VoxCPM2", f"Không thể kết nối đến {self.server_url} ({e})")
        except Exception as e:
            raise EngineFailed("VoxCPM2", str(e))
