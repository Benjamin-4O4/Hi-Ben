from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import TelegramBaseHandler


class TelegramStartHandler(TelegramBaseHandler):
    """处理 /start 命令"""

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理开始命令"""
        welcome_text = (
            "👋 欢迎使用 Hi-Ben!\n\n"
            "我可以帮你:\n"
            "📝 记录笔记和想法\n"
            "✅ 提取并创建任务\n"
            "🗂 自动分类和整理\n\n"
            "使用 /help 查看更多帮助"
        )

        keyboard = [
            [InlineKeyboardButton("📖 帮助", callback_data="help")],
            [InlineKeyboardButton("⚙️ 设置", callback_data="settings")],
            [InlineKeyboardButton("❌ 退出", callback_data="exit")],
        ]

        await self.send_message(
            update, context, welcome_text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理开始命令的回调"""
        query = update.callback_query
        if query.data == "start":
            await self.handle(update, context)
        await query.answer()
