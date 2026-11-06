"""
TAIO RemakeStudio: Engine Registry & Execution Chains
Quy ước Mục 4:
- Danh bạ engine tập trung ENGINES. Thêm engine = 1 file + 1 dòng trong ENGINES.
- Luồng (flows/*.py) chỉ gọi chuỗi engine (TranscribeChain, TranslateChain, TTSRouter, SeparatorChain), không gọi thẳng engine cụ thể.
- Kiểm tra tính sẵn sàng (readiness) cho từng engine rõ ràng, không nuốt lỗi.
"""

import os
import shutil
import logging
from typing import Dict, Any, List, Optional, Tuple

from engines.models import Transcript
from engines.errors import EngineUnavailable, EngineFailed, FeatureDisabled
from engines.profile import DeployProfile

logger = logging.getLogger("taio.registry")


class EngineMetadata:
    def __init__(self, name: str, category: str, cls_path: str, required_env: List[str] = None, required_libs: List[str] = None):
        self.name = name
        self.category = category
        self.cls_path = cls_path
        self.required_env = required_env or []
        self.required_libs = required_libs or []

    def check_readiness(self) -> Tuple[bool, str]:
        # Kiểm tra biến môi trường
        missing_envs = [env for env in self.required_env if not os.getenv(env) or len(os.getenv(env).strip()) < 8 or "your_" in os.getenv(env)]
        if missing_envs:
            return False, f"Thiếu biến môi trường: {', '.join(missing_envs)}. Vui lòng thêm vào file .env."

        # Kiểm tra thư viện
        for lib in self.required_libs:
            try:
                __import__(lib)
            except ImportError:
                return False, f"Thiếu thư viện Python: '{lib}'. Cần chạy 'pip install {lib}'."

        return True, "Sẵn sàng hoạt động"


# Danh bạ toàn bộ các Engine trong hệ thống
ENGINES: Dict[str, EngineMetadata] = {
    # 1. Chép lời (Transcribe)
    "groq_turbo": EngineMetadata("Groq Whisper Large v3 Turbo", "transcribe", "engines.transcribe.groq_turbo.GroqTurboTranscriber", required_env=["GROQ_API_KEY"], required_libs=["groq"]),
    "groq_large_v3": EngineMetadata("Groq Whisper Large v3", "transcribe", "engines.transcribe.groq_large_v3.GroqLargeV3Transcriber", required_env=["GROQ_API_KEY"], required_libs=["groq"]),
    "phowhisper": EngineMetadata("VinAI PhoWhisper Medium", "transcribe", "engines.transcribe.phowhisper.PhoWhisperTranscriber", required_libs=["torch", "transformers"]),
    "faster_whisper_local": EngineMetadata("Faster Whisper Local", "transcribe", "engines.transcribe.faster_whisper_local.FasterWhisperTranscriber", required_libs=["faster_whisper"]),

    # 2. Dịch thuật (Translate)
    "gemini": EngineMetadata("Google Gemini Flash", "translate", "engines.translate.gemini.GeminiTranslator", required_env=["GEMINI_API_KEY"], required_libs=["google.generativeai"]),
    "deepseek": EngineMetadata("DeepSeek Chat", "translate", "engines.translate.deepseek.DeepSeekTranslator", required_env=["DEEPSEEK_API_KEY"], required_libs=["openai"]),

    # 3. Giọng đọc (TTS)
    "edge_tts": EngineMetadata("Microsoft Edge TTS", "tts", "engines.tts.edge_tts_fallback.EdgeTTSEngine", required_libs=["edge_tts"]),
    "vieneu": EngineMetadata("VieNeu-TTS", "tts", "engines.tts.vieneu.VieNeuTTSEngine"),
    "fpt_ai": EngineMetadata("FPT.AI Text to Speech", "tts", "engines.tts.fpt_ai.FptAITTSEngine", required_env=["FPT_AI_API_KEY"]),
    "omnivoice": EngineMetadata("OmniVoice International", "tts", "engines.tts.omnivoice.OmniVoiceEngine", required_env=["OMNIVOICE_SERVER_URL"]),

    # 4. Tách nhạc (Separate)
    "demucs": EngineMetadata("Demucs Audio Separator", "separate", "engines.separate.demucs.DemucsSeparator", required_libs=["demucs", "torch"])
}


def load_engine_class(cls_path: str):
    module_path, class_name = cls_path.rsplit(".", 1)
    mod = __import__(module_path, fromlist=[class_name])
    return getattr(mod, class_name)


