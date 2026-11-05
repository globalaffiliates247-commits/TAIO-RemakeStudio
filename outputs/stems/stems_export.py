"""
Đầu ra Luồng L5: Stems Export
Xuất các bản nhạc tách riêng phục vụ tập nhạc (Deliberate Practice) hoặc Karaoke:
- Vocals (Giọng hát)
- Drums (Trống)
- Bass (Guitar bass)
- Other (Piano, Synth, Guitar lead...)
- Minus Drums (Nhạc đệm bỏ trống để tập trống)
- Karaoke / Instrumental (Nhạc đệm bỏ giọng hát)
"""

import os
import subprocess
import logging
from typing import Dict

logger = logging.getLogger("taio.outputs.stems")


class StemsExporter:
    @staticmethod
    def mix_minus_track(stem_paths: Dict[str, str], excluded_stem: str, output_path: str) -> str:
        """
        Ghép tất cả các stems lại, loại trừ 1 stem (ví dụ loại trừ 'drums' để tập trống, loại trừ 'vocals' để làm karaoke)
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        included_files = [path for name, path in stem_paths.items() if name != excluded_stem and os.path.exists(path)]

        if not included_files:
            logger.warning("Không có file stem nào để trộn.")
            return output_path

        inputs = []
        for f in included_files:
            inputs.extend(["-i", f])

        filter_complex = f"amix=inputs={len(included_files)}:duration=longest"
        cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, output_path]

        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_path
        except Exception as e:
            logger.error(f"Lỗi khi trộn minus track {excluded_stem}: {e}")
            return included_files[0]
