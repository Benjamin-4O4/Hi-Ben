from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_settings import BaseSettingsHandler
from .....services.notion.notion_api import NotionAPI
from .....services.notion.notion_service import NotionService
from .....utils.exceptions import ServiceError
import asyncio


class NotionSettingsHandler(BaseSettingsHandler):
    """Notion 设置处理器"""

    def __init__(self):
        super().__init__()
        self.notion_service = NotionService()
        self._temp_apis: Dict[str, NotionAPI] = {}  # 临时API实例

    def _cleanup_temp_api(self, user_id: str) -> None:
        """清理临时API实例"""
        if user_id in self._temp_apis:
            del self._temp_apis[user_id]

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 Notion 设置命令"""
        try:
            await self.show_menu(update, context)
        except Exception as e:
            self.logger.error(f"处理 Notion 设置命令失败: {str(e)}")
            await update.message.reply_text("设置出错，请稍后重试")

    async def show_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """显示 Notion 设置菜单"""
        user_id = str(update.effective_user.id)
        notion_key = (
            self.config_manager.get_user_value(user_id, "notion.api_key") or "未设置"
        )
        notion_page = (
            self.config_manager.get_user_value(user_id, "notion.page_id") or "未设置"
        )
        notion_database = (
            self.config_manager.get_user_value(user_id, "notion.database_id")
            or "未设置"
        )

        # 处理敏感信息显示
        if notion_key != "未设置":
            notion_key = notion_key[:4] + "*" * 4 + notion_key[-4:]
        if notion_page != "未设置":
            notion_page = notion_page[:4] + "*" * 4 + notion_page[-4:]
        if notion_database != "未设置":
            notion_database = notion_database[:4] + "*" * 4 + notion_database[-4:]

        text = (
            "📝 Notion 设置\n\n"
            f"🔑 API Key: {notion_key}\n"
            f"📄 Page ID: {notion_page}\n"
            f"🗄️ Database ID: {notion_database}\n\n"
            "选择要修改的选项:"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔑 设置 API Key", callback_data="settings_notion_key"
                )
            ],
            [
                InlineKeyboardButton(
                    "📄 设置 Page ID", callback_data="settings_notion_page"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗄️ 设置 Database ID", callback_data="settings_notion_database"
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

    async def prompt_api_key(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示输入 API Key"""
        try:
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {
                        "setting": "notion_key",
                        "chat_id": update.effective_chat.id,
                    },
                    timeout=180.0,  # 3分钟超时
                )

            text = (
                "🔑 请输入你的 Notion API Key:\n\n"
                "1. 访问 https://www.notion.so/my-integrations\n"
                "2. 点击 '新建集成'\n"
                "3. 填写名称并选择关联的工作区\n"
                "4. 复制生成的 API Key\n"
                "5. 将 API Key 发送给我"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_notion"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            await self.send_message(
                update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            self.logger.error(f"显示API Key设置提示失败: {str(e)}")
            await self.show_menu(update, context)

    async def prompt_page_id(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示输入 Page ID"""
        try:
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {
                        "setting": "notion_page",
                        "chat_id": update.effective_chat.id,
                    },
                    timeout=120.0,  # 2分钟超时
                )

            text = (
                "📄 请输入 Notion Page ID:\n\n"
                "1. 打开你的 Notion 页面\n"
                "2. 从页面 URL 中复制 ID\n"
                "例如: https://www.notion.so/Page-Title-13c261ba...\n"
                "其中 13c261ba... 就是 Page ID\n\n"
                "⚠️注意⚠️：确保该页面已经与你的集成共享"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_notion"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            await self.send_message(
                update, context, text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            self.logger.error(f"显示Page ID设置提示失败: {str(e)}")
            await self.show_menu(update, context)

    async def prompt_database_id(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示选择数据库"""
        user_id = str(update.effective_user.id)

        try:
            # 获取 API Key 和 Page ID
            api_key = self.config_manager.get_user_value(user_id, "notion.api_key")
            page_id = self.config_manager.get_user_value(user_id, "notion.page_id")

            if not api_key:
                raise ServiceError("请先设置 API Key")
            if not page_id:
                raise ServiceError("请先设置 Page ID")

            # 创建临时 API 实例
            temp_api = NotionAPI(api_key)

            # 获取数据库列表
            text = "🔄 正在获取数据库列表..."
            await self.update_menu(update, context, text, None)

            databases = await temp_api.list_databases(page_id)

            # 修改按钮构建逻辑，使用短标识符
            keyboard = []
            for idx, db in enumerate(databases):
                if not db.get('title') or not db.get('id'):
                    self.logger.warning(f"数据库信息不完整: {db}")
                    continue

                # 使用短标识符，存储完整ID到临时存储中
                short_id = f"db_{idx}"
                context.user_data[f"notion_db_{short_id}"] = db['id']

                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"📊 {db['title']}",
                            callback_data=f"settings_notion_db_{short_id}",  # 使用短标识符
                        )
                    ]
                )

            # 添加新建数据库按钮，添加 settings_notion_ 前缀
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "➕ 新建数据库",
                        callback_data="settings_notion_create_database",  # 添加前缀
                    )
                ]
            )

            # 添加返回和退出按钮
            keyboard.append(
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_notion"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            )

            # 使用 update_menu 更新菜单
            text = (
                "🗄️ 选择数据库:\n\n"
                f"找到 {len(databases)} 个数据库\n"
                "选择一个现有数据库或创建新数据库"
            )

            await self.update_menu(
                update, context, text, InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            self.logger.error(f"获取数据库列表失败: {str(e)}", exc_info=True)
            error_text = (
                "❌ 获取数据库列表失败\n\n"
                f"错误信息: {str(e)}\n\n"
                "请检查设置是否正确，稍后重试"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔙 返回", callback_data="settings_notion"),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]

            try:
                await self.update_menu(
                    update, context, error_text, InlineKeyboardMarkup(keyboard)
                )
            except Exception as update_error:
                self.logger.error(
                    f"更新错误菜单失败: {str(update_error)}", exc_info=True
                )
                # 尝试发送新消息
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

    async def prompt_database_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """提示输入新数据库名称"""
        try:
            # 删除旧菜单
            await update.callback_query.message.delete()

            # 设置状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.set_state(
                    update.effective_user.id,
                    {
                        "setting": "notion_database_name",
                        "chat_id": update.effective_chat.id,
                    },
                    timeout=60.0,
                )

            # 发送新的提示消息并保存引用
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📝 创建新数据库\n\n"
                "请输入数据库名称:\n"
                "例如: My Notes, Tasks 等\n\n"
                "⚠️ 名称将显示在 Notion 页面中\n\n",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔙 返回", callback_data="settings_notion_database"
                            ),
                            InlineKeyboardButton("❌ 退出", callback_data="exit"),
                        ]
                    ]
                ),
            )

            # 保存消息引用以便后续删除
            context.user_data['last_prompt_message'] = message

        except Exception as e:
            self.logger.error(f"提示输入数据库名称失败: {e}")
            await update.callback_query.message.reply_text(
                "❌ 操作失败，请重试",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("返回", callback_data="settings_notion")]]
                ),
            )

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理用户的设置输入"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text

        # 从 state_manager 获取状态
        state_manager = context.bot_data.get('state_manager')
        if not state_manager:
            return

        state = state_manager.get_state(user_id)
        if not state:
            return

        setting = state["data"].get("setting")
        if not setting:
            return

        try:
            # 修改这里，匹配正确的状态名称
            if setting == "notion_key":
                await self.save_api_key(update, context, text)
            elif setting == "notion_page":
                await self.save_page_id(update, context, text)
            elif setting == "notion_database_name":  # 修改这里
                await self.create_database(update, context, text)
                return  # 添加 return 避免继续执行
            else:
                self.logger.warning(f"未知的设置状态: {setting}")
                await update.message.reply_text(
                    "❌ 未知的设置状态，请重试",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "返回", callback_data="settings_notion"
                                )
                            ]
                        ]
                    ),
                )
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}")
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 重试", callback_data=f"settings_notion_{setting}"
                    ),
                    InlineKeyboardButton("❌ 退出", callback_data="exit"),
                ]
            ]
            await update.message.reply_text(
                f"保存设置失败: {str(e)}", reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def save_api_key(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, api_key: str
    ) -> None:
        """保存 API Key"""
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            # 删除用户发送的消息
            await update.message.delete()

            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔄 正在验证 API Key...\n\n" "• 连接 Notion API...",
            )

            # 创建临时 API 实例进行验证
            temp_api = NotionAPI(api_key)

            # 更新验证状态
            await status_message.edit_text(
                "🔄 正在验证 API Key...\n\n"
                "• 连接 Notion API... ✅\n"
                "• 验证访问权限..."
            )

            # 尝试获取用户信息来验证 API Key
            await temp_api.get_users()

            # 更新验证状态
            await status_message.edit_text(
                "🔄 正在验证 API Key...\n\n"
                "• 连接 Notion API... ✅\n"
                "• 验证访问权限... ✅\n"
                "• 保存配置..."
            )

            # API Key 验证成功，保存配置
            self.config_manager.set_user_config(user_id, "notion.api_key", api_key)

            # 更新最终状态
            await status_message.edit_text(
                "✅ Notion API Key 验证成功！\n\n" "2秒后返回设置菜单..."
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
            error_msg = str(e).lower()
            if 'unauthorized' in error_msg or 'invalid' in error_msg:
                error_text = "无效的 API Key"
            else:
                error_text = f"验证失败: {str(e)}"

            if status_message:
                await status_message.edit_text(f"❌ {error_text}\n\n2秒后返回重试...")
                await asyncio.sleep(2)
                await status_message.delete()

            await self.prompt_api_key(update, context)

    async def save_page_id(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str
    ) -> None:
        """保存页面ID"""
        try:
            user_id = str(update.effective_user.id)

            # 创建状态消息
            status_message = await update.message.reply_text(
                "🔄 正在验证页面访问权限...\n\n" "• 验证访问权限..."
            )

            # 验证页面访问权限
            api_key = self.config_manager.get_user_value(user_id, "notion.api_key")
            if not api_key:
                raise ValueError("请先设置 API Key")

            temp_api = NotionAPI(api_key)
            try:
                # 验证页面权限
                await temp_api.get_page(page_id)
                await status_message.edit_text(
                    "🔄 正在验证页面访问权限...\n\n"
                    "• 验证访问权限... ✅\n"
                    "• 保存配置..."
                )
            except Exception as e:
                await status_message.edit_text(
                    f"❌ 页面访问失败: {str(e)}\n\n"
                    "请确保:\n"
                    "1. 页面ID正确\n"
                    "2. 已将集成添加到页面\n\n"
                    "2秒后返回..."
                )
                await asyncio.sleep(2)
                await status_message.delete()
                await self.prompt_page_id(update, context)
                return

            # 保存配置
            self.config_manager.set_user_config(user_id, "notion.page_id", page_id)

            # 更新状态
            await status_message.edit_text(
                "✅ 页面配置成功！\n\n" "2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)
            await status_message.delete()

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            self.logger.error(f"保存页面ID失败: {str(e)}")
            if status_message:
                await status_message.edit_text(
                    f"❌ 保存失败: {str(e)}\n\n" "2秒后返回..."
                )
                await asyncio.sleep(2)
                await status_message.delete()
            await self.prompt_page_id(update, context)

    async def save_database_id(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, database_id: str
    ) -> None:
        """保存数据库ID"""
        try:
            user_id = str(update.effective_user.id)

            # 创建状态消息
            status_message = await update.callback_query.message.reply_text(
                "🔄 正在验证数据库...\n\n" "• 验证访问权限..."
            )

            # 验证数据库访问权限
            api = self._temp_apis.get(user_id)
            if not api:
                api_key = self.config_manager.get_user_value(user_id, "notion.api_key")
                api = NotionAPI(api_key)

            try:
                database = await api.get_database(database_id)
            except Exception as e:
                await status_message.edit_text(
                    f"❌ 数据库访问失败: {str(e)}\n\n"
                    "请确保:\n"
                    "1. 数据库ID正确\n"
                    "2. 已将集成添加到数据库\n\n"
                    "2秒后返回..."
                )
                await asyncio.sleep(2)
                await status_message.delete()
                await self.prompt_database_id(update, context)
                return

            # 更新状态
            await status_message.edit_text(
                "🔄 正在验证数据库...\n\n"
                "• 验证访问权限... ✅\n"
                "• 初始化数据库结构..."
            )

            # 初始化数据库结构
            try:
                await api.init_database(database_id)
                await status_message.edit_text(
                    "🔄 正在验证数据库...\n\n"
                    "• 验证访问权限... ✅\n"
                    "• 初始化数据库结构... ✅\n"
                    "• 保存配置..."
                )
            except Exception as e:
                await status_message.edit_text(
                    f"❌ 数据库初始化失败: {str(e)}\n\n"
                    "请确保机器人拥有编辑数据库的权限\n\n"
                    "2秒后返回..."
                )
                await asyncio.sleep(2)
                await status_message.delete()
                await self.prompt_database_id(update, context)
                return

            # 保存配置
            self.config_manager.set_user_config(
                user_id, "notion.database_id", database_id
            )

            # 清理临时API实例
            self._cleanup_temp_api(user_id)

            # 更新状态
            await status_message.edit_text(
                "✅ 数据库配置成功！\n\n"
                "提示：\n"
                "1. 请勿手动修改数据库的属性结构\n"
                "2. 如需修改，请使用机器人的设置功能\n\n"
                "2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)
            await status_message.delete()

            # 返回设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            self.logger.error(f"保存数据库ID失败: {str(e)}")
            if status_message:
                await status_message.edit_text(
                    f"❌ 保存失败: {str(e)}\n\n" "2秒后返回..."
                )
                await asyncio.sleep(2)
                await status_message.delete()
            await self.prompt_database_id(update, context)

    async def create_database(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, name: str
    ) -> None:
        """创建新数据库"""
        user_id = str(update.effective_user.id)
        status_message = None

        try:
            # 删除用户的输入消息
            await update.message.delete()

            # 删除之前的提示消息
            if 'last_prompt_message' in context.user_data:
                try:
                    await context.user_data['last_prompt_message'].delete()
                    del context.user_data['last_prompt_message']
                except Exception as e:
                    self.logger.warning(f"删除旧提示消息失败: {e}")

            # 清除旧状态
            state_manager = context.bot_data.get('state_manager')
            if state_manager:
                state_manager.clear_state(update.effective_user.id)

            # 发送状态消息
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔄 正在创建数据库...\n\n• 准备创建...",
            )

            # 获取必要的配置
            api_key = self.config_manager.get_user_value(user_id, "notion.api_key")
            page_id = self.config_manager.get_user_value(user_id, "notion.page_id")

            if not api_key or not page_id:
                raise ValueError("请先完成 API Key 和 Page ID 的设置")

            # 创建 API 实例
            temp_api = NotionAPI(api_key)

            # 更新状态
            await status_message.edit_text(
                "🔄 正在创建数据库...\n\n" "• 准备创建... ✅\n" "• 创建数据库..."
            )

            # 创建数据库
            database = await temp_api.create_database(
                page_id=page_id, title=name, description="Created by Hi-Ben Bot"
            )

            # 更新状态
            await status_message.edit_text(
                "🔄 正在创建数据库...\n\n"
                "• 准备创建... ✅\n"
                "• 创建数据库... ✅\n"
                "• 初始化数据库结构..."
            )

            # 初始化数据库结构
            database_id = database["id"]
            await temp_api.init_database(database_id)

            # 保存数据库ID
            self.config_manager.set_user_config(
                user_id, "notion.database_id", database_id
            )

            # 更新状态
            await status_message.edit_text(
                "✅ 数据库创建成功！\n\n" "2秒后返回设置菜单..."
            )

            # 等待2秒
            await asyncio.sleep(2)

            # 删除状态消息
            if status_message:
                await status_message.delete()

            # 返回 Notion 设置菜单
            await self.show_menu(update, context)

        except Exception as e:
            error_text = f"创建数据库失败: {str(e)}"
            if status_message:
                await status_message.edit_text(f"❌ {error_text}\n\n" "2秒后返回...")
                await asyncio.sleep(2)
                await status_message.delete()

            # 返回到输入界面
            await self.prompt_database_name(update, context)

    async def process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        query = update.callback_query
        data = query.data
        user_id = str(update.effective_user.id)

        try:
            self.logger.info(f"处理 Notion 设置回调: {data}")
            await query.answer()

            # 处理退出操作
            if data == "exit":
                self._cleanup_temp_api(user_id)
                state_manager = context.bot_data.get('state_manager')
                if state_manager:
                    state_manager.clear_state(update.effective_user.id)
                await self.cleanup_messages(update, context)
                return

            # 处理数据库选择
            if "settings_notion_db_" in data:  # 修改判断条件
                short_id = data.replace("settings_notion_db_", "")
                database_id = context.user_data.get(f"notion_db_{short_id}")
                if database_id:
                    await self.save_database_id(update, context, database_id)
                    # 清理临时数据
                    del context.user_data[f"notion_db_{short_id}"]
                    return  # 添加return避免进入后续逻辑
                else:
                    raise ValueError("数据库ID无效或已过期")

            # 其他回调处理
            if data == "settings_notion":
                await self.show_menu(update, context)
            elif data == "settings_notion_key":
                await self.prompt_api_key(update, context)
            elif data == "settings_notion_page":
                await self.prompt_page_id(update, context)
            elif data == "settings_notion_database":
                await self.prompt_database_id(update, context)
            elif data == "settings_notion_create_database":
                await self.prompt_database_name(update, context)
            elif data == "settings":
                self._cleanup_temp_api(user_id)
                from .main_settings import MainSettingsHandler

                main_handler = MainSettingsHandler()
                await main_handler.show_menu(update, context)
            else:
                self.logger.warning(f"未知的回调数据: {data}")
                await query.message.reply_text("❌ 未知的操作")

        except Exception as e:
            self.logger.error(f"处理 Notion 设置回调失败: {str(e)}", exc_info=True)
            error_text = "❌ 处理设置失败\n\n请重试或联系管理员"
            try:
                await query.message.edit_text(
                    error_text,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔙 返回", callback_data="settings_notion"
                                )
                            ]
                        ]
                    ),
                )
            except Exception as edit_error:
                self.logger.error(f"更新错误消息失败: {str(edit_error)}", exc_info=True)
                await query.message.reply_text(error_text)
