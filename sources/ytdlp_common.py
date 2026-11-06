"""
yt-dlp Common Utilities
Xử lý tải video và trích xuất thông tin chung từ TikTok, Facebook.
Từ chối YouTube và ném SourceFetchError có hướng dẫn rõ ràng.
"""

import os
import subprocess
import logging
from typing import Dict, Any
from engines.errors import SourceFetchError

logger = logging.getLogger("taio.sources.ytdlp")


def validate_source_url(url: str) -> str:
    """Kiểm tra nền tảng và tính hợp lệ của link."""
    u = url.strip().lower()
    if not u.startswith(("http://", "https://")):
        raise SourceFetchError("URL", "Đường dẫn không hợp lệ. Vui lòng nhập link bắt đầu bằng http:// hoặc https://", action_hint="Kiểm tra lại link")

    if "youtube.com" in u or "youtu.be" in u:
        raise SourceFetchError(
            "YouTube",
            "Hiện chưa hỗ trợ YouTube do chính sách kiểm duyệt IP máy chủ đám mây.",
            action_hint="Hãy tải video về máy rồi dùng tab 'Tải file lên'"
        )

    if "tiktok.com" in u or "douyin.com" in u:
        return "tiktok"
    elif "facebook.com" in u or "fb.watch" in u:
        return "facebook"
    else:
        return "generic"


def get_media_info_from_url(url: str) -> Dict[str, Any]:
    """Trích xuất metadata (tiêu đề, thời lượng, thumbnail) từ link mà không tải cả video."""
    platform = validate_source_url(url)

    try:
        import yt_dlp
        ydl_opts = {
            'no_warnings': True,
            'quiet': True,
            'skip_download': True,
            'nocheckcertificate': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        duration = float(info.get("duration", 0.0) or 0.0)
        title = info.get("title", f"Video {platform.capitalize()}")
        thumbnail = info.get("thumbnail") or ""

        return {
            "title": title,
            "platform": platform,
            "duration": duration,
            "thumbnail": thumbnail,
            "uploader": info.get("uploader", "")
        }
    except SourceFetchError:
        raise
    except Exception as e:
        logger.error(f"Lỗi extract info từ {url}: {e}")
        err_str = str(e)
        if "Private" in err_str or "login" in err_str:
            raise SourceFetchError(platform, "Video ở chế độ riêng tư hoặc yêu cầu đăng nhập", action_hint="Tải file lên thay thế")
        raise SourceFetchError(platform, f"Không thể lấy thông tin video ({err_str[:80]})", action_hint="Tải file lên thay thế")
