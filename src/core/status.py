from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
from ..utils.logger import Logger
import asyncio


class MessageStatus(str, Enum):
    """消息状态"""

    RECEIVED = "received"  # 已接收
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class ProcessStep(str, Enum):
    """处理步骤"""

    RECEIVE = "接收消息"
    ANALYZE = "分析内容"
    PROCESS = "处理中"
    SAVE = "保存内容"
    RESPOND = "响应完成"


class StatusMessage(BaseModel):
    """状态消息模型"""

    message_id: str
    platform: str
    chat_id: str
    text: str
    reply_to_message_id: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class ProcessStatus(BaseModel):
    """处理状态模型"""

    status: MessageStatus
    step: ProcessStep
    progress: float
    description: str
    details: Dict = {}
    started_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class PlatformStatusUpdater:
    """平台状态更新器基类"""

    async def create_status_message(
        self, chat_id: str, text: str, reply_to_message_id: Optional[str] = None
    ) -> Optional[StatusMessage]:
        """创建状态消息"""
        raise NotImplementedError

    async def update_status_message(self, message: StatusMessage, text: str) -> bool:
        """更新状态消息"""
        raise NotImplementedError

    async def delete_status_message(self, message: StatusMessage) -> bool:
        """删除状态消息"""
        raise NotImplementedError


class StatusManager:
    """统一状态管理器

    职责:
    1. 管理所有平台的状态消息
    2. 处理状态更新
    3. 状态超时处理
    4. 状态持久化
    """

    def __init__(self, timeout: float = 60.0):
        """初始化状态管理器

        Args:
            timeout: 状态超时时间(秒)
        """
        self.logger = Logger("status.manager")
        self.timeout = timeout
        self._status_messages: Dict[str, StatusMessage] = (
            {}
        )  # message_id -> StatusMessage
        self._process_status: Dict[str, ProcessStatus] = (
            {}
        )  # message_id -> ProcessStatus
        self._platform_updaters: Dict[str, PlatformStatusUpdater] = (
            {}
        )  # platform -> Updater

    def register_platform(self, platform: str, updater: PlatformStatusUpdater) -> None:
        """注册平台状态更新器"""
        self._platform_updaters[platform] = updater
        self.logger.info(f"注册平台状态更新器: {platform}")

    async def create_status(
        self,
        platform: str,
        chat_id: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[StatusMessage]:
        """创建状态消息"""
        try:
            updater = self._platform_updaters.get(platform)
            if not updater:
                raise ValueError(f"未注册的平台: {platform}")

            status_message = await updater.create_status_message(
                chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id
            )

            if status_message:
                self._status_messages[status_message.message_id] = status_message

            return status_message

        except Exception as e:
            self.logger.error(f"创建状态消息失败: {e}")
            return None

    async def update_status(
        self,
        message_id: str,
        status: MessageStatus,
        step: ProcessStep,
        progress: float,
        description: str,
        details: Dict = {},
    ) -> bool:
        """更新状态"""
        try:
            # 更新处理状态
            process_status = ProcessStatus(
                status=status,
                step=step,
                progress=progress,
                description=description,
                details=details,
                updated_at=datetime.now(),
            )
            self._process_status[message_id] = process_status

            # 更新状态消息
            status_message = self._status_messages.get(message_id)
            if not status_message:
                return False

            # 构建状态文本
            status_text = (
                f"💫 处理进度: {int(progress * 100)}%\n"
                f"当前步骤: {step.value}\n"
                f"{description}"
            )

            # 获取对应的平台更新器
            updater = self._platform_updaters.get(status_message.platform)
            if not updater:
                return False

            # 更新状态消息
            return await updater.update_status_message(status_message, status_text)

        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")
            return False

    def get_status(self, message_id: str) -> Optional[ProcessStatus]:
        """获取处理状态"""
        return self._process_status.get(message_id)

    async def clear_status(self, message_id: str) -> None:
        """清除状态"""
        try:
            # 删除状态消息
            status_message = self._status_messages.pop(message_id, None)
            if status_message:
                updater = self._platform_updaters.get(status_message.platform)
                if updater:
                    await updater.delete_status_message(status_message)

            # 删除处理状态
            self._process_status.pop(message_id, None)

        except Exception as e:
            self.logger.error(f"清除状态失败: {e}")

    def _cleanup_expired(self) -> None:
        """清理过期状态"""
        now = datetime.now()
        expired_time = now - timedelta(seconds=self.timeout)

        # 清理过期的状态消息
        expired_messages = [
            message_id
            for message_id, message in self._status_messages.items()
            if message.updated_at < expired_time
        ]

        for message_id in expired_messages:
            asyncio.create_task(self.clear_status(message_id))
