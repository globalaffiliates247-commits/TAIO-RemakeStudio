"""
Mức 1: Xuất phụ đề SRT (SubRip Subtitle)
Hỗ trợ:
1. Phụ đề tiếng Việt dịch
2. Phụ đề song ngữ (Bilingual: Câu gốc + Dịch)
3. Chế độ bài hát 3 dòng (Chữ Hán + Pinyin + Dịch tiếng Việt)
"""

import os
from engines.models import Transcript


class SrtExporter:
    @staticmethod
    def export(
        transcript: Transcript,
        output_path: str,
        bilingual: bool = True,
        song_mode: bool = False
    ) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        entries = []

        for idx, s in enumerate(transcript.segments, 1):
            st = transcript.format_timestamp(s.start, srt_format=True)
            en = transcript.format_timestamp(s.end, srt_format=True)

            text_lines = []
            if song_mode and s.pinyin:
                # 3 dòng: Chữ gốc - Pinyin - Tiếng Việt
                text_lines.append(s.original_text)
                text_lines.append(s.pinyin)
                text_lines.append(s.translated_text or "")
            elif bilingual and s.original_text and s.translated_text:
                text_lines.append(s.original_text)
                text_lines.append(s.translated_text)
            else:
                text_lines.append(s.translated_text or s.original_text)

            body = "\n".join(filter(None, text_lines))
            entries.append(f"{idx}\n{st} --> {en}\n{body}\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(entries))

        return output_path
