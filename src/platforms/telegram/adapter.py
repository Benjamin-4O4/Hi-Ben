from typing import Optional, Union, Dict, Any, List
from datetime import datetime
import asyncio
from telegram import Bot, Update, Message as TGMessage
from telegram.ext import Application, ContextTypes
from ...core.models.message import Message, MessageType
from ...core.models.platform import PlatformAdapter
from ...utils.logger import Logger
from ...utils.config import Config
from ...utils.exceptions import PlatformError
from .telegram_bot import TelegramBot


class TelegramAdapter(PlatformAdapter):
    """Telegram平台适配器

    负责:
    1. 统一平台接口
    2. 消息格式转换
    3. 平台特性适配
    4. 错误处理和转换
    """

    def __init__(self):
        self.logger = Logger(__name__)
        self.config = Config()
        self.bot = TelegramBot()

    async def initialize(self) -> None:
        """初始化适配器"""
        try:
            await self.bot.initialize()
            self.logger.info("Telegram适配器初始化完成")
        except Exception as e:
            self.logger.error(f"初始化Telegram适配器失败: {str(e)}")
            raise PlatformError(f"初始化失败: {str(e)}")

    async def start(self) -> None:
        """启动服务"""
        try:
            await self.bot.start()
        except Exception as e:
            self.logger.error(f"启动Telegram服务失败: {str(e)}")
            raise PlatformError(f"启动失败: {str(e)}")

    async def stop(self) -> None:
        """停止服务"""
        try:
            await self.bot.stop()
        except Exception as e:
            self.logger.error(f"停止Telegram服务失败: {str(e)}")
            raise PlatformError(f"停止失败: {str(e)}")

    async def send_message(
        self,
        chat_id: str,
        message: Union[str, Message],
        reply_to: Optional[Message] = None,
    ) -> Message:
        """发送消息

        Args:
            chat_id: 聊天ID
            message: 消息内容
            reply_to: 回复的消息

        Returns:
            Message: 发送的消息
        """
        try:
            if isinstance(message, str):
                # 创建统一消息格式
                message = Message(
                    type=MessageType.TEXT,
                    content={"text": message},
                    metadata={
                        "chat_id": chat_id,
                        "reply_to": reply_to.metadata.message_id if reply_to else None,
                    },
                )

            # 发送消息
            tg_message = await self.bot.send_message(
                chat_id=chat_id,
                text=message.content.get("text", ""),
                reply_to_message_id=message.metadata.get("reply_to"),
            )

            # 转换回统一格式
            return await self._convert_to_message(tg_message)

        except Exception as e:
            self.logger.error(f"发送消息失败: {str(e)}")
            raise PlatformError(f"发送消息失败: {str(e)}")

    async def edit_message(
        self, chat_id: str, message_id: str, new_content: Union[str, Message]
    ) -> Message:
        """编辑消息

        Args:
            chat_id: 聊天ID
            message_id: 消息ID
            new_content: 新的消息内容

        Returns:
            Message: 编辑后的消息
        """
        try:
            if isinstance(new_content, str):
                new_content = Message(
                    type=MessageType.TEXT,
                    content={"text": new_content},
                    metadata={
                        "chat_id": chat_id,
                        "message_id": message_id,
                    },
                )

            # 编辑消息
            tg_message = await self.bot.edit_message(
                chat_id=chat_id,
                message_id=message_id,
                text=new_content.content.get("text", ""),
            )

            return await self._convert_to_message(tg_message)

        except Exception as e:
            self.logger.error(f"编辑消息失败: {str(e)}")
            raise PlatformError(f"编辑消息失败: {str(e)}")

    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """删除消息

        Args:
            chat_id: 聊天ID
            message_id: 消息ID

        Returns:
            bool: 是否删除成功
        """
        try:
            return await self.bot.delete_message(chat_id, message_id)
        except Exception as e:
            self.logger.error(f"删除消息失败: {str(e)}")
            raise PlatformError(f"删除消息失败: {str(e)}")

    async def _convert_to_message(self, tg_message: TGMessage) -> Message:
        """转换Telegram消息为统一格式

        Args:
            tg_message: Telegram消息对象

        Returns:
            Message: 统一格式的消息对象
        """
        # 获取消息类型和内容
        message_type = self._get_message_type(tg_message)
        content = await self._extract_content(tg_message)

        # 创建元数据
        metadata = {
            "message_id": str(tg_message.message_id),
            "chat_id": str(tg_message.chat_id),
            "user_id": str(tg_message.from_user.id if tg_message.from_user else None),
            "timestamp": tg_message.date,
            "platform": "telegram",
        }

        return Message(
            type=message_type,
            content=content,
            metadata=metadata,
        )

    def _get_message_type(self, message: TGMessage) -> MessageType:
        """获取消息类型"""
        # ... 实现消息类型判断逻辑 ...
        pass

    async def _extract_content(self, message: TGMessage) -> Dict[str, Any]:
        """提取消息内容"""
        # ... 实现内容提取逻辑 ...
        pass
