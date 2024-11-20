from typing import Optional, List, Dict
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


class MediaProcessor(BaseProcessor):
    """媒体消息处理器"""

    async def process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[Message]:
        """处理媒体消息"""
        if not update.message:
            return None

        # 提取媒体信息
        media_info = await self._extract_media_info(update.message)

        # 确定消息类型
        message_type = (
            MessageType.MEDIA_GROUP
            if update.message.media_group_id
            else MessageType.IMAGE
        )

        # 创建消息内容
        content = MessageContent(
            type=message_type, data=media_info, raw_data=update.message.to_dict()
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
            media_group_id=update.message.media_group_id,
        )

        # 提取文件信息
        files = await self._extract_files(update.message)

        # 创建统一消息格式
        message = Message(
            content=content,
            metadata=metadata,
            files=files,
        )

        return message

    async def _extract_media_info(self, message: TGMessage) -> Dict:
        """提取媒体信息"""
        media_info = {
            'caption': message.caption,
            'media_group_id': message.media_group_id,
        }

        if message.photo:
            photo = message.photo[-1]  # 获取最大尺寸的图片
            media_info.update(
                {
                    'type': 'photo',
                    'width': photo.width,
                    'height': photo.height,
                    'file_size': photo.file_size,
                }
            )
        elif message.video:
            media_info.update(
                {
                    'type': 'video',
                    'duration': message.video.duration,
                    'width': message.video.width,
                    'height': message.video.height,
                    'mime_type': message.video.mime_type,
                    'file_size': message.video.file_size,
                }
            )

        return media_info

    async def _extract_files(self, message: TGMessage) -> List[Dict]:
        """提取文件信息"""
        files = []

        if message.photo:
            photo = message.photo[-1]
            files.append(
                {
                    'type': 'photo',
                    'file_id': photo.file_id,
                    'file_unique_id': photo.file_unique_id,
                    'width': photo.width,
                    'height': photo.height,
                    'file_size': photo.file_size,
                    'thumbnail': self._extract_thumbnail(photo),
                }
            )
        elif message.video:
            files.append(
                {
                    'type': 'video',
                    'file_id': message.video.file_id,
                    'file_unique_id': message.video.file_unique_id,
                    'duration': message.video.duration,
                    'width': message.video.width,
                    'height': message.video.height,
                    'mime_type': message.video.mime_type,
                    'file_size': message.video.file_size,
                    'thumbnail': self._extract_thumbnail(message.video.thumbnail),
                }
            )

        return files

    def _extract_thumbnail(self, thumbnail) -> Optional[Dict]:
        """提取缩略图信息"""
        if not thumbnail:
            return None

        return {
            'file_id': thumbnail.file_id,
            'file_unique_id': thumbnail.file_unique_id,
            'width': thumbnail.width,
            'height': thumbnail.height,
            'file_size': thumbnail.file_size,
        }
