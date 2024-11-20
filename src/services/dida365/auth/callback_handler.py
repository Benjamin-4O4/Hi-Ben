from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from ....utils.logger import Logger
from ....utils.config_manager import ConfigManager
from .auth_manager import DidaAuthManager


class DidaCallbackHandler:
    """滴答清单OAuth回调处理器"""

    def __init__(self, app: FastAPI):
        """初始化回调处理器

        Args:
            app: FastAPI应用实例
        """
        self.app = app
        self.logger = Logger("dida.callback")
        self.auth_manager = DidaAuthManager()
        self.config_manager = ConfigManager()

        # 注册路由
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""

        @self.app.get("/dida/callback")
        async def handle_callback(
            request: Request, code: str, state: Optional[str] = None
        ):
            """处理OAuth回调

            Args:
                request: 请求对象
                code: 授权码
                state: 状态码
            """
            try:
                # 从state中提取用户ID
                if not state:
                    raise HTTPException(
                        status_code=400, detail="Missing state parameter"
                    )

                # state格式: user_id:random_string
                user_id = state.split(":")[0]

                # 使用授权码获取令牌
                await self.auth_manager.exchange_code(user_id, code)

                # 返回成功页面
                return """
                <html>
                    <head>
                        <title>授权成功</title>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                margin: 0;
                                background-color: #f5f5f5;
                            }
                            .container {
                                text-align: center;
                                padding: 20px;
                                background-color: white;
                                border-radius: 8px;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            }
                            .success-icon {
                                color: #4CAF50;
                                font-size: 48px;
                                margin-bottom: 16px;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="success-icon">✓</div>
                            <h1>授权成功！</h1>
                            <p>请返回Telegram继续操作</p>
                        </div>
                    </body>
                </html>
                """

            except Exception as e:
                self.logger.error(f"处理回调失败: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
