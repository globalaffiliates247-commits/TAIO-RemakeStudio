"""
Base Flow Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from engines.models import Transcript


class BaseFlow(ABC):
    def __init__(self, flow_id: str, name: str):
        self.flow_id = flow_id
        self.name = name

    @abstractmethod
    def run(
        self,
        audio_path: str,
        video_path: Optional[str],
        output_dir: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Thực thi luồng và trả về danh sách các tệp đầu ra (output_files)
        """
        pass
