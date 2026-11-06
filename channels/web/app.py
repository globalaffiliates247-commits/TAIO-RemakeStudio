"""
TAIO RemakeStudio: Web API Server (v0.3)
Theo Mục 6:
- GET /health
- GET /api/readiness
- GET /api/config
- POST /api/probe
- POST /api/process
- GET /api/task/{id}
- POST /api/task/{id}/extend
- GET /api/download/{task_id}/{file_id}
- GET /api/voices/{voice_id}/sample
"""

import os
import shutil
import uuid
import yaml
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from channels.web.readiness import get_system_readiness
from channels.web.intents import IntentResolver
from channels.web.tasks import TaskManager
from sources.probe import probe_media
from engines.registry import TranscribeChain, TranslateChain, TTSRouter, SeparatorChain, ENGINES
from engines.models import Transcript
from engines.errors import RemakeStudioError, EngineUnavailable, SourceFetchError
from outputs.level1_text.txt import TextExporter
from outputs.level1_text.srt import SrtExporter
from outputs.level1_text.docx_export import DocxExporter
from storage.quota import QuotaTracker
from storage.retention import RetentionManager

logger = logging.getLogger("taio.web.app")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "voice_samples")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="TAIO RemakeStudio",
    description="Hệ thống đọc lại, dịch lại và lồng tiếng video đa định dạng",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

intent_resolver = IntentResolver()
quota_tracker = QuotaTracker()


# ==========================================
# CUSTOM EXCEPTION HANDLER
# ==========================================
@app.exception_handler(RemakeStudioError)
async def remake_studio_error_handler(request: Request, exc: RemakeStudioError):
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )


# ==========================================
# 1. GIAO DIỆN & HEALTH CHECK
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>TAIO RemakeStudio v0.3 is Running</h1>"


@app.get("/health")
async def health_check():
    readiness = get_system_readiness()
    return {
        "status": readiness["status"],
        "deploy_profile": readiness["deploy_profile"],
        "demo_mode": readiness["demo_mode"],
        "missing_env": readiness["missing_env"]
    }


# ==========================================
# 2. READINESS & CONFIG
# ==========================================
@app.get("/api/readiness")
async def api_readiness():
    return get_system_readiness()


@app.get("/api/config")
async def api_config():
    readiness = get_system_readiness()
    voices_file = os.path.join(BASE_DIR, "config", "voices.yaml")
    intents_file = os.path.join(BASE_DIR, "config", "intents.yaml")

    all_voices = {}
    if os.path.exists(voices_file):
        with open(voices_file, "r", encoding="utf-8") as f:
            all_voices = yaml.safe_load(f).get("voices", {})

    all_intents = {}
    if os.path.exists(intents_file):
        with open(intents_file, "r", encoding="utf-8") as f:
            all_intents = yaml.safe_load(f).get("intents", {})

    # Gắn trạng thái khả dụng cho từng intent và voice
    intents_payload = []
    for i_id, i_val in all_intents.items():
        st = readiness["intents"].get(i_id, {"enabled": True, "reason": ""})
        i_val["enabled"] = st["enabled"]
        i_val["disabled_reason"] = st["reason"]
        intents_payload.append(i_val)

    voices_payload = []
    for v_id, v_val in all_voices.items():
        v_eng = v_val.get("engine", "edge_tts")
        meta = ENGINES.get(v_eng)
        is_ready = True
        msg = ""
        if meta:
            is_ready, msg = meta.check_readiness()
        v_val["enabled"] = is_ready
        v_val["disabled_reason"] = msg if not is_ready else ""
        voices_payload.append(v_val)

    return {
        "intents": intents_payload,
        "voices": voices_payload,
        "deploy_profile": readiness["deploy_profile"],
        "demo_mode": readiness["demo_mode"],
        "missing_env": readiness["missing_env"]
    }


# ==========================================
# 3. PROBE (XEM TRƯỚC VIDEO BƯỚC 1)
# ==========================================
@app.post("/api/probe")
async def probe_endpoint(
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    try:
        input_id = str(uuid.uuid4())[:8]
        saved_file = None

        if file and file.filename:
            file_ext = os.path.splitext(file.filename)[1]
            dest = os.path.join(UPLOAD_DIR, f"{input_id}_{file.filename}")
            with open(dest, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_file = dest

        info = probe_media(url=url, file_path=saved_file)
        info["input_id"] = input_id
        if saved_file:
            info["saved_file"] = saved_file
        return info

    except RemakeStudioError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e), "action": "upload"})


