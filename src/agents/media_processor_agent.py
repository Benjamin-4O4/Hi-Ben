from typing import Dict, List, Optional, Union
from ..utils.logger import Logger
from ..utils.config_manager import ConfigManager
from ..services.whisper.whisper_service import WhisperService
from ..services.llm.llm_service import LLMService
from ..core.models.message import Message, MessageType
from ..core.status import StatusManager, MessageStatus, ProcessStep
from ..agents.base_agent import BaseAgent


class MediaProcessorAgent(BaseAgent):
    """媒体处理智能体

    职责:
    1. 语音/音频转文本并校对
    2. 文本+图片的多模态分析
    3. 实时状态反馈
    """

    def __init__(self, status_manager=None, telegram_status_updater=None):
        super().__init__(
            name="media_processor",
            status_manager=status_manager,
            telegram_status_updater=telegram_status_updater,
        )
        self.whisper = WhisperService()
        self.llm_service = LLMService()

    async def process_voice(
        self, message: Message, status_message_id: Optional[str] = None
    ) -> Dict:
        """处理语音/音频消息

        Args:
            message: 统一消息格式
            status_message_id: 状态消息ID（用于Telegram）

        Returns:
            Dict: {
                "text": str,  # 处理后的文本
                "raw_text": str,  # 原始识别文本
                "duration": float,  # 语音时长
                "file_path": str  # 语音文件路径
            }
        """
        try:
            # 更新状态：开始转换
            await self._update_status(
                message,
                MessageStatus.PROCESSING,
                ProcessStep.PROCESS,
                0.1,
                "🎤 正在转换语音...",
                status_message_id,
            )

            # 语音转文本
            voice_file = message.content.data.get("file_path")
            if not voice_file:
                raise ValueError("未找到语音文件")

            raw_text = await self.whisper.transcribe(voice_file)

            # 更新状态：开始校对
            await self._update_status(
                message,
                MessageStatus.PROCESSING,
                ProcessStep.PROCESS,
                0.6,
                "✨ 正在优化文本...",
                status_message_id,
            )

            # LLM校对和优化
            optimized_text = await self.llm_service.proofread_text(raw_text)

            # 更新状态：处理完成
            await self._update_status(
                message,
                MessageStatus.COMPLETED,
                ProcessStep.PROCESS,
                1.0,
                "✅ 语音处理完成",
                status_message_id,
            )

            return {
                "text": optimized_text,
                "raw_text": raw_text,
                "duration": message.content.data.get("duration", 0),
                "file_path": voice_file,
            }

        except Exception as e:
            self.logger.error(f"处理语音失败: {e}")
            await self.handle_error(message, e, status_message_id)
            raise

    async def process_text_with_media(
        self, message: Message, status_message_id: Optional[str] = None
    ) -> Dict:
        """处理文本+图片消息

        Args:
            message: 统一消息格式
            status_message_id: 状态消息ID（用于Telegram）

        Returns:
            Dict: {
                "text": str,  # 分析后的文本
                "summary": str,  # 内容总结
                "media_files": List[Dict]  # 处理后的媒体文件列表
            }
        """
        try:
            # 更新状态：开始分析
            await self._update_status(
                message,
                MessageStatus.PROCESSING,
                ProcessStep.PROCESS,
                0.2,
                "🔍 正在分析内容...",
                status_message_id,
            )

            text_content = message.content.data.get("text", "")
            media_files = message.files

            # 使用 LLM 分析文本和媒体
            analysis_result = await self.llm_service.analyze_text_with_media(
                text=text_content, media_files=media_files
            )

            # 更新状态：处理完成
            await self._update_status(
                message,
                MessageStatus.COMPLETED,
                ProcessStep.PROCESS,
                1.0,
                "✅ 内容分析完成",
                status_message_id,
            )

            return {
                "text": analysis_result["text"],
                "summary": analysis_result["summary"],
                "media_files": media_files,
            }

        except Exception as e:
            self.logger.error(f"处理文本和媒体失败: {e}")
            await self.handle_error(message, e, status_message_id)
            raise

    async def process(
        self, message: Message, status_message_id: Optional[str] = None
    ) -> Dict:
        """处理媒体消息

        Args:
            message: 统一消息格式
            status_message_id: 状态消息ID（用于Telegram）

        Returns:
            Dict: 处理结果
        """
        message_type = message.content.type

        if message_type in [MessageType.VOICE, MessageType.AUDIO]:
            return await self.process_voice(message, status_message_id)
        else:
            return await self.process_text_with_media(message, status_message_id)
