"""Telegram 消息处理器"""

from .base_processor import BaseProcessor
from .text_processor import TextProcessor
from .media_processor import MediaProcessor
from .file_processor import FileProcessor

__all__ = [
    'BaseProcessor',
    'TextProcessor',
    'MediaProcessor',
    'FileProcessor',
]
