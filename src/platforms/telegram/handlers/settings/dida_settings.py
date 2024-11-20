from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_settings import BaseSettingsHandler
from .....services.dida365.dida_api import DidaAPI
from .....services.dida365.dida_service import DidaService
from .....utils.exceptions import ServiceError
from .....services.dida365.auth.auth_manager import DidaAuthManager
import asyncio
import secrets
from datetime import datetime, timedelta
import time


class DidaSettingsHandler(BaseSettingsHandler):
    """滴答清单设置处理器"""

    def __init__(self):
        """初始化滴答清单设置处理器"""
        super().__init__()
        self.dida_service = DidaService()
        self.auth_manager = DidaAuthManager()
        self._temp_apis: Dict[str, DidaAPI] = {}  # 临时API实例
        self._auth_states: Dict[str, str] = {}  # 用户ID -> state映射

    def _cleanup_temp_api(self, user_id: str) -> None:
        """清理临时API实例"""
        if user_id in self._temp_apis:
            del self._temp_apis[user_id]

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理滴答清单设置命令"""
        try:
            await self.show_menu(update, context)
        except Exception as e:
            self.logger.error(f"处理滴答清单设置命令失败: {str(e)}")
            await update.message.reply_text("设置出错，请稍后重试")

    async def show_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """显示滴答清单设置菜单"""
        user_id = str(update.effective_user.id)
        client_id = (
            self.config_manager.get_user_value(user_id, "dida.client_id") or "未设置"
        )
        client_secret = (
            self.config_manager.get_user_value(user_id, "dida.client_secret")
            or "未设置"
        )
        token_info = await self.auth_manager.get_valid_token(user_id)

        # 处理敏感信息显示
        if client_id != "未设置":
            client_id = client_id[:4] + "*" * 4 + client_id[-4:]
        if client_secret != "未设置":
            client_secret = client_secret[:4] + "*" * 4 + client_secret[-4:]

        # 获取已保存的项目列表和默认标签
        projects = self.config_manager.get_user_value(user_id, "dida.projects") or []
        default_tag = (
            self.config_manager.get_user_value(user_id, "dida.default_tag") or "未设置"
        )

        # 构建项目列表文本
        projects_text = (
            "\n".join([f"• {p['name']}" for p in projects]) if projects else "暂无项目"
        )

        # 构建授权状态信息
        auth_status = "未授权"
        expires_info = ""
        if token_info:
            auth_status = f"已授权 {token_info.get_status_emoji()}"
            if not token_info.is_expired():
                expires_info = f"\n⏰ {token_info.get_expires_info()}"
            else:
                expires_info = "\n⚠️ 已过期，需要重新授权"

        text = (
            "✅ 滴答清单设置\n\n"
            f"🔑 Client ID: {client_id}\n"
            f"🔐 Client Secret: {client_secret}\n"
            f"🎫 授权状态: {auth_status}{expires_info}\n\n"
            f"🏷️ 默认标签: {default_tag}\n\n"
            "📁 已同步的项目:\n"
            f"{projects_text}\n\n"
            "选择要修改的选项:"
        )

        keyboard = []
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔑 设置 Client ID", callback_data="settings_dida_client_id"
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔐 设置 Client Secret", callback_data="settings_dida_client_secret"
                )
            ]
        )

        if client_id != "未设置" and client_secret != "未设置":
            if token_info and not token_info.is_expired():
                keyboard.extend(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 重新授权", callback_data="settings_dida_auth"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔄 刷新项目列表",
                                callback_data="settings_dida_refresh_projects",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🏷️ 设置默认标签", callback_data="settings_dida_tag"
                            )
                        ],
                    ]
                )
            else:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "✨ 开始授权", callback_data="settings_dida_auth"
                        )
                    ]
                )

        keyboard.append(
            [
                InlineKeyboardButton("🔙 返回", callback_data="settings"),
                InlineKeyboardButton("❌ 退出", callback_data="exit"),
            ]
        )

        await self.send_message(
            update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        query = update.callback_query
        data = query.data
        user_id = str(update.effective_user.id)

        try:
            self.logger.info(f"处理滴答清单设置回调: {data}")

            if data == "exit":
                # 清理临时API实例
                self._cleanup_temp_api(user_id)
                # 清除状态
                state_manager = context.bot_data.get('state_manager')
                if state_manager:
                    state_manager.clear_state(update.effective_user.id)
                # 清理所有消息
                await self.cleanup_messages(update, context)
                await query.answer("已退出设置")
                return

            # 其他回调处理
            if data == "settings_dida":
                await self.show_menu(update, context)
            elif data == "settings_dida_client_id":
                await self.prompt_client_id(update, context)
            elif data == "settings_dida_client_secret":
                await self.prompt_client_secret(update, context)
            elif data == "settings_dida_auth":
                await self.start_auth(update, context)
            elif data == "settings_dida_refresh_projects":
                await self.refresh_projects(update, context)
            elif data == "settings_dida_tag":
                await self.prompt_default_tag(update, context)
            elif data == "settings":
                # 清理临时API实例
                self._cleanup_temp_api(user_id)
                # 返回主设置菜单
                main_handler = MainSettingsHandler()
                await main_handler.show_menu(update, context)

            # 处理完成后应答回调查询
            await query.answer()

        except Exception as e:
            self.logger.error(f"处理滴答清单设置回调失败: {str(e)}", exc_info=True)
            await query.answer("处理设置失败", show_alert=True)

    async def prompt_client_id(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示输入 Client ID"""
        try:
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {"setting": "dida_client_id", "chat_id": update.effective_chat.id},
                    timeout=180.0,
                )

            text = (
                "🔑 请输入滴答清单 Client ID:\n\n"
                "1. 访问滴答清单发者平台\n"
                "2. 创建新应用\n"
                "3. 复制 Client ID\n"
                "4. 将 Client ID 发送给我"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_dida"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            # 直接发送或更新消息
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await self.send_message(
                    update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
                )

        except Exception as e:
            self.logger.error(f"显示Client ID设置提示失败: {str(e)}")
            await self.show_menu(update, context)

    async def prompt_client_secret(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示输入 Client Secret"""
        try:
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {
                        "setting": "dida_client_secret",
                        "chat_id": update.effective_chat.id,
                    },
                    timeout=180.0,
                )

            text = (
                "请输入滴答清单 Client Secret:\n\n"
                "1. 在应用详情页面\n"
                "2. 复制 Client Secret\n"
                "3. 将 Client Secret 发送给我"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_dida"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            # 直接发送或更新消息
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await self.send_message(
                    update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
                )

        except Exception as e:
            self.logger.error(f"显示Client Secret设置提示失败: {str(e)}")
            await self.show_menu(update, context)

    async def start_auth(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """开始OAuth认证流程"""
        user_id = str(update.effective_user.id)
        message_id = str(update.callback_query.message.message_id)

        try:
            self.logger.info(f"开始滴答清单授权流程: user_id={user_id}")

            # 设置更长的状态超时时间
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {"setting": "dida_auth", "chat_id": update.effective_chat.id},
                    timeout=300.0,  # 设置5分钟超时
                )

            # 检查配置
            client_id = self.config_manager.get_user_value(user_id, "dida.client_id")
            client_secret = self.config_manager.get_user_value(
                user_id, "dida.client_secret"
            )

            self.logger.info(
                f"当前配置状态 - Client ID: {bool(client_id)}, Client Secret: {bool(client_secret)}"
            )

            if not client_id or not client_secret:
                error_msg = "请先配置 Client ID 和 Client Secret"
                self.logger.warning(f"授权失败: {error_msg}")
                await update.callback_query.answer(error_msg, show_alert=True)
                return

            # 生成包含用户ID、消息ID和时间戳的state
            random_str = secrets.token_urlsafe(16)
            timestamp = str(time.time())  # 添加时间戳
            state = f"{user_id}:{message_id}:{timestamp}:{random_str}"
            self._auth_states[user_id] = state
            self.logger.info(f"生成state: {state}")

            try:
                # 取授权URL
                self.logger.info("正在获取授权URL...")
                auth_url = self.auth_manager.get_auth_url(user_id, state)
                self.logger.info(f"获取授权URL成功: {auth_url}")
            except Exception as e:
                error_msg = f"获取授权URL失败: {str(e)}"
                self.logger.error(error_msg)
                await update.callback_query.answer(error_msg, show_alert=True)
                return

            # 构建息文本
            text = (
                "🔐 滴答清单授权\n\n"
                "请在5分钟内完成以下步骤：\n\n"
                "1. 点击下方按钮打开授权页面\n"
                "2. 在打开的页面中登录滴答清单\n"
                "3. 点击授权按钮\n"
                "4. 等待跳转回来\n\n"
                "⚠️ 如果按钮无法打开，请复制下方链接在浏览器中打开：\n\n"
                f"`{auth_url}`\n\n"
                "⏰ 授权链接将在5分钟后过期"
            )

            # 构建按钮
            keyboard = [
                [InlineKeyboardButton("🌐 点击授权", url=auth_url)],
                [
                    InlineKeyboardButton(
                        "🔄 重新生成链接", callback_data="settings_dida_auth"
                    )
                ],
                [InlineKeyboardButton("🔙 返回", callback_data="settings_dida")],
                [InlineKeyboardButton("❌ 退出", callback_data="exit")],
            ]

            self.logger.info("正在发送授权消息...")

            # 先应答回调查询
            await update.callback_query.answer()

            # 发送或更新消息
            try:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                )
                self.logger.info("授权消息发送成功")
            except Exception as e:
                self.logger.warning(f"编辑消息失败，尝试发送新消息: {str(e)}")
                await self.send_menu(
                    update,
                    context,
                    text,
                    InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                )
                self.logger.info("新授权消息发送成功")

        except Exception as e:
            error_msg = f"开始授权失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            await update.callback_query.answer(error_msg, show_alert=True)

    async def handle_oauth_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理OAuth回调"""
        user_id = str(update.effective_user.id)
        query_params = context.args[0] if context.args else ""

        try:
            # 解析回调参数
            params = dict(param.split('=') for param in query_params.split('&'))
            code = params.get('code')
            state = params.get('state')

            # 验证state
            if not state or state != self._auth_states.get(user_id):
                raise ServiceError("无效的授权请求")

            # 交换访问令牌
            await self.auth_manager.exchange_code(user_id, code)

            # 清理state
            self._auth_states.pop(user_id, None)

            await update.message.reply_text(
                "✅ 授权成功！\n\n2秒后返回设置菜单...",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⚙️ 返回设置", callback_data="settings_dida"
                            )
                        ]
                    ]
                ),
            )

            await asyncio.sleep(2)
            await self.show_menu(update, context)

        except Exception as e:
            self.logger.error(f"处理OAuth回调失败: {str(e)}")
            await update.message.reply_text(
                f"❌ 授权失败: {str(e)}\n\n请重试",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 重新授权", callback_data="dida_auth"
                            ),
                            InlineKeyboardButton("❌ 退出", callback_data="exit"),
                        ]
                    ]
                ),
            )

    async def save_client_id(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: str
    ) -> None:
        """保存 Client ID

        Args:
            update: 更新对象
            context: 上下文对象
            client_id: 客户ID
        """
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            self.logger.info(f"开始保存 Client ID: {client_id[:4]}****{client_id[-4:]}")

            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id, text="🔄 正在保存 Client ID..."
            )

            # 保存配置
            self.config_manager.set_user_config(user_id, "dida.client_id", client_id)

            # 清除状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.clear_state(user_id)

            # 更新状态消息
            await status_message.edit_text(
                "✅ Client ID 已保存！\n\n2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)

            # 删除状态消息和用户的输入消息
            await status_message.delete()
            if update.message:
                try:
                    await update.message.delete()
                except Exception as e:
                    self.logger.warning(f"删除用户消息失败: {str(e)}")

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            error_msg = f"保存 Client ID 失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if status_message:
                await status_message.edit_text(f"❌ {error_msg}\n\n2秒后返回...")
                await asyncio.sleep(2)
                await status_message.delete()

            await self.prompt_client_id(update, context)

    async def save_client_secret(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_secret: str
    ) -> None:
        """保存 Client Secret

        Args:
            update: 更新对象
            context: 上下文对象
            client_secret: 客户密钥
        """
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            self.logger.info(
                f"开始保存 Client Secret: {client_secret[:4]}****{client_secret[-4:]}"
            )

            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id, text="🔄 正在保存 Client Secret..."
            )

            # 保存配置
            self.config_manager.set_user_config(
                user_id, "dida.client_secret", client_secret
            )

            # 清除状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.clear_state(user_id)

            # 更新状态消息
            await status_message.edit_text(
                "✅ Client Secret 已保存！\n\n2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)

            # 删除状态消息和用户的输入消息
            await status_message.delete()
            if update.message:
                try:
                    await update.message.delete()
                except Exception as e:
                    self.logger.warning(f"删除用户消息失败: {str(e)}")

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            error_msg = f"保存 Client Secret 失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if status_message:
                await status_message.edit_text(f"❌ {error_msg}\n\n2秒后返回...")
                await asyncio.sleep(2)
                await status_message.delete()

            await self.prompt_client_secret(update, context)

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理用户的设置输入"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text

        # 添加日志以便调试
        self.logger.info(f"处理用户消息: {text}")

        # 获取状态管理器
        state_manager = context.bot_data.get('state_manager')
        if not state_manager:
            self.logger.warning("状态管理器不存在")
            return

        # 获取当前状态
        state = state_manager.get_state(user_id)
        if not state:
            self.logger.warning(f"用户 {user_id} 没有活动状态")
            return

        # 获取设置类型
        setting = state.get("data", {}).get("setting")
        if not setting:
            self.logger.warning(f"用户 {user_id} 的状态中没有setting字段")
            return

        self.logger.info(f"当前设置状态: {setting}")

        try:
            if setting == "dida_client_id":
                await self.save_client_id(update, context, text)
            elif setting == "dida_client_secret":
                await self.save_client_secret(update, context, text)
            elif setting == "dida_default_tag":
                await self.save_default_tag(update, context, text)
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}", exc_info=True)
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 重试", callback_data=f"settings_dida_{setting}"
                    ),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]
            await update.message.reply_text(
                f"保存设置失败: {str(e)}", reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def refresh_projects(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """刷新项目列表"""
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔄 正在同步项目列表...\n\n" "• 获取访问令牌...",
            )

            # 获取有效的访问令牌
            token_info = await self.auth_manager.get_valid_token(user_id)
            if not token_info:
                raise ServiceError("无效的访问令牌")

            # 更新状态
            await status_message.edit_text(
                "🔄 正在同步项目列表...\n\n"
                "• 获取访问令牌... ✅\n"
                "• 获取项目列表..."
            )

            # 获取项目列表
            api = DidaAPI(token_info.access_token)
            try:
                projects = await api.get_projects()
            except Exception as e:
                self.logger.error(f"获取项目列表失败: {str(e)}", exc_info=True)
                raise

            # 更新状态
            await status_message.edit_text(
                "🔄 正在同步项目列表...\n\n"
                "• 获取访问令牌... ✅\n"
                "• 获取项目列表... ✅\n"
                "• 保存配置..."
            )

            # 保存项目列表
            self.config_manager.set_user_config(user_id, "dida.projects", projects)

            # 更新最终状态
            await status_message.edit_text(
                f"✅ 已同步 {len(projects)} 个项目！\n\n" "2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)

            # 删除状态消息
            await status_message.delete()

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            error_msg = f"同步项目失败: {str(e)}"
            if status_message:
                await status_message.edit_text(
                    f"❌ {error_msg}\n\n2秒后返回设置菜单..."
                )
                await asyncio.sleep(2)
                await status_message.delete()

            await self.show_menu(update, context)

    async def prompt_default_tag(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示设置默认标签"""
        try:
            # 设置状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {
                        "setting": "dida_default_tag",
                        "chat_id": update.effective_chat.id,
                    },
                    timeout=180.0,  # 3分钟超时
                )

            text = (
                "🏷️ 设置默认标签\n\n"
                "此标签将自动添加到通过机器人创建的所有任务中。\n\n"
                "• 直接发送标签名称\n"
                "• 发送空格或 - 可清除默认标签\n"
                "• 标签无需包含 # 符号\n\n"
                "示例：Bot任务"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_dida"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            await self.send_message(
                update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            self.logger.error(f"显示标签设置提示失败: {str(e)}")
            await self.show_menu(update, context)

    async def save_default_tag(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, tag: str
    ) -> None:
        """保存默认标签

        Args:
            update: 更新对象
            context: 上下文对象
            tag: 标签名称
        """
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            # 删除用户发送的消息
            await update.message.delete()

            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id, text="🔄 正在保存默认标签..."
            )

            # 处理清除标签情况
            if tag.strip() in [" ", "-"]:
                tag = ""
                status_text = "✅ 已清除默认标签！"
            else:
                status_text = "✅ 默认标签已保存！"

            # 保存配置
            self.config_manager.set_user_config(user_id, "dida.default_tag", tag)

            # 更新状态消息
            await status_message.edit_text(f"{status_text}\n\n2秒后返回设置菜单...")

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
            error_text = f"保存默认标签失败: {str(e)}"
            if status_message:
                await status_message.edit_text(f"❌ {error_text}\n\n2秒后返回...")
                await asyncio.sleep(2)
                await status_message.delete()

            # 返回到输入界面
            await self.prompt_default_tag(update, context)