class TranscribeChain:
    """Chuỗi dự phòng chép lời."""
    def __init__(self, preferred_engines: Optional[List[str]] = None):
        profile = DeployProfile()
        self.engine_keys = preferred_engines or profile.transcribe_chain

    def transcribe(self, audio_file_path: str, language: str = "en") -> Tuple[Transcript, str]:
        reasons = []
        for key in self.engine_keys:
            if key not in ENGINES:
                continue
            meta = ENGINES[key]
            ready, msg = meta.check_readiness()
            if not ready:
                reasons.append(f"{meta.name}: {msg}")
                continue

            try:
                cls = load_engine_class(meta.cls_path)
                engine = cls()
                logger.info(f"Đang chép lời bằng {meta.name}...")
                transcript = engine.transcribe(audio_file_path, language=language)
                if transcript and transcript.segments:
                    return transcript, meta.name
            except Exception as e:
                logger.warning(f"Engine {meta.name} chạy thất bại: {e}")
                reasons.append(f"{meta.name}: {str(e)}")

        # Nếu tất cả engine trong chuỗi đều không khả dụng hoặc thất bại
        hint = "Vui lòng thêm GROQ_API_KEY vào file .env và khởi động lại."
        raise EngineUnavailable("Bộ chép lời (Transcribe Chain)", "; ".join(reasons), setup_hint=hint)


class TranslateChain:
    """Chuỗi dự phòng dịch thuật."""
    def __init__(self, preferred_engines: Optional[List[str]] = None):
        profile = DeployProfile()
        self.engine_keys = preferred_engines or profile.translate_chain

    def translate_transcript(self, transcript: Transcript, target_lang: str = "vi") -> Tuple[Transcript, str]:
        reasons = []
        for key in self.engine_keys:
            if key not in ENGINES:
                continue
            meta = ENGINES[key]
            ready, msg = meta.check_readiness()
            if not ready:
                reasons.append(f"{meta.name}: {msg}")
                continue

            try:
                cls = load_engine_class(meta.cls_path)
                engine = cls()
                logger.info(f"Đang dịch ngữ cảnh bằng {meta.name}...")
                trans_res = engine.translate_transcript(transcript, target_lang=target_lang)
                return trans_res, meta.name
            except Exception as e:
                logger.warning(f"Engine {meta.name} dịch thất bại: {e}")
                reasons.append(f"{meta.name}: {str(e)}")

        hint = "Vui lòng thêm GEMINI_API_KEY vào file .env để dịch thuật ngữ cảnh."
        raise EngineUnavailable("Bộ dịch thuật (Translate Chain)", "; ".join(reasons), setup_hint=hint)


class TTSRouter:
    """Điều hướng tổng hợp giọng đọc."""
    def __init__(self):
        pass

    def synthesize(self, text: str, output_path: str, voice_id: str = "vi_north_female_1", speed_multiplier: float = 1.0) -> Tuple[str, str]:
        # Xác định engine từ voice_id qua voices.yaml hoặc fallback
        from engines.tts.edge_tts_fallback import EdgeTTSEngine
        engine = EdgeTTSEngine()
        used_engine = "edge_tts"

        ready, msg = ENGINES["edge_tts"].check_readiness()
        if not ready:
            raise EngineUnavailable("Edge TTS", msg, setup_hint="Cần cài đặt thư viện 'edge-tts'")

        try:
            res_path = engine.synthesize(text, output_path, speed_multiplier=speed_multiplier)
            return res_path, used_engine
        except Exception as e:
            raise EngineFailed("Edge TTS", str(e))


class SeparatorChain:
    """Chuỗi tách nhạc stems."""
    def __init__(self):
        profile = DeployProfile()
        self.engine_keys = profile.separator_chain

    def separate(self, audio_file_path: str, output_dir: str) -> Dict[str, str]:
        if "demucs" not in self.engine_keys:
            raise FeatureDisabled("Tách nhạc Stems", "Tính năng tách nhạc Demucs bị tắt trên máy chủ cấu hình nhẹ.")

        meta = ENGINES["demucs"]
        ready, msg = meta.check_readiness()
        if not ready:
            raise EngineUnavailable("Demucs", msg, setup_hint="Cần cài đặt thư viện 'demucs' và 'torch'.")

        try:
            from engines.separate.demucs import DemucsSeparator
            sep = DemucsSeparator()
            return sep.separate(audio_file_path, output_dir)
        except Exception as e:
            raise EngineFailed("Demucs", str(e))
