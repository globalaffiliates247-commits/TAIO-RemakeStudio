"""
Upload File Source
Xử lý file audio/video tải lên trực tiếp từ giao diện web hoặc Telegram.
"""

import os
import shutil
import subprocess
import logging
from sources.base import BaseMediaSource, SourceMediaInfo

logger = logging.getLogger("taio.sources.upload")


class UploadFileSource(BaseMediaSource):
    def fetch(self, input_target: str, output_dir: str) -> SourceMediaInfo:
        os.makedirs(output_dir, exist_ok=True)
        file_path = input_target

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file tải lên: {file_path}")

        filename = os.path.basename(file_path)
        dest_path = os.path.join(output_dir, filename)
        if dest_path != file_path:
            shutil.copyfile(file_path, dest_path)

        # Trích xuất audio nếu là video
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]:
            audio_path = dest_path
        else:
            audio_path = os.path.splitext(dest_path)[0] + ".mp3"
            if not os.path.exists(audio_path):
                try:
                    subprocess.run(["ffmpeg", "-y", "-i", dest_path, "-vn", "-acodec", "libmp3lame", audio_path], check=True)
                except Exception:
                    audio_path = dest_path

        return SourceMediaInfo(
            title=os.path.splitext(filename)[0],
            media_path=dest_path,
            audio_path=audio_path,
            platform="upload"
        )
