from typing import Optional
from telegram import Bot, Message
from ....utils.logger import Logger
from ....core.status import PlatformStatusUpdater, StatusMessage


class TelegramStatusUpdater(PlatformStatusUpdater):
    """Telegram 状态更新器

    职责:
    1. 创建和更新状态消息
    2. 处理消息引用
    3. 格式化状态文本
    """

    def __init__(self, bot: Bot):
        """初始化更新器

        Args:
            bot: Telegram Bot实例
        """
        self.logger = Logger("telegram.status")
        self.bot = bot

    async def create_status_message(
        self, chat_id: str, text: str, reply_to_message_id: Optional[str] = None
    ) -> Optional[StatusMessage]:
        """创建状态消息

        Args:
            chat_id: 聊天ID
            text: 消息文本
            reply_to_message_id: 要回复的消息ID

        Returns:
            StatusMessage: 创建的状态消息
            None: 如果创建失败
        """
        try:
            # 创建消息
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=(
                    int(reply_to_message_id) if reply_to_message_id else None
                ),
            )

            # 转换为状态消息
            return StatusMessage(
                message_id=str(message.message_id),
                platform="telegram",
                chat_id=str(chat_id),
                text=text,
                reply_to_message_id=reply_to_message_id,
            )

        except Exception as e:
            self.logger.error(f"创建状态消息失败: {e}")
            return None

    async def update_status_message(self, message: StatusMessage, text: str) -> bool:
        """更新状态消息

        Args:
            message: 状态消息
            text: 新的消息文本

        Returns:
            bool: 是否更新成功
        """
        try:
            # 更新消息
            await self.bot.edit_message_text(
                chat_id=message.chat_id, message_id=int(message.message_id), text=text
            )
            return True

        except Exception as e:
            self.logger.error(f"更新状态消息失败: {e}")
            return False

    async def delete_status_message(self, message: StatusMessage) -> bool:
        """删除状态消息

        Args:
            message: 状态消息

        Returns:
            bool: 是否删除成功
        """
        try:
            # 删除消息
            await self.bot.delete_message(
                chat_id=message.chat_id, message_id=int(message.message_id)
            )
            return True

        except Exception as e:
            self.logger.error(f"删除状态消息失败: {e}")
            return False

    def format_status_text(
        self, progress: float, step: str, description: str, emoji: str = "💫"
    ) -> str:
        """格式化状态文本

        Args:
            progress: 进度(0-1)
            step: 步骤描述
            description: 详细描述
            emoji: 状态emoji

        Returns:
            str: 格式化后的状态文本
        """
        # 检查描述中是否已有emoji
        has_emoji = any(
            char in description
            for char in ('🔄', '🎤', '🔍', '🤖', '✨', '💾', '✅', '❌', '📋', '📌')
        )

        # 进度条样式
        bar_length = 20  # 增加进度条长度
        filled_length = int(progress * bar_length)

        # 使用不同的进度条字符
        filled = "█" * filled_length  # 实心方块
        empty = "░" * (bar_length - filled_length)  # 空心方块
        bar = filled + empty

        # 百分比
        percent = f"{int(progress * 100):3d}%"

        # 如果描述已包含emoji，不添加新的emoji
        desc = description if has_emoji else f"{emoji} {description}"

        # 构建状态文本 (使用等宽字符对齐)
        return f"{desc}\n" f"{bar} {percent}"
