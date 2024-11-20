from typing import Dict, Type, Optional
from .processors.base_processor import BaseProcessor
from .processors.text_processor import TextProcessor
from .processors.media_processor import MediaProcessor
from .processors.file_processor import FileProcessor
from ...utils.logger import Logger
from ...core.models.message import MessageType


class ProcessorManager:
    """处理器管理器"""

    def __init__(self):
        """初始化处理器管理器"""
        self.logger = Logger(__name__)
        self._processors: Dict[MessageType, BaseProcessor] = {}
        self._register_processors()

    def _register_processors(self) -> None:
        """注册所有处理器"""
        media_processor = MediaProcessor()  # 创建单个实例
        self._processors = {
            MessageType.TEXT: TextProcessor(),
            MessageType.MEDIA_GROUP: media_processor,  # 使用同一个实例处理
            MessageType.IMAGE: media_processor,  # 媒体组和图片
            MessageType.VIDEO: media_processor,  # 视频也用这个处理器
            MessageType.FILE: FileProcessor(),
        }

    def get_processor(self, message_type: MessageType) -> Optional[BaseProcessor]:
        """获取对应类型的处理器"""
        return self._processors.get(message_type)
