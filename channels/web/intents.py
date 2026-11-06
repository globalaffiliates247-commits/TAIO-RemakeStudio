"""
TAIO RemakeStudio: Intent Resolution Engine
Chuyển đổi Ý Định (Intent) người dùng chọn sang Luồng xử lý kỹ thuật (Flow L1-L5)
dựa trên ngôn ngữ phát hiện và phân quyền vai trò.
"""

import os
import yaml
import logging
from typing import Dict, Any, Tuple
from engines.errors import FeatureDisabled, RemakeStudioError

logger = logging.getLogger("taio.intents")


class IntentResolver:
    def __init__(self, config_path: str = "config/intents.yaml"):
        self.config_path = config_path
        self.intents = self._load_intents()

    def _load_intents(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f).get("intents", {})
        return {}

    def resolve_flow(
        self,
        intent_id: str,
        detected_language: str = "en",
        user_role: str = "level_1"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Xác định flow_id (L1-L5) và các thiết lập tương ứng từ intent_id.
        Kiểm tra mâu thuẫn ngôn ngữ và phân quyền.
        """
        if intent_id not in self.intents:
            raise RemakeStudioError(f"Ý định '{intent_id}' không hợp lệ.")

        intent_config = self.intents[intent_id]
        allowed_roles = intent_config.get("roles", ["super_admin"])
        if user_role not in allowed_roles and "super_admin" not in user_role:
            raise FeatureDisabled(
                intent_config.get("name", intent_id),
                f"Tài khoản {user_role} chưa được cấp quyền sử dụng tính năng này."
            )

        lang = (detected_language or "en").lower().strip()

        # 1. Ý định: Nghe bằng tiếng Việt
        if intent_id == "listen_vi":
            if lang == "vi":
                raise RemakeStudioError(
                    "Video này đã là tiếng Việt. Bạn có muốn chọn ý định 'Đổi giọng đọc' không?",
                    action="switch_intent"
                )
            elif lang == "en":
                return "L1", {"source_lang": "en", "target_lang": "vi"}
            else:
                return "L2", {"source_lang": lang, "target_lang": "vi"}

        # 2. Ý định: Đổi giọng đọc (tiếng Việt -> tiếng Việt)
        elif intent_id == "revoice":
            if lang != "vi" and lang != "auto":
                raise RemakeStudioError(
                    f"Video này là tiếng nước ngoài ({lang}). Bạn có muốn chuyển sang ý định 'Nghe bằng tiếng Việt' không?",
                    action="switch_intent"
                )
            return "L4", {"source_lang": "vi", "target_lang": "vi"}

        # 3. Ý định: Tách nhạc để tập
        elif intent_id == "music_stems":
            return "L5", {}

        # 4. Ý định: Dịch ra tiếng nước ngoài (L3)
        elif intent_id == "translate_intl":
            if user_role != "super_admin":
                raise FeatureDisabled("Dịch ra tiếng nước ngoài", "Chỉ dành riêng cho vai trò Super Admin.")
            return "L3", {"source_lang": "vi"}

        raise RemakeStudioError(f"Chưa hỗ trợ định tuyến cho ý định '{intent_id}'.")
