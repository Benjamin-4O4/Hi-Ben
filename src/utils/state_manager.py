from typing import Dict, Any, Optional, Callable, Coroutine
import asyncio
from datetime import datetime
from .logger import Logger


class StateManager:
    """状态管理器基类

    负责:
    1. 用户状态管理
    2. 状态超时处理
    3. 状态清理
    4. 倒计时管理
    """

    def __init__(self, timeout: float = 60.0):
        self.logger = Logger(__name__)
        self._states: Dict[int, Dict[str, Any]] = {}  # 用户状态
        self._timers: Dict[int, asyncio.Task] = {}  # 超时计时器
        self._countdown_timers: Dict[int, asyncio.Task] = {}  # 倒计时计时器
        self._timeout = timeout  # 默认超时时间(秒)
        self._countdown_handlers: Dict[int, Callable] = {}  # 倒计时处理器

    def get_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户状态"""
        return self._states.get(user_id)

    def set_state(
        self,
        user_id: int,
        state_data: Dict[str, Any],
        timeout: Optional[float] = None,
        countdown_handler: Optional[Callable[[int, int], Coroutine]] = None,
    ) -> None:
        """设置用户状态

        Args:
            user_id: 用户ID
            state_data: 状态数据
            timeout: 可选的超时时间，None则使用默认值
            countdown_handler: 倒计时处理函数，接收剩余秒数和用户ID
        """
        self._states[user_id] = {
            "data": state_data,
            "timestamp": datetime.now(),
        }

        if countdown_handler:
            self._countdown_handlers[user_id] = countdown_handler

        self._reset_timer(user_id, timeout or self._timeout)

    def clear_state(self, user_id: int) -> None:
        """清除用户状态"""
        if user_id in self._states:
            del self._states[user_id]
        if user_id in self._timers:
            self._timers[user_id].cancel()
            del self._timers[user_id]
        if user_id in self._countdown_timers:
            self._countdown_timers[user_id].cancel()
            del self._countdown_timers[user_id]
        if user_id in self._countdown_handlers:
            del self._countdown_handlers[user_id]

    def _reset_timer(self, user_id: int, timeout: float) -> None:
        """重置超时计时器"""
        if user_id in self._timers:
            self._timers[user_id].cancel()

        timer = asyncio.create_task(self._handle_timeout(user_id, timeout))
        self._timers[user_id] = timer

    async def _handle_timeout(self, user_id: int, timeout: float) -> None:
        """处理超时"""
        try:
            # 如果有倒计时处理器，先等待到倒计时开始
            if user_id in self._countdown_handlers:
                countdown_start = 10  # 倒计时开始前的秒数
                await asyncio.sleep(max(0, timeout - countdown_start))

                # 如果状态已清除，直接返回
                if user_id not in self._states:
                    return

                # 开始倒计时
                countdown_handler = self._countdown_handlers[user_id]
                # 创建倒计时任务，而不是直接等待
                countdown_task = asyncio.create_task(
                    self._run_countdown(countdown_handler, countdown_start, user_id)
                )
                self._countdown_timers[user_id] = countdown_task

                # 等待倒计时完成
                await countdown_task

            else:
                # 没有倒计时处理器，直接等待超时
                await asyncio.sleep(timeout)

            if user_id in self._states:
                # 触发超时回调
                await self._on_timeout(user_id)
                # 清理状态
                self.clear_state(user_id)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"处理状态超时失败: {str(e)}")

    async def _run_countdown(
        self, handler: Callable, countdown_start: int, user_id: int
    ) -> None:
        """运行倒计时"""
        for i in range(countdown_start, 0, -1):
            if user_id not in self._states:  # 如果状态已清除，停止倒计时
                break
            await handler(i, user_id)
            await asyncio.sleep(1)

    async def _on_timeout(self, user_id: int) -> None:
        """超时回调，由子类实现具体逻辑"""
        pass
