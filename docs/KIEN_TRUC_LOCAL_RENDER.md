# TAIO.CLUB RemakeStudio: kiến trúc chạy trên Mac (không cần key) và bản Render (v0.4)

Nov 12, 2026 · TAIO-Lee · cập nhật cho macOS 13.1

> Dành cho TAIO-Lee và AI coding agent (Antigravity / Claude Code). Bổ sung cho `BUILD_SPEC.md` v0.3; mọi quy tắc ở mục 0 của BUILD_SPEC vẫn áp dụng (không dữ liệu giả, lỗi phải hiện ra, mỗi phần một file, dán kết quả kiểm thử).
> Repo: `github.com/globalaffiliates247-commits/TAIO-RemakeStudio`. Thư mục trên Mac: `/Users/abc/.gemini/antigravity/scratch/taio-remakestudio`.

---

## 1. Một codebase, hai cách chạy

```
                       ┌──────────── BẢN MAC (mac_local) ────────────┐
 Trình duyệt trên Mac ─▶ App (FastAPI) ─▶ chuỗi engine chạy trên máy  │
                       │   Whisper · Qwen3/Ollama · VieNeu · OmniVoice · Demucs
                       └──────────────────────────────────────────────┘

                       ┌──── BẢN ONLINE (render_gateway + Mac worker) ────┐
 Người dùng ─▶ Render Free: giao diện + hàng đợi + file tạm               │
                 │  ▲                                                     │
   chuông báo ───┘  │ Mac worker KÉO việc về, chạy đúng chuỗi engine      │
   (ntfy)           │ của bản Mac, rồi đẩy kết quả lên lại                │
                       └──────────────────────────────────────────────────┘
```

- **Bản Mac:** mọi engine là mã nguồn mở chạy trên máy. Không cần API key, không tốn phí, dùng được cả khi mất mạng (trừ bước tải link TikTok/Facebook).
- **Bản online:** Render Free (512 MB RAM, 0,1 CPU) không chạy nổi model nào, nên Render chỉ làm cổng. Việc nặng do chính Mac xử lý, bằng đúng code và engine của bản Mac. Mac chủ động kéo việc về, nên không phải mở cổng hay tunnel vào máy.
- Lợi ích phụ: video TikTok/Facebook được tải từ mạng nhà của Mac, ít bị chặn hơn tải từ IP trung tâm dữ liệu của Render.

---

## 2. Engine bản Mac (tất cả mã nguồn mở, không cần key)

| Bước | Engine | Giấy phép | Chạy thế nào | File trong repo |
| --- | --- | --- | --- | --- |
| Tải video | yt-dlp | Unlicense | Trong app | `sources/*` (đã có) |
| Âm thanh, video | ffmpeg | LGPL/GPL | Cài bằng Homebrew | — |
| Chép lời (chính) | Whisper large-v3-turbo qua `transformers` | MIT | Trong app, GPU tích hợp (MPS); model **đã có sẵn** trong bộ nhớ đệm | `engines/transcribe/hf_whisper_local.py` |
| Chép lời tiếng Việt (tuỳ chọn) | PhoWhisper-medium | Apache-2.0 | Cùng engine trên, bật bằng `HF_WHISPER_MODEL_VI` | như trên |
| Chép lời (nhanh hơn, tuỳ chọn) | mlx-whisper | MIT | Trong app; cần macOS 13.5+ | `engines/transcribe/mlx_whisper_local.py` |
| Dịch | Qwen3 8B (máy dưới 16 GB RAM: 4B) | Apache-2.0 (model) | **macOS 14+:** Ollama (MIT). **macOS 13 (máy TAIO-Lee đang là 13.1):** llama.cpp server qua `llama-cpp-python` (MIT), model Qwen3 bản nén Q4_K_M. Cả hai cùng chuẩn OpenAI `/v1/chat/completions`, engine không đổi | `engines/translate/openai_compat.py` |
| Giọng Việt Bắc/Trung/Nam | VieNeu-TTS v3 Turbo, 25 giọng | Apache-2.0 | Server riêng (môi trường riêng), CPU/ONNX, chuẩn OpenAI `/v1/audio/speech`, cổng 8101 | `engines/tts/openai_speech.py` |
| Giọng nước ngoài, nhân bản giọng | OmniVoice | Apache-2.0 | Trong app, MPS; model **đã có sẵn** | `engines/tts/omnivoice_local.py` |
| Tách nhạc | Demucs | MIT | Trong app | `engines/separate/demucs.py` (đã có) |
| Đổi định dạng, tốc độ | ffmpeg | | Dùng chung | `engines/tts/audio_utils.py` |

