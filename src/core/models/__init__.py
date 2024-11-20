"""数据模型"""

from .message import (
    Message,
    MessageType,
    MessageContent,
    MessageMetadata,
    MessageSource,
)
from .platform import PlatformAdapter

__all__ = [
    'Message',
    'MessageType',
    'MessageContent',
    'MessageMetadata',
    'MessageSource',
    'PlatformAdapter',
]
