"""
TAIO RemakeStudio: Định dạng dữ liệu chuẩn Transcript
Quy ước PRD: Tất cả các luồng, công cụ và mức đầu ra giao tiếp qua Transcript.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import json


@dataclass
class TranscriptSegment:
    id: int
    start: float  # Giây bắt đầu (ví dụ 1.25)
    end: float    # Giây kết thúc (ví dụ 4.80)
    speaker: str = "Speaker 1"
    original_text: str = ""
    translated_text: str = ""
    pinyin: Optional[str] = None      # Dùng cho Song Mode tiếng Hoa
    romaji: Optional[str] = None      # Dùng cho Song Mode tiếng Nhật/Hàn
    audio_path: Optional[str] = None  # File âm thanh TTS của riêng đoạn này (Mức 2)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Transcript:
    title: str = "Video Transcript"
    source_url: Optional[str] = None
    media_path: Optional[str] = None
    source_language: str = "en"
    target_language: str = "vi"
    duration: float = 0.0
    segments: List[TranscriptSegment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_segment(self, segment: TranscriptSegment):
        self.segments.append(segment)
        if segment.end > self.duration:
            self.duration = segment.end

    @property
    def word_count(self) -> int:
        return sum(len((s.translated_text or s.original_text).split()) for s in self.segments)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source_url": self.source_url,
            "media_path": self.media_path,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "duration": self.duration,
            "word_count": self.word_count,
            "segments": [s.to_dict() for s in self.segments],
            "metadata": self.metadata
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transcript":
        segments = [TranscriptSegment(**seg) for seg in data.get("segments", [])]
        return cls(
            title=data.get("title", ""),
            source_url=data.get("source_url"),
            media_path=data.get("media_path"),
            source_language=data.get("source_language", "en"),
            target_language=data.get("target_language", "vi"),
            duration=data.get("duration", 0.0),
            segments=segments,
            metadata=data.get("metadata", {})
        )

    def format_timestamp(self, seconds: float, srt_format: bool = True) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        sep = "," if srt_format else "."
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"
