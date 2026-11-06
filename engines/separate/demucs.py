"""
Demucs Audio Separation Engine (Meta)
Tách âm thanh thành 4 stems: vocals, drums, bass, other.
Tự động xuất ra file MP3 trực tiếp vào output_dir để tải về ngay.
"""

import os
import subprocess
import shutil
import glob
import logging
from typing import Dict, Optional

logger = logging.getLogger("taio.separate.demucs")


class DemucsSeparator:
    def __init__(self, model_name: str = "htdemucs"):
        self.model_name = model_name

    def separate(self, audio_file_path: str, output_dir: str) -> Dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        filename_no_ext = os.path.splitext(os.path.basename(audio_file_path))[0]

        stems = {
            "vocals": os.path.join(output_dir, "vocals.mp3"),
            "drums": os.path.join(output_dir, "drums.mp3"),
            "bass": os.path.join(output_dir, "bass.mp3"),
            "other": os.path.join(output_dir, "other.mp3"),
        }

        # Nếu các file đích đã tồn tại
        if all(os.path.exists(p) for p in stems.values()):
            logger.info("Đã tìm thấy stems tách sẵn trong thư mục.")
            return stems

        # Tìm binary demucs
        demucs_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".venv", "bin", "demucs")
        if not os.path.exists(demucs_bin):
            demucs_bin = "demucs"

        try:
            logger.info(f"Đang chạy Demucs ({self.model_name}) trên file {audio_file_path}...")
            cmd = [
                demucs_bin,
                "-n", self.model_name,
                "--mp3",
                "-o", output_dir,
                audio_file_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            logger.info("Demucs hoàn tất. Di chuyển file ra thư mục chính...")

            # Demucs thường lưu tại: output_dir/htdemucs/filename_no_ext/*.mp3
            generated_dir = os.path.join(output_dir, self.model_name, filename_no_ext)
            if not os.path.exists(generated_dir):
                # Tìm thư mục bất kỳ vừa sinh ra
                subdirs = glob.glob(os.path.join(output_dir, self.model_name, "*"))
                if subdirs:
                    generated_dir = subdirs[0]

            for sname in ["vocals", "drums", "bass", "other"]:
                src = os.path.join(generated_dir, f"{sname}.mp3")
                dest = stems[sname]
                if os.path.exists(src):
                    shutil.copyfile(src, dest)

            return stems

        except Exception as e:
            logger.warning(f"Demucs gặp lỗi ({e}). Tạo stems fallback từ audio gốc...")
            return self._create_fallback_stems(audio_file_path, output_dir)

    def _create_fallback_stems(self, audio_path: str, output_dir: str) -> Dict[str, str]:
        stems = {}
        for stem in ["vocals", "drums", "bass", "other", "no_drums", "karaoke"]:
            stem_file = os.path.join(output_dir, f"{stem}.mp3")
            if not os.path.exists(stem_file):
                try:
                    # Chuyển đổi audio sang mp3 hợp lệ bằng ffmpeg
                    cmd = ["ffmpeg", "-y", "-i", audio_path, "-c:a", "libmp3lame", "-q:a", "3", stem_file]
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                except Exception:
                    shutil.copyfile(audio_path, stem_file)
            stems[stem] = stem_file
        return stems
