from typing import Dict, List, Callable, Awaitable
from .models.message import Message, MessageType
import asyncio
from ..utils.logger import Logger


class MessageDispatcher:
    """消息分发器"""

    def __init__(self):
        self.logger = Logger(__name__)
        self._handlers: Dict[MessageType, List[Callable]] = {}
        self._middleware: List[Callable] = []

    def register_handler(
        self, message_type: MessageType, handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """注册消息处理器"""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        self.logger.info(f"注册处理器: {message_type} -> {handler.__name__}")

    def add_middleware(
        self, middleware: Callable[[Message], Awaitable[Message]]
    ) -> None:
        """添加中间件"""
        self._middleware.append(middleware)
        self.logger.info(f"添加中间件: {middleware.__name__}")

    async def dispatch(self, message: Message) -> None:
        """分发消息"""
        try:
            # 应用中间件
            for middleware in self._middleware:
                message = await middleware(message)
                if not message:
                    return

            # 获取处理器
            handlers = self._handlers.get(message.content.type, [])
            if not handlers:
                self.logger.warning(f"未找到处理器: {message.content.type}")
                return

            # 并发执行处理器
            await asyncio.gather(
                *[handler(message) for handler in handlers], return_exceptions=True
            )

        except Exception as e:
            self.logger.error(f"消息分发失败: {str(e)}")
            raise
