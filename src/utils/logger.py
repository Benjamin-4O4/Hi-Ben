import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import functools


class Logger:
    """日志管理器"""

    _loggers = {}

    def __new__(cls, name: str):
        if name not in cls._loggers:
            instance = super(Logger, cls).__new__(cls)
            instance._init_logger(name)
            cls._loggers[name] = instance
        return cls._loggers[name]

    def _init_logger(self, name: str):
        """初始化日志记录器"""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 如果已经有处理器，不重复添加
        if self.logger.handlers:
            return

        # 创建日志目录
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # 文件处理器
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 设置格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)


def log_async(func):
    """异步函数日志装饰器"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = Logger(func.__module__)
        try:
            logger.debug(f"调用 {func.__name__} - 参数: {args}, {kwargs}")
            result = await func(*args, **kwargs)
            logger.debug(f"{func.__name__} 返回: {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {str(e)}", exc_info=True)
            raise

    return wrapper


def log_sync(func):
    """同步函数日志装饰器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = Logger(func.__module__)
        try:
            logger.debug(f"调用 {func.__name__} - 参数: {args}, {kwargs}")
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} 返回: {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {str(e)}", exc_info=True)
            raise

    return wrapper
