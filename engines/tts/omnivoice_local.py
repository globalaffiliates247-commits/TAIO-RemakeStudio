"""
OmniVoice (k2-fsa, Apache-2.0) chạy thẳng trong tiến trình — không cần server, không cần API key.

600+ ngôn ngữ. Dùng cho giọng nước ngoài (luồng L3) và nhân bản giọng (L4) trên máy có GPU / Mac chip Apple.
Ba chế độ, chọn theo cấu hình giọng trong voices.yaml:
  - Nhân bản:   omnivoice_ref_audio (file 3–10 giây) + omnivoice_ref_text (lời trong file đó)
  - Thiết kế:   omnivoice_instruct, ví dụ "female, young adult, warm" (ổn định nhất với tiếng Anh/Trung)
  - Tự động:    không đặt gì, model tự chọn giọng
Có thể ép đúng thời lượng câu gốc (tham số duration) để lồng tiếng khớp hình.

Biến môi trường:
  OMNIVOICE_MODEL    mặc định k2-fsa/OmniVoice (đã có trong bộ nhớ đệm trên máy TAIO-Lee)
  OMNIVOICE_DEVICE   auto | mps | cuda:0 | cpu
"""

import os
import logging
import tempfile
from typing import Optional

from engines.tts.audio_utils import to_mp3

logger = logging.getLogger("taio.tts.omnivoice_local")

try:
    from engines.errors import EngineFailed, EngineUnavailable
except ImportError:  # dùng độc lập ngoài repo
    class EngineUnavailable(RuntimeError):
        def __init__(self, engine_name, reason, setup_hint=""):
            super().__init__(f"{engine_name}: {reason}")

    class EngineFailed(RuntimeError):
        def __init__(self, engine_name, original_error):
            super().__init__(f"{engine_name}: {original_error}")

ENGINE_NAME = "OmniVoice (máy)"

SAMPLE_RATE = 24000


class OmniVoiceLocalEngine:
    _model = None

    def __init__(self, voice: Optional[str] = None, language: Optional[str] = None,
                 instruct: Optional[str] = None, ref_audio: Optional[str] = None, ref_text: Optional[str] = None):
        self.language = language
        self.instruct = instruct
        self.ref_audio = ref_audio
        self.ref_text = ref_text
        if voice and not (instruct or ref_audio):
            self.instruct = voice  # voice_key trong voices.yaml dùng làm mô tả giọng

    @classmethod
    def _load(cls):
        if cls._model is None:
            try:
                import torch
                from omnivoice import OmniVoice
            except ImportError:
                raise EngineUnavailable(ENGINE_NAME, "chưa cài omnivoice/torch (xem requirements-mac-local.txt)")
            device = os.getenv("OMNIVOICE_DEVICE", "auto")
            if device == "auto":
                device = "cuda:0" if torch.cuda.is_available() else (
                    "mps" if torch.backends.mps.is_available() else "cpu")
            dtype = torch.float16 if device != "cpu" else torch.float32
            logger.info(f"Nạp OmniVoice trên {device}...")
            cls._model = OmniVoice.from_pretrained(os.getenv("OMNIVOICE_MODEL", "k2-fsa/OmniVoice"),
                                                   device_map=device, dtype=dtype)
        return cls._model

    def synthesize(self, text: str, output_path: str, speed_multiplier: float = 1.0,
                   duration: Optional[float] = None) -> str:
        model = self._load()
        kwargs = {"text": text, "language": self.language}
        if self.ref_audio:
            if not os.path.exists(self.ref_audio):
                raise EngineFailed(ENGINE_NAME, f"không thấy file giọng mẫu: {self.ref_audio}")
            kwargs.update(ref_audio=self.ref_audio, ref_text=self.ref_text)
        elif self.instruct:
            kwargs["instruct"] = self.instruct
        if duration:
            kwargs["duration"] = float(duration)
        elif abs(speed_multiplier - 1.0) > 0.01:
            kwargs["speed"] = float(speed_multiplier)

        try:
            import soundfile as sf
            audio = model.generate(**kwargs)
        except Exception as e:
            raise EngineFailed(ENGINE_NAME, f"OmniVoice lỗi: {e}")
        if not audio or len(audio[0]) == 0:
            raise EngineFailed(ENGINE_NAME, "OmniVoice không tạo ra âm thanh")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            sf.write(wav_path, audio[0], SAMPLE_RATE)
            return to_mp3(wav_path, output_path)
        finally:
            os.remove(wav_path)
