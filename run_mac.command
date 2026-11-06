#!/bin/bash

# TAIO RemakeStudio: One-Click Mac Launcher
# Nhấp đúp (Double-click) vào file này để khởi chạy ứng dụng trên Mac

cd "$(dirname "$0")"

echo "=========================================================="
echo "    🚀 KHỞI ĐỘNG TAIO REMAKESTUDIO (LOCAL MAC)            "
echo "    'Không cần giỏi ngoại ngữ. Nghe lại bằng tiếng Việt.' "
echo "=========================================================="
echo ""

# Kiểm tra Virtual Environment
if [ -d ".venv" ]; then
    PYTHON_EXEC=".venv/bin/python"
else
    echo "[*] Đang khởi tạo môi trường ảo Python 3.11 qua uv..."
    uv venv --python 3.11 .venv
    uv pip install -r requirements.txt
    PYTHON_EXEC=".venv/bin/python"
fi

# Lấy địa chỉ IP mạng nội bộ (LAN IP)
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
PORT=${PORT:-8000}

echo "📍 Địa chỉ máy chủ trên Mac của bạn:"
echo "   👉 Trực tiếp trên Mac:  http://localhost:${PORT}"
echo "   📱 Thiết bị cùng Wi-Fi: http://${LOCAL_IP}:${PORT}"
echo ""
echo "⏳ Đang mở trình duyệt..."
(sleep 1 && open "http://localhost:${PORT}") &

echo "🟢 Máy chủ đang chạy... (Nhấn Ctrl + C để dừng)"
echo "----------------------------------------------------------"
$PYTHON_EXEC main.py
