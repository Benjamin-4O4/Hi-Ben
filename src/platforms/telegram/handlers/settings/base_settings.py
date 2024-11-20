from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes
from ..base_handler import TelegramBaseHandler
from .....utils.config_manager import ConfigManager
from abc import ABC, abstractmethod


class BaseSettingsHandler(TelegramBaseHandler, ABC):
    """设置处理器基类"""

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()

    def create_keyboard(self, buttons: Dict[str, str]) -> InlineKeyboardMarkup:
        """创建设置菜单键盘"""
        keyboard = []
        for text, callback_data in buttons.items():
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

        # 添加返回和退出按钮
        keyboard.append(
            [
                InlineKeyboardButton("🔙 返回", callback_data="settings"),
                InlineKeyboardButton("❌ 退出", callback_data="exit"),
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    async def handle_timeout(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理超时"""
        await self.send_message(
            update,
            context,
            "⌛️ 设置已超时，请重新开始",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⚙️ 重新设置", callback_data="settings")]]
            ),
        )

    async def update_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        keyboard: InlineKeyboardMarkup,
    ) -> None:
        """更新现有菜单消息,如果失败则发送新消息

        Args:
            update: 更新对象
            context: 上下文对象
            text: 消息文本
            keyboard: 键盘标记
        """
        try:
            # 先清理旧消息
            await self.cleanup_messages(update, context)

            # 发送新消息
            await self.send_message(update, context, text, reply_markup=keyboard)
        except Exception as e:
            self.logger.error(f"更新菜单失败: {str(e)}")
            # 如果更新失败,发送新消息
            await self.send_message(update, context, text, reply_markup=keyboard)

    async def _process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        query = update.callback_query
        if query.data == "exit":
            # 清除状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.clear_state(update.effective_user.id)
            # 清理所有消息
            await self.cleanup_messages(update, context)
            await query.answer("已退出设置")
        else:
            await query.answer()

    @abstractmethod
    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理用户的设置输入"""
        pass
