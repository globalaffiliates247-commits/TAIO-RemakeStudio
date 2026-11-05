"""
Luồng L5: Tách nhạc (Music Stems Separation - Deliberate Practice)
Sử dụng Demucs để tách bài hát thành các track riêng biệt:
- Giọng hát (Vocals)
- Tiếng trống (Drums)
- Guitar Bass (Bass)
- Nhạc cụ khác (Other)
- Nhạc đệm bỏ trống (Minus Drums)
- Karaoke (Minus Vocals)
"""

import os
import logging
from typing import Dict, Any, Optional
from flows.base import BaseFlow
from engines.separate.demucs import DemucsSeparator
from outputs.stems.stems_export import StemsExporter

logger = logging.getLogger("taio.flows.l5")


class MusicStemsFlow(BaseFlow):
    def __init__(self):
        super().__init__("L5", "Tách nhạc (Music Stems)")
        self.demucs = DemucsSeparator()

    def run(
        self,
        audio_path: str,
        video_path: Optional[str],
        output_dir: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Khởi chạy Luồng L5: Tách stems âm thanh từ {audio_path}...")

        # 1. Tách stems cơ bản
        stems = self.demucs.separate(audio_path, output_dir)

        # 2. Tạo bản mix bổ sung: Nhạc đệm bỏ trống & Karaoke
        no_drums_path = os.path.join(output_dir, "minus_drums.mp3")
        karaoke_path = os.path.join(output_dir, "karaoke_no_vocals.mp3")

        StemsExporter.mix_minus_track(stems, "drums", no_drums_path)
        StemsExporter.mix_minus_track(stems, "vocals", karaoke_path)

        stems["no_drums"] = no_drums_path
        stems["karaoke"] = karaoke_path

        return {
            "flow": self.flow_id,
            "title": os.path.splitext(os.path.basename(audio_path))[0],
            "stems": stems,
            "files": stems
        }
