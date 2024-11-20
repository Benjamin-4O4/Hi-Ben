from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_settings import BaseSettingsHandler
import asyncio


class ProfileSettingsHandler(BaseSettingsHandler):
    """个人信息设置处理器"""

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理个人信息设置命令"""
        try:
            await self.show_menu(update, context)
        except Exception as e:
            self.logger.error(f"处理个人信息设置命令失败: {str(e)}")
            await update.message.reply_text("设置出错，请稍后重试")

    async def show_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """显示个人信息设置菜单"""
        user_id = str(update.effective_user.id)
        profile = (
            self.config_manager.get_user_value(user_id, "user.profile") or "未设置"
        )

        # 如果个人信息太长，只显示部分
        if profile != "未设置" and len(profile) > 100:
            profile = profile[:97] + "..."

        text = (
            "👤 个人信息设置\n\n"
            "个人信息将帮助AI更好地理解你的背景和需求。\n\n"
            f"当前个人信息:\n{profile}\n\n"
            "点击下方按钮修改个人信息"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "✏️ 修改个人信息", callback_data="settings_profile_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑 清除个人信息", callback_data="settings_profile_clear"
                )
            ],
            [
                InlineKeyboardButton("🔙 返回", callback_data="settings"),
                InlineKeyboardButton("❌ 退出", callback_data="exit"),
            ],
        ]

        await self.send_message(
            update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def clear_profile(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """清除个人信息"""
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id, text="🔄 正在清除个人信息..."
            )

            # 清除配置
            self.config_manager.set_user_config(user_id, "user.profile", "")

            # 更新状态消息
            await status_message.edit_text(
                "✅ 已清除个人信息！\n\n2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)

            # 删除状态消息
            await status_message.delete()

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            error_text = f"清除个人信息失败: {str(e)}"
            if status_message:
                await status_message.edit_text(f"❌ {error_text}\n\n2秒后返回...")
                await asyncio.sleep(2)
                await status_message.delete()
            await self.show_menu(update, context)

    async def prompt_profile(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示输入个人信息"""
        try:
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {
                        "setting": "user_profile",
                        "chat_id": update.effective_chat.id,
                    },
                    timeout=300.0,  # 5分钟超时
                )

            text = (
                "✏️ 请输入你的个人信息:\n\n"
                "可以包含以下内容:\n"
                "• 职业背景\n"
                "• 兴趣爱好\n"
                "• 工作领域\n"
                "• 使用场景\n"
                "• 特殊需求\n\n"
                "示例:\n"
                "我是一名软件工程师，主要做后端开发，对AI和自动化工具感兴趣。"
                "平时喜欢研究新技术，需要记录学习笔记和项目想法。\n\n"
                "📝 直接发送文本即可"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_profile"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            await self.send_message(
                update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            self.logger.error(f"显示个人信息设置提示失败: {str(e)}")
            await self.show_menu(update, context)

    async def save_profile(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, profile: str
    ) -> None:
        """保存个人信息"""
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            # 先清理所有旧消息（包括菜单和用户输入）
            await self.cleanup_messages(update, context)

            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id, text="🔄 正在保存个人信息..."
            )

            # 保存配置
            self.config_manager.set_user_config(user_id, "user.profile", profile)

            # 更新状态消息
            await status_message.edit_text(
                "✅ 个人信息已保存！\n\n2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)

            # 删除状态消息
            await status_message.delete()

            # 清除状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.clear_state(update.effective_user.id)

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            error_text = f"保存个人信息失败: {str(e)}"
            if status_message:
                await status_message.edit_text(f"❌ {error_text}\n\n2秒后返回...")
                await asyncio.sleep(2)
                await status_message.delete()
            await self.prompt_profile(update, context)

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理用户的设置输入"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text

        state = context.bot_data.get('state_manager').get_state(user_id)
        if not state:
            return

        setting = state["data"].get("setting")
        if not setting:
            return

        try:
            if setting == "user_profile":
                await self.save_profile(update, context, text)
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}")
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 重试", callback_data="settings_profile_edit"
                    ),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]
            await update.message.reply_text(
                f"保存设置失败: {str(e)}", reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        query = update.callback_query
        data = query.data

        try:
            self.logger.info(f"处理个人信息设置回调: {data}")

            if data == "exit":
                # 清除状态
                state_manager = context.bot_data.get('state_manager')
                if state_manager:
                    state_manager.clear_state(update.effective_user.id)
                # 清理所有消息
                await self.cleanup_messages(update, context)
                await query.answer("已退出设置")
                return

            if data == "settings_profile":
                await self.show_menu(update, context)
            elif data == "settings_profile_edit":
                await self.prompt_profile(update, context)
            elif data == "settings_profile_clear":
                # 直接清除用户的个人信息设置
                user_id = str(update.effective_user.id)
                self.config_manager.set_user_config(user_id, "user.profile", "")

                # 发送临时提示消息
                status_message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="✅ 已清除个人信息！\n\n2秒后返回设置菜单...",
                )

                # 等待2秒
                await asyncio.sleep(2)

                # 删除提示消息
                await status_message.delete()

                # 返回设置菜单
                await self.show_menu(update, context)
            elif data == "settings":
                # 返回主设置菜单
                from .main_settings import MainSettingsHandler

                main_handler = MainSettingsHandler()
                await main_handler.show_menu(update, context)

            await query.answer()

        except Exception as e:
            self.logger.error(f"处理个人信息设置回调失败: {str(e)}", exc_info=True)
            await query.answer("处理设置失败", show_alert=True)
