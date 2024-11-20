import asyncio
from functools import wraps
from typing import Type, Tuple, Optional, Callable, Any
from pydantic import BaseModel
from .logger import Logger
from .exceptions import AppError

logger = Logger(__name__)


def log_async(func):
    """异步函数日志装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        _logger = Logger(func.__module__)
        try:
            _logger.debug(f"调用 {func.__name__} - 参数: {args}, {kwargs}")
            result = await func(*args, **kwargs)
            _logger.debug(f"{func.__name__} 返回: {result}")
            return result
        except Exception as e:
            _logger.error(f"{func.__name__} 失败: {str(e)}", exc_info=True)
            raise

    return wrapper


def retry_async(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger: Optional[Logger] = None,
):
    """异步重试装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _logger = logger or Logger(__name__)
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        _logger.error(
                            f"{func.__name__} 最终失败: {str(e)}", exc_info=True
                        )
                        raise

                    _logger.warning(
                        f"{func.__name__} 第{attempt}次尝试失败: {str(e)}, "
                        f"{current_delay}秒后重试"
                    )

                    await asyncio.sleep(current_delay)
                    attempt += 1
                    current_delay *= backoff

            raise AppError(f"{func.__name__} 超过最大重试次数")

        return wrapper

    return decorator


def validate_params(validator: Type[BaseModel]):
    """参数验证装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # 验证kwargs
                validated_data = validator(**kwargs)
                # 更新kwargs为验证后的数据
                kwargs.update(validated_data.dict())
                return await func(*args, **kwargs)
            except ValueError as e:
                raise AppError(f"参数验证失败: {str(e)}")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                validated_data = validator(**kwargs)
                kwargs.update(validated_data.dict())
                return func(*args, **kwargs)
            except ValueError as e:
                raise AppError(f"参数验证失败: {str(e)}")

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
