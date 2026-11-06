"""
TikTok Video Source (yt-dlp Python API)
Tải video công khai từ TikTok không watermark và trích xuất audio.
"""

import os
import subprocess
import logging
from sources.base import BaseMediaSource, SourceMediaInfo

logger = logging.getLogger("taio.sources.tiktok")


class TikTokSource(BaseMediaSource):
    def fetch(self, input_target: str, output_dir: str) -> SourceMediaInfo:
        os.makedirs(output_dir, exist_ok=True)
        url = input_target.strip()
        logger.info(f"Đang tải video TikTok từ: {url}")

        output_template = os.path.join(output_dir, "tiktok_%(id)s.%(ext)s")

        try:
            import yt_dlp

            ydl_opts = {
                'format': 'best',
                'outtmpl': output_template,
                'no_warnings': True,
                'quiet': True,
                'nocheckcertificate': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            video_id = info.get("id", "tiktok_video")
            ext = info.get("ext", "mp4")
            title = info.get("title", "TikTok Video")
            duration = float(info.get("duration", 0.0) or 0.0)

            video_path = output_template.replace("%(id)s", str(video_id)).replace("%(ext)s", str(ext))
            if not os.path.exists(video_path):
                files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if str(video_id) in f and not f.endswith(".mp3")]
                video_path = files[0] if files else output_dir

            audio_path = os.path.splitext(video_path)[0] + ".mp3"
            if not os.path.exists(audio_path):
                self._extract_audio(video_path, audio_path)

            return SourceMediaInfo(
                title=title,
                media_path=video_path,
                audio_path=audio_path,
                duration=duration,
                thumbnail_url=info.get("thumbnail"),
                uploader=info.get("uploader"),
                platform="tiktok",
                metadata=info
            )

        except Exception as e:
            logger.error(f"Lỗi khi tải TikTok: {e}")
            raise RuntimeError(
                f"Không thể tải video từ link TikTok ({e}). "
                f"Vui lòng kiểm tra lại link hoặc tải trực tiếp file video lên bằng tab 'Tải File Lên'."
            )

    def _extract_audio(self, video_path: str, audio_path: str):
        try:
            cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", audio_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except Exception:
            import shutil
            shutil.copyfile(video_path, audio_path)
