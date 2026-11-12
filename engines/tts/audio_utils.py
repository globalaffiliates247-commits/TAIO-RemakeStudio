"""
Tiện ích âm thanh dùng chung cho các engine giọng đọc: đổi định dạng sang MP3 và chỉnh tốc độ bằng ffmpeg.
"""

import os
import subprocess

try:
    from engines.errors import EngineFailed, EngineUnavailable
except ImportError:  # dùng độc lập ngoài repo
    class EngineUnavailable(RuntimeError):
        def __init__(self, engine_name, reason, setup_hint=""):
            super().__init__(f"{engine_name}: {reason}")

    class EngineFailed(RuntimeError):
        def __init__(self, engine_name, original_error):
            super().__init__(f"{engine_name}: {original_error}")

ENGINE_NAME = "ffmpeg"


def _atempo_chain(speed: float) -> str:
    """ffmpeg atempo nhận 0.5–2.0 mỗi lần; ghép nhiều lần nếu vượt ngưỡng."""
    parts, s = [], max(0.25, min(4.0, speed))
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


def to_mp3(src_path: str, dst_path: str, speed: float = 1.0) -> str:
    """Chuyển src (wav/pcm có header) sang MP3 tại dst; speed != 1 thì đổi tốc độ, giữ nguyên cao độ."""
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src_path]
    if abs(speed - 1.0) > 0.01:
        cmd += ["-filter:a", _atempo_chain(speed)]
    cmd += ["-c:a", "libmp3lame", "-q:a", "2", dst_path]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except FileNotFoundError:
        raise EngineFailed(ENGINE_NAME, "chưa cài ffmpeg")
    except subprocess.CalledProcessError as e:
        raise EngineFailed(ENGINE_NAME, f"ffmpeg đổi sang MP3 lỗi: {(e.stderr or b'').decode(errors='ignore')[-200:]}")
    if not os.path.exists(dst_path) or os.path.getsize(dst_path) < 512:
        raise EngineFailed(ENGINE_NAME, "file MP3 tạo ra rỗng")
    return dst_path
