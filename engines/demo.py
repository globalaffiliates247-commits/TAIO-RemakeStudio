"""
TAIO RemakeStudio: Demo Mock Provider
Quy tắc Mục 4: Nơi duy nhất chứa dữ liệu mẫu, CHỈ chạy khi DEMO_MODE=1.
Nếu DEMO_MODE != 1, bất kỳ hàm nào trong đây đều ném lỗi từ chối phục vụ.
"""

import os
from engines.models import Transcript, TranscriptSegment
from engines.errors import FeatureDisabled


def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "0").strip() in ["1", "true", "True"]


def get_demo_transcript(lang: str = "en") -> Transcript:
    if not is_demo_mode():
        raise FeatureDisabled("Chế độ Demo", "Hệ thống đang chạy chế độ thật (DEMO_MODE=0). Vui lòng cấu hình API key để chép lời.")

    t = Transcript(
        title="Bản chép mẫu (Demo Mode)",
        source_language=lang,
        target_language="vi",
        duration=11.0
    )
    t.add_segment(TranscriptSegment(
        id=1,
        start=0.0,
        end=3.5,
        original_text="Welcome to TAIO RemakeStudio, the all-in-one media localization tool.",
        translated_text="Chào mừng đến với TAIO RemakeStudio, công cụ bản địa hóa video."
    ))
    t.add_segment(TranscriptSegment(
        id=2,
        start=3.6,
        end=7.2,
        original_text="Now anyone can listen to global content in Vietnamese with natural regional voices.",
        translated_text="Giờ đây ai cũng có thể nghe nội dung quốc tế bằng tiếng Việt với giọng đọc thân quen."
    ))
    t.add_segment(TranscriptSegment(
        id=3,
        start=7.5,
        end=11.0,
        original_text="From TikTok and Facebook videos to podcasts and favorite songs.",
        translated_text="Từ video TikTok, Facebook đến podcast và bài hát yêu thích."
    ))
    return t
