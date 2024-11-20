from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import TelegramBaseHandler


class TelegramHelpHandler(TelegramBaseHandler):
    """处理 /help 命令"""

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理帮助命令"""
        help_text = (
            "🔍 帮助信息\n\n"
            "基本命令:\n"
            "/start - 开始使用\n"
            "/help - 显示此帮助\n"
            "/settings - 设置\n\n"
            "使用方法:\n"
            "- 直接发送文本记录笔记\n"
            "- 发送语音自动转文字\n"
            "- 发送图片自动识别\n"
            "- 发送文件自动保存\n\n"
            "高级功能:\n"
            "- 自动提取任务\n"
            "- 智能分类标签\n"
            "- 关联其他服务"
        )

        keyboard = [
            [InlineKeyboardButton("⚙️ 设置", callback_data="settings")],
            [InlineKeyboardButton("👥 联系支持", callback_data="support")],
            [
                InlineKeyboardButton("🔙 返回", callback_data="start"),
                InlineKeyboardButton("❌ 退出", callback_data="exit"),
            ],
        ]

        await self.send_message(
            update, context, help_text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _process_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理帮助回调"""
        query = update.callback_query
        if query.data == "help":
            await self.handle(update, context)
        await query.answer()
