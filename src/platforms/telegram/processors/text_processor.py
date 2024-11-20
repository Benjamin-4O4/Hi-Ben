from typing import Optional
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .base_processor import BaseProcessor
from ....core.models.message import (
    Message,
    MessageType,
    MessageContent,
    MessageMetadata,
    MessageSource,
)


class TextProcessor(BaseProcessor):
    """文本消息处理器"""

    async def process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[Message]:
        """处理文本消息"""
        if not update.message or not update.message.text:
            return None

        # 创建消息内容
        content = MessageContent(
            type=MessageType.TEXT, data={"text": update.message.text}
        )

        # 创建消息元数据
        metadata = MessageMetadata(
            message_id=str(update.message.message_id),
            platform="telegram",
            chat_id=str(update.message.chat_id),
            user_id=(
                str(update.message.from_user.id) if update.message.from_user else None
            ),
            timestamp=update.message.date,
            source=MessageSource.USER,
            reply_to=(
                str(update.message.reply_to_message.message_id)
                if update.message.reply_to_message
                else None
            ),
            edit_date=update.message.edit_date,
        )

        # 创建统一消息格式
        message = Message(
            content=content,
            metadata=metadata,
        )

        return message
