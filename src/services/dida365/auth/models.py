from typing import Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class OAuthConfig:
    """OAuth配置"""

    client_id: str
    client_secret: str
    redirect_uri: str = (
        "https://api.example.com/dida/callback"  # 需要替换为实际的回调地址
    )


@dataclass
class TokenInfo:
    """令牌信息"""

    access_token: str
    refresh_token: str = ''  # 可选字段
    token_type: str = 'Bearer'  # 默认值
    expires_in: int = 3600  # 默认1小时
    scope: str = 'tasks:write tasks:read'  # 默认scope
    user_id: str = ''  # 用户ID
    created_at: datetime = field(default_factory=datetime.now)  # 使用field设置默认值

    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        return datetime.now() > self.created_at + timedelta(seconds=self.expires_in)

    def get_expires_info(self) -> str:
        """获取过期时间信息"""
        expires_at = self.created_at + timedelta(seconds=self.expires_in)
        remaining = expires_at - datetime.now()

        if remaining.total_seconds() <= 0:
            return "已过期"

        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return f"{hours}小时{minutes}分钟后过期"

    def get_status_emoji(self) -> str:
        """获取状态emoji"""
        if self.is_expired():
            return "⚠️"
        return "✅"

    @classmethod
    def from_dict(cls, data: dict, user_id: str) -> 'TokenInfo':
        """从字典创建令牌信息"""
        # 如果有created_at字段，将其转换为datetime对象
        if 'created_at' in data:
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])

        return cls(
            access_token=data['access_token'],
            refresh_token=data.get('refresh_token', ''),
            token_type=data.get('token_type', 'Bearer'),
            expires_in=int(data.get('expires_in', 3600)),
            scope=data.get('scope', 'tasks:write tasks:read'),
            user_id=user_id,
            created_at=data.get('created_at', datetime.now()),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_type': self.token_type,
            'expires_in': self.expires_in,
            'scope': self.scope,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
        }
