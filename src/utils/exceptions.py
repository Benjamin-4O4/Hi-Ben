from typing import Optional, Dict, Any


class AppError(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ConfigError(AppError):
    """配置相关异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class StorageError(AppError):
    """存储相关异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "STORAGE_ERROR", details)


class PlatformError(AppError):
    """平台相关异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PLATFORM_ERROR", details)


class MessageError(AppError):
    """消息处理相关异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MESSAGE_ERROR", details)


"""自定义异常类"""


class BaseError(Exception):
    """基础异常类"""

    pass


class ConfigError(BaseError):
    """配置错误"""

    pass


class PlatformError(BaseError):
    """平台错误"""

    pass


class ServiceError(BaseError):
    """服务错误"""

    pass


class ValidationError(BaseError):
    """验证错误"""

    pass


class ProcessError(BaseError):
    """处理错误"""

    pass


class StateError(BaseError):
    """状态错误"""

    pass
