"""
Microsoft Edge TTS Engine (Chính thức, Apache 2.0)
Giọng đọc AI tiếng Việt chất lượng cao hoàn toàn miễn phí.
Theo chuẩn v0.3: Không chứa dữ liệu giả lập hoặc dummy bytes.
"""

import os
import subprocess
import logging
from typing import Optional
from engines.errors import EngineUnavailable, EngineFailed

logger = logging.getLogger("taio.tts.edge")


class EdgeTTSEngine:
    def __init__(self, voice: str = "vi-VN-HoaiMyNeural"):
        self.voice = voice

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if not text or not text.strip():
            raise EngineFailed("Edge TTS", "Văn bản rỗng, không thể tổng hợp giọng nói.")

        rate_percent = int((speed_multiplier - 1.0) * 100)
        rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        # Tìm binary edge-tts trong venv hoặc system
        edge_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".venv", "bin", "edge-tts")
        if not os.path.exists(edge_bin):
            edge_bin = "edge-tts"

        cmd = [edge_bin, "--voice", self.voice, "--text", text.strip(), "--write-media", output_path]
        if rate_percent != 0:
            cmd.append(f"--rate={rate_str}")

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return output_path
            else:
                err_msg = res.stderr.strip() or "Không nhận được âm thanh từ Microsoft Edge TTS"
                raise EngineFailed("Edge TTS", err_msg)
        except Exception as e:
            logger.error(f"Lỗi Edge TTS: {e}")
            raise EngineFailed("Edge TTS", str(e))
