from typing import Dict, Optional
from abc import ABC, abstractmethod
from ..utils.logger import Logger
from ..utils.config_manager import ConfigManager
from ..core.status import StatusManager, MessageStatus, ProcessStep, StatusMessage
from ..core.models.message import Message
from ..platforms.telegram.utils.status_updater import TelegramStatusUpdater


class BaseAgent(ABC):
    """智能体基类"""

    def __init__(
        self,
        name: str,
        status_manager: Optional[StatusManager] = None,
        telegram_status_updater: Optional[TelegramStatusUpdater] = None,
    ):
        """初始化基类

        Args:
            name: 智能体名称
            status_manager: 状态管理器
            telegram_status_updater: Telegram状态更新器
        """
        self.logger = Logger(f"agents.{name}")
        self.config = ConfigManager()
        self.status_manager = status_manager or StatusManager()
        self.telegram_status_updater = telegram_status_updater

    async def _update_status(
        self,
        message: Message,
        status: MessageStatus,
        step: ProcessStep,
        progress: float,
        description: str,
        status_message_id: Optional[str] = None,
        emoji: str = "💫",
    ) -> None:
        """更新处理状态"""
        try:
            # 如果是Telegram消息且有状态更新器
            if (
                message.metadata.platform == "telegram"
                and self.telegram_status_updater
                and status_message_id
            ):
                # 格式化状态文本
                status_text = self.telegram_status_updater.format_status_text(
                    progress=progress,
                    step=step.value,
                    description=description,
                    emoji=emoji,
                )

                # 获取状态消息
                status_message = StatusMessage(
                    message_id=status_message_id,
                    platform="telegram",
                    chat_id=message.metadata.chat_id,
                    text=status_text,
                    reply_to_message_id=message.metadata.message_id,
                )

                # 更新状态消息
                await self.telegram_status_updater.update_status_message(
                    message=status_message, text=status_text
                )

            # 更新全局状态
            if self.status_manager:
                await self.status_manager.update_status(
                    message_id=str(message.metadata.message_id),
                    status=status,
                    step=step.value,
                    progress=progress,
                    description=description,
                    details={"platform": message.metadata.platform},
                )

        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")

    async def handle_error(
        self,
        message: Message,
        error: Exception,
        status_message_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> None:
        """处理错误

        Args:
            message: 消息对象
            error: 错误对象
            status_message_id: 状态消息ID
            context: 上下文信息
        """
        error_msg = str(error)
        self.logger.error(f"处理失败: {error_msg}", exc_info=True)

        # 更新错误状态
        await self._update_status(
            message,
            MessageStatus.FAILED,
            ProcessStep.PROCESS,
            0.0,
            f"❌ 处理失败: {error_msg}",
            status_message_id,
            emoji="❌",
        )

    @abstractmethod
    async def process(self, *args, **kwargs):
        """处理消息(由子类实现)"""
        pass
