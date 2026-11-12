"""
Giọng đọc qua mọi máy chủ theo chuẩn OpenAI `POST /v1/audio/speech` — một engine cho nhiều server.

Dùng cho:
  - VieNeu-TTS v3 Turbo (Apache-2.0) chạy trên máy:  `uv run python -m apps.openai_speech` trong repo VieNeu-TTS.
    25 giọng có sẵn Bắc/Trung/Nam (xem GET /v1/voices), chạy CPU (ONNX), không cần API key.
  - VoxCPM2, OmniVoice khi chạy dạng server, hoặc dịch vụ trả phí sau này: chỉ đổi biến môi trường.

Mỗi server một tiền tố biến môi trường (env_prefix), ví dụ VIENEU_*, VOXCPM_*:
  <PREFIX>_BASE_URL   ví dụ http://127.0.0.1:8101/v1  (bắt buộc)
  <PREFIX>_API_KEY    Bearer key nếu server có đặt (VieNeu: VIENEU_API_KEY)
  <PREFIX>_MODEL      tên model gửi kèm (VieNeu chấp nhận chuỗi bất kỳ)
  <PREFIX>_FORMAT     wav | mp3 (VieNeu chỉ nhận wav hoặc pcm; mặc định wav)
  <PREFIX>_SPEED_VIA_FFMPEG  1 = chỉnh tốc độ bằng ffmpeg (VieNeu bỏ qua tham số speed); mặc định 1

Tham số voice = tên giọng của server (VieNeu: "Ngọc Linh", "Mỹ Duyên", "Ngọc Trân"...).
"""

import os
import logging
import tempfile
from typing import Optional

import requests

from engines.tts.audio_utils import to_mp3

logger = logging.getLogger("taio.tts.openai_speech")

try:
    from engines.errors import EngineFailed, EngineUnavailable
except ImportError:  # dùng độc lập ngoài repo
    class EngineUnavailable(RuntimeError):
        def __init__(self, engine_name, reason, setup_hint=""):
            super().__init__(f"{engine_name}: {reason}")

    class EngineFailed(RuntimeError):
        def __init__(self, engine_name, original_error):
            super().__init__(f"{engine_name}: {original_error}")

ENGINE_NAME = "Giọng đọc qua /v1/audio/speech"


class OpenAISpeechEngine:
    def __init__(self, voice: Optional[str] = None, env_prefix: str = "VIENEU"):
        p = env_prefix.upper()
        self.prefix = p
        self.base_url = (os.getenv(f"{p}_BASE_URL") or "").rstrip("/")
        self.api_key = os.getenv(f"{p}_API_KEY", "")
        self.model = os.getenv(f"{p}_MODEL", "tts")
        self.fmt = os.getenv(f"{p}_FORMAT", "wav")
        self.speed_via_ffmpeg = os.getenv(f"{p}_SPEED_VIA_FFMPEG", "1") != "0"
        self.timeout = float(os.getenv(f"{p}_TIMEOUT", "120"))
        self.voice = voice

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> str:
        if not self.base_url:
            raise EngineUnavailable(ENGINE_NAME, f"chưa đặt {self.prefix}_BASE_URL")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "input": text, "response_format": self.fmt}
        if self.voice:
            payload["voice"] = self.voice
        if not self.speed_via_ffmpeg:
            payload["speed"] = speed_multiplier

        try:
            resp = requests.post(f"{self.base_url}/audio/speech", json=payload, headers=headers,
                                 timeout=self.timeout, stream=True)
        except requests.RequestException as e:
            raise EngineUnavailable(ENGINE_NAME, f"không kết nối được {self.base_url}: {e}")
        if resp.status_code != 200:
            raise EngineFailed(ENGINE_NAME, f"{self.prefix} trả mã {resp.status_code}: {resp.text[:200]}")

        with tempfile.NamedTemporaryFile(suffix=f".{self.fmt}", delete=False) as tmp:
            for chunk in resp.iter_content(65536):
                tmp.write(chunk)
            raw_path = tmp.name
        try:
            if os.path.getsize(raw_path) < 512:
                raise EngineFailed(ENGINE_NAME, f"{self.prefix} trả về âm thanh rỗng")
            speed = speed_multiplier if self.speed_via_ffmpeg else 1.0
            return to_mp3(raw_path, output_path, speed=speed)
        finally:
            os.remove(raw_path)
