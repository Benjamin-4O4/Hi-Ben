from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import ContextTypes
from ....utils.logger import Logger
from ....utils.exceptions import PlatformError
import asyncio
from telegram.error import BadRequest


class TelegramBaseHandler(ABC):
    """Telegram 处理器基类"""

    def __init__(self):
        self.logger = Logger(f"telegram.handler.{self.__class__.__name__}")

    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理消息"""
        pass

    async def delete_command_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """删除命令消息"""
        try:
            if update.message:
                await update.message.delete()
        except Exception as e:
            self.logger.warning(f"删除命令消息失败: {str(e)}")

    async def send_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        **kwargs,
    ) -> Optional[Message]:
        """发送消息并记录消息ID

        Args:
            update: 更新对象
            context: 上下文对象
            text: 消息文本
            reply_markup: 键盘标记
            **kwargs: 其他参数

        Returns:
            Optional[Message]: 发送的消息对象
        """
        try:
            # 先清理旧消息
            await self.cleanup_messages(update, context)

            # 发送新消息
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                **kwargs,
            )

            # 记录新消息ID
            state_manager = context.bot_data.get('state_manager')
            if state_manager and message:
                state_manager.add_message(update.effective_user.id, message.message_id)

            return message

        except Exception as e:
            self.logger.error(f"发送消息失败: {str(e)}")
            # 如果是连接错误,尝试重新发送
            if "All connection attempts failed" in str(e):
                try:
                    await asyncio.sleep(1)  # 等待1秒后重试
                    return await self.send_message(
                        update, context, text, reply_markup, **kwargs
                    )
                except Exception as retry_e:
                    self.logger.error(f"重试发送消息失败: {str(retry_e)}")
                    raise PlatformError(f"发送消息失败: {str(retry_e)}")
            raise PlatformError(f"发送消息失败: {str(e)}")

    async def edit_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> None:
        """编辑消息"""
        if not update.callback_query:
            return

        try:
            await update.callback_query.edit_message_text(
                text=text, reply_markup=reply_markup
            )
        except Exception as e:
            self.logger.error(f"编辑消息失败: {str(e)}")
            raise PlatformError(f"编辑消息失败: {str(e)}")

    def create_keyboard(self, buttons: Dict[str, str]) -> InlineKeyboardMarkup:
        """创建内联键盘"""
        keyboard = []
        for text, callback_data in buttons.items():
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        return InlineKeyboardMarkup(keyboard)

    async def answer_callback(
        self, update: Update, text: Optional[str] = None, show_alert: bool = False
    ) -> None:
        """响应回调查询"""
        if not update.callback_query:
            return

        try:
            await update.callback_query.answer(text=text, show_alert=show_alert)
        except Exception as e:
            self.logger.error(f"响应回调失败: {str(e)}")
            raise PlatformError(f"响应回调失败: {str(e)}")

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        if not update.callback_query:
            return

        try:
            await self._process_callback(update, context)
        except Exception as e:
            self.logger.error(f"处理回调失败: {str(e)}")
            await update.callback_query.answer("处理失败", show_alert=True)

    @abstractmethod
    async def _process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理具体的回调逻辑"""
        pass

    async def cleanup_messages(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """清理用户的所有菜单消息和命令消息"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id

            # 先删除当前命令消息
            if update.message:
                try:
                    await update.message.delete()
                except BadRequest as e:
                    if "message to delete not found" not in str(e).lower():
                        self.logger.warning(f"删除命令消息失败: {str(e)}")
                except Exception as e:
                    self.logger.warning(f"删除命令消息失败: {str(e)}")

            # 再删除其他消息
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                message_ids = state_manager.get_user_messages(user_id)
                if message_ids:
                    for msg_id in message_ids:
                        try:
                            await context.bot.delete_message(
                                chat_id=chat_id, message_id=msg_id
                            )
                        except BadRequest as e:
                            if "message to delete not found" not in str(e).lower():
                                self.logger.warning(f"删除消息 {msg_id} 失败: {str(e)}")
                        except Exception as e:
                            self.logger.warning(f"删除消息 {msg_id} 失败: {str(e)}")

                    # 清空该用户的消息记录
                    state_manager.clear_user_messages(user_id)

        except Exception as e:
            self.logger.error(f"清理消息失败: {str(e)}")
