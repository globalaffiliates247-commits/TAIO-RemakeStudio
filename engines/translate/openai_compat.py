"""
Dịch qua mọi máy chủ theo chuẩn OpenAI Chat Completions — một engine cho nhiều nơi chạy.

Mặc định: Ollama chạy trên máy (http://localhost:11434/v1) với model Qwen3 (Apache-2.0, có tiếng Việt),
không cần API key. Đổi sang nơi khác chỉ cần đổi biến môi trường, không sửa code:
  - LM Studio trên máy:        LLM_BASE_URL=http://localhost:1234/v1
  - Máy GPU riêng / thuê GPU:  LLM_BASE_URL=https://<máy-của-bạn>/v1
  - DeepSeek, OpenRouter, Gemini (endpoint tương thích OpenAI): đặt LLM_BASE_URL + LLM_API_KEY + LLM_MODEL

Biến môi trường:
  LLM_BASE_URL   mặc định http://localhost:11434/v1
  LLM_MODEL      mặc định qwen3:8b
  LLM_API_KEY    mặc định "ollama" (Ollama không kiểm tra key)
  LLM_TIMEOUT    giây, mặc định 300
  LLM_BATCH      số câu gửi mỗi lần, mặc định 40
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional

from engines.models import Transcript

logger = logging.getLogger("taio.translate.openai_compat")

try:
    from engines.errors import EngineFailed, EngineUnavailable
except ImportError:  # dùng độc lập ngoài repo
    class EngineUnavailable(RuntimeError):
        def __init__(self, engine_name, reason, setup_hint=""):
            super().__init__(f"{engine_name}: {reason}")

    class EngineFailed(RuntimeError):
        def __init__(self, engine_name, original_error):
            super().__init__(f"{engine_name}: {original_error}")

ENGINE_NAME = "LLM dịch (Ollama/OpenAI-compatible)"

LANG_NAMES = {"vi": "tiếng Việt", "en": "English", "zh": "中文", "ja": "日本語", "ko": "한국어", "th": "ภาษาไทย"}


def parse_translation_json(raw: str) -> Dict[int, str]:
    """Đọc mảng [{"id":..,"translated":..}] từ câu trả lời; bỏ phần <think> của Qwen3 và khối ```json."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    elif "```" in text:
        parts = text.split("```")
        for p in parts[1:]:
            p_clean = p.strip()
            if p_clean.lower().startswith("json"):
                p_clean = p_clean[4:].strip()
            if "[" in p_clean and "]" in p_clean:
                text = p_clean
                break

    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        json_slice = text[start:end + 1]
        try:
            items = json.loads(json_slice)
            if isinstance(items, list):
                return {int(item["id"]): str(item.get("translated", "")).strip() for item in items if "id" in item}
        except Exception:
            pass

    # Fallback regex trích xuất {"id": ..., "translated": "..."}
    result: Dict[int, str] = {}
    pattern = re.compile(r'\{\s*"id"\s*:\s*(\d+)\s*,\s*"translated"\s*:\s*"(.*?)"\s*\}', re.DOTALL)
    for m in pattern.finditer(text):
        result[int(m.group(1))] = m.group(2).strip()
    if result:
        return result

    pattern_loose = re.compile(r'"id"\s*:\s*(\d+).*?"translated"\s*:\s*"(.*?)(?="\s*[,}\n]|\Z)', re.DOTALL)
    for m in pattern_loose.finditer(text):
        result[int(m.group(1))] = m.group(2).strip()
    if result:
        return result

    raise json.JSONDecodeError(f"không đọc được mảng JSON: {raw[:150]}", text, 0)


class OpenAICompatTranslator:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "qwen3:8b")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "ollama")
        self.timeout = float(os.getenv("LLM_TIMEOUT", "600"))
        self.batch = int(os.getenv("LLM_BATCH", "3"))

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError:
            raise EngineUnavailable(ENGINE_NAME, "chưa cài thư viện openai")
        return OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout, max_retries=1)

    def _translate_batch(self, client, items: List[dict], target_lang: str) -> Dict[int, str]:
        lang = LANG_NAMES.get(target_lang, target_lang)
        prompt = (
            f"Dịch từng câu phụ đề sau sang {lang}. Dịch tự nhiên, ngắn gọn để đọc kịp trong 'duration' giây, "
            f"giữ đúng ngữ cảnh cả đoạn, giữ nguyên tên riêng. Giữ nguyên id và số câu. "
            f"Lưu ý quan trọng: Không dùng dấu ngoặc kép bên trong câu dịch. "
            f"Chỉ trả về một mảng JSON dạng [{{\"id\": 1, \"translated\": \"...\"}}], không giải thích.\n"
            f"{json.dumps(items, ensure_ascii=False)}"
        )
        max_tokens = min(1024, max(256, len(items) * 120))
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional video subtitle translator. Output JSON only. Never explain."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
        except Exception as e:
            msg = str(e)
            if "Connection" in msg or "connect" in msg:
                raise EngineUnavailable(ENGINE_NAME, f"không kết nối được {self.base_url} (Ollama đã chạy chưa?)")
            raise EngineFailed(ENGINE_NAME, f"{self.model} lỗi: {msg}")
        raw_text = resp.choices[0].message.content or ""
        logger.info("LLM translation raw output: %s", raw_text[:300])
        try:
            return parse_translation_json(raw_text)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Parse translation JSON failed. Raw response: %s", raw_text)
            raise EngineFailed(ENGINE_NAME, f"{self.model} trả về không đúng định dạng JSON: {e}")

    def translate_transcript(self, transcript: Transcript, target_lang: str = "vi") -> Transcript:
        if not transcript.segments:
            return transcript
        client = self._client()
        segs = transcript.segments
        result: Dict[int, str] = {}
        for i in range(0, len(segs), self.batch):
            chunk = [{"id": s.id, "text": s.original_text, "duration": round(s.duration, 2)} for s in segs[i:i + self.batch]]
            result.update(self._translate_batch(client, chunk, target_lang))
        for seg in segs:
            seg.translated_text = result.get(seg.id, "")
        transcript.target_language = target_lang
        transcript.metadata["translate_model"] = f"{self.model} @ {self.base_url}"
        return transcript
