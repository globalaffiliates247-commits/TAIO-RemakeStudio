"""
Media Probe Service
Xử lý xem trước thông tin video (POST /api/probe) cho link hoặc file tải lên.
"""

import os
import subprocess
import math
from typing import Dict, Any, Optional
from sources.ytdlp_common import get_media_info_from_url, validate_source_url
from engines.errors import SourceFetchError


def probe_file(file_path: str) -> Dict[str, Any]:
    """Đo thời lượng và metadata của file cục bộ bằng ffmpeg/ffprobe."""
    if not os.path.exists(file_path):
        raise SourceFetchError("File Upload", "Tệp tải lên không tồn tại trên hệ thống.")

    duration = 0.0
    try:
        cmd = ["ffmpeg", "-i", file_path]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                time_str = line.split("Duration:")[1].split(",")[0].strip()
                parts = time_str.split(":")
                duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                break
    except Exception:
        duration = 0.0

    cost_minutes = math.ceil(duration / 60.0) if duration > 0 else 1

    return {
        "title": os.path.splitext(os.path.basename(file_path))[0],
        "platform": "upload",
        "duration": round(duration, 1),
        "thumbnail": "",
        "cost_minutes": cost_minutes,
        "media_path": file_path
    }


def probe_media(url: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    if url and url.strip():
        info = get_media_info_from_url(url.strip())
        dur = info.get("duration", 0.0)
        cost_minutes = math.ceil(dur / 60.0) if dur > 0 else 1
        info["cost_minutes"] = cost_minutes
        return info
    elif file_path and os.path.exists(file_path):
        return probe_file(file_path)
    else:
        raise SourceFetchError("Input", "Vui lòng cung cấp link hoặc chọn tệp tải lên.")
