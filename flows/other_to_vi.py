"""
Luồng L2: Ngoại ngữ khác (Trung, Nhật, Hàn...) ➔ Tiếng Việt
Hỗ trợ Song Mode (tách giọng trước khi chép lời, pinyin 3 dòng).
"""

import os
import logging
from typing import Dict, Any, Optional
from flows.base import BaseFlow
from engines.transcribe.groq_turbo import GroqTurboTranscriber
from engines.translate.gemini import GeminiTranslator
from modes.song_mode import SongModeProcessor
from outputs.level1_text.txt import TextExporter
from outputs.level1_text.srt import SrtExporter
from outputs.level1_text.docx_export import DocxExporter
from outputs.level2_voice.voice_synth import VoiceSynthesizer
from outputs.level3_video.video_muxer import VideoMuxer
from outputs.level4_summary.summary_gen import SummaryGenerator

logger = logging.getLogger("taio.flows.l2")


class OtherToViFlow(BaseFlow):
    def __init__(self):
        super().__init__("L2", "Ngoại ngữ khác → Tiếng Việt")
        self.transcriber = GroqTurboTranscriber()
        self.translator = GeminiTranslator()
        self.voice_synth = VoiceSynthesizer()
        self.song_processor = SongModeProcessor()

    def run(
        self,
        audio_path: str,
        video_path: Optional[str],
        output_dir: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        source_lang = options.get("source_lang", "auto")
        is_song_mode = options.get("song_mode", False)
        target_level = int(options.get("target_level", 2))
        voice_id = options.get("voice_id", "vi_north_female_1")

        process_audio = audio_path
        if is_song_mode:
            logger.info("Song Mode kích hoạt: Tách giọng hát trước khi chép lời...")
            process_audio = self.song_processor.prepare_isolated_vocals(audio_path, output_dir)

        # Chép lời
        transcript = self.transcriber.transcribe(process_audio, language=source_lang)

        # Phiên âm nếu là bài hát tiếng Trung
        if is_song_mode:
            self.song_processor.enrich_with_romanization(transcript, lang=source_lang)

        # Dịch sang tiếng Việt
        transcript = self.translator.translate_transcript(transcript, target_lang="vi")

        results = {
            "flow": self.flow_id,
            "title": transcript.title,
            "duration": transcript.duration,
            "word_count": transcript.word_count,
            "transcript": transcript.to_dict(),
            "files": {}
        }

        # Xuất Mức 1
        txt_file = os.path.join(output_dir, "transcript.txt")
        srt_file = os.path.join(output_dir, "subtitles.srt")
        docx_file = os.path.join(output_dir, "document.docx")

        TextExporter.export(transcript, txt_file)
        SrtExporter.export(transcript, srt_file, bilingual=True, song_mode=is_song_mode)
        DocxExporter.export(transcript, docx_file)

        results["files"]["txt"] = txt_file
        results["files"]["srt"] = srt_file
        results["files"]["docx"] = docx_file

        if target_level >= 2:
            mp3_file = os.path.join(output_dir, "voice_vietnamese.mp3")
            self.voice_synth.synthesize_transcript(transcript, mp3_file, voice_id=voice_id)
            results["files"]["audio"] = mp3_file

        if target_level >= 3 and video_path and os.path.exists(video_path):
            mp4_file = os.path.join(output_dir, "video_dubbed.mp4")
            VideoMuxer.mux_dubbed_video(video_path, results["files"]["audio"], srt_file, mp4_file)
            results["files"]["video"] = mp4_file

        if target_level >= 4:
            md_file = os.path.join(output_dir, "notebooklm_summary.md")
            SummaryGenerator.generate_summary_markdown(transcript, md_file)
            results["files"]["summary_md"] = md_file

        return results