Ghi chú:
- **VoxCPM2 không dùng trên Mac:** cách chạy nhanh của nó (vLLM) chỉ có trên GPU NVIDIA; bản Mac qua llama.cpp chậm hơn thời gian thực. Giữ cho máy GPU NVIDIA sau này.
- **Edge TTS, gTTS, Google Web Speech:** không dùng (dịch vụ không chính thức).
- VieNeu bỏ qua tham số tốc độ, nên engine chỉnh tốc độ bằng ffmpeg (giữ nguyên cao độ) để khớp thời lượng câu gốc. OmniVoice nhận thẳng thời lượng mong muốn (`duration`), khớp hình tốt nhất.

### Nguyên tắc "cổng chuẩn OpenAI"
Ba loại engine dùng chung một chuẩn giao tiếp HTTP: chép lời (`/v1/audio/transcriptions`), dịch (`/v1/chat/completions`), đọc giọng (`/v1/audio/speech`). Muốn đổi từ máy Mac sang máy GPU thuê, hay sang dịch vụ trả phí (Groq, DeepSeek, OpenRouter...), **chỉ đổi biến `*_BASE_URL`**, không sửa code. Đây là cổng mở rộng cho giai đoạn scale.

---

## 3. Cài và chạy bản Mac

Bộ file đi kèm (giải nén vào thư mục repo, giữ nguyên đường dẫn):

| File | Việc |
| --- | --- |
| `engines/transcribe/hf_whisper_local.py`, `mlx_whisper_local.py` | Chép lời trên máy |
| `engines/translate/openai_compat.py` | Dịch qua Ollama hoặc mọi API chuẩn OpenAI |
| `engines/tts/openai_speech.py`, `omnivoice_local.py`, `audio_utils.py` | Giọng đọc |
| `config/deploy_profiles.add.yaml` | 3 profile mới: `mac_local`, `render_gateway`, `render_api_fallback` |
| `config/voices.mac_local.add.yaml` | 6 giọng VieNeu Bắc/Trung/Nam + giọng OmniVoice |
| `requirements-mac-local.txt`, `.env.mac_local.example` | Thư viện và cấu hình |
| `scripts/setup_mac_local.sh` | Cài một lần |
| `scripts/start_mac_local.sh` | Chạy hằng ngày (tự bật Ollama hoặc llama.cpp server, và VieNeu) |
| `scripts/make_test_fixtures.sh`, `tests/fixtures/drums_song.mp3` | Tạo clip mẫu cho kiểm thử M1 |
| `tools/backup/fork_to_github.sh` | Fork 13 repo engine về GitHub của bạn |

Các bước:
1. `bash scripts/setup_mac_local.sh` (một lần, cần mạng). Script tự cài ffmpeg, Ollama, uv; tạo `.venv`; tải Qwen3; clone VieNeu-TTS vào `../taio-engines/`; tạo `.env`.
2. `bash scripts/start_mac_local.sh`. Mở `http://localhost:8000`.

