"""
Luồng L4: Đổi giọng (Tiếng Việt ➔ Tiếng Việt)
Không dịch, chỉ thay giọng đọc vùng miền hoặc giọng nhân bản.
Tự động tách giọng gốc khỏi nhạc nền (Demucs) và ghép giọng mới với nhạc nền.
"""

import os
import logging
from typing import Dict, Any, Optional
from flows.base import BaseFlow
from engines.transcribe.phowhisper import PhoWhisperTranscriber
from engines.tts.vieneu import VieNeuTTSEngine
from engines.separate.demucs import DemucsSeparator
from outputs.level1_text.txt import TextExporter
from outputs.level1_text.srt import SrtExporter
from outputs.level2_voice.voice_synth import VoiceSynthesizer
from outputs.level3_video.video_muxer import VideoMuxer

logger = logging.getLogger("taio.flows.l4")


class ViRevoiceFlow(BaseFlow):
    def __init__(self):
        super().__init__("L4", "Đổi giọng: Tiếng Việt → Tiếng Việt")
        self.transcriber = PhoWhisperTranscriber()
        self.tts = VieNeuTTSEngine()
        self.voice_synth = VoiceSynthesizer(tts_engine=self.tts)
        self.demucs = DemucsSeparator()

    def run(
        self,
        audio_path: str,
        video_path: Optional[str],
        output_dir: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        target_level = int(options.get("target_level", 2))
        voice_id = options.get("voice_id", "vi_south_female_1")
        user_voice_sample = options.get("user_voice_sample")  # File thu âm của chính người dùng

        logger.info(f"Khởi chạy Luồng L4: Đổi giọng tiếng Việt ({voice_id})...")

        # 1. Chép lời tiếng Việt
        transcript = self.transcriber.transcribe(audio_path, language="vi")

        # Không dịch: translated_text = original_text
        for seg in transcript.segments:
            seg.translated_text = seg.original_text

        results = {
            "flow": self.flow_id,
            "title": transcript.title,
            "duration": transcript.duration,
            "word_count": transcript.word_count,
            "transcript": transcript.to_dict(),
            "files": {}
        }

        # Mức 1: Xuất phụ đề & chữ
        txt_file = os.path.join(output_dir, "transcript_vi.txt")
        srt_file = os.path.join(output_dir, "subtitles_vi.srt")
        TextExporter.export(transcript, txt_file)
        SrtExporter.export(transcript, srt_file, bilingual=False)
        results["files"]["txt"] = txt_file
        results["files"]["srt"] = srt_file

        # Mức 2: Đọc lại bằng giọng mới khớp thời lượng
        if target_level >= 2:
            mp3_file = os.path.join(output_dir, "revoiced_vietnamese.mp3")
            self.voice_synth.synthesize_transcript(transcript, mp3_file, voice_id=voice_id)
            results["files"]["audio"] = mp3_file

        # Mức 3: Tách nhạc nền & Ghép video mới
        if target_level >= 3 and video_path and os.path.exists(video_path):
            stems_dir = os.path.join(output_dir, "bgm_stems")
            stems = self.demucs.separate(audio_path, stems_dir)
            bgm_path = stems.get("other")  # hoặc minus-vocals

            mp4_file = os.path.join(output_dir, "video_revoiced.mp4")
            VideoMuxer.mux_dubbed_video(
                video_path,
                results["files"]["audio"],
                srt_file,
                mp4_file,
                background_music_path=bgm_path
            )
            results["files"]["video"] = mp4_file

        return results
