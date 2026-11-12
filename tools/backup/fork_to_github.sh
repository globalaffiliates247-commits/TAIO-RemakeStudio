#!/bin/bash
# Fork (sao lưu) toàn bộ mã nguồn engine về GitHub của TAIO-Lee.
# Fork nằm trên GitHub, không tốn ổ đĩa máy Mac, nên không vướng ngưỡng 15 GB.
# Cần GitHub CLI đã đăng nhập:  brew install gh && gh auth login
#   bash tools/backup/fork_to_github.sh                       # fork về tài khoản đang đăng nhập
#   TARGET_ORG=ten-to-chuc bash tools/backup/fork_to_github.sh  # fork về một tổ chức (organization)
set -uo pipefail

REPOS=(
  "openai/whisper"                 # MIT — Whisper gốc
  "ml-explore/mlx-examples"        # MIT — mlx-whisper (Whisper nhanh trên Mac)
  "VinAIResearch/PhoWhisper"       # Apache-2.0 — Whisper tiếng Việt
  "ollama/ollama"                  # MIT — chạy LLM trên máy
  "QwenLM/Qwen3"                   # Apache-2.0 — model dịch (trọng số trên Hugging Face)
  "pnnbao97/VieNeu-TTS"            # Apache-2.0 — giọng Việt Bắc/Trung/Nam
  "k2-fsa/OmniVoice"               # Apache-2.0 — 600+ ngôn ngữ, nhân bản giọng
  "OpenBMB/VoxCPM"                 # Apache-2.0 — giọng dự phòng (máy GPU NVIDIA)
  "facebookresearch/demucs"        # MIT — tách nhạc
  "snakers4/silero-vad"            # MIT — lọc đoạn im lặng
  "yt-dlp/yt-dlp"                  # Unlicense — tải video
  "mozillazg/python-pinyin"        # MIT — phiên âm pinyin
  "binwiederhier/ntfy"             # Apache-2.0/GPL-2.0 — chuông báo việc mới (bản Render)
)

ORG_FLAG=()
[ -n "${TARGET_ORG:-}" ] && ORG_FLAG=(--org "$TARGET_ORG")

for r in "${REPOS[@]}"; do
  echo "▶ $r"
  gh repo fork "$r" "${ORG_FLAG[@]}" --clone=false 2>&1 | sed 's/^/   /' || echo "   ⚠️  không fork được $r"
done

echo ""
echo "Xong. Giữ fork luôn mới: vào từng repo fork trên GitHub, bấm 'Sync fork', hoặc chạy"
echo "  gh repo sync <tai-khoan>/<ten-repo> --source <chu-goc>/<ten-repo>"
echo "Trọng số model KHÔNG nằm trên GitHub: sao lưu bằng cách chép ~/.cache/huggingface/hub và ~/.ollama/models."
