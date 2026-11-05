"""
Mức 1: Xuất tài liệu Microsoft Word (.docx)
Trình bày bảng song ngữ chuyên nghiệp cho cuộc họp hoặc học tập.
"""

import os
import logging
from engines.models import Transcript

logger = logging.getLogger("taio.outputs.docx")


class DocxExporter:
    @staticmethod
    def export(transcript: Transcript, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor

            doc = Document()
            title = doc.add_heading(f"TAIO RemakeStudio: {transcript.title}", 0)

            # Metadata info
            p = doc.add_paragraph()
            p.add_run(f"Ngôn ngữ: ").bold = True
            p.add_run(f"{transcript.source_language} ➔ {transcript.target_language}\n")
            p.add_run(f"Thời lượng: ").bold = True
            p.add_run(f"{round(transcript.duration, 1)}s\n")
            p.add_run(f"Số lượng từ: ").bold = True
            p.add_run(f"{transcript.word_count} từ\n")

            # Table song ngữ
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Light Shading Accent 1'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Mốc thời gian'
            hdr_cells[1].text = 'Người nói'
            hdr_cells[2].text = 'Nguyên tác'
            hdr_cells[3].text = 'Bản dịch tiếng Việt'

            for s in transcript.segments:
                row_cells = table.add_row().cells
                st = transcript.format_timestamp(s.start, srt_format=False)
                en = transcript.format_timestamp(s.end, srt_format=False)
                row_cells[0].text = f"{st} - {en}"
                row_cells[1].text = s.speaker
                row_cells[2].text = s.original_text + (f"\n({s.pinyin})" if s.pinyin else "")
                row_cells[3].text = s.translated_text

            doc.save(output_path)
            return output_path

        except ImportError:
            logger.warning("python-docx chưa được cài. Xuất ra file định dạng văn bản thay thế.")
            from outputs.level1_text.txt import TextExporter
            txt_path = os.path.splitext(output_path)[0] + ".txt"
            return TextExporter.export(transcript, txt_path)
