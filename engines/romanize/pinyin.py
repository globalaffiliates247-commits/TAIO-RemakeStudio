"""
Chinese Pinyin Romanizer (thư viện pypinyin, MIT)
Phiên âm chữ Hán có thanh điệu cho người học tiếng Trung qua bài hát.
"""

import logging

logger = logging.getLogger("taio.romanize.pinyin")


class PinyinRomanizer:
    @staticmethod
    def to_pinyin(text: str) -> str:
        try:
            from pypinyin import pinyin, Style
            res = pinyin(text, style=Style.TONE)
            return " ".join([item[0] for item in res])
        except ImportError:
            # Fallback nếu pypinyin chưa cài
            logger.warning("pypinyin chưa được cài đặt. Trả về text gốc.")
            return text
