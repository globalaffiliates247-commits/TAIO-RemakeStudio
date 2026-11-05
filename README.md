# TAIO: RemakeStudio (TAIO Đọc Lại – Dịch Lại)

> **Thông điệp:** *"Không cần giỏi ngoại ngữ. Nghe lại bằng tiếng Việt."*  
> **Phiên bản:** v0.2 MVP · **Tác giả:** TAIO Team · **Ngày duyệt:** 05/11/2026

Công cụ cho phép dán link video TikTok/Facebook hoặc tải file video/âm thanh lên → nhận lại **bản dịch tiếng Việt** dưới dạng chữ, giọng đọc quê hương, video lồng tiếng hoặc bản tóm tắt chủ đề chuẩn bị cho Google NotebookLM.

---

## 🌟 1. Điểm Nổi Bật & Các Luồng Dịch (Flows)

| Luồng | Hướng Dịch | Engine Chép Lời | Engine Dịch | Giọng Đọc / Xuất Bản |
| :--- | :--- | :--- | :--- | :--- |
| **L1** (Mặc định) | Tiếng Anh ➔ Tiếng Việt | Groq Whisper Large v3 Turbo (~0.04$/h) | Gemini 1.5/2.0 Flash | Giọng Bắc / Nam / Trung |
| **L2** | Ngoại ngữ khác (Trung, Nhật, Hàn...) ➔ Tiếng Việt | Groq Whisper Large v3 Turbo | Gemini Flash | Giọng Bắc / Nam + Pinyin song ngữ |
| **L3** | Tiếng Việt ➔ Nhiều ngôn ngữ quốc tế | VinAI PhoWhisper | Gemini Flash | OmniVoice (600+ ngôn ngữ quốc tế) |
| **L4** | Đổi giọng: Tiếng Việt ➔ Tiếng Việt | VinAI PhoWhisper | Không dịch (giữ nguyên lời) | Giọng vùng miền / Nhân bản giọng |
| **L5** | Tách nhạc Stems (Deliberate Practice) | Không chép lời | Không dịch | Demucs (Meta) 4 track: Trống, Bass, Vocals, Karaoke |

---

## 💎 2. Bốn Mức Đầu Ra (Tích Luỹ)

1. **Mức 1: Chữ & Phụ Đề:** Bản chép lời gốc + bản dịch có mốc thời gian (`.srt`, `.txt`, `.docx`). Hỗ trợ hiển thị song ngữ hoặc 3 dòng (Chữ Hán · Pinyin · Tiếng Việt trong Chế độ bài hát).
2. **Mức 2: Giọng Đọc (MP3):** Tự động điều chỉnh tốc độ đọc (speed adjustment) từng câu để phát âm khớp chuẩn xác với thời lượng gốc của video.
3. **Mức 3: Video Lồng Tiếng (MP4):** Ghép video gốc + phụ đề + giọng đọc mới thay thế giọng gốc (giữ nhạc nền bằng Demucs).
4. **Mức 4: Tóm Tắt Chủ Đề (Markdown / DOCX):** Tóm tắt theo phương pháp ghi chép Cornell, sẵn sàng nạp trực tiếp vào **Google NotebookLM** để nghiên cứu sâu.

---

## 🚀 3. Hướng Dẫn Triển Khai Lên Render Space (1-Click)

Dự án đã được cấu hình sẵn **`render.yaml`** (Blueprint) và **`Dockerfile`** chuẩn production.

### Cách 1: Triển khai qua Render Blueprint (Khuyên dùng)
1. Đăng nhập [Render Dashboard](https://dashboard.render.com).
2. Nhấn nút **New +** ➔ Chọn **Blueprint**.
3. Kết nối với kho lưu trữ GitHub: `https://github.com/globalaffiliates247-commits/TAIO-RemakeStudio`.
4. Render sẽ tự động đọc file `render.yaml` và cấu hình Web Service.
5. Điền các biến môi trường (Environment Variables) nếu có:
   - `GROQ_API_KEY`: Khóa API Groq Whisper (tốc độ cao).
   - `GEMINI_API_KEY`: Khóa API Google Gemini.
   - `TELEGRAM_BOT_TOKEN`: Token bot Telegram (nếu muốn kích hoạt bot).
6. Nhấn **Apply**. Web service sẽ tự động build và chạy trực tiếp!

### Cách 2: Triển khai thủ công (Web Service)
1. Chọn **New +** ➔ **Web Service** ➔ Chọn repo `TAIO-RemakeStudio`.
2. Runtime: **Docker**.
3. Region: **Singapore** (độ trễ thấp nhất về Việt Nam).
4. Instance Type: **Free** hoặc **Starter**.
5. Nhấn **Deploy**.

---

## 💻 4. Chạy Trên Máy Cá Nhân (Local Run / Cấp 2)

### Bước 1: Cài đặt thư viện
```bash
git clone https://github.com/globalaffiliates247-commits/TAIO-RemakeStudio.git
cd TAIO-RemakeStudio
pip install -r requirements.txt
```

### Bước 2: Thiết lập biến môi trường
```bash
cp .env.example .env
# Chỉnh sửa file .env và điền GROQ_API_KEY, GEMINI_API_KEY...
```

### Bước 3: Khởi chạy
- **Chạy giao diện Web & Telegram bot:**
  ```bash
  python main.py
  ```
  Truy cập giao diện tại: `http://localhost:8000`

- **Chạy dòng lệnh CLI (Cấp 2):**
  ```bash
  python channels/cli/main.py "https://www.tiktok.com/@example/video/123456" --flow L1 --level 2 --voice vi_north_female_1
  ```

---

## 🛡️ 5. Tuân Thủ & Bảo Vệ Dữ Liệu

- **Nghị định 13/2023 & Luật BV dữ liệu cá nhân 2026:** Tự động dọn dẹp các tệp tạm sau 7 ngày qua module `storage/retention.py`.
- **Bản quyền & Sáng tạo:** Super Admin chia sẻ nội dung hợp pháp, ghi nguồn rõ ràng. Không sử dụng nhân bản giọng của bên thứ ba khi chưa được sự cho phép.
- **Giấy phép mã nguồn:** Tuân thủ sao lưu LGPL / MIT / Apache-2.0 theo danh sách `tools/backup/backup_list.yaml`.
