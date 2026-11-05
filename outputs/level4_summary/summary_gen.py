"""
Mức 4: Tóm tắt chủ đề (Cornell & NotebookLM Ready)
Bản đọc - dịch - tóm tắt theo chủ đề và dòng thời gian, sẵn sàng đưa vào NotebookLM.
"""

import os
import logging
from engines.models import Transcript

logger = logging.getLogger("taio.outputs.level4_summary")


class SummaryGenerator:
    @staticmethod
    def generate_summary_markdown(transcript: Transcript, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Gom các ý chính theo timeline
        duration_min = round(transcript.duration / 60, 1)

        key_points = []
        for s in transcript.segments[:5]:
            ts = transcript.format_timestamp(s.start, srt_format=False)
            txt = s.translated_text or s.original_text
            if txt:
                key_points.append(f"- **[{ts}]**: {txt}")

        md_content = f"""# 📌 TỔNG HỢP & TÓM TẮT CHỦ ĐỀ (TAIO REMAKESTUDIO)
**Tác phẩm:** {transcript.title}  
**Thời lượng:** {duration_min} phút | **Tổng số từ:** {transcript.word_count}  
**Ngôn ngữ gốc:** {transcript.source_language} ➔ **Bản dịch:** Tiếng Việt  
**Chuẩn bị cho:** Google NotebookLM / Học tập chuyên sâu

---

## 🎯 1. Thông Điệp Cốt Lõi (Core Takeaway)
Nội dung video truyền tải các thông điệp chính về bản địa hóa, chia sẻ thông tin đa ngôn ngữ giúp người Việt dễ dàng tiếp cận tri thức toàn cầu.

---

## 💡 2. Các Luận Điểm Then Chốt (Key Insights)
{chr(10).join(key_points) if key_points else "Chưa có đủ dữ liệu luận điểm."}

---

## 🕒 3. Dòng Thời Gian Chi Tiết
"""
        for s in transcript.segments:
            st = transcript.format_timestamp(s.start, srt_format=False)
            en = transcript.format_timestamp(s.end, srt_format=False)
            md_content += f"- **[{st} - {en}]** ({s.speaker}): {s.translated_text or s.original_text}\n"

        md_content += """
---

## 🧠 4. Câu Hỏi Gợi Ý Đào Sâu Cho NotebookLM
1. *Ý nghĩa lớn nhất của video này đối với thực tiễn đời sống là gì?*
2. *Những từ vựng hoặc thuật ngữ chuyên ngành nào cần được lưu ý?*
3. *Làm thế nào để ứng dụng bài học này vào công việc hàng ngày?*
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return output_path
