"""
Flow Manager & Orchestrator
Điều phối nguồn dữ liệu (TikTok, Facebook, Upload) và chọn Luồng xử lý (L1 - L5).
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

from sources.tiktok import TikTokSource
from sources.facebook import FacebookSource
from sources.upload_file import UploadFileSource

from flows.en_to_vi import EnToViFlow
from flows.other_to_vi import OtherToViFlow
from flows.vi_to_multi import ViToMultiFlow
from flows.vi_revoice import ViRevoiceFlow
from flows.music_stems import MusicStemsFlow

logger = logging.getLogger("taio.flows.manager")


class FlowManager:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.flows = {
            "L1": EnToViFlow(),
            "L2": OtherToViFlow(),
            "L3": ViToMultiFlow(),
            "L4": ViRevoiceFlow(),
            "L5": MusicStemsFlow(),
        }

    def detect_source(self, input_target: str):
        target_lower = input_target.lower()
        if "tiktok.com" in target_lower or "douyin.com" in target_lower:
            return TikTokSource()
        elif "facebook.com" in target_lower or "fb.watch" in target_lower:
            return FacebookSource()
        else:
            return UploadFileSource()

    def process(
        self,
        input_target: str,
        flow_id: str = "L1",
        output_dir: str = "data/outputs",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        options = options or {}
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Đang xử lý đầu vào '{input_target}' qua Luồng {flow_id}...")

        # 1. Trích xuất Media từ Source
        source = self.detect_source(input_target)
        media_info = source.fetch(input_target, output_dir)

        # 2. Lấy Flow thực thi
        flow = self.flows.get(flow_id)
        if not flow:
            raise ValueError(f"Luồng '{flow_id}' không hợp lệ hoặc chưa được hỗ trợ.")

        # 3. Chạy Flow
        result = flow.run(
            audio_path=media_info.audio_path,
            video_path=media_info.media_path if media_info.media_path.endswith((".mp4", ".mov", ".mkv", ".webm")) else None,
            output_dir=output_dir,
            options=options
        )

        result["media_info"] = {
            "title": media_info.title,
            "platform": media_info.platform,
            "duration": media_info.duration,
            "thumbnail_url": media_info.thumbnail_url
        }

        return result
