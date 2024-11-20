from abc import ABC, abstractmethod
from typing import Any, Optional, Union, List, Dict
from .message import Message


class PlatformAdapter(ABC):
    """平台适配器基类"""

    @abstractmethod
    async def initialize(self) -> None:
        """初始化平台连接"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        message: Union[str, Message],
        reply_to: Optional[Message] = None,
    ) -> Message:
        """发送消息"""
        pass

    @abstractmethod
    async def edit_message(
        self, chat_id: str, message_id: str, new_content: Union[str, Message]
    ) -> Message:
        """编辑消息"""
        pass

    @abstractmethod
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """删除消息"""
        pass

    @abstractmethod
    async def convert_to_message(self, platform_message: Any) -> Message:
        """转换平台特定消息为统一格式"""
        pass

    @abstractmethod
    async def convert_from_message(self, message: Message) -> Dict:
        """转换统一格式为平台特定格式"""
        pass
