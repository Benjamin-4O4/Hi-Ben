from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_settings import BaseSettingsHandler
from .notion_settings import NotionSettingsHandler
from .dida_settings import DidaSettingsHandler
from .profile_settings import ProfileSettingsHandler  # 添加导入
import asyncio


class MainSettingsHandler(BaseSettingsHandler):
    """主设置处理器"""

    def __init__(self):
        super().__init__()
        self._notion_handler = NotionSettingsHandler()  # 创建单例
        self._dida_handler = DidaSettingsHandler()  # 添加滴答清单处理器
        self._profile_handler = ProfileSettingsHandler()  # 添加个人信息处理器

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理设置命令"""
        try:
            # 记录命令消息ID
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.add_message(
                    update.effective_user.id, update.message.message_id
                )

            # 显示设置菜单
            await self.show_menu(update, context)
        except Exception as e:
            self.logger.error(f"处理设置命令失败: {str(e)}")
            await update.message.reply_text("设置出错，请稍后重试")

    async def show_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """显示主设置菜单"""
        text = "⚙️ 设置\n\n请选择要设置的项目:"

        keyboard = [
            [InlineKeyboardButton("📝 Notion设置", callback_data="settings_notion")],
            [InlineKeyboardButton("✅ 滴答清单设置", callback_data="settings_dida")],
            [InlineKeyboardButton("👤 个人信息", callback_data="settings_profile")],
            [InlineKeyboardButton("❌ 退出", callback_data="exit")],
        ]

        await self.send_message(
            update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        query = update.callback_query
        data = query.data

        try:
            self.logger.info(f"主设置处理器收到回调: {data}")

            if data == "exit":
                self.logger.info("处理退出回调")
                state_manager = context.bot_data.get('state_manager')
                if state_manager:
                    state_manager.clear_state(update.effective_user.id)
                await query.message.delete()
                await query.answer("已退出设置")
                return

            if data == "settings":
                self.logger.info("显示主设置菜单")
                await self.show_menu(update, context)
            elif data.startswith("settings_notion"):
                self.logger.info(f"转发到 Notion 处理器: {data}")
                await self._notion_handler.process_callback(update, context)
            elif data.startswith("settings_dida"):
                self.logger.info(f"转发到滴答清单处理器: {data}")
                await self._dida_handler.process_callback(update, context)
            elif data.startswith("settings_profile"):
                self.logger.info(f"转发到个人信息处理器: {data}")
                await self._profile_handler.process_callback(update, context)
            else:
                self.logger.warning(f"未知的回调数据: {data}")
                await query.answer("未知的操作", show_alert=True)
                return

            await query.answer()

        except Exception as e:
            self.logger.error(f"处理回调失败: {str(e)}", exc_info=True)
            await query.answer("处理失败", show_alert=True)

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理用户的设置输入"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text

        # 从 state_manager 获取状态
        state = context.bot_data.get('state_manager').get_state(user_id)
        if not state:
            return

        setting = state["data"].get("setting")
        if not setting:
            return

        try:
            # 根据不同的设置状态路由到对应的处理器
            if setting.startswith("notion_"):
                # 转发给 Notion 设置处理器
                await self._notion_handler.handle_message(update, context)
            elif setting.startswith("dida_"):
                # 转发给滴答清单设置处理器
                await self._dida_handler.handle_message(update, context)
            elif setting.startswith("user_profile"):
                # 转发给个人信息设置处理器
                await self._profile_handler.handle_message(update, context)
            else:
                self.logger.warning(f"未知的设置状态: {setting}")

        except Exception as e:
            self.logger.error(f"处理设置消息失败: {str(e)}")
            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]
            await update.message.reply_text(
                f"处理设置失败: {str(e)}", reply_markup=InlineKeyboardMarkup(keyboard)
            )