Phần agent phải nối vào code hiện có (giai đoạn M1, mục 6):
- Thêm vào `ENGINES` trong `engines/registry.py`:
  ```python
  "hf_whisper_local": EngineMetadata("Whisper trên máy", "transcribe", "engines.transcribe.hf_whisper_local.HFWhisperTranscriber", required_libs=["torch", "transformers"]),
  "mlx_whisper_local": EngineMetadata("Whisper MLX trên máy", "transcribe", "engines.transcribe.mlx_whisper_local.MLXWhisperTranscriber", required_libs=["mlx_whisper"]),
  "ollama_qwen": EngineMetadata("Qwen3 qua Ollama", "translate", "engines.translate.openai_compat.OpenAICompatTranslator", required_libs=["openai"]),
  "vieneu_server": EngineMetadata("VieNeu-TTS trên máy", "tts", "engines.tts.openai_speech.OpenAISpeechEngine", required_env=["VIENEU_BASE_URL"]),
  "omnivoice_local": EngineMetadata("OmniVoice trên máy", "tts", "engines.tts.omnivoice_local.OmniVoiceLocalEngine", required_libs=["omnivoice", "torch", "soundfile"]),
  ```
- `check_readiness` thêm kiểm tra server có phản hồi: `ollama_qwen` gọi `GET {LLM_BASE_URL}/models` và kiểm tra có `LLM_MODEL`; `vieneu_server` gọi `GET {VIENEU_BASE_URL}/voices`.
- `TTSRouter` thêm 2 nhánh:
  ```python
  elif eng_key == "vieneu_server":
      engine = OpenAISpeechEngine(voice=voice_info.get("voice_key"), env_prefix="VIENEU")
  elif eng_key == "omnivoice_local":
      engine = OmniVoiceLocalEngine(language=voice_info.get("language"), instruct=voice_info.get("omnivoice_instruct"),
                                    ref_audio=voice_info.get("omnivoice_ref_audio"), ref_text=voice_info.get("omnivoice_ref_text"))
  ```
  Với OmniVoice, truyền `duration=thời lượng câu gốc` khi làm Mức 3 để giọng khớp hình.
- Giọng không thuộc engine trong `tts_chain` của profile đang chạy thì ẩn khỏi danh sách giọng trên giao diện.

---

## 4. Bản online: Render làm cổng, Mac làm máy xử lý

### 4.1 Vai trò
| Thành phần | Chạy ở | Việc |
| --- | --- | --- |
| Gateway | Render Free, `DEPLOY_PROFILE=render_gateway` | Giao diện, nhận link/file, hàng đợi, giữ file tạm, trả kết quả |
| Worker | Mac, `bash scripts/start_mac_local.sh --worker` | Kéo việc, chạy `FlowManager` như bản Mac, báo tiến trình, đẩy file kết quả |
| Chuông báo | ntfy (mã nguồn mở; dùng máy chủ công cộng ntfy.sh hoặc tự host sau) | Gateway báo "có việc mới"; worker nghe và kéo việc ngay |

### 4.2 Vì sao cần chuông báo
Render Free ngủ sau 15 phút không có ai gọi, và chỉ có **750 giờ chạy miễn phí mỗi tháng cho cả tài khoản**, dùng chung với Cover Studio đang chạy trên Render. Nếu worker hỏi gateway liên tục ("có việc chưa?"), gateway sẽ không bao giờ ngủ và tiêu gần hết số giờ đó. Cách làm:
- Worker **không hỏi gateway khi rảnh**. Nó giữ một kết nối nghe ntfy (không tốn giờ Render).
- Có người gửi việc: gateway thức dậy, xếp hàng, gửi tin "có việc" lên ntfy (tin không chứa dữ liệu người dùng).
- Worker nhận tin, kéo việc trong vài giây, xử lý xong đẩy kết quả lên. Hết việc thì gateway được ngủ.
- Lưới an toàn: worker vẫn hỏi gateway mỗi 6 giờ một lần, phòng khi lỡ tin báo.

### 4.3 API giữa gateway và worker
Mọi lệnh gọi kèm `Authorization: Bearer <WORKER_TOKEN>` (so sánh bằng `hmac.compare_digest`; sai → 401).

