from typing import Optional, Dict
from datetime import datetime
from telegram import Update, Message as TGMessage
from telegram.ext import ContextTypes
from .base_processor import BaseProcessor
from ....core.models.message import (
    Message,
    MessageType,
    MessageContent,
    MessageMetadata,
    MessageSource,
)


class FileProcessor(BaseProcessor):
    """文件消息处理器"""

    async def process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[Message]:
        """处理文件消息"""
        if not update.message or not update.message.document:
            return None

        # 提取文件信息
        file_info = await self._extract_file_info(update.message)

        # 创建消息内容
        content = MessageContent(type=MessageType.FILE, data=file_info)

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
        )

        # 创建统一消息格式
        message = Message(
            content=content,
            metadata=metadata,
        )

        return message

    async def _extract_file_info(self, message: TGMessage) -> Dict:
        """提取文件信息

        Args:
            message: Telegram消息对象

        Returns:
            Dict: 文件信息字典
        """
        doc = message.document
        return {
            'file_id': doc.file_id,
            'file_unique_id': doc.file_unique_id,
            'file_name': doc.file_name,
            'mime_type': doc.mime_type,
            'file_size': doc.file_size,
            'thumbnail': self._extract_thumbnail(doc.thumbnail),
            'caption': message.caption,
        }

    def _extract_thumbnail(self, thumbnail) -> Optional[Dict]:
        """提取缩略图信息

        Args:
            thumbnail: Telegram缩略图对象

        Returns:
            Optional[Dict]: 缩略图信息字典
        """
        if not thumbnail:
            return None

        return {
            'file_id': thumbnail.file_id,
            'file_unique_id': thumbnail.file_unique_id,
            'width': thumbnail.width,
            'height': thumbnail.height,
            'file_size': thumbnail.file_size,
        }
