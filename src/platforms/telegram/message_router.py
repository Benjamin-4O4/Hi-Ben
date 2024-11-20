from typing import Optional, Dict, List, Callable, Awaitable
from telegram import Update, Bot
from telegram.ext import ContextTypes
import asyncio
from ...utils.logger import Logger
from ...core.models.message import (
    Message,
    MessageType,
    MessageContent,
    MessageMetadata,
    MessageSource,
)
from ...agents.media_processor_agent import MediaProcessorAgent
from ...agents.note_taker_agent import NoteTakerAgent
from .state_manager import TelegramStateManager


class MessageRouter:
    """消息路由器"""

    def __init__(
        self,
        start_handler=None,
        help_handler=None,
        settings_handler=None,
        state_manager: Optional[TelegramStateManager] = None,
    ):
        self.logger = Logger("telegram.router")
        self.start_handler = start_handler
        self.help_handler = help_handler
        self.settings_handler = settings_handler
        self.state_manager = state_manager

        self.bot = None
        self.media_processor = None
        self.note_taker = None

    def set_bot(self, bot: Bot) -> None:
        """设置 Bot 实例"""
        self.bot = bot
        if self.state_manager:
            self.state_manager.bot = bot

    def set_agents(
        self, media_processor: MediaProcessorAgent, note_taker: NoteTakerAgent
    ) -> None:
        """设置智能体

        Args:
            media_processor: 媒体处理智能体
            note_taker: 笔记处理智能体
        """
        self.media_processor = media_processor
        self.note_taker = note_taker
        self.logger.info("智能体设置完成")

    async def route(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """路由消息

        Args:
            update: Telegram更新对象
            context: 上下文对象
        """
        if not update.message:
            return

        try:
            # 检查是否是设置状态下的消息
            if await self._check_settings_state(update, context):
                return

            # 检查是否是媒体组消息
            if update.message.media_group_id:
                await self._handle_media_group_message(update, context)
                return

            # 处理普通消息
            await self._process_message(update, context)

        except Exception as e:
            self.logger.error(f"路由消息失败: {e}")
            if update.message:
                await update.message.reply_text("❌ 处理消息时出现错误，请稍后重试")

    async def route_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """路由回调查询"""
        if not update.callback_query:
            return

        try:
            query = update.callback_query
            data = query.data

            # 根据回调数据路由到对应的处理器
            if data == "settings" or data.startswith("settings_"):
                await self.settings_handler.handle_callback(update, context)
            elif data == "help":
                await self.help_handler.handle_callback(update, context)
            elif data == "exit":
                await self._handle_exit_callback(update, context)
            else:
                await query.answer("未知的回调")

        except Exception as e:
            self.logger.error(f"处理回调失败: {e}")
            await update.callback_query.answer("处理失败", show_alert=True)

    async def _check_settings_state(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """检查是否是设置状态下的消息"""
        if not update.message or not update.message.text:
            return False

        user_id = update.effective_user.id
        state = self.state_manager.get_state(user_id)

        if state and "setting" in state["data"]:
            try:
                await self.settings_handler.handle_message(update, context)
                return True
            except Exception as e:
                self.logger.error(f"处理设置消息失败: {e}")
                await update.message.reply_text("处理设置失败，请重试")
                return True

        return False

    async def _process_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理单条消息"""
        try:
            self.logger.debug(f"开始处理消息: {update.message}")

            # 确保智能体已设置
            if not self.media_processor or not self.note_taker:
                raise ValueError("智能体未初始化")

            # 获取消息类型和转换消息格式
            message_type = self._get_message_type(update.message)
            message = await self._convert_to_message(update.message)
            self.logger.debug(f"消息类型: {message_type}, 转换后的消息: {message}")

            # 如果是语音或媒体消息，先进行处理
            if message_type in [MessageType.VOICE, MessageType.AUDIO, MessageType.IMAGE]:
                result = await self.media_processor.process(message=message)
                text_content = result.get("text", "")
                media_files = result.get("media_files", [])
            else:
                text_content = update.message.text or ""
                media_files = []

            # 交给笔记处理智能体，使用状态管理器
            results = await self.note_taker.process(
                message=message,
                telegram_status_updater=self.state_manager
            )

            # 处理结果
            if results:
                # 格式化结果消息
                result_text = "✅ 处理完成\n\n"
                if isinstance(results, dict):
                    for key, value in results.items():
                        if isinstance(value, str) and value.strip():
                            result_text += f"{value}\n"
                elif isinstance(results, (list, tuple)):
                    result_text += "\n".join(str(r) for r in results if str(r).strip())
                else:
                    result_text += str(results)
                
                # 发送结果消息，引用原始消息
                await update.message.reply_text(
                    result_text,
                    reply_to_message_id=update.message.message_id
                )

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}", exc_info=True)
            # 发送错误消息，引用原始消息
            await update.message.reply_text(
                f"❌ 处理失败: {str(e)}",
                reply_to_message_id=update.message.message_id
            )

    def _get_message_type(self, message) -> MessageType:
        """获取消息类型"""
        if message.voice:
            return MessageType.VOICE
        elif message.audio:
            return MessageType.AUDIO
        elif message.photo:
            return MessageType.IMAGE
        elif message.document:
            return MessageType.FILE
        elif message.text:
            return MessageType.TEXT
        return MessageType.UNKNOWN

    async def _convert_to_message(self, tg_message) -> Message:
        """转换为统一消息格式

        Args:
            tg_message: Telegram消息对象

        Returns:
            Message: 统一消息格式
        """
        try:
            # 获取消息类型
            message_type = self._get_message_type(tg_message)

            # 提取消息内容
            content_data = {}
            files = []

            if message_type == MessageType.TEXT:
                content_data = {
                    "text": tg_message.text,
                    "entities": [
                        {
                            "type": entity.type,
                            "offset": entity.offset,
                            "length": entity.length,
                        }
                        for entity in (tg_message.entities or [])
                    ],
                }

            elif message_type == MessageType.VOICE:
                voice = tg_message.voice
                content_data = {
                    "file_id": voice.file_id,
                    "duration": voice.duration,
                    "mime_type": voice.mime_type,
                    "file_size": voice.file_size,
                }
                # 获取文件路径
                if self.bot:
                    file = await self.bot.get_file(voice.file_id)
                    content_data["file_path"] = file.file_path

            elif message_type == MessageType.AUDIO:
                audio = tg_message.audio
                content_data = {
                    "file_id": audio.file_id,
                    "duration": audio.duration,
                    "mime_type": audio.mime_type,
                    "file_size": audio.file_size,
                    "title": audio.title,
                    "performer": audio.performer,
                }
                # 获取文件路径
                if self.bot:
                    file = await self.bot.get_file(audio.file_id)
                    content_data["file_path"] = file.file_path

            elif message_type == MessageType.IMAGE:
                photo = max(tg_message.photo, key=lambda x: x.file_size)
                content_data = {
                    "file_id": photo.file_id,
                    "width": photo.width,
                    "height": photo.height,
                    "file_size": photo.file_size,
                    "caption": tg_message.caption,
                }
                # 获取文件路径
                if self.bot:
                    file = await self.bot.get_file(photo.file_id)
                    content_data["file_path"] = file.file_path
                    files.append(
                        {
                            "type": "image",
                            "path": file.file_path,
                            "mime_type": "image/jpeg",
                            "file_size": photo.file_size,
                            "description": tg_message.caption,
                        }
                    )

            elif message_type == MessageType.FILE:
                doc = tg_message.document
                content_data = {
                    "file_id": doc.file_id,
                    "file_name": doc.file_name,
                    "mime_type": doc.mime_type,
                    "file_size": doc.file_size,
                    "caption": tg_message.caption,
                }
                # 获取文件路径
                if self.bot:
                    file = await self.bot.get_file(doc.file_id)
                    content_data["file_path"] = file.file_path
                    files.append(
                        {
                            "type": "file",
                            "path": file.file_path,
                            "mime_type": doc.mime_type,
                            "file_size": doc.file_size,
                            "file_name": doc.file_name,
                            "description": tg_message.caption,
                        }
                    )

            # 创建消息内容
            content = MessageContent(type=message_type, data=content_data)

            # 创建消息元数据
            metadata = MessageMetadata(
                message_id=str(tg_message.message_id),
                platform="telegram",
                chat_id=str(tg_message.chat_id),
                user_id=str(tg_message.from_user.id) if tg_message.from_user else None,
                timestamp=tg_message.date,
                source=MessageSource.USER,
                reply_to=(
                    str(tg_message.reply_to_message.message_id)
                    if tg_message.reply_to_message
                    else None
                ),
                edit_date=tg_message.edit_date,
                forward_from=(
                    {
                        "chat_id": str(
                            getattr(tg_message, 'forward_from_chat', {}).get('id', '')
                        ),
                        "message_id": str(
                            getattr(tg_message, 'forward_from_message_id', '')
                        ),
                    }
                    if hasattr(tg_message, 'forward_from_chat')
                    and tg_message.forward_from_chat
                    else None
                ),
                attributes={
                    "media_group_id": getattr(tg_message, 'media_group_id', None),
                    "has_protected_content": getattr(
                        tg_message, 'has_protected_content', False
                    ),
                    "author_signature": getattr(tg_message, 'author_signature', None),
                },
            )

            # 创建统一消息格式
            message = Message(content=content, metadata=metadata, files=files)

            return message

        except Exception as e:
            self.logger.error(f"转换消息格式失败: {e}")
            raise

    async def _handle_exit_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理退出回调"""
        query = update.callback_query
        if not query:
            return

        try:
            # 删除消息
            await query.message.delete()
            await query.answer("已退出")
        except Exception as e:
            self.logger.error(f"处理退出回调失败: {e}")
            await query.answer("退出失败", show_alert=True)