| Method | Đường dẫn | Việc |
| --- | --- | --- |
| POST | `/worker/heartbeat` | `{worker_id, version, readiness}`: báo worker đang bật và engine nào sẵn sàng |
| POST | `/worker/claim` | Nhận việc kế tiếp (204 nếu không có). Việc được "giữ chỗ" 15 phút |
| GET | `/worker/jobs/{id}/input` | Tải file người dùng gửi (nếu là link thì worker tự tải bằng yt-dlp) |
| POST | `/worker/jobs/{id}/progress` | `{step, status, engine}` để giao diện hiện tiến trình theo bước |
| POST | `/worker/jobs/{id}/files` | Tải lên từng file kết quả (multipart) |
| POST | `/worker/jobs/{id}/complete` hoặc `/fail` | Kết quả cuối hoặc lỗi |

- Worker tắt giữa chừng: hết 15 phút giữ chỗ, việc tự quay về hàng đợi.
- Không có worker bật (heartbeat cũ hơn 2 phút): giao diện báo "Máy xử lý TAIO.CLUB đang nghỉ. Việc của bạn đã vào hàng chờ, số thứ tự X", không bịa kết quả.
- Gateway bật khoá web bằng `APP_PASSWORD` (Basic Auth) như Cover Studio, trừ `/health` và `/worker/*` (đã có token riêng).

### 4.4 File mới cho chế độ online
```
channels/worker/worker.py     # vòng lặp worker: nghe chuông, claim, chạy FlowManager, đẩy kết quả
channels/web/worker_api.py    # route /worker/* của gateway
storage/job_queue.py          # QueuePort: bản bộ nhớ (memory) trước
storage/file_store.py         # StoragePort: ổ đĩa tạm của Render trước
notify/doorbell.py            # gửi/nghe chuông ntfy
```
Giới hạn đã biết: ổ đĩa Render Free bị xoá khi khởi động lại, nên hàng đợi và file kết quả mất theo. Giao diện nhắc người dùng tải kết quả về ngay; giai đoạn scale đổi sang Redis/Postgres và kho file S3.

---

## 5. Cổng mở rộng cho giai đoạn scale (chưa làm)

| Cổng | Bây giờ | Khi scale (chỉ đổi cấu hình hoặc thêm 1 file) |
| --- | --- | --- |
| Máy xử lý | 1 Mac worker | Thêm Mac thứ hai, hoặc máy GPU thuê theo giờ chạy **cùng code worker** |
| Engine | Ollama, VieNeu, OmniVoice trên máy | Đổi `*_BASE_URL` sang máy GPU riêng hoặc dịch vụ trả phí |
| Hàng đợi (`QueuePort`) | Trong bộ nhớ gateway | Redis hoặc Postgres |
| Kho file (`StoragePort`) | Ổ đĩa tạm Render | Kho chuẩn S3 (ví dụ Cloudflare R2) |
| Dự phòng khi Mac tắt | Xếp hàng chờ | Profile `render_api_fallback`: Groq/Gemini/FPT bằng key |
| Đăng nhập | `APP_PASSWORD` chung | Token thành viên TAIO.CLUB |
| Chuông báo | ntfy.sh công cộng | Tự host ntfy |

---

## 6. Giai đoạn build và kiểm thử

Mỗi giai đoạn một commit; dán bảng kết quả theo mẫu ở BUILD_SPEC mục 8.3 rồi dừng chờ duyệt.

**M1. Bản Mac không cần key:** nối engine (mục 3), profile `mac_local`, script cài và chạy.
| # | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| M1.1 | `.env` không có `GROQ_API_KEY`, `GEMINI_API_KEY`; mở `/api/readiness` | Chép lời, dịch, giọng, tách nhạc đều "sẵn sàng" bằng engine trên máy |
| M1.2 | "Nghe bằng tiếng Việt" với file tiếng Anh 30 giây | Bản song ngữ đúng nội dung; log ghi `hf_whisper_local` và `qwen3` |
| M1.3 | Nghe bản đọc với 3 giọng Bắc, Trung, Nam | 3 MP3 thật (`ffprobe` > 0 giây), đúng giọng vùng miền |
| M1.4 | "Dịch ra tiếng nước ngoài" (Super Admin), sang tiếng Anh | MP3 giọng OmniVoice |
| M1.5 | "Tách nhạc để tập", bỏ trống | MP3 thật, không còn tiếng trống |
| M1.6 | Tắt Wi-Fi, chạy lại M1.2 bằng file tải lên | Vẫn ra kết quả, chứng minh chạy hoàn toàn trên máy |
| M1.7 | Tắt Ollama rồi chạy M1.2 | Task `failed`, lỗi ghi "không kết nối được Ollama", không có kết quả giả |

