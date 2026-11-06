"""
TAIO RemakeStudio: Main Application Entrypoint
Khởi chạy Web App và Telegram Bot Worker song song (Tối ưu cho Render Cloud).
"""

import os
import sys
import threading
import logging
import uvicorn

# Đảm bảo các binary trong .venv/bin (ffmpeg, yt-dlp) và brew luôn được ưu tiên
project_root = os.path.dirname(os.path.abspath(__file__))
venv_bin = os.path.join(project_root, ".venv", "bin")
os.environ["PATH"] = f"{venv_bin}:/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("taio.main")


def start_telegram_worker():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        try:
            logger.info("Đang khởi động Telegram Bot Worker song song...")
            from channels.telegram_bot.bot import start_bot
            start_bot()
        except Exception as e:
            logger.error(f"Lỗi khởi động Telegram Bot: {e}")
    else:
        logger.info("Chưa có TELEGRAM_BOT_TOKEN, bỏ qua Telegram worker.")


def main():
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"

    # In bảng kiểm tra tính sẵn sàng khi khởi động (Mục 3)
    try:
        from channels.web.readiness import print_readiness_terminal
        print_readiness_terminal()
    except Exception as e:
        logger.warning(f"Không thể in bảng sẵn sàng: {e}")

    # Chạy Telegram Bot trong một daemon thread
    tg_thread = threading.Thread(target=start_telegram_worker, daemon=True)
    tg_thread.start()

    logger.info(f"🚀 TAIO RemakeStudio đang lắng nghe tại http://{host}:{port}")
    uvicorn.run("channels.web.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
