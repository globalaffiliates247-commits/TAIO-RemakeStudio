"""
Telegram Bot Worker for TAIO RemakeStudio
Cho phép người dùng share link TikTok/Facebook hoặc gửi voice message/video vào bot
để tự động dịch sang tiếng Việt và nhận lại file âm thanh / văn bản.
"""

import os
import telebot
import logging
from flows.manager import FlowManager

logger = logging.getLogger("taio.telegram_bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None
flow_manager = FlowManager()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Chào mừng bạn đến với **TAIO RemakeStudio**!\n\n"
        "✨ *Sứ mệnh:* 'Không cần giỏi ngoại ngữ. Nghe lại bằng tiếng Việt.'\n\n"
        "🎯 **Cách dùng siêu nhanh:**\n"
        "1. Thấy video hay trên TikTok/Facebook? Nhấn **Chia sẻ (Share)** và gửi link vào bot này.\n"
        "2. Hoặc gửi trực tiếp file ghi âm/video ngắn.\n"
        "3. Nhận lại bản dịch tiếng Việt dưới dạng phụ đề SRT, văn bản và giọng đọc vùng miền!\n\n"
        "Gõ /flows để xem danh sách các luồng dịch hỗ trợ."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


@bot.message_handler(commands=['flows'])
def list_flows(message):
    flows_text = (
        "🚀 **CÁC LUỒNG DỊCH TAIO REMAKESTUDIO:**\n\n"
        "• **L1 (Mặc định):** Tiếng Anh ➔ Tiếng Việt (Groq Whisper Turbo + Gemini Flash)\n"
        "• **L2:** Ngoại ngữ khác (Trung, Nhật, Hàn) ➔ Tiếng Việt\n"
        "• **L3:** Tiếng Việt ➔ Nhiều ngôn ngữ (Super Admin)\n"
        "• **L4:** Đổi giọng: Tiếng Việt ➔ Tiếng Việt (Giọng Bắc/Nam/Trung)\n"
        "• **L5:** Tách nhạc (Stems: trống, bass, karaoke)\n"
    )
    bot.reply_to(message, flows_text, parse_mode="Markdown")


@bot.message_handler(func=lambda msg: msg.text and ("http" in msg.text))
def handle_video_link(message):
    url = message.text.strip()
    chat_id = message.chat.id

    msg_status = bot.reply_to(message, "⏳ Đang nhận link, trích xuất âm thanh và tiến hành đọc lại...")

    try:
        task_output_dir = f"data/outputs/tg_{chat_id}_{message.message_id}"
        os.makedirs(task_output_dir, exist_ok=True)

        result = flow_manager.process(
            input_target=url,
            flow_id="L1",
            output_dir=task_output_dir,
            options={"target_level": 2, "voice_id": "vi_north_female_1"}
        )

        files = result.get("files", {})

        # Gửi file Audio lồng tiếng
        if "audio" in files and os.path.exists(files["audio"]):
            with open(files["audio"], "rb") as audio:
                bot.send_audio(chat_id, audio, caption="🎧 Bản đọc tiếng Việt (Mức 2)")

        # Gửi file phụ đề SRT
        if "srt" in files and os.path.exists(files["srt"]):
            with open(files["srt"], "rb") as srt:
                bot.send_document(chat_id, srt, caption="📝 Phụ đề song ngữ SRT (Mức 1)")

        bot.delete_message(chat_id, msg_status.message_id)

    except Exception as e:
        logger.error(f"Telegram processing error: {e}")
        bot.edit_message_text(f"❌ Xử lý thất bại: {str(e)}", chat_id, msg_status.message_id)


def start_bot():
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN chưa được cung cấp. Bỏ qua chạy Telegram bot.")
        return
    logger.info("Khởi động Telegram Bot Worker...")
    bot.infinity_polling()


if __name__ == "__main__":
    start_bot()
