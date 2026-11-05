"""
Audio Minutes & Quota Tracking
Theo dõi số phút audio sử dụng thực tế (minh bạch, không dùng credit ảo).
"""

import json
import os
import time
from typing import Dict, Any


class QuotaTracker:
    def __init__(self, db_file: str = "data/user_quotas.json"):
        self.db_file = db_file
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {}

    def _save(self):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_user_quota(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.data:
            self.data[user_id] = {
                "remaining_minutes": 60.0,
                "used_minutes": 0.0,
                "total_files": 0,
                "role": "level_1",
                "last_active": time.time()
            }
            self._save()
        return self.data[user_id]

    def deduct_minutes(self, user_id: str, minutes_used: float) -> bool:
        user = self.get_user_quota(user_id)
        if user["role"] in ["super_admin", "level_2"]:
            user["used_minutes"] += minutes_used
            user["total_files"] += 1
            self._save()
            return True

        if user["remaining_minutes"] >= minutes_used:
            user["remaining_minutes"] -= minutes_used
            user["used_minutes"] += minutes_used
            user["total_files"] += 1
            self._save()
            return True
        return False
