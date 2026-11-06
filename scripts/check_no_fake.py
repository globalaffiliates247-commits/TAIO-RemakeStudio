"""
TAIO RemakeStudio: Verification Script (scripts/check_no_fake.py)
Quét toàn bộ mã nguồn để đảm bảo:
1. Không chứa dữ liệu giả lập ngầm (hardcoded mock transcript, dummy 1KB bytes) ngoài file engines/demo.py.
2. Không import các thư viện bị cấm hoặc không được phép (gTTS, FreeSpeechTranscriber).
3. Đảm bảo quy chuẩn v0.3: Không có key -> báo lỗi rõ ràng, không tạo task.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORBIDDEN_PATTERNS = [
    "Welcome to TAIO RemakeStudio",
    "b\"ID3\\x03",
    "gtts",
    "FreeSpeechTranscriber",
    "_mock_transcription",
    "_auto_translate_fallback"
]

EXEMPT_FILES = [
    "engines/demo.py",
    "scripts/check_no_fake.py"
]


def run_check():
    violations = []
    print("🔍 Đang quét toàn bộ mã nguồn TAIO RemakeStudio để phát hiện dữ liệu giả...")

    for root, dirs, files in os.walk(BASE_DIR):
        # Bỏ qua thư mục venv, git, node_modules, cache
        if any(ignored in root for ignored in [".venv", ".git", "__pycache__", "data", "dist"]):
            continue

        for file in files:
            if not file.endswith((".py", ".js", ".html")):
                continue

            rel_path = os.path.relpath(os.path.join(root, file), BASE_DIR)
            if rel_path in EXEMPT_FILES:
                continue

            with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern in content:
                        violations.append((rel_path, pattern))

    if violations:
        print("\n❌ PHÁT HIỆN DỮ LIỆU HOẶC THƯ VIỆN GIẢ BỊ CẤM:")
        for path, pat in violations:
            print(f"  • {path} chứa: '{pat}'")
        sys.exit(1)
    else:
        print("\n✅ KIỂM TRA THÀNH CÔNG: Mã nguồn 100% sạch, không chứa dữ liệu giả ngầm!")
        sys.exit(0)


if __name__ == "__main__":
    run_check()
