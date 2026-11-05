"""
Mức 1: Xuất văn bản thuần TXT
Bao gồm bản chép lời gốc + bản dịch tiếng Việt song ngữ theo mốc thời gian.
"""

import os
from engines.models import Transcript


class TextExporter:
    @staticmethod
    def export(transcript: Transcript, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        lines = [
            f"=== {transcript.title.upper()} ===",
            f"Ngôn ngữ: {transcript.source_language} ➔ {transcript.target_language}",
            f"Thời lượng: {round(transcript.duration, 1)}s | Số từ: {transcript.word_count}",
            "=" * 50,
            ""
        ]

        for s in transcript.segments:
            st_str = transcript.format_timestamp(s.start, srt_format=False)
            en_str = transcript.format_timestamp(s.end, srt_format=False)

            lines.append(f"[{st_str} --> {en_str}] ({s.speaker})")
            if s.original_text:
                lines.append(f"  • Gốc: {s.original_text}")
            if s.pinyin:
                lines.append(f"  • Pinyin: {s.pinyin}")
            if s.translated_text:
                lines.append(f"  • Dịch: {s.translated_text}")
            lines.append("")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path
