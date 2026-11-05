#!/bin/bash
# TAIO RemakeStudio: Script kích hoạt Render Deploy Webhook
# Thay thế HOOK_URL bằng Deploy Hook từ Render Web Service Settings

HOOK_URL="${RENDER_DEPLOY_HOOK:-}"

if [ -z "$HOOK_URL" ]; then
    echo "⚠️ Chưa tìm thấy RENDER_DEPLOY_HOOK trong biến môi trường."
    echo "👉 Vui lòng cấu hình RENDER_DEPLOY_HOOK trong file .env hoặc Render Dashboard."
    exit 1
fi

echo "🚀 Đang kích hoạt Render Space Auto-Deploy..."
curl -X POST "$HOOK_URL"
echo ""
echo "✅ Đã gửi tín hiệu deploy thành công lên Render!"
