"""
Mức 2: Giọng đọc (Audio MP3)
Đọc bản dịch tiếng Việt theo giọng vùng miền đã chọn (Bắc / Trung / Nam).
Tự động tính toán và điều chỉnh tốc độ đọc (speed adjustment) của từng đoạn
để thời lượng phát âm khớp chuẩn xác với thời lượng gốc của video.
"""

import os
import shutil
import subprocess
import logging
from typing import Optional
from engines.models import Transcript

logger = logging.getLogger("taio.outputs.level2_voice")


class VoiceSynthesizer:
    def __init__(self, tts_engine=None):
        if tts_engine is None:
            from engines.registry import TTSRouter
            self.tts_engine = TTSRouter()
        else:
            self.tts_engine = tts_engine

    def synthesize_transcript(
        self,
        transcript: Transcript,
        output_audio_path: str,
        voice_id: str = "vi_north_female_1"
    ) -> str:
        """
        Duyệt qua các segment, tổng hợp TTS cho từng đoạn, chỉnh tốc độ và ghép lại thành file MP3 hoàn chỉnh.
        """
        os.makedirs(os.path.dirname(output_audio_path), exist_ok=True)
        temp_dir = os.path.join(os.path.dirname(output_audio_path), f"tts_chunks_{os.getpid()}")
        os.makedirs(temp_dir, exist_ok=True)

        segment_audio_files = []

        try:
            for seg in transcript.segments:
                text_to_read = seg.translated_text or seg.original_text
                if not text_to_read.strip():
                    continue

                seg_raw_path = os.path.join(temp_dir, f"seg_{seg.id}.mp3")

                # Dự đoán tốc độ: tiếng Việt trung bình ~3.5 âm tiết/giây
                estimated_syllables = len(text_to_read.split())
                target_duration = max(1.0, seg.duration)
                natural_duration = estimated_syllables / 3.5

                speed_ratio = 1.0
                if natural_duration > target_duration:
                    speed_ratio = min(1.6, natural_duration / target_duration)
                elif natural_duration < target_duration * 0.7:
                    speed_ratio = max(0.85, natural_duration / target_duration)

                # Tổng hợp âm thanh đoạn này qua TTSRouter
                try:
                    self.tts_engine.synthesize(text_to_read, seg_raw_path, voice_id=voice_id, speed_multiplier=speed_ratio)
                except TypeError:
                    self.tts_engine.synthesize(text_to_read, seg_raw_path, speed_multiplier=speed_ratio)
                seg.audio_path = seg_raw_path
                segment_audio_files.append(seg_raw_path)

            # Ghép tất cả các đoạn lại thành 1 file MP3
            if segment_audio_files:
                self._concat_audio_files(segment_audio_files, output_audio_path)
            else:
                with open(output_audio_path, "wb") as f:
                    f.write(b"EMPTY_AUDIO")

            return output_audio_path

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _concat_audio_files(self, file_list: list, output_path: str):
        if not file_list:
            return

        if len(file_list) == 1:
            shutil.copyfile(file_list[0], output_path)
            return

        concat_txt = output_path + ".list.txt"
        with open(concat_txt, "w") as f:
            for fpath in file_list:
                f.write(f"file '{os.path.abspath(fpath)}'\n")

        try:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_txt,
                "-c:a", "libmp3lame", "-q:a", "2",
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except Exception as e:
            logger.warning(f"ffmpeg concat audio thất bại ({e}). Ghép trực tiếp MP3 frames.")
            try:
                with open(output_path, "wb") as outfile:
                    for f in file_list:
                        with open(f, "rb") as infile:
                            outfile.write(infile.read())
            except Exception:
                shutil.copyfile(file_list[0], output_path)
        finally:
            if os.path.exists(concat_txt):
                os.remove(concat_txt)
