"""
Whisper chạy trên máy qua thư viện transformers (không cần API key).

- Mac chip Apple: chạy bằng GPU tích hợp (MPS). Máy NVIDIA: CUDA. Không có GPU: CPU.
- Model mặc định: openai/whisper-large-v3-turbo (MIT) — đã có sẵn trong bộ nhớ đệm Hugging Face trên máy TAIO-Lee.
- Tiếng Việt: nếu đặt HF_WHISPER_MODEL_VI (ví dụ vinai/PhoWhisper-medium, Apache-2.0) thì dùng model đó khi
  biết trước nguồn là tiếng Việt (luồng L3, L4).

Biến môi trường:
  HF_WHISPER_MODEL      mặc định openai/whisper-large-v3-turbo
  HF_WHISPER_MODEL_VI   tuỳ chọn, model riêng cho tiếng Việt
  HF_WHISPER_DEVICE     auto | mps | cuda | cpu (mặc định auto)
"""

import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
import logging
from typing import Optional

from engines.models import Transcript, TranscriptSegment

logger = logging.getLogger("taio.transcribe.hf_whisper")

try:
    from engines.errors import EngineFailed, EngineUnavailable
except ImportError:  # dùng độc lập ngoài repo
    class EngineUnavailable(RuntimeError):
        def __init__(self, engine_name, reason, setup_hint=""):
            super().__init__(f"{engine_name}: {reason}")

    class EngineFailed(RuntimeError):
        def __init__(self, engine_name, original_error):
            super().__init__(f"{engine_name}: {original_error}")

ENGINE_NAME = "Whisper (máy, transformers)"


def _pick_device(torch) -> str:
    wanted = os.getenv("HF_WHISPER_DEVICE", "auto")
    if wanted != "auto":
        return wanted
    if torch.cuda.is_available():
        return "cuda:0"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        import platform
        try:
            ver = tuple(int(x) for x in platform.mac_ver()[0].split(".")[:2])
            if ver and ver < (14, 0):
                logger.info(f"macOS {platform.mac_ver()[0]} < 14.0: MPS chưa hỗ trợ toán tử Long isin, chuyển sang CPU.")
                return "cpu"
        except Exception:
            pass
        return "mps"
    return "cpu"


def _read_audio(audio_file_path: str, sr: int = 16000):
    """Giải mã file audio/video bằng ffmpeg sang mảng numpy float32 16kHz."""
    import subprocess
    import numpy as np
    cmd = [
        "ffmpeg", "-nostdin", "-threads", "0", "-i", audio_file_path,
        "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return np.frombuffer(out, np.float32)
    except Exception as e:
        logger.warning(f"ffmpeg decode thất bại ({e}), dùng path trực tiếp: {audio_file_path}")
        return audio_file_path


class HFWhisperTranscriber:
    _pipes = {}  # nạp model một lần cho mỗi (model, device)

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3-turbo")
        self.model_name_vi = os.getenv("HF_WHISPER_MODEL_VI", "")

    def _pipeline(self, model_name: str):
        try:
            import torch
            from transformers import pipeline
        except ImportError:
            raise EngineUnavailable(ENGINE_NAME, "chưa cài torch/transformers (xem requirements-mac-local.txt)")
        device = _pick_device(torch)
        key = (model_name, device)
        if key not in self._pipes:
            dtype = torch.float16 if device != "cpu" else torch.float32
            logger.info(f"Nạp {model_name} trên {device}...")
            common = dict(model=model_name, device=device)
            try:  # transformers 5.x dùng tham số `dtype`
                self._pipes[key] = pipeline("automatic-speech-recognition", dtype=dtype, **common)
            except TypeError:  # transformers 4.x dùng `torch_dtype`
                self._pipes[key] = pipeline("automatic-speech-recognition", torch_dtype=dtype, **common)
        return self._pipes[key]

    def transcribe(self, audio_file_path: str, language: str = "auto") -> Transcript:
        if not os.path.exists(audio_file_path):
            raise EngineFailed(ENGINE_NAME, f"không tìm thấy file audio: {os.path.basename(audio_file_path)}")

        model_name = self.model_name_vi if (language == "vi" and self.model_name_vi) else self.model_name
        pipe = self._pipeline(model_name)

        generate_kwargs = {"task": "transcribe"}
        if language and language != "auto" and "PhoWhisper" not in model_name:
            generate_kwargs["language"] = language

        try:
            audio_input = _read_audio(audio_file_path)
            result = pipe(audio_input, return_timestamps=True, generate_kwargs=generate_kwargs)
        except Exception as e:
            raise EngineFailed(ENGINE_NAME, f"Whisper ({model_name}) lỗi: {e}")

        # Tự động nhận diện ngôn ngữ nếu chưa biết
        detected_lang = language
        full_text = (result.get("text") or "").strip()
        if not detected_lang or detected_lang == "auto":
            vi_chars = set("àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ")
            if any(c in vi_chars for c in full_text.lower()):
                detected_lang = "vi"
            else:
                detected_lang = "en"

        transcript = Transcript(
            title=os.path.basename(audio_file_path),
            media_path=audio_file_path,
            source_language=detected_lang,
        )
        for idx, chunk in enumerate(result.get("chunks", []) or []):
            text = (chunk.get("text") or "").strip()
            if not text:
                continue
            start, end = chunk.get("timestamp") or (0.0, None)
            start = float(start or 0.0)
            end = float(end) if end is not None else start + 3.0
            transcript.add_segment(TranscriptSegment(id=len(transcript.segments) + 1, start=start, end=end,
                                                     original_text=text))
        if not transcript.segments and (result.get("text") or "").strip():
            transcript.add_segment(TranscriptSegment(id=1, start=0.0, end=5.0, original_text=result["text"].strip()))
        if not transcript.segments:
            raise EngineFailed(ENGINE_NAME, "không nghe thấy lời nói trong file")
        transcript.metadata["transcribe_model"] = model_name
        if os.getenv("DEPLOY_PROFILE") == "mac_local":
            self._pipes.clear()
            import gc
            gc.collect()
        return transcript
