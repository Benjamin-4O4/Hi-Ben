from typing import Optional
import torch
import whisper
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager


class WhisperService:
    """Whisper 语音识别服务

    负责:
    1. 语音转文本
    2. 模型管理
    3. 设备管理
    """

    def __init__(self):
        """初始化 Whisper 服务"""
        self.logger = Logger("services.whisper")
        self.config = ConfigManager()

        # 获取配置
        self.model_name = self.config.get("whisper", "model", default="base")
        self.device = self.config.get("whisper", "device", default="cpu")

        # 检查 CUDA 可用性
        if self.device == "cuda" and not torch.cuda.is_available():
            self.logger.warning("CUDA不可用，切换到CPU")
            self.device = "cpu"

        self.logger.info(f"使用设备: {self.device}")
        self.logger.info(f"使用模型: {self.model_name}")

        # 加载模型
        try:
            self.model = whisper.load_model(self.model_name)
            self.model = self.model.to(self.device)
            self.logger.info("Whisper模型加载成功")
        except Exception as e:
            self.logger.error(f"加载Whisper模型失败: {e}")
            raise

    async def transcribe(self, audio_path: str, language: Optional[str] = "zh") -> str:
        """转录音频文件

        Args:
            audio_path: 音频文件路径
            language: 语言代码(默认中文)

        Returns:
            str: 转录文本

        Raises:
            Exception: 转录失败
        """
        try:
            self.logger.info(f"开始转录音频: {audio_path}")

            # 转录配置
            options = {
                "language": language,
                "task": "transcribe",
                "fp16": False if self.device == "cpu" else True,
            }

            # 执行转录
            result = self.model.transcribe(audio_path, **options)

            # 获取文本
            text = result["text"].strip()

            self.logger.info("转录完成")
            return text

        except Exception as e:
            self.logger.error(f"转录音频失败: {e}")
            raise

    def __del__(self):
        """清理资源"""
        try:
            # 释放 CUDA 内存
            if hasattr(self, 'model') and self.device == "cuda":
                del self.model
                torch.cuda.empty_cache()
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")
