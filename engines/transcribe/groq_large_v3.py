"""
Groq Whisper Large v3 (Chuyên dụng nguồn tiếng Việt và audio phức tạp)
"""

import os
import logging
from typing import Optional
from engines.models import Transcript, TranscriptSegment
from engines.transcribe.groq_turbo import GroqTurboTranscriber

logger = logging.getLogger("taio.transcribe.groq_large_v3")


class GroqLargeV3Transcriber(GroqTurboTranscriber):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)
        self.model = "whisper-large-v3"
