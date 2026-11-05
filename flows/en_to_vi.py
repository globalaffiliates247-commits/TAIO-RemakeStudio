"""
Luồng L1: Tiếng Anh ➔ Tiếng Việt (Mặc định cho mọi người dùng)
Chép lời Groq Turbo ➔ Dịch Gemini Flash ➔ Xuất Mức 1-4
"""

import os
import logging
from typing import Dict, Any, Optional
from flows.base import BaseFlow
from engines.transcribe.groq_turbo import GroqTurboTranscriber
from engines.translate.gemini import GeminiTranslator
from outputs.level1_text.txt import TextExporter
from outputs.level1_text.srt import SrtExporter
from outputs.level1_text.docx_export import DocxExporter
from outputs.level2_voice.voice_synth import VoiceSynthesizer
from outputs.level3_video.video_muxer import VideoMuxer
from outputs.level4_summary.summary_gen import SummaryGenerator

logger = logging.getLogger("taio.flows.l1")


class EnToViFlow(BaseFlow):
    def __init__(self):
        super().__init__("L1", "Tiếng Anh → Tiếng Việt")
        self.transcriber = GroqTurboTranscriber()
        self.translator = GeminiTranslator()
        self.voice_synth = VoiceSynthesizer()

    def run(
        self,
        audio_path: str,
        video_path: Optional[str],
        output_dir: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        target_level = int(options.get("target_level", 2))
        voice_id = options.get("voice_id", "vi_north_female_1")

        logger.info(f"Khởi chạy Luồng L1 (Target Level: {target_level})...")

        # 1. Chép lời tiếng Anh
        transcript = self.transcriber.transcribe(audio_path, language="en")

        # 2. Dịch sang tiếng Việt
        transcript = self.translator.translate_transcript(transcript, target_lang="vi")

        results = {
            "flow": self.flow_id,
            "title": transcript.title,
            "duration": transcript.duration,
            "word_count": transcript.word_count,
            "transcript": transcript.to_dict(),
            "files": {}
        }

        # Mức 1: Xuất văn bản TXT, SRT, DOCX
        txt_file = os.path.join(output_dir, "transcript.txt")
        srt_file = os.path.join(output_dir, "subtitles.srt")
        docx_file = os.path.join(output_dir, "document.docx")

        TextExporter.export(transcript, txt_file)
        SrtExporter.export(transcript, srt_file, bilingual=True)
        DocxExporter.export(transcript, docx_file)

        results["files"]["txt"] = txt_file
        results["files"]["srt"] = srt_file
        results["files"]["docx"] = docx_file

        # Mức 2: Giọng đọc tiếng Việt (MP3)
        if target_level >= 2:
            mp3_file = os.path.join(output_dir, "voice_vietnamese.mp3")
            self.voice_synth.synthesize_transcript(transcript, mp3_file, voice_id=voice_id)
            results["files"]["audio"] = mp3_file

        # Mức 3: Video lồng tiếng (MP4)
        if target_level >= 3 and video_path and os.path.exists(video_path):
            mp4_file = os.path.join(output_dir, "video_dubbed.mp4")
            VideoMuxer.mux_dubbed_video(video_path, results["files"]["audio"], srt_file, mp4_file)
            results["files"]["video"] = mp4_file

        # Mức 4: Tóm tắt chủ đề Cornell cho NotebookLM
        if target_level >= 4:
            md_file = os.path.join(output_dir, "notebooklm_summary.md")
            SummaryGenerator.generate_summary_markdown(transcript, md_file)
            results["files"]["summary_md"] = md_file

        return results
