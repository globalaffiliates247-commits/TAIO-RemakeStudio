"""
Luồng L3: Tiếng Việt ➔ Nhiều ngôn ngữ quốc tế (Chỉ dành cho Super Admin)
Chép lời PhoWhisper ➔ Dịch Gemini Flash ➔ Lồng tiếng quốc tế OmniVoice
"""

import os
import logging
from typing import Dict, Any, Optional
from flows.base import BaseFlow
from engines.transcribe.phowhisper import PhoWhisperTranscriber
from engines.translate.gemini import GeminiTranslator
from engines.tts.omnivoice import OmniVoiceEngine
from outputs.level1_text.txt import TextExporter
from outputs.level1_text.srt import SrtExporter
from outputs.level1_text.docx_export import DocxExporter
from outputs.level2_voice.voice_synth import VoiceSynthesizer
from outputs.level3_video.video_muxer import VideoMuxer

logger = logging.getLogger("taio.flows.l3")


class ViToMultiFlow(BaseFlow):
    def __init__(self):
        super().__init__("L3", "Tiếng Việt → Nhiều ngôn ngữ")
        self.transcriber = PhoWhisperTranscriber()
        self.translator = GeminiTranslator()
        self.omnivoice = OmniVoiceEngine()
        self.voice_synth = VoiceSynthesizer(tts_engine=self.omnivoice)

    def run(
        self,
        audio_path: str,
        video_path: Optional[str],
        output_dir: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        target_lang = options.get("target_lang", "en")
        target_level = int(options.get("target_level", 2))

        logger.info(f"Khởi chạy Luồng L3: Xuất khẩu nội dung tiếng Việt sang {target_lang}...")

        # 1. Chép lời tiếng Việt
        transcript = self.transcriber.transcribe(audio_path, language="vi")

        # 2. Dịch sang ngôn ngữ đích
        transcript = self.translator.translate_transcript(transcript, target_lang=target_lang)

        results = {
            "flow": self.flow_id,
            "title": transcript.title,
            "duration": transcript.duration,
            "word_count": transcript.word_count,
            "transcript": transcript.to_dict(),
            "files": {}
        }

        # Mức 1
        txt_file = os.path.join(output_dir, f"transcript_{target_lang}.txt")
        srt_file = os.path.join(output_dir, f"subtitles_{target_lang}.srt")
        docx_file = os.path.join(output_dir, f"document_{target_lang}.docx")

        TextExporter.export(transcript, txt_file)
        SrtExporter.export(transcript, srt_file, bilingual=True)
        DocxExporter.export(transcript, docx_file)

        results["files"]["txt"] = txt_file
        results["files"]["srt"] = srt_file
        results["files"]["docx"] = docx_file

        # Mức 2
        if target_level >= 2:
            mp3_file = os.path.join(output_dir, f"voice_{target_lang}.mp3")
            self.voice_synth.synthesize_transcript(transcript, mp3_file)
            results["files"]["audio"] = mp3_file

        # Mức 3
        if target_level >= 3 and video_path and os.path.exists(video_path):
            mp4_file = os.path.join(output_dir, f"video_dubbed_{target_lang}.mp4")
            VideoMuxer.mux_dubbed_video(video_path, results["files"]["audio"], srt_file, mp4_file)
            results["files"]["video"] = mp4_file

        return results
