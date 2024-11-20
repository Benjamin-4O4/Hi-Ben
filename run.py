"""Hi-Ben 主程序"""

import asyncio
import logging
from src.utils.logger import Logger
from src.utils.config_manager import ConfigManager
from src.platforms.telegram.telegram_bot import TelegramBot
from src.services.dida365.auth.gateway.auth_gateway import DidaAuthGateway

# 配置日志
logger = Logger(__name__)


async def start_gateway(gateway: DidaAuthGateway):
    """启动授权网关服务"""
    try:
        logger.info("正在启动授权网关服务...")
        await gateway.start(host="127.0.0.1", port=8000)
        logger.info("授权网关服务启动成功")
    except Exception as e:
        logger.error(f"启动授权网关服务失败: {str(e)}")
        raise


async def start_bot(bot: TelegramBot):
    """启动Telegram Bot服务"""
    try:
        logger.info("正在启动Telegram Bot服务...")
        await bot.start()
        logger.info("Telegram Bot服务启动成功")
    except Exception as e:
        logger.error(f"启动Telegram Bot服务失败: {str(e)}")
        raise


async def main():
    """主函数"""
    try:
        # 初始化配置
        config_manager = ConfigManager()

        # 创建服务实例
        bot = TelegramBot()
        gateway = DidaAuthGateway()

        # 初始化 bot
        await bot.initialize()

        # 将bot实例存储到gateway的应用状态中
        gateway.app.state.bot = bot.bot
        gateway.app.state.state_manager = bot.state_manager

        # 创建并启动服务
        tasks = [
            asyncio.create_task(start_bot(bot), name="bot"),
            asyncio.create_task(start_gateway(gateway), name="gateway"),
        ]

        # 等待所有任务完成或出错
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_EXCEPTION  # 任何任务出错时立即返回
        )

        # 检查是否有任务出错
        for task in done:
            if task.exception():
                logger.error(f"服务出错: {task.get_name()} - {task.exception()}")
                raise task.exception()

    except Exception as e:
        logger.error(f"运行出错: {str(e)}")
        if 'bot' in locals():
            await bot.stop()
        raise


if __name__ == "__main__":
    try:
        logger.info("正在启动服务...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"运行出错: {str(e)}")