# ==========================================
# 4. PROCESS PIPELINE (BƯỚC 2 THEO Ý ĐỊNH)
# ==========================================
def execute_intent_task(task_id: str, input_target: str, intent: str, options: dict):
    task_dir = os.path.join(OUTPUT_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    try:
        # Bước 1: Tải & trích xuất audio
        TaskManager.update_step(task_id, 0, "running", engine="yt-dlp")
        from sources.upload_file import UploadFileSource
        from sources.tiktok import TikTokSource
        from sources.facebook import FacebookSource

        if input_target.startswith(("http://", "https://")):
            if "tiktok" in input_target:
                source = TikTokSource()
            else:
                source = FacebookSource()
        else:
            source = UploadFileSource()

        media_info = source.fetch(input_target, task_dir)
        TaskManager.update_step(task_id, 0, "completed", engine=media_info.platform)

        # Xử lý Luồng L5 (Tách nhạc) riêng biệt
        if intent == "music_stems":
            TaskManager.update_step(task_id, 1, "skipped", engine="demucs")
            TaskManager.update_step(task_id, 2, "skipped", engine="demucs")
            TaskManager.update_step(task_id, 3, "running", engine="demucs")

            sep_chain = SeparatorChain()
            stems = sep_chain.separate(media_info.audio_path, task_dir)

            task = TaskManager.get_task(task_id)
            task["status"] = "completed"
            task["current_step"] = "Hoàn tất tách nhạc!"
            task["files"] = [
                {"id": sname, "label": sname.upper(), "kind": "audio", "download_url": f"/api/download/{task_id}/{os.path.basename(path)}"}
                for sname, path in stems.items() if os.path.exists(path)
            ]
            TaskManager.update_step(task_id, 3, "completed", engine="demucs")
            return

        # Bước 2: Chép lời & Tự động phát hiện ngôn ngữ
        TaskManager.update_step(task_id, 1, "running", engine="Groq Whisper")
        transcribe_chain = TranscribeChain()
        transcript, used_trans_engine = transcribe_chain.transcribe(media_info.audio_path, language="auto")
        TaskManager.update_step(task_id, 1, "completed", engine=used_trans_engine)

        detected_lang = transcript.source_language or "en"
        flow_id, flow_opts = intent_resolver.resolve_flow(intent, detected_language=detected_lang)

        task = TaskManager.get_task(task_id)
        task["detected_language"] = detected_lang
        task["flow"] = flow_id

        # Bước 3: Dịch thuật ngữ cảnh (nếu là L1, L2, L3)
        if flow_id in ["L1", "L2", "L3"]:
            TaskManager.update_step(task_id, 2, "running", engine="Gemini Flash")
            trans_chain = TranslateChain()
            target_lang = options.get("target_lang", "vi")
            transcript, used_translate_engine = trans_chain.translate_transcript(transcript, target_lang=target_lang)
            TaskManager.update_step(task_id, 2, "completed", engine=used_translate_engine)
        else:
            # L4: Đổi giọng (không dịch)
            for seg in transcript.segments:
                seg.translated_text = seg.original_text
            TaskManager.update_step(task_id, 2, "skipped", engine="None")

        # Bước 4: Xuất Mức 1 & Lưu transcript.json
        TaskManager.update_step(task_id, 3, "running", engine="TextExporter")
        TaskManager.save_transcript(task_id, transcript)

        txt_file = os.path.join(task_dir, "transcript.txt")
        srt_file = os.path.join(task_dir, "subtitles.srt")
        docx_file = os.path.join(task_dir, "document.docx")

        TextExporter.export(transcript, txt_file)
        SrtExporter.export(transcript, srt_file, bilingual=True)
        DocxExporter.export(transcript, docx_file)

        task["status"] = "completed"
        task["current_step"] = "Hoàn tất Mức 1 (Sẵn sàng mở rộng Mức 2–4)"
        task["transcript"] = transcript.to_dict()
        task["files"] = [
            {"id": "srt", "label": "Phụ đề SRT", "kind": "subtitles", "download_url": f"/api/download/{task_id}/subtitles.srt"},
            {"id": "txt", "label": "Văn bản TXT", "kind": "text", "download_url": f"/api/download/{task_id}/transcript.txt"},
            {"id": "docx", "label": "Tài liệu Word", "kind": "docx", "download_url": f"/api/download/{task_id}/document.docx"}
        ]
        TaskManager.update_step(task_id, 3, "completed", engine="TextExporter")

    except RemakeStudioError as e:
        task = TaskManager.get_task(task_id)
        task["status"] = "failed"
        task["error"] = e.to_dict()
    except Exception as e:
        task = TaskManager.get_task(task_id)
        task["status"] = "failed"
        task["error"] = {"error": str(e), "action": "retry"}


@app.post("/api/process")
async def start_process(
    background_tasks: BackgroundTasks,
    input_id: Optional[str] = Form(None),
    video_url: Optional[str] = Form(None),
    intent: str = Form("listen_vi"),
    voice_id: Optional[str] = Form("vi_north_female_1"),
    target_lang: Optional[str] = Form("vi"),
    song_mode: bool = Form(False)
):
    # Kiểm tra tính sẵn sàng trước khi cho phép tạo task (Theo Mục 3)
    readiness = get_system_readiness()
    intent_state = readiness["intents"].get(intent, {})
    if not intent_state.get("enabled", True):
        raise HTTPException(
            status_code=400,
            detail={"error": intent_state.get("reason", "Tính năng này chưa sẵn sàng."), "action": "setup"}
        )

    # Xác định đường dẫn input
    target = video_url
    if not target and input_id:
        # Tìm file upload
        matches = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if f.startswith(input_id)]
        if matches:
            target = matches[0]

    if not target:
        raise HTTPException(status_code=400, detail={"error": "Vui lòng nhập link video hoặc tải file lên.", "action": "upload"})

    task_id = str(uuid.uuid4())[:8]
    TaskManager.create_task(task_id, target, intent)

    options = {
        "voice_id": voice_id,
        "target_lang": target_lang,
        "song_mode": song_mode
    }

    background_tasks.add_task(execute_intent_task, task_id, target, intent, options)
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "Không tìm thấy nhiệm vụ.", "action": "retry"})
    return task