**M2. Chế độ worker (chạy thử gateway và worker cùng trên Mac):** file ở mục 4.4.
| # | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| W1 | Gateway `DEPLOY_PROFILE=render_gateway` cổng 9000, worker trỏ vào đó; gửi việc qua giao diện cổng 9000 | Worker nhận trong vòng 10 giây, kết quả tải được từ gateway |
| W2 | Tắt worker giữa chừng | Sau 15 phút việc quay lại hàng đợi; bật worker lại thì chạy tiếp |
| W3 | Không bật worker, gửi việc | Giao diện báo "đang nghỉ, hàng chờ số X"; không có kết quả giả |
| W4 | Gọi `/worker/claim` sai token | 401 |

**M3. Đưa gateway lên Render + chuông ntfy.**
| # | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| R1 | Gateway đang ngủ, gửi việc từ điện thoại | Mac nhận qua chuông, xử lý, kết quả tải được trên điện thoại |
| R2 | `/health` | Báo worker đang bật hay tắt, và lần heartbeat cuối |
| R3 | Để yên 30 phút không dùng | Gateway ngủ (xem Render dashboard); worker không đánh thức nó |
| R4 | Link TikTok/Facebook công khai | Worker tải bằng mạng nhà, không lỗi chặn IP |

---

## 7. Sao lưu mã nguồn và model

- **Mã nguồn:** `bash tools/backup/fork_to_github.sh` fork 13 repo engine về GitHub của bạn. Fork nằm trên GitHub nên không tốn ổ Mac, không vướng ngưỡng 15 GB. Sau khi fork, script cài có thể trỏ `VIENEU_GIT_URL` sang bản fork của bạn.
- **Model (không nằm trên GitHub):** chép `~/.cache/huggingface/hub` (Whisper turbo khoảng 1,6 GB, OmniVoice, PhoWhisper nếu bật) và `~/.ollama/models` (Qwen3 8B bản nén khoảng 5 GB) ra ổ ngoài. Không tải bản gốc đầy đủ của Qwen3-8B từ Hugging Face để sao lưu: khoảng 16 GB, vượt ngưỡng 15 GB, phải hỏi TAIO-Lee trước.

---

## 8. Điểm chưa kiểm chứng (thử trên Mac trước khi dựa vào)

- **Máy TAIO-Lee đang chạy macOS 13.1:** Ollama cần macOS 14 nên script tự chuyển sang llama.cpp server (phải biên dịch trên máy, cần Xcode Command Line Tools). mlx-whisper cần 13.5 nên bị bỏ qua. onnxruntime của VieNeu nếu không cài được trên 13.1 thì đặt `VIENEU_BACKEND=pytorch`. Nâng lên macOS 14 trở lên sẽ gỡ cả ba hạn chế này.

- VieNeu-TTS cài trên macOS bằng `uv sync` theo README của họ; bộ cài riêng cho Mac họ ghi là "sắp có".
- Giới tính của 6 giọng VieNeu trong `voices.mac_local.add.yaml` đoán theo tên: nghe thử và sửa.
- mlx-whisper cần macOS 13.5 trở lên; máy Ventura bản thấp hơn tự dùng Whisper qua `transformers`.
- Chất lượng dịch của Qwen3 8B chạy trên máy kém hơn Gemini/GPT lớn; với nội dung quan trọng, đổi `LLM_BASE_URL` sang dịch vụ mạnh hơn (cổng ở mục 5).
- Tốc độ trên Mac phụ thuộc chip và RAM; clip 30 giây dự kiến xử lý trong khoảng 1–3 phút cho Mức 1–2.
