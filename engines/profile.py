"""
Deploy Profile Loader
Quản lý hồ sơ triển khai máy chủ (local, self_host, render_free, render_starter).
"""

import os
import yaml
import logging
from typing import Dict, Any, List

logger = logging.getLogger("taio.profile")


class DeployProfile:
    def __init__(self, profile_name: str = None, config_path: str = "config/deploy_profiles.yaml"):
        self.profile_name = profile_name or os.getenv("DEPLOY_PROFILE", "local")
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                all_profiles = yaml.safe_load(f).get("profiles", {})
                if self.profile_name in all_profiles:
                    return all_profiles[self.profile_name]
                logger.warning(f"Không tìm thấy profile '{self.profile_name}', dùng fallback 'local'.")
                return all_profiles.get("local", {})
        return {}

    @property
    def allowed_flows(self) -> List[str]:
        return self.data.get("allowed_flows", ["L1", "L2", "L3", "L4", "L5"])

    @property
    def allowed_levels(self) -> List[int]:
        return self.data.get("allowed_levels", [1, 2, 3, 4])

    @property
    def max_duration_minutes(self) -> int:
        return self.data.get("max_duration_minutes", 10)

    @property
    def transcribe_chain(self) -> List[str]:
        return self.data.get("transcribe_chain", ["groq_turbo", "groq_large_v3"])

    @property
    def translate_chain(self) -> List[str]:
        return self.data.get("translate_chain", ["gemini", "deepseek"])

    @property
    def tts_chain(self) -> List[str]:
        return self.data.get("tts_chain", ["edge_tts", "vieneu", "fpt_ai"])

    @property
    def separator_chain(self) -> List[str]:
        return self.data.get("separator_chain", ["demucs"])
