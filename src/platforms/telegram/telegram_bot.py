from typing import Optional, Dict, Any, List
import logging
import asyncio
from telegram import Bot, Update, BotCommand, BotCommandScopeDefault, MenuButtonCommands
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager
from ...utils.context import RequestContext
from ...utils.exceptions import PlatformError
from .handlers import TelegramStartHandler, TelegramHelpHandler, MainSettingsHandler
from .message_router import MessageRouter
from .state_manager import TelegramStateManager
from ..telegram.utils.status_updater import TelegramStatusUpdater
from ...agents.media_processor_agent import MediaProcessorAgent
from ...agents.note_taker_agent import NoteTakerAgent

# 设置 httpx 日志级别为 WARNING 避免所有 GET 和 POST 请求被记录
logging.getLogger("httpx").setLevel(logging.WARNING)


class TelegramBot:
    """Telegram Bot 实现

    职责:
    1. Bot生命周期管理
    2. 消息队列管理
    3. 命令处理器管理
    4. 并发处理
    """

    def __init__(self):
        self.logger = Logger(__name__)
        self.config = ConfigManager()
        self.bot: Optional[Bot] = None
        self.app: Optional[Application] = None

        # 创建状态管理器
        self.state_manager = TelegramStateManager(timeout=60.0)  # 60秒超时

        # 创建状态更新器
        self.status_updater = None  # 初始化时创建

        # 创建智能体
        self.media_processor = None  # 初始化时创建
        self.note_taker = None  # 初始化时创建

        # 消息队列和工作器
        self.message_queue = asyncio.Queue()
        self.max_workers = 10  # 最大并发处理数
        self._workers = []  # 工作任务列表

        # 初始化处理器
        self.start_handler = TelegramStartHandler()
        self.help_handler = TelegramHelpHandler()
        self.settings_handler = MainSettingsHandler()

        # 将处理器传递给路由器
        self.message_router = MessageRouter(
            start_handler=self.start_handler,
            help_handler=self.help_handler,
            settings_handler=self.settings_handler,
            state_manager=self.state_manager,
        )

    async def initialize(self) -> None:
        """初始化 Bot"""
        try:
            token = self.config.get("telegram", "bot_token")
            if not token:
                raise PlatformError("未配置 Telegram Bot Token")

            # 创建应用，启用并发更新
            self.app = (
                ApplicationBuilder()
                .token(token)
                .concurrent_updates(True)  # 启用并发处理
                .pool_timeout(60.0)  # 增加池超时时间到60秒
                .connection_pool_size(100)  # 设置连接池大小
                .connect_timeout(30.0)  # 设置连接超时为30秒
                .read_timeout(30.0)  # 设置读取超时为30秒
                .write_timeout(30.0)  # 设置写入超时为30秒
                .get_updates_read_timeout(30.0)  # 设置获取更新的读取超时
                .get_updates_connection_pool_size(100)  # 设置获取更新的连接池大小
                .build()
            )
            self.bot = self.app.bot

            # 创建状态更新器
            self.status_updater = TelegramStatusUpdater(self.bot)

            # 创建智能体
            self.media_processor = MediaProcessorAgent(
                status_manager=self.state_manager,
                telegram_status_updater=self.status_updater,
            )
            self.note_taker = NoteTakerAgent(
                status_manager=self.state_manager,
                telegram_status_updater=self.status_updater,
            )

            # 设置命令菜单
            commands = [
                BotCommand("start", "👋 开始使用"),
                BotCommand("help", "📖 帮助信息"),
                BotCommand("settings", "⚙️ 设置"),
            ]
            await self.bot.set_my_commands(commands=commands)
            await self.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

            # 设置状态管理器的 bot
            self.state_manager.bot = self.bot

            # 将状态管理器存储在应用上下文中
            self.app.bot_data['state_manager'] = self.state_manager

            # 设置路由器的 bot 和智能体
            self.message_router.set_bot(self.bot)
            self.message_router.set_agents(
                media_processor=self.media_processor, note_taker=self.note_taker
            )

            # 注册处理器
            self._register_handlers()

            self.logger.info("Telegram Bot 初始化完成")

        except Exception as e:
            self.logger.error(f"初始化 Telegram Bot 失败: {str(e)}")
            raise PlatformError(f"初始化失败: {str(e)}")

    def _register_handlers(self) -> None:
        """注册消息处理器"""
        try:
            # 命令处理器
            self.app.add_handler(CommandHandler("start", self._handle_start))
            self.app.add_handler(CommandHandler("help", self._handle_help))
            self.app.add_handler(CommandHandler("settings", self._handle_settings))

            # 消息处理器
            self.app.add_handler(
                MessageHandler(filters.ALL & ~filters.COMMAND, self._handle_message)
            )

            # 回调查询处理器
            self.app.add_handler(CallbackQueryHandler(self._handle_callback))

            # 错误处理器
            self.app.add_error_handler(self._handle_error)

            self.logger.info("注册处理器完成")

        except Exception as e:
            self.logger.error(f"注册处理器失败: {str(e)}")
            raise

    async def start(self) -> None:
        """启动 Bot"""
        try:
            # 启动应用
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
            )

            # 启动消息处理工作器
            self._workers = [
                asyncio.create_task(self._message_worker())
                for _ in range(self.max_workers)
            ]

            self.logger.info("Telegram Bot 启动成功")

        except Exception as e:
            self.logger.error(f"启动 Telegram Bot 失败: {str(e)}")
            raise PlatformError(f"启动失败: {str(e)}")

    async def stop(self) -> None:
        """停止 Bot"""
        try:
            # 停止所有工作器
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers = []

            # 停止应用
            await self.app.stop()
            await self.app.shutdown()

            self.logger.info("Telegram Bot 已停止")

        except Exception as e:
            self.logger.error(f"停止 Telegram Bot 失败: {str(e)}")
            raise PlatformError(f"停止失败: {str(e)}")

    async def _message_worker(self):
        """消息处理工作器"""
        while True:
            try:
                # 从队列获取消息
                update, context = await self.message_queue.get()

                # 处理消息
                await self._process_message(update, context)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"消息处理失败: {str(e)}")
            finally:
                self.message_queue.task_done()

    async def _process_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理消息"""
        async with RequestContext(
            request_id=str(update.update_id),
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
        ):
            await self.message_router.route(update, context)

    async def _handle_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理 /start 命令"""
        async with RequestContext(
            request_id=str(update.update_id),
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
        ):
            await self.start_handler.handle(update, context)

    async def _handle_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理 /help 命令"""
        async with RequestContext(
            request_id=str(update.update_id),
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
        ):
            await self.help_handler.handle(update, context)

    async def _handle_settings(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理 /settings 命令"""
        async with RequestContext(
            request_id=str(update.update_id),
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
        ):
            await self.settings_handler.handle(update, context)

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理普通消息"""
        if not update.message:
            return
        # 所有消息直接放入队列处理
        await self.message_queue.put((update, context))

    async def _handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理回调查询"""
        if not update.callback_query:
            return

        async with RequestContext(
            request_id=str(update.update_id),
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            callback_data=update.callback_query.data,
        ):
            await self.message_router.route_callback(update, context)

    async def _handle_error(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理错误"""
        try:
            error = context.error
            self.logger.error(f"处理消息时出错: {str(error)}", exc_info=error)

            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ 处理消息时出现错误，请稍后重试"
                )
        except Exception as e:
            self.logger.error(f"处理错误时出错: {str(e)}")
