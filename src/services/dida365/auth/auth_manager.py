from typing import Optional, Dict
import requests
from datetime import datetime
import json
from pathlib import Path
from ....utils.logger import Logger
from ....utils.config_manager import ConfigManager
from ....utils.exceptions import ServiceError
from .models import TokenInfo, OAuthConfig
import base64


class DidaAuthManager:
    """滴答清单认证管理器"""

    AUTH_URL = "https://dida365.com/oauth/authorize"
    TOKEN_URL = "https://dida365.com/oauth/token"

    def __init__(self):
        """初始化认证管理器"""
        self.logger = Logger("dida.auth")
        self.config_manager = ConfigManager()
        self.data_dir = Path("data/dida/tokens")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 从系统配置获取回调地址
        self.redirect_uri = self.config_manager.get('dida', 'redirect_uri')
        if not self.redirect_uri:
            raise ValueError("系统未配置滴答清单回调地址")

    def get_oauth_config(self, user_id: str) -> Optional[OAuthConfig]:
        """获取用户的OAuth配置

        Args:
            user_id: 用户ID

        Returns:
            Optional[OAuthConfig]: OAuth配置对象，如果配置不存在则返回None
        """
        try:
            client_id = self.config_manager.get_user_value(user_id, "dida.client_id")
            client_secret = self.config_manager.get_user_value(
                user_id, "dida.client_secret"
            )

            if not client_id or not client_secret:
                self.logger.warning(f"用户 {user_id} 的OAuth配置不完整")
                return None

            return OAuthConfig(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=self.redirect_uri,
            )

        except Exception as e:
            self.logger.error(f"获取OAuth配置失败: {str(e)}")
            return None

    def get_auth_url(self, user_id: str, state: str) -> str:
        """获取授权URL

        Args:
            user_id: 用户ID
            state: 状态码

        Returns:
            str: 授权URL

        Raises:
            ServiceError: 获取失败
        """
        self.logger.info(f"正在获取授权URL: user_id={user_id}, state={state}")

        config = self.get_oauth_config(user_id)
        if not config:
            raise ServiceError("请先配置Client ID和Client Secret")

        # 参考示例构建URL
        auth_url = (
            f"{self.AUTH_URL}"
            f"?client_id={config.client_id}"
            f"&redirect_uri={config.redirect_uri}"
            f"&state={state}"
            f"&response_type=code"
            f"&scope=tasks:write tasks:read"
        )

        self.logger.info(f"生成授权URL: {auth_url}")
        return auth_url

    async def exchange_code(self, user_id: str, code: str) -> TokenInfo:
        """使用授权码交换访问令牌"""
        try:
            config = self.get_oauth_config(user_id)
            if not config:
                raise ServiceError("无效的OAuth配置")

            # 构建请求数据
            data = {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            }

            self.logger.info("正在交换访问令牌...")
            self.logger.debug(f"请求数据: {data}")
            self.logger.debug(f"请求头: {headers}")

            # 发送请求
            response = requests.post(
                self.TOKEN_URL, data=data, headers=headers, verify=True
            )

            # 记录响应
            self.logger.debug(f"响应状态码: {response.status_code}")
            self.logger.debug(f"响应内容: {response.text}")
            self.logger.debug(f"响应头: {response.headers}")

            if response.status_code != 200:
                error_msg = f"交换访问令牌失败: HTTP {response.status_code}"
                if response.text:
                    error_msg += f"\n响应内容: {response.text}"
                raise ServiceError(error_msg)

            token_data = response.json()
            self.logger.debug(f"令牌数据: {token_data}")

            # 构造令牌信息，使用默认值处理可能缺失的字段
            token_info = TokenInfo(
                access_token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token', ''),
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=int(token_data.get('expires_in', 3600)),
                scope=token_data.get('scope', 'tasks:write tasks:read'),
                user_id=user_id,
            )

            # 验证必要字段
            if not token_info.access_token:
                raise ServiceError("响应中缺少access_token")

            self.logger.info("成功获取访问令牌")

            # 保存到用户配置
            token_dict = token_info.to_dict()
            self.config_manager.set_user_config(user_id, "dida.token", token_dict)
            self.logger.info(f"令牌信息已保存到用户配置: {token_dict}")

            # 同时保存到令牌文件
            self._save_token(token_info)
            self.logger.info("令牌信息已保存到文件")

            return token_info

        except Exception as e:
            error_msg = f"交换访问令牌失败: {str(e)}"
            self.logger.error(error_msg)
            raise ServiceError(error_msg)

    async def refresh_token(self, user_id: str, refresh_token: str) -> TokenInfo:
        """刷新访问令牌

        Args:
            user_id: 用户ID
            refresh_token: 刷新令牌

        Returns:
            TokenInfo: 新的令牌信息

        Raises:
            ServiceError: 刷新失败
        """
        try:
            config = self.get_oauth_config(user_id)
            if not config:
                raise ServiceError("无效的OAuth配置")

            data = {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post(
                self.TOKEN_URL, data=data, headers={"Accept": "application/json"}
            )
            response.raise_for_status()

            token_data = response.json()
            token_info = TokenInfo.from_dict(token_data, user_id)
            self._save_token(token_info)

            return token_info

        except Exception as e:
            self.logger.error(f"刷新令牌失败: {str(e)}")
            raise ServiceError(f"刷新访问令牌失败: {str(e)}")

    async def get_valid_token(self, user_id: str) -> Optional[TokenInfo]:
        """获取有效的令牌信息

        Args:
            user_id: 用户ID

        Returns:
            TokenInfo: 令牌信息
            None: 如果没有有效的令牌
        """
        try:
            token_info = self._load_token(user_id)
            if not token_info:
                return None

            if token_info.is_expired():
                # 令牌过期，尝试刷新
                token_info = await self.refresh_token(user_id, token_info.refresh_token)

            return token_info

        except Exception as e:
            self.logger.error(f"获取有效令牌失败: {str(e)}")
            return None

    def _save_token(self, token_info: TokenInfo) -> None:
        """保存令牌信息

        Args:
            token_info: 令牌信息
        """
        try:
            file_path = self.data_dir / f"{token_info.user_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(token_info.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存令牌失败: {str(e)}")

    def _load_token(self, user_id: str) -> Optional[TokenInfo]:
        """加载令牌信息

        Args:
            user_id: 用户ID

        Returns:
            TokenInfo: 令牌信息
            None: 如果文件不存在
        """
        try:
            file_path = self.data_dir / f"{user_id}.json"
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                return TokenInfo(**data)

        except Exception as e:
            self.logger.error(f"加载令牌失败: {str(e)}")
            return None
