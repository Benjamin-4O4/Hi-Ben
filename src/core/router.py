from typing import Dict, List, Callable, Awaitable, Pattern, Optional
import re
from .models.message import Message, MessageType
from ..utils.logger import Logger


class Route:
    """路由规则"""

    def __init__(
        self,
        pattern: str,
        handler: Callable[[Message], Awaitable[None]],
        message_type: Optional[MessageType] = None,
        description: str = "",
    ):
        self.pattern = re.compile(pattern)
        self.handler = handler
        self.message_type = message_type
        self.description = description


class MessageRouter:
    """消息路由器"""

    def __init__(self):
        self.logger = Logger(__name__)
        self.routes: List[Route] = []
        self.default_handler: Optional[Callable[[Message], Awaitable[None]]] = None

    def add_route(
        self,
        pattern: str,
        handler: Callable[[Message], Awaitable[None]],
        message_type: Optional[MessageType] = None,
        description: str = "",
    ) -> None:
        """添加路由规则"""
        self.routes.append(Route(pattern, handler, message_type, description))
        self.logger.info(f"添加路由: {pattern} -> {handler.__name__}")

    def set_default_handler(
        self, handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """设置默认处理器"""
        self.default_handler = handler
        self.logger.info(f"设置默认处理器: {handler.__name__}")

    async def route(self, message: Message) -> bool:
        """路由消息到对应的处理器"""
        try:
            message_text = message.content.data.get("text", "")
            message_type = message.content.type

            for route in self.routes:
                # 检查消息类型
                if route.message_type and route.message_type != message_type:
                    continue

                # 检查内容匹配
                if route.pattern.match(message_text):
                    self.logger.debug(f"匹配路由: {route.pattern.pattern}")
                    await route.handler(message)
                    return True

            # 使用默认处理器
            if self.default_handler:
                await self.default_handler(message)
                return True

            self.logger.warning(f"未找到匹配的路由: {message_text}")
            return False

        except Exception as e:
            self.logger.error(f"消息路由失败: {str(e)}")
            raise
