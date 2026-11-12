#!/bin/bash
# TAIO.CLUB RemakeStudio — cài đặt một lần cho Mac chip Apple, chạy KHÔNG cần API key.
# Chạy từ thư mục gốc repo:  bash scripts/setup_mac_local.sh
# Chạy lại bao nhiêu lần cũng được: bước nào đã xong sẽ bỏ qua.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO_DIR="$(pwd)"
ENGINES_DIR="$(cd "$REPO_DIR/.." && pwd)/taio-engines"

ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; }
step() { echo ""; echo "▶ $*"; }

step "1/7 Kiểm tra máy"
[ "$(uname -m)" = "arm64" ] || { echo "Cần Mac chip Apple (arm64)."; exit 1; }
MACOS_VER="$(sw_vers -productVersion)"
RAM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
ok "macOS $MACOS_VER, RAM ${RAM_GB} GB"
command -v brew >/dev/null || { echo "Chưa có Homebrew. Cài tại https://brew.sh rồi chạy lại."; exit 1; }

# Ollama cần macOS 14 trở lên. Máy thấp hơn dùng llama.cpp server (cùng chuẩn OpenAI, cùng model Qwen3).
if [ "$(printf '%s\n' "14.0" "$MACOS_VER" | sort -V | head -1)" = "14.0" ]; then LLM_BACKEND=ollama; else LLM_BACKEND=llamacpp; fi
ok "Công cụ chạy model dịch: $LLM_BACKEND"

step "2/7 Công cụ hệ thống: ffmpeg, uv, git (+ Ollama nếu macOS 14+)"
PKGS=(ffmpeg git cmake); [ "$LLM_BACKEND" = "ollama" ] && PKGS+=(ollama)
for pkg in "${PKGS[@]}"; do
  if command -v "$pkg" >/dev/null; then ok "$pkg đã có"; else brew install "$pkg"; fi
done
if command -v uv >/dev/null; then ok "uv đã có"; else curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH"; fi

step "3/7 Môi trường Python của app (.venv, Python 3.11)"
[ -d .venv ] || uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-mac-local.txt
# mlx-whisper cần macOS 13.5 trở lên
if [ "$(printf '%s\n' "13.5" "$MACOS_VER" | sort -V | head -1)" = "13.5" ]; then
  uv pip install --python .venv/bin/python mlx-whisper && ok "mlx-whisper đã cài (chép lời nhanh hơn)"
else
  warn "macOS $MACOS_VER < 13.5: bỏ qua mlx-whisper, dùng Whisper qua transformers (vẫn chạy được)"
fi

step "4/7 File cấu hình .env"
if [ -f .env ] && grep -q '^LLM_BACKEND=' .env; then
  ok ".env bản Mac đã có (không ghi đè)"
else
  if [ -f .env ]; then mv .env ".env.backup-$(date +%Y%m%d-%H%M%S)"; warn "đã cất .env cũ thành .env.backup-* (key cũ vẫn còn trong đó)"; fi
  cp .env.mac_local.example .env; ok "đã tạo .env từ .env.mac_local.example"
fi
if [ "$RAM_GB" -lt 16 ]; then
  sed -i '' 's/^LLM_MODEL=.*/LLM_MODEL=qwen3:4b/' .env
  warn "RAM < 16 GB: dùng qwen3:4b cho nhẹ (dịch kém hơn bản 8b một chút)"
fi
LLM_MODEL="$(grep '^LLM_MODEL=' .env | cut -d= -f2)"

step "5/7 Model dịch Qwen3 ($LLM_BACKEND)"
sed -i '' "s/^LLM_BACKEND=.*/LLM_BACKEND=$LLM_BACKEND/" .env
if [ "$LLM_BACKEND" = "ollama" ]; then
  sed -i '' 's#^LLM_BASE_URL=.*#LLM_BASE_URL=http://localhost:11434/v1#' .env
  if ! curl -s http://localhost:11434/api/tags >/dev/null; then (ollama serve >/tmp/taio-ollama.log 2>&1 &) ; sleep 3; fi
  ollama pull "$LLM_MODEL" && ok "đã có $LLM_MODEL"
else
  # llama.cpp qua llama-cpp-python: biên dịch trên máy với Metal (cần Xcode Command Line Tools, mất vài phút)
  CMAKE_ARGS="-DGGML_METAL=on" uv pip install --python .venv/bin/python "llama-cpp-python[server]"
  SIZE="$(echo "$LLM_MODEL" | sed -E 's/.*:([0-9]+b).*/\1/; s/b$/B/')"     # qwen3:8b -> 8B
  GGUF="$(.venv/bin/python - "$SIZE" <<'PY'
