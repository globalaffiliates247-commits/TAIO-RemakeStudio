#!/bin/bash
# TAIO.CLUB RemakeStudio — chạy trên Mac, KHÔNG cần API key.
#   bash scripts/start_mac_local.sh            # mở app tại http://localhost:8000
#   bash scripts/start_mac_local.sh --worker   # (giai đoạn 2-3) làm máy xử lý cho bản Render
# Tự bật Ollama và VieNeu-TTS server nếu chưa chạy; tắt app (Ctrl+C) là tắt luôn VieNeu.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Chưa có .env. Chạy trước: bash scripts/setup_mac_local.sh"; exit 1; }
set -a; source .env; set +a
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

MODE="${1:-app}"
VIENEU_PORT="$(echo "$VIENEU_BASE_URL" | sed -E 's#.*:([0-9]+).*#\1#')"
LOG_DIR="data/logs"; mkdir -p "$LOG_DIR"
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

wait_for() { # url, tên, số giây
  for _ in $(seq 1 "$3"); do curl -s "$1" >/dev/null && { echo "  ✅ $2 sẵn sàng"; return 0; }; sleep 1; done
  echo "  ❌ $2 chưa lên sau $3 giây (xem $LOG_DIR)"; return 1
}

if [ "${LLM_BACKEND:-ollama}" = "ollama" ]; then
  echo "▶ Ollama (dịch Qwen3)"
  if ! curl -s http://localhost:11434/api/tags >/dev/null; then
    ollama serve >"$LOG_DIR/ollama.log" 2>&1 & PIDS+=($!)
  fi
  wait_for http://localhost:11434/api/tags "Ollama" 30
else
  echo "▶ llama.cpp server (dịch Qwen3) cổng ${LLAMACPP_PORT:-8102}"
  if ! curl -s "http://127.0.0.1:${LLAMACPP_PORT:-8102}/v1/models" >/dev/null; then
    HOST=127.0.0.1 PORT="${LLAMACPP_PORT:-8102}" .venv/bin/python -m llama_cpp.server --model "$LLAMACPP_MODEL_PATH" --model_alias "$LLM_MODEL" \
      --n_gpu_layers "${LLAMACPP_GPU_LAYERS:-0}" --n_ctx "${LLAMACPP_CTX:-2048}" --n_threads 4 --chat_template_kwargs '{"enable_thinking":false}' \
      --host 127.0.0.1 --port "${LLAMACPP_PORT:-8102}" \
      >"$LOG_DIR/llamacpp.log" 2>&1 & PIDS+=($!)
  fi
  wait_for "http://127.0.0.1:${LLAMACPP_PORT:-8102}/v1/models" "llama.cpp server" 120
fi

if [ -n "${VIENEU_DIR:-}" ] && [ -x "$VIENEU_DIR/.venv/bin/python" ]; then
  echo "▶ VieNeu-TTS server (giọng Việt) cổng $VIENEU_PORT"
  if ! curl -s "http://127.0.0.1:$VIENEU_PORT/health" >/dev/null; then
    ( cd "$VIENEU_DIR" && HOST=127.0.0.1 PORT="$VIENEU_PORT" VIENEU_BACKEND="${VIENEU_BACKEND:-onnx}" \
        .venv/bin/python -m apps.openai_speech >"$OLDPWD/$LOG_DIR/vieneu.log" 2>&1 ) & PIDS+=($!)
  fi
  wait_for "http://127.0.0.1:$VIENEU_PORT/health" "VieNeu-TTS" 180
else
  echo "⚠️  VieNeu-TTS chưa cài (VIENEU_DIR trống) → giọng Việt dùng OmniVoice"
fi

if [ "$MODE" = "--worker" ]; then
  echo "▶ Chế độ worker: nhận việc từ $GATEWAY_URL"
  .venv/bin/python -m channels.worker.worker
else
  echo "▶ App: http://localhost:$PORT   (Wi-Fi nội bộ: http://$(ipconfig getifaddr en0 2>/dev/null || echo localhost):$PORT)"
  (sleep 2 && open "http://localhost:$PORT") &
  .venv/bin/python main.py
fi