# ==========================================
# 5. PROGRESSIVE EXTENSION (MỨC 2–4 TỪ TRANSCRIPT)
# ==========================================
@app.post("/api/task/{task_id}/extend")
async def extend_task_endpoint(
    task_id: str,
    level: int = Form(2),
    voice_id: Optional[str] = Form("vi_north_female_1")
):
    try:
        updated_task = TaskManager.extend_task_level(task_id, target_level=level, voice_id=voice_id)
        return updated_task
    except RemakeStudioError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e), "action": "retry"})


# ==========================================
# 6. DOWNLOAD & VOICE SAMPLE
# ==========================================
@app.get("/api/download/{task_id}/{file_id}")
async def download_output_file(task_id: str, file_id: str):
    task_dir = os.path.join(OUTPUT_DIR, task_id)
    if not os.path.exists(task_dir):
        raise HTTPException(status_code=404, detail={"error": "Thư mục nhiệm vụ không tồn tại.", "action": "retry"})

    target_file = None
    for root, dirs, files in os.walk(task_dir):
        if file_id in files:
            target_file = os.path.join(root, file_id)
            break

    if not target_file or not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail={"error": f"Tệp '{file_id}' không tồn tại trên hệ thống.", "action": "retry"})

    return FileResponse(target_file, filename=file_id)


@app.get("/api/voices/{voice_id}/sample")
async def get_voice_sample(voice_id: str):
    sample_file = os.path.join(SAMPLES_DIR, f"{voice_id}.mp3")
    if not os.path.exists(sample_file):
        # Tạo câu mẫu 3 giây một lần và lưu lại
        from engines.tts.edge_tts_fallback import EdgeTTSEngine
        engine = EdgeTTSEngine()
        sample_text = "Chào bạn! Đây là giọng đọc mẫu của TAIO RemakeStudio."
        try:
            engine.synthesize(sample_text, sample_file)
        except Exception:
            raise HTTPException(status_code=503, detail={"error": "Chưa tạo được giọng đọc mẫu.", "action": "setup"})

    return FileResponse(sample_file, media_type="audio/mpeg")


@app.on_event("startup")
async def startup_event():
    RetentionManager.cleanup_expired_files(UPLOAD_DIR, max_age_days=7)
    RetentionManager.cleanup_expired_files(OUTPUT_DIR, max_age_days=7)
