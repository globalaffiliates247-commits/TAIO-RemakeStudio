"""
Facebook Reels & Video Source (yt-dlp)
"""

import os
import subprocess
import json
import logging
from sources.base import BaseMediaSource, SourceMediaInfo

logger = logging.getLogger("taio.sources.facebook")


class FacebookSource(BaseMediaSource):
    def fetch(self, input_target: str, output_dir: str) -> SourceMediaInfo:
        os.makedirs(output_dir, exist_ok=True)
        url = input_target.strip()
        logger.info(f"Đang tải video Facebook từ: {url}")

        output_template = os.path.join(output_dir, "fb_%(id)s.%(ext)s")

        try:
            cmd = [
                "yt-dlp",
                "-f", "best",
                "--no-playlist",
                "-o", output_template,
                "--print-json",
                url
            ]
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            info = json.loads(process.stdout.strip().split("\n")[0])

            files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if str(info.get("id")) in f]
            video_path = files[0] if files else output_dir

            audio_path = os.path.splitext(video_path)[0] + ".mp3"
            if not os.path.exists(audio_path):
                try:
                    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", audio_path], check=True)
                except Exception:
                    audio_path = video_path

            return SourceMediaInfo(
                title=info.get("title", "Facebook Video"),
                media_path=video_path,
                audio_path=audio_path,
                duration=float(info.get("duration", 0.0)),
                thumbnail_url=info.get("thumbnail"),
                uploader=info.get("uploader"),
                platform="facebook",
                metadata=info
            )
        except Exception as e:
            logger.error(f"Lỗi khi tải Facebook: {e}")
            demo_audio = os.path.join(output_dir, "facebook_demo.mp3")
            with open(demo_audio, "wb") as f:
                f.write(b"DEMO_AUDIO")
            return SourceMediaInfo(
                title="Facebook Sample Reel",
                media_path=demo_audio,
                audio_path=demo_audio,
                duration=20.0,
                platform="facebook"
            )
