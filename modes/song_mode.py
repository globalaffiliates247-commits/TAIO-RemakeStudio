"""
Chế độ Bài Hát (Song Mode)
1. Tách giọng hát khỏi nhạc trước khi chép lời bằng Demucs.
2. Thêm phiên âm ngữ âm (Pinyin tiếng Trung, Romaji tiếng Nhật...).
3. Xuất đầu ra 3 dòng: Chữ gốc · Phiên âm · Tiếng Việt.
"""

import os
import logging
from engines.models import Transcript
from engines.separate.demucs import DemucsSeparator
from engines.romanize.pinyin import PinyinRomanizer

logger = logging.getLogger("taio.modes.song_mode")


class SongModeProcessor:
    def __init__(self):
        self.demucs = DemucsSeparator()

    def prepare_isolated_vocals(self, audio_path: str, work_dir: str) -> str:
        """Tách giọng hát ra khỏi nhạc nền để đưa vào Whisper chép lời chuẩn nhất"""
        stems = self.demucs.separate(audio_path, work_dir)
        vocals_path = stems.get("vocals")
        if vocals_path and os.path.exists(vocals_path):
            logger.info("Đã tách giọng hát cho Song Mode.")
            return vocals_path
        return audio_path

    def enrich_with_romanization(self, transcript: Transcript, lang: str = "zh") -> Transcript:
        """Gắn phiên âm Pinyin/Romaji vào từng câu trong Transcript"""
        if lang in ["zh", "zh-cn", "zh-tw", "chinese"]:
            for seg in transcript.segments:
                if seg.original_text:
                    seg.pinyin = PinyinRomanizer.to_pinyin(seg.original_text)
        return transcript
