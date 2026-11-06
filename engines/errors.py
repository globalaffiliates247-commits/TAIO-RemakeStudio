"""
TAIO RemakeStudio: Các lớp ngoại lệ chuẩn hóa (Standard Errors)
Theo Mục 4: EngineUnavailable, EngineFailed, FeatureDisabled, SourceFetchError.
Mọi lỗi trả về đều có thông báo tiếng Việt rõ ràng và gợi ý hành động.
"""


class RemakeStudioError(Exception):
    def __init__(self, message: str, action: str = "retry", details: str = ""):
        super().__init__(message)
        self.message = message
        self.action = action
        self.details = details

    def to_dict(self):
        return {
            "error": self.message,
            "action": self.action,
            "details": self.details
        }


class EngineUnavailable(RemakeStudioError):
    """Xảy ra khi engine thiếu key, thiếu thư viện, hoặc server URL không phản hồi."""
    def __init__(self, engine_name: str, reason: str, setup_hint: str = ""):
        msg = f"Công cụ '{engine_name}' chưa sẵn sàng: {reason}."
        if setup_hint:
            msg += f" {setup_hint}"
        super().__init__(msg, action="setup", details=f"Engine: {engine_name}")
        self.engine_name = engine_name
        self.reason = reason
        self.setup_hint = setup_hint


class EngineFailed(RemakeStudioError):
    """Xảy ra khi engine đang chạy thì gặp lỗi nội bộ hoặc timeout."""
    def __init__(self, engine_name: str, original_error: str):
        msg = f"Công cụ '{engine_name}' xử lý thất bại: {original_error}"
        super().__init__(msg, action="retry", details=f"Engine: {engine_name}")
        self.engine_name = engine_name
        self.original_error = original_error


class FeatureDisabled(RemakeStudioError):
    """Xảy ra khi tính năng chưa được kích hoạt theo phân quyền hoặc hồ sơ triển khai."""
    def __init__(self, feature_name: str, reason: str):
        msg = f"Tính năng '{feature_name}' đang tạm khoá: {reason}"
        super().__init__(msg, action="upgrade", details=f"Feature: {feature_name}")
        self.feature_name = feature_name
        self.reason = reason


class SourceFetchError(RemakeStudioError):
    """Xảy ra khi tải link video thất bại (link riêng tư, sai định dạng, YouTube chưa hỗ trợ)."""
    def __init__(self, platform: str, reason: str, action_hint: str = "Tải file lên thay thế"):
        msg = f"Không tải được video từ {platform}: {reason}."
        super().__init__(msg, action="upload", details=f"Platform: {platform}")
        self.platform = platform
        self.reason = reason
        self.action_hint = action_hint
