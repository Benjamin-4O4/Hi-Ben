from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
from .....utils.logger import Logger
from .....utils.config_manager import ConfigManager
from ..auth_manager import DidaAuthManager
from telegram import Update, CallbackQuery, User
import asyncio
from datetime import datetime
from telegram.ext import CallbackContext
from telegram import Message, Chat
import time
from ...dida_api import DidaAPI
from ..models import TokenInfo


class DidaAuthGateway:
    """滴答清单OAuth授权网关"""

    def __init__(self):
        """初始化授权网关"""
        self.logger = Logger("dida.auth.gateway")
        self.config_manager = ConfigManager()
        self.app = FastAPI(title="Dida365 Auth Gateway")
        self.dida_auth = DidaAuthManager()
        self._used_states = set()  # 添加已使用的state集合

        # 设置模板目录
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # 初始化模板引擎
        self.templates = Jinja2Templates(directory=str(self.templates_dir))

        # 注册路由
        self._setup_routes()

    def _is_state_valid(self, state: str) -> tuple[bool, str]:
        """检查state是否有效，并返回错误信息

        Args:
            state: 状态字符串 (格式: user_id:message_id:timestamp:random_str)

        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            # 检查格式
            parts = state.split(":")
            if len(parts) != 4:
                return False, "无效的授权链接"

            # 获取时间戳
            timestamp = float(parts[2])

            # 检查是否在5分钟内
            if (time.time() - timestamp) > 300:  # 300秒 = 5分钟
                return False, "授权链接已过期（有效期5分钟），请返回Telegram重新获取"

            # 检查是否已使用
            if state in self._used_states:
                return False, "授权链接已被使用，请返回Telegram重新获取"

            return True, ""

        except (IndexError, ValueError):
            return False, "无效的授权链接格式"

    async def _sync_projects(self, user_id: str, token_info: TokenInfo) -> None:
        """同步用户的项目列表"""
        try:
            # 获取项目列表
            api = DidaAPI(token_info.access_token)
            projects = await api.get_projects()

            # 保存项目列表
            self.config_manager.set_user_config(user_id, "dida.projects", projects)
            self.logger.info(f"已同步 {len(projects)} 个项目")

        except Exception as e:
            self.logger.error(f"同步项目列表失败: {str(e)}")
            # 这里我们只记录错误，不抛出异常，因为这不应该影响授权流程

    async def _send_settings_menu(self, bot, user_id: str) -> None:
        """发送设置菜单

        Args:
            bot: Telegram Bot实例
            user_id: 用户ID
        """
        try:
            # 导入所需的处理器
            from src.platforms.telegram.handlers.settings import DidaSettingsHandler
            from telegram.ext import CallbackContext
            from telegram import Update, Message, Chat, User

            # 创建处理器实例
            settings_handler = DidaSettingsHandler()

            # 创建一个简单的消息对象
            message = Message(
                message_id=0,
                date=0,
                chat=Chat(id=int(user_id), type="private"),
                from_user=User(id=int(user_id), is_bot=False, first_name="User"),
            )

            # 创建Update对象
            update = Update(0)
            update._message = message  # 使用_message而不是直接设置message

            # 创建Context对象
            context = CallbackContext.from_update(update, bot)
            context.bot = bot
            context._bot_data = {
                'state_manager': bot.application.bot_data.get('state_manager')
            }

            # 显示设置菜单
            await settings_handler.show_menu(update, context)

        except Exception as e:
            self.logger.error(f"发送设置菜单失败: {str(e)}")
            raise

    def _setup_routes(self):
        """设置路由"""

        @self.app.get("/")
        async def index(request: Request):
            """网关首页"""
            return self.templates.TemplateResponse(
                "base.html",
                {
                    "request": request,
                    "title": "Hi-Ben Auth Gateway",
                    "message": "OAuth授权网关服务正在运行",
                    "detail": "请通过Telegram Bot进行授权操作",
                },
            )

        @self.app.get("/dida/callback")
        async def dida_callback(request: Request, code: str = None, state: str = None):
            """处理滴答清单OAuth回调"""
            try:
                if not code or not state:
                    return self.templates.TemplateResponse(
                        "error.html",
                        {
                            "request": request,
                            "title": "授权失败",
                            "message": "缺少必要的参数",
                            "detail": "请返回Telegram重新获取授权链接",
                        },
                        status_code=400,
                    )

                # 检查state是否有效
                is_valid, error_msg = self._is_state_valid(state)
                if not is_valid:
                    return self.templates.TemplateResponse(
                        "error.html",
                        {
                            "request": request,
                            "title": "授权失败",
                            "message": error_msg,
                            "detail": "请返回Telegram重新获取授权链接",
                        },
                        status_code=400,
                    )

                # 从state中提取用户ID和消息ID
                parts = state.split(":")
                user_id = parts[0]
                message_id = int(parts[1])

                self.logger.info(
                    f"收到OAuth回调: user_id={user_id}, message_id={message_id}"
                )

                # 标记state为已使用
                self._used_states.add(state)

                # 交换访问令牌
                try:
                    token_info = await self.dida_auth.exchange_code(user_id, code)
                    self.logger.info(f"用户 {user_id} 授权成功")

                    # 同步项目列表
                    await self._sync_projects(user_id, token_info)

                    # 发送Telegram通知
                    try:
                        bot = request.app.state.bot
                        if bot:
                            # 先删除旧的授权菜单
                            try:
                                await bot.delete_message(
                                    chat_id=user_id, message_id=message_id
                                )
                                self.logger.info(
                                    f"已删除旧的授权菜单 message_id={message_id}"
                                )
                            except Exception as e:
                                self.logger.warning(f"删除旧菜单失败: {str(e)}")

                            # 发送临时成功消息
                            status_message = await bot.send_message(
                                chat_id=user_id,
                                text="🔄 正在处理授权...\n\n" "• 验证授权码...",
                            )

                            # 更新验证状态
                            await status_message.edit_text(
                                "🔄 正在处理授权...\n\n"
                                "• 验证授权码... ✅\n"
                                "• 获取访问令牌..."
                            )

                            # 更新验证状态
                            await status_message.edit_text(
                                "🔄 正在处理授权...\n\n"
                                "• 验证授权码... ✅\n"
                                "• 获取访问令牌... ✅\n"
                                "• 保存配置..."
                            )

                            # 更新最终状态
                            await status_message.edit_text(
                                "✅ 滴答清单授权成功！\n\n" "2秒后返回设置菜单..."
                            )

                            # 等待2秒
                            await asyncio.sleep(2)

                            # 删除状态消息
                            await status_message.delete()

                            # 使用统一的方法发送设置菜单
                            await self._send_settings_menu(bot, user_id)

                    except Exception as e:
                        self.logger.error(f"发送Telegram通知失败: {str(e)}")

                except Exception as e:
                    self.logger.error(f"令牌交换失败: {str(e)}")
                    return self.templates.TemplateResponse(
                        "error.html",
                        {
                            "request": request,
                            "title": "授权失败",
                            "message": str(e),
                            "detail": "请返回Telegram重新尝试授权",
                        },
                        status_code=400,
                    )

                return self.templates.TemplateResponse(
                    "success.html",
                    {
                        "request": request,
                        "title": "授权成功",
                        "message": "滴答清单授权已完成",
                        "detail": "请返回Telegram继续操作",
                    },
                )

            except Exception as e:
                self.logger.error(f"处理回调失败: {str(e)}")
                return self.templates.TemplateResponse(
                    "error.html",
                    {
                        "request": request,
                        "title": "授权失败",
                        "message": str(e),
                        "detail": "请返回Telegram重试",
                    },
                    status_code=400,
                )

    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """启动网关服务"""
        try:
            self.logger.info(f"正在启动授权网关 [http://{host}:{port}]")
            config = uvicorn.Config(
                app=self.app, host=host, port=port, log_level="info", access_log=True
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            self.logger.error(f"启动授权网关失败: {str(e)}")
            raise
