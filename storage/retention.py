"""
Storage Retention Management (Tuân thủ Nghị định 13/2023 & Luật Bảo vệ dữ liệu cá nhân 2026)
Tự động dọn dẹp các tệp tạm và dữ liệu người dùng khi hết hạn lưu trữ.
"""

import os
import time
import shutil
import logging

logger = logging.getLogger("taio.storage.retention")


class RetentionManager:
    @staticmethod
    def cleanup_expired_files(directory: str, max_age_days: int = 7) -> int:
        """
        Quét và xóa các file hoặc thư mục đã lưu quá max_age_days ngày.
        Trả về số lượng file đã xóa.
        """
        if not os.path.exists(directory) or max_age_days < 0:
            return 0

        cutoff_time = time.time() - (max_age_days * 86400)
        deleted_count = 0

        for root, dirs, files in os.walk(directory, topdown=False):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    if os.path.getmtime(fpath) < cutoff_time:
                        os.remove(fpath)
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Không thể xóa file {fpath}: {e}")

            for d in dirs:
                dpath = os.path.join(root, d)
                try:
                    if not os.listdir(dpath):
                        os.rmdir(dpath)
                except Exception:
                    pass

        logger.info(f"Đã dọn dẹp {deleted_count} tệp hết hạn lưu trữ tại {directory}.")
        return deleted_count