import glob, sys
from huggingface_hub import snapshot_download
size = sys.argv[1]
d = snapshot_download(f"Qwen/Qwen3-{size}-GGUF", allow_patterns=["*Q4_K_M*.gguf"])
print(sorted(glob.glob(f"{d}/*Q4_K_M*.gguf"))[0])
PY
)"
  [ -f "$GGUF" ] || { echo "Không tải được model GGUF Qwen3-$SIZE"; exit 1; }
  sed -i '' "s#^LLAMACPP_MODEL_PATH=.*#LLAMACPP_MODEL_PATH=$GGUF#" .env
  PORT_LLM="$(grep '^LLAMACPP_PORT=' .env | cut -d= -f2)"
  sed -i '' "s#^LLM_BASE_URL=.*#LLM_BASE_URL=http://127.0.0.1:${PORT_LLM:-8102}/v1#" .env
  ok "đã có $GGUF"
fi

step "6/7 VieNeu-TTS (giọng Việt Bắc/Trung/Nam) — môi trường riêng"
# onnxruntime (VieNeu cần) chỉ có bản cài sẵn cho macOS từ 13.3 trở lên:
#   macOS >= 13.4 -> 1.23.2 (bản cuối trước khi lên macOS 14)
#   macOS == 13.3 -> 1.21.1 (được biên dịch với SDK 13.3)
#   macOS <  13.3 -> không có bản nào chạy được; cần cập nhật macOS (Ventura 13.7, miễn phí) hoặc SKIP_VIENEU=1
ver_ge() { [ "$(printf '%s\n' "$1" "$2" | sort -V | head -1)" = "$1" ]; }   # ver_ge MIN VER
if ver_ge 13.4 "$MACOS_VER"; then ORT_VER=1.23.2
elif ver_ge 13.3 "$MACOS_VER"; then ORT_VER=1.21.1
else ORT_VER=""; fi
if [ -z "$ORT_VER" ] && [ "${SKIP_VIENEU:-0}" != "1" ]; then
  echo "  ❌ macOS $MACOS_VER quá cũ cho VieNeu-TTS (onnxruntime cần macOS 13.3 trở lên)."
  echo "     Cách 1 (khuyên dùng): Cài đặt hệ thống → Cài đặt chung → Cập nhật phần mềm → lên macOS Ventura 13.7.x, rồi chạy lại script này."
  echo "     Cách 2 (tạm): SKIP_VIENEU=1 bash scripts/setup_mac_local.sh  → bỏ VieNeu, giọng Việt dùng OmniVoice."
  exit 1
fi
if [ "${SKIP_VIENEU:-0}" = "1" ]; then
  warn "SKIP_VIENEU=1: bỏ qua VieNeu-TTS, giọng Việt dùng OmniVoice"
  sed -i '' "s#^VIENEU_DIR=.*#VIENEU_DIR=#" .env
  grep -q '^TTS_VI_ENGINE=' .env && sed -i '' 's/^TTS_VI_ENGINE=.*/TTS_VI_ENGINE=omnivoice/' .env || echo "TTS_VI_ENGINE=omnivoice" >> .env
else
mkdir -p "$ENGINES_DIR"
if [ -d "$ENGINES_DIR/VieNeu-TTS/.git" ]; then
  git -C "$ENGINES_DIR/VieNeu-TTS" pull --ff-only || warn "không cập nhật được VieNeu-TTS, dùng bản đang có"
else
  # Nếu đã fork về GitHub của bạn, đổi URL này sang bản fork (xem tools/backup/fork_to_github.sh)
  git clone "${VIENEU_GIT_URL:-https://github.com/pnnbao97/VieNeu-TTS.git}" "$ENGINES_DIR/VieNeu-TTS"
fi
cd "$ENGINES_DIR/VieNeu-TTS"
if [ "$LLM_BACKEND" = "ollama" ]; then
  uv sync || { echo "  ❌ Cài VieNeu-TTS thất bại"; exit 1; }
else
  [ -d .venv ] || uv venv --python 3.12 .venv
  echo "  macOS $MACOS_VER → onnxruntime $ORT_VER"
  uv pip install --python .venv/bin/python -e . "onnxruntime==$ORT_VER" || { echo "  ❌ Cài VieNeu-TTS thất bại"; exit 1; }
fi
.venv/bin/python -c "import vieneu, onnxruntime; print('  onnxruntime', onnxruntime.__version__)" \
  || { echo "  ❌ VieNeu-TTS cài xong nhưng không import được (macOS $MACOS_VER). Thử: SKIP_VIENEU=1 bash scripts/setup_mac_local.sh"; exit 1; }
cd "$REPO_DIR"
ok "VieNeu-TTS sẵn sàng tại $ENGINES_DIR/VieNeu-TTS"
sed -i '' "s#^VIENEU_DIR=.*#VIENEU_DIR=$ENGINES_DIR/VieNeu-TTS#" .env
fi

step "7/7 Tải trước model (lần đầu mất vài phút, các lần sau dùng bộ nhớ đệm)"
.venv/bin/python - <<'PY'
import os
from huggingface_hub import snapshot_download
for repo in [os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3-turbo"), "k2-fsa/OmniVoice"]:
    try:
        snapshot_download(repo)
        print(f"  ✅ {repo}")
    except Exception as e:
        print(f"  ⚠️  {repo}: {e}")
PY

echo ""
echo "🎉 Cài đặt xong. Chạy app:  bash scripts/start_mac_local.sh"
