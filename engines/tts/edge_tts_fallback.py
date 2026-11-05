"""
Edge TTS Engine: Giọng đọc AI tiếng Việt chất lượng cao hoàn toàn miễn phí
Hỗ trợ giọng Bắc (Hoài My, Nam Minh) mượt mà, tự nhiên.
"""

import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("taio.tts.edge")


class EdgeTTSEngine:
    def __init__(self, voice: str = "vi-VN-HoaiMyNeural"):
        self.voice = voice

    async def _synth_async(self, text: str, output_path: str, rate: str = "+0%"):
        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice, rate=rate)
        await communicate.save(output_path)

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0) -> str:
        """
        Tổng hợp giọng nói tiếng Việt từ văn bản và lưu ra file MP3.
        speed_multiplier: >1.0 nếu cần đọc nhanh hơn để vừa khớp timeline video.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        rate_percent = int((speed_multiplier - 1.0) * 100)
        rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        try:
            asyncio.run(self._synth_async(text, output_path, rate=rate_str))
            return output_path
        except Exception as e:
            logger.warning(f"edge-tts error: {e}. Tạo file silent/dummy audio.")
            self._generate_dummy_audio(output_path)
            return output_path

    def _generate_dummy_audio(self, output_path: str):
        # Tạo file wav hoặc mp3 rỗng hợp lệ
        with open(output_path, "wb") as f:
            f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 1024)
