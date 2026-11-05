"""
Base Media Source
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class SourceMediaInfo:
    title: str
    media_path: str        # Đường dẫn file video hoặc audio đã tải/lưu
    audio_path: str        # Đường dẫn file audio (mp3 hoặc wav) trích xuất để chép lời
    duration: float = 0.0
    thumbnail_url: Optional[str] = None
    uploader: Optional[str] = None
    platform: str = "local"
    metadata: Dict[str, Any] = None


class BaseMediaSource(ABC):
    @abstractmethod
    def fetch(self, input_target: str, output_dir: str) -> SourceMediaInfo:
        pass
