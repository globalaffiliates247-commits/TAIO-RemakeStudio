"""
TAIO RemakeStudio: Task State & Progressive Extension Manager
Theo Mục 4 & Mục 5.4:
- Quản lý trạng thái thực thi task theo từng bước thật (Download -> Transcribe -> Translate -> Voice).
- Lưu và tải transcript.json của từng task để mở rộng Mức 2-4 (POST /api/task/{id}/extend) mà KHÔNG chép lời lại.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List

from engines.models import Transcript
from outputs.level2_voice.voice_synth import VoiceSynthesizer
from outputs.level3_video.video_muxer import VideoMuxer
from outputs.level4_summary.summary_gen import SummaryGenerator

logger = logging.getLogger("taio.tasks")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")

# Bộ nhớ tạm task trong RAM
_TASKS: Dict[str, Dict[str, Any]] = {}


class TaskManager:
    @staticmethod
    def create_task(task_id: str, input_target: str, intent: str) -> Dict[str, Any]:
        task_info = {
            "id": task_id,
            "status": "queued",
            "intent": intent,
            "input": input_target,
            "current_step": "Khởi tạo",
            "steps": [
                {"name": "Tải & chuẩn bị media", "status": "pending", "engine": "yt-dlp", "duration": 0.0},
                {"name": "Chép lời phát hiện ngôn ngữ", "status": "pending", "engine": "Groq Whisper", "duration": 0.0},
                {"name": "Dịch thuật ngữ cảnh", "status": "pending", "engine": "Gemini Flash", "duration": 0.0},
                {"name": "Tổng hợp Mức 1 (Chữ & SRT)", "status": "pending", "engine": "TextExporter", "duration": 0.0}
            ],
            "detected_language": "unknown",
            "flow": "",
            "level": 1,
            "files": [],
            "error": None,
            "created_at": time.time()
        }
        _TASKS[task_id] = task_info
        return task_info

    @staticmethod
    def get_task(task_id: str) -> Optional[Dict[str, Any]]:
        return _TASKS.get(task_id)

    @staticmethod
    def update_step(task_id: str, step_index: int, status: str, engine: str = "", error: str = ""):
        task = _TASKS.get(task_id)
        if task and 0 <= step_index < len(task["steps"]):
            step = task["steps"][step_index]
            step["status"] = status
            if engine:
                step["engine"] = engine
            if error:
                step["error"] = error

    @staticmethod
    def save_transcript(task_id: str, transcript: Transcript) -> str:
        task_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        t_path = os.path.join(task_dir, "transcript.json")
        with open(t_path, "w", encoding="utf-8") as f:
            f.write(transcript.to_json())
        return t_path

    @staticmethod
    def load_transcript(task_id: str) -> Optional[Transcript]:
        t_path = os.path.join(OUTPUT_DIR, task_id, "transcript.json")
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Transcript.from_dict(data)
        return None

    @staticmethod
    def extend_task_level(task_id: str, target_level: int, voice_id: str = "vi_north_female_1") -> Dict[str, Any]:
        """
        Thực hiện Mức 2–4 từ transcript.json sẵn có, KHÔNG chép lời lại!
        """
        task = _TASKS.get(task_id)
        if not task:
            raise KeyError(f"Không tìm thấy nhiệm vụ {task_id}")

        transcript = TaskManager.load_transcript(task_id)
        if not transcript:
            raise FileNotFoundError(f"Chưa có transcript.json cho nhiệm vụ {task_id}")

        task_dir = os.path.join(OUTPUT_DIR, task_id)
        new_files = {}

        # Mức 2: Giọng đọc vùng miền MP3
        if target_level >= 2:
            mp3_path = os.path.join(task_dir, "voice_vietnamese.mp3")
            synth = VoiceSynthesizer()
            synth.synthesize_transcript(transcript, mp3_path, voice_id=voice_id)
            new_files["audio"] = mp3_path

        # Mức 3: Video lồng tiếng MP4
        if target_level >= 3:
            video_files = [f for f in os.listdir(task_dir) if f.endswith((".mp4", ".mov", ".mkv")) and not f.startswith("video_dubbed")]
            if video_files:
                original_video = os.path.join(task_dir, video_files[0])
                dubbed_video = os.path.join(task_dir, "video_dubbed.mp4")
                srt_path = os.path.join(task_dir, "subtitles.srt")
                mp3_path = os.path.join(task_dir, "voice_vietnamese.mp3")
                if os.path.exists(mp3_path) and os.path.exists(srt_path):
                    VideoMuxer.mux_dubbed_video(original_video, mp3_path, srt_path, dubbed_video)
                    new_files["video"] = dubbed_video

        # Mức 4: Tóm tắt chủ đề Cornell NotebookLM
        if target_level >= 4:
            summary_path = os.path.join(task_dir, "notebooklm_summary.md")
            SummaryGenerator.generate_summary_markdown(transcript, summary_path)
            new_files["summary_md"] = summary_path

        task["level"] = max(task.get("level", 1), target_level)

        # Cập nhật danh sách file có thể tải
        for fid, fpath in new_files.items():
            if os.path.exists(fpath):
                task["files"].append({
                    "id": fid,
                    "filename": os.path.basename(fpath),
                    "download_url": f"/api/download/{task_id}/{os.path.basename(fpath)}"
                })

        return task
