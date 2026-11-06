"""
TAIO RemakeStudio: Web Application Server (FastAPI)
Cung cấp giao diện trực quan và REST API cho người dùng & Render Cloud deployment.
"""

import os
import shutil
import uuid
import yaml
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from flows.manager import FlowManager
from storage.quota import QuotaTracker
from storage.retention import RetentionManager

app = FastAPI(
    title="TAIO: RemakeStudio",
    description="Công cụ đọc lại, dịch lại và lồng tiếng video đa định dạng bằng tiếng Việt",
    version="0.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

flow_manager = FlowManager()
quota_tracker = QuotaTracker(os.path.join(BASE_DIR, "data", "user_quotas.json"))

# Task in-memory store
processing_tasks = {}


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>TAIO RemakeStudio API is Running!</h1>"


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TAIO RemakeStudio",
        "version": "0.2.0",
        "timestamp": os.path.getmtime(os.path.abspath(__file__)) if os.path.exists(__file__) else None
    }


@app.get("/api/config")
async def get_system_config():
    voices_file = os.path.join(BASE_DIR, "config", "voices.yaml")
    flows_file = os.path.join(BASE_DIR, "config", "flows.yaml")
    voices = {}
    flows = {}
    if os.path.exists(voices_file):
        with open(voices_file, "r", encoding="utf-8") as f:
            voices = yaml.safe_load(f).get("voices", {})
    if os.path.exists(flows_file):
        with open(flows_file, "r", encoding="utf-8") as f:
            flows = yaml.safe_load(f).get("flows", {})

    return {
        "voices": voices,
        "flows": flows
    }


@app.get("/api/quota/{user_id}")
async def get_user_quota(user_id: str):
    quota = quota_tracker.get_user_quota(user_id)
    return quota


def run_pipeline_task(task_id: str, input_target: str, flow_id: str, target_level: int, voice_id: str, song_mode: bool, user_id: str):
    try:
        processing_tasks[task_id]["status"] = "processing"
        processing_tasks[task_id]["progress"] = 25
        processing_tasks[task_id]["step"] = "Đang trích xuất âm thanh và tải video..."

        task_output_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)

        processing_tasks[task_id]["progress"] = 50
        processing_tasks[task_id]["step"] = "Đang chép lời và dịch ngữ cảnh tiếng Việt..."

        options = {
            "target_level": target_level,
            "voice_id": voice_id,
            "song_mode": song_mode
        }

        result = flow_manager.process(
            input_target=input_target,
            flow_id=flow_id,
            output_dir=task_output_dir,
            options=options
        )

        processing_tasks[task_id]["progress"] = 85
        processing_tasks[task_id]["step"] = "Đang tổng hợp giọng đọc và xuất các mức đầu ra..."

        # Trừ phút
        audio_dur_minutes = result.get("duration", 60.0) / 60.0
        quota_tracker.deduct_minutes(user_id, audio_dur_minutes)

        # Chuyển đổi đường dẫn file thành URL tải
        file_urls = {}
        for fkey, fpath in result.get("files", {}).items():
            if os.path.exists(fpath):
                file_urls[fkey] = f"/api/download/{task_id}/{os.path.basename(fpath)}"

        processing_tasks[task_id]["status"] = "completed"
        processing_tasks[task_id]["progress"] = 100
        processing_tasks[task_id]["step"] = "Hoàn tất xử lý!"
        processing_tasks[task_id]["result"] = result
        processing_tasks[task_id]["download_urls"] = file_urls

    except Exception as e:
        processing_tasks[task_id]["status"] = "failed"
        processing_tasks[task_id]["error"] = str(e)


@app.post("/api/process")
async def start_process(
    background_tasks: BackgroundTasks,
    video_url: Optional[str] = Form(None),
    flow_id: str = Form("L1"),
    target_level: int = Form(2),
    voice_id: str = Form("vi_north_female_1"),
    song_mode: bool = Form(False),
    user_id: str = Form("guest_user"),
    file: Optional[UploadFile] = File(None)
):
    if not video_url and not file:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp link video hoặc tải lên một file.")

    task_id = str(uuid.uuid4())[:8]

    input_target = video_url
    if file:
        file_ext = os.path.splitext(file.filename)[1]
        uploaded_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
        with open(uploaded_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        input_target = uploaded_path

    processing_tasks[task_id] = {
        "id": task_id,
        "status": "queued",
        "progress": 5,
        "step": "Đang xếp hàng chuẩn bị xử lý...",
        "input": input_target,
        "flow": flow_id
    }

    background_tasks.add_task(
        run_pipeline_task,
        task_id=task_id,
        input_target=input_target,
        flow_id=flow_id,
        target_level=target_level,
        voice_id=voice_id,
        song_mode=song_mode,
        user_id=user_id
    )

    return {"task_id": task_id, "status": "queued"}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ.")
    return processing_tasks[task_id]


@app.get("/api/download/{task_id}/{filename}")
async def download_output_file(task_id: str, filename: str):
    task_dir = os.path.join(OUTPUT_DIR, task_id)
    file_path = os.path.join(task_dir, filename)

    # Tìm kiếm đệ quy trong thư mục task nếu chưa thấy ở thư mục gốc
    if not os.path.exists(file_path):
        for root, dirs, files in os.walk(task_dir):
            if filename in files:
                file_path = os.path.join(root, filename)
                break

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Tệp không tồn tại hoặc đã hết hạn lưu trữ.")
    return FileResponse(file_path, filename=filename)


# Cron dọn dẹp file hết hạn lưu
@app.on_event("startup")
async def startup_event():
    # Quét dọn file cũ hơn 7 ngày
    RetentionManager.cleanup_expired_files(UPLOAD_DIR, max_age_days=7)
    RetentionManager.cleanup_expired_files(OUTPUT_DIR, max_age_days=7)
