from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class MessageType(str, Enum):
    """消息类型"""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    FILE = "file"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"
    POLL = "poll"
    DICE = "dice"
    ANIMATION = "animation"
    MEDIA_GROUP = "media_group"
    UNKNOWN = "unknown"


class MessageSource(str, Enum):
    """消息来源"""

    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class MessageContent(BaseModel):
    """消息内容"""

    type: MessageType
    data: Dict[str, Any]  # 根据type存储不同的数据结构
    raw_data: Optional[Dict] = None  # 原始数据


class MessageMetadata(BaseModel):
    """消息元数据"""

    message_id: str
    platform: str
    chat_id: str
    user_id: Optional[str] = None
    timestamp: datetime
    source: MessageSource
    reply_to: Optional[str] = None
    edit_date: Optional[datetime] = None
    forward_from: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """统一消息模型"""

    content: MessageContent
    metadata: MessageMetadata
    files: List[Dict] = []  # 附件列表
    reply_to: Optional['Message'] = None
