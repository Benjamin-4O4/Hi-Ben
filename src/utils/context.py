from typing import Optional, Dict, Any, List
from contextvars import ContextVar, Token
from datetime import datetime
from .logger import Logger

# 上下文变量
request_id_ctx = ContextVar('request_id', default=None)
user_id_ctx = ContextVar('user_id', default=None)
start_time_ctx = ContextVar('start_time', default=None)
metadata_ctx = ContextVar('metadata', default={})


class RequestContext:
    """请求上下文管理器"""

    def __init__(self, request_id: str, user_id: Optional[str] = None, **metadata):
        self.request_id = request_id
        self.user_id = user_id
        self.metadata = metadata
        self.logger = Logger(__name__)
        self._tokens = {}  # 使用字典存储每个变量的 token

    async def __aenter__(self):
        # 设置上下文变量并保存对应的 token
        self._tokens = {
            'request_id': request_id_ctx.set(self.request_id),
            'user_id': user_id_ctx.set(self.user_id),
            'start_time': start_time_ctx.set(datetime.now()),
            'metadata': metadata_ctx.set(self.metadata),
        }

        self.logger.info(
            f"开始请求处理 [request_id={self.request_id}] [user_id={self.user_id}]"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            # 计算处理时间
            start_time = start_time_ctx.get()
            if start_time:
                duration = (datetime.now() - start_time).total_seconds()
                self.logger.info(
                    f"请求处理完成 [request_id={self.request_id}] [duration={duration:.3f}s]"
                )

            # 恢复上下文变量
            for var_name, token in self._tokens.items():
                if var_name == 'request_id':
                    request_id_ctx.reset(token)
                elif var_name == 'user_id':
                    user_id_ctx.reset(token)
                elif var_name == 'start_time':
                    start_time_ctx.reset(token)
                elif var_name == 'metadata':
                    metadata_ctx.reset(token)

            # 记录异常
            if exc_type:
                self.logger.error(
                    f"请求处理异常 [request_id={self.request_id}] "
                    f"[error={exc_type.__name__}] {str(exc_val)}",
                    exc_info=True,
                )
        except Exception as e:
            self.logger.error(f"上下文清理失败: {str(e)}")

    @classmethod
    def get_current_request_id(cls) -> Optional[str]:
        """获取当前请求ID"""
        return request_id_ctx.get()

    @classmethod
    def get_current_user_id(cls) -> Optional[str]:
        """获取当前用户ID"""
        return user_id_ctx.get()

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """获取当前元数据"""
        return metadata_ctx.get()
