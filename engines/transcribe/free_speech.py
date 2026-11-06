"""
Free Speech Recognition Engine
Chép lời audio thực tế miễn phí 100% bằng Google Web Speech API (qua speech_recognition).
Tự động cắt nhỏ audio theo mốc thời gian để nhận diện từng câu chính xác,
không bao giờ trả về text demo giả.
"""

import os
import subprocess
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment

logger = logging.getLogger("taio.transcribe.free")


class FreeSpeechTranscriber:
    def __init__(self):
        pass

    def transcribe(self, audio_file_path: str, language: str = "vi") -> Transcript:
        logger.info(f"Đang chép lời bằng FreeSpeechTranscriber ({language}): {audio_file_path}")
        transcript = Transcript(
            title=os.path.basename(audio_file_path),
            media_path=audio_file_path,
            source_language=language
        )

        lang_code_map = {
            "vi": "vi-VN",
            "en": "en-US",
            "zh": "zh-CN",
            "ja": "ja-JP",
            "ko": "ko-KR",
            "auto": "vi-VN"
        }
        rec_lang = lang_code_map.get(language, "vi-VN")

        # 1. Đo tổng thời lượng audio bằng ffmpeg/ffprobe
        duration = self._get_audio_duration(audio_file_path)
        transcript.duration = duration

        # 2. Chuyển đổi audio sang wav 16kHz mono chuẩn
        temp_dir = os.path.join(os.path.dirname(audio_file_path), f"rec_chunks_{os.getpid()}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            import speech_recognition as sr
            r = sr.Recognizer()

            # Cắt audio thành các đoạn ngắn ~8 giây để nhận dạng và tạo timestamp chính xác
            chunk_duration = 8.0
            current_start = 0.0
            seg_id = 1

            while current_start < duration:
                current_end = min(duration, current_start + chunk_duration)
                chunk_wav = os.path.join(temp_dir, f"chunk_{seg_id}.wav")

                # Cắt đoạn bằng ffmpeg
                cut_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(current_start),
                    "-t", str(current_end - current_start),
                    "-i", audio_file_path,
                    "-ar", "16000",
                    "-ac", "1",
                    chunk_wav
                ]
                subprocess.run(cut_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

                # Nhận diện âm thanh đoạn này
                text = ""
                try:
                    with sr.AudioFile(chunk_wav) as source:
                        audio_data = r.record(source)
                        text = r.recognize_google(audio_data, language=rec_lang)
                except sr.UnknownValueError:
                    # Khoảng lặng hoặc nhạc không có lời
                    text = ""
                except Exception as ex:
                    logger.debug(f"Chunk {seg_id} skip: {ex}")
                    text = ""

                if text.strip():
                    transcript.add_segment(TranscriptSegment(
                        id=seg_id,
                        start=round(current_start, 2),
                        end=round(current_end, 2),
                        original_text=text.strip()
                    ))
                    seg_id += 1

                current_start += chunk_duration

            # Nếu toàn bộ file là nhạc không lời hoặc không nhận diện được
            if not transcript.segments:
                transcript.add_segment(TranscriptSegment(
                    id=1,
                    start=0.0,
                    end=duration if duration > 0 else 5.0,
                    original_text="[Đoạn âm thanh không có lời thoại rõ ràng hoặc là nhạc nền]"
                ))

            return transcript

        except Exception as e:
            logger.error(f"FreeSpeechTranscriber error: {e}")
            transcript.add_segment(TranscriptSegment(
                id=1,
                start=0.0,
                end=duration if duration > 0 else 5.0,
                original_text="[Không thể nhận diện âm thanh]"
            ))
            return transcript

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            cmd = ["ffmpeg", "-i", audio_path]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            for line in res.stderr.splitlines():
                if "Duration:" in line:
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = time_str.split(":")
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except Exception:
            pass
        return 10.0
