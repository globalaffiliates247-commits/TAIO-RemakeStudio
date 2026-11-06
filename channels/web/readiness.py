"""
TAIO RemakeStudio: System Readiness Checker
Theo Mục 3:
- GET /api/readiness: Trả về trạng thái từng bước (tải, chép lời, dịch, giọng, tách nhạc).
- In bảng sẵn sàng ra terminal khi khởi động main.py.
- Xác định ý định nào có thể chạy được, ý định nào bị mờ kèm lý do và cách bật.
"""

import os
import shutil
from typing import Dict, Any, List
from engines.registry import ENGINES
from engines.profile import DeployProfile


def get_system_readiness() -> Dict[str, Any]:
    profile = DeployProfile()
    demo_mode = os.getenv("DEMO_MODE", "0").strip() in ["1", "true", "True"]

    categories = {
        "source": {"name": "Tải video (yt-dlp + ffmpeg)", "engines": ["yt_dlp"]},
        "transcribe": {"name": "Chép lời (Speech-to-Text)", "engines": profile.transcribe_chain},
        "translate": {"name": "Dịch thuật (Translation)", "engines": profile.translate_chain},
        "tts": {"name": "Giọng đọc (TTS)", "engines": profile.tts_chain},
        "separate": {"name": "Tách nhạc (Demucs)", "engines": profile.separator_chain}
    }

    readiness_data = {}
    missing_all_keys = []

    for cat_key, cat_info in categories.items():
        engine_statuses = []
        any_ready = False

        if cat_key == "source":
            # Kiểm tra yt-dlp & ffmpeg
            has_ffmpeg = bool(shutil.which("ffmpeg"))
            has_ytdlp = False
            try:
                import yt_dlp
                has_ytdlp = True
            except ImportError:
                pass

            is_ready = has_ffmpeg and has_ytdlp
            engine_statuses.append({
                "id": "yt_dlp_ffmpeg",
                "name": "yt-dlp & ffmpeg",
                "ready": is_ready,
                "message": "Sẵn sàng" if is_ready else "Thiếu ffmpeg hoặc yt-dlp"
            })
            any_ready = is_ready

        else:
            for eng_id in cat_info["engines"]:
                if eng_id in ENGINES:
                    meta = ENGINES[eng_id]
                    ready, msg = meta.check_readiness()
                    engine_statuses.append({
                        "id": eng_id,
                        "name": meta.name,
                        "ready": ready,
                        "message": msg
                    })
                    if ready:
                        any_ready = True
                    else:
                        for env in meta.required_env:
                            if env not in missing_all_keys and (not os.getenv(env) or len(os.getenv(env).strip()) < 8 or "your_" in os.getenv(env)):
                                missing_all_keys.append(env)

        readiness_data[cat_key] = {
            "name": cat_info["name"],
            "ready": any_ready or demo_mode,
            "demo": demo_mode,
            "engines": engine_statuses
        }

    # Đánh giá tính khả dụng của từng Ý Định (Intents)
    can_transcribe = readiness_data["transcribe"]["ready"]
    can_translate = readiness_data["translate"]["ready"]
    can_tts = readiness_data["tts"]["ready"]
    can_separate = readiness_data["separate"]["ready"]

    intent_readiness = {
        "listen_vi": {
            "enabled": can_transcribe and can_translate and can_tts,
            "reason": "" if (can_transcribe and can_translate and can_tts) else _build_intent_reason(can_transcribe, can_translate, can_tts)
        },
        "revoice": {
            "enabled": can_transcribe and can_tts,
            "reason": "" if (can_transcribe and can_tts) else _build_revoice_reason(can_transcribe, can_tts)
        },
        "music_stems": {
            "enabled": can_separate,
            "reason": "" if can_separate else "Cần cài đặt thư viện 'demucs' và 'torch' để tách nhạc."
        },
        "translate_intl": {
            "enabled": can_transcribe and can_translate,
            "reason": "" if (can_transcribe and can_translate) else "Cần GROQ_API_KEY và GEMINI_API_KEY để dịch ra quốc tế."
        }
    }

    return {
        "status": "healthy" if (can_transcribe and can_translate and can_tts) else "degraded",
        "deploy_profile": profile.profile_name,
        "demo_mode": demo_mode,
        "missing_env": missing_all_keys,
        "steps": readiness_data,
        "intents": intent_readiness
    }


def _build_intent_reason(transcribe: bool, translate: bool, tts: bool) -> str:
    reasons = []
    if not transcribe:
        reasons.append("Cần GROQ_API_KEY để chép lời")
    if not translate:
        reasons.append("Cần GEMINI_API_KEY để dịch thuật")
    if not tts:
        reasons.append("Cần công cụ TTS")
    return ". ".join(reasons) + ". Thêm vào file .env rồi khởi động lại."


def _build_revoice_reason(transcribe: bool, tts: bool) -> str:
    reasons = []
    if not transcribe:
        reasons.append("Cần GROQ_API_KEY để chép lời")
    if not tts:
        reasons.append("Cần công cụ TTS")
    return ". ".join(reasons) + ". Thêm vào file .env rồi khởi động lại."


def print_readiness_terminal():
    data = get_system_readiness()
    print("\n" + "=" * 65)
    print("📊 BẢNG TÌNH TRẠNG HỆ THỐNG KHI KHỞI ĐỘNG (SYSTEM READINESS)")
    print(f"🌍 Hồ sơ triển khai: {data['deploy_profile'].upper()} | Demo Mode: {'BẬT (DEMO_MODE=1)' if data['demo_mode'] else 'TẮT (Chế độ thật)'}")
    print("-" * 65)
    print(f"{'BƯỚC XỬ LÝ':<25} | {'TRẠNG THÁI':<12} | {'ENGINE SẴN SÀNG / THIẾU'}")
    print("-" * 65)

    for cat_id, step in data["steps"].items():
        status_icon = "✅ SẴN SÀNG" if step["ready"] else "⚠️ THIẾU KEY"
        eng_summary = []
        for eng in step["engines"]:
            mark = "✓" if eng["ready"] else "✗"
            eng_summary.append(f"{mark} {eng['name']}")
        print(f"{step['name']:<25} | {status_icon:<12} | {', '.join(eng_summary)}")

    print("-" * 65)
    if data["missing_env"]:
        print(f"⚠️  Biến môi trường cần cấu hình trong .env: {', '.join(data['missing_env'])}")
        print("💡 Hướng dẫn: Mở file .env và điền các khóa API để mở khóa toàn bộ tính năng.")
    else:
        print("🎉 Toàn bộ công cụ và API keys đã sẵn sàng 100%!")
    print("=" * 65 + "\n")
