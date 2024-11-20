from typing import Any, Optional, Dict
from pydantic import BaseModel, validator
import re


class ConfigValidator(BaseModel):
    """配置验证器"""

    telegram_bot_token: str
    openai_api_key: Optional[str]
    log_level: str = "INFO"

    @validator('telegram_bot_token')
    def validate_bot_token(cls, v: str) -> str:
        if not re.match(r'^\d+:[A-Za-z0-9_-]+$', v):
            raise ValueError("无效的Telegram Bot Token格式")
        return v

    @validator('openai_api_key')
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^sk-[A-Za-z0-9]+$', v):
            raise ValueError("无效的OpenAI API Key格式")
        return v

    @validator('log_level')
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"无效的日志级别，必须是: {', '.join(valid_levels)}")
        return v.upper()


class MessageValidator(BaseModel):
    """消息验证器"""

    content: str
    chat_id: str
    user_id: str

    @validator('content')
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("消息内容不能为空")
        return v.strip()

    @validator('chat_id', 'user_id')
    def validate_ids(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ID不能为空")
        return v.strip()
