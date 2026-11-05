"""
Community Rewards & Mission System
Thực hiện nhiệm vụ (chia sẻ video, báo lỗi, điểm danh) để nhận thêm phút dịch.
"""

from typing import Dict, Any


class RewardsManager:
    @staticmethod
    def claim_reward(user_quota_tracker, user_id: str, task_id: str) -> Dict[str, Any]:
        tasks = {
            "daily_checkin": 5,
            "join_telegram_community": 30,
            "share_translated_video": 20,
            "report_bug_or_feedback": 15
        }
        reward = tasks.get(task_id, 0)
        if reward > 0:
            user = user_quota_tracker.get_user_quota(user_id)
            user["remaining_minutes"] += reward
            user_quota_tracker._save()
            return {"success": True, "reward_minutes": reward, "new_total": user["remaining_minutes"]}
        return {"success": False, "message": "Nhiệm vụ không tồn tại"}
