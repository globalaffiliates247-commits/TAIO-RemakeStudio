"""
Community Hub & Super Admin Publishing
Super Admin chia sẻ bản dịch công khai cho cộng đồng (chỉ nội dung có bản quyền hợp lệ).
"""

import json
import os
import time
from typing import List, Dict, Any


class CommunityShareManager:
    def __init__(self, db_file: str = "data/community_feed.json"):
        self.db_file = db_file
        os.makedirs(os.path.dirname(db_file), exist_ok=True)

    def publish_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        items = self.get_feed()
        item_data["published_at"] = time.time()
        item_data["id"] = f"share_{int(time.time())}"
        items.insert(0, item_data)

        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        return item_data

    def get_feed(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []
