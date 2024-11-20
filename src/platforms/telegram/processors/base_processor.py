from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from telegram import Update, Message as TGMessage
from telegram.ext import ContextTypes
from ....utils.logger import Logger
from ....core.models.message import Message


class BaseProcessor(ABC):
    """处理器基类"""

    def __init__(self):
        self.logger = Logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[Message]:
        """处理消息"""
        pass

    async def pre_process(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """预处理,返回是否继续处理"""
        return True

    async def post_process(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        result: Optional[Message],
    ) -> None:
        """后处理"""
        pass
