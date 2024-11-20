from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from ...utils.logger import Logger
from telegram import Bot, Message


class TelegramStateManager:
    """Telegram 状态管理器

    职责:
    1. 管理用户状态
    2. 管理状态消息
    3. 状态超时处理
    """

    def __init__(self, timeout: float = 60.0):
        """初始化状态管理器

        Args:
            timeout: 状态超时时间(秒)
        """
        self.logger = Logger("telegram.state")
        self.timeout = timeout
        self.bot: Optional[Bot] = None
        self._states: Dict[int, Dict] = {}  # 用户状态
        self._status_messages: Dict[str, Message] = {}  # 状态消息 {message_id: message}
        self._user_messages: Dict[int, List[int]] = {}  # {user_id: [message_ids]}
        self._menu_states: Dict[int, str] = {}  # {user_id: current_menu}

    def set_state(
        self, user_id: int, data: Dict, timeout: Optional[float] = None
    ) -> None:
        """设置用户状态

        Args:
            user_id: 用户ID
            data: 状态数据
            timeout: 超时时间(秒)
        """
        self._states[user_id] = {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=timeout or self.timeout),
        }

    def get_state(self, user_id: int) -> Optional[Dict]:
        """获取用户状态

        Args:
            user_id: 用户ID

        Returns:
            Dict: 状态数据
            None: 如果状态不存在或已过期
        """
        state = self._states.get(user_id)
        if not state:
            return None

        # 检查是否过期
        if datetime.now() > state["expires"]:
            self.clear_state(user_id)
            return None

        return state

    def clear_state(self, user_id: int) -> None:
        """清除用户状态

        Args:
            user_id: 用户ID
        """
        self._states.pop(user_id, None)

    async def create_status_message(
        self,
        chat_id: str,
        text: str,
        reply_to_message_id: Optional[int] = None,
    ) -> Message:
        """创建状态消息"""
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id,
                allow_sending_without_reply=True,
            )
            # 存储状态消息
            self._status_messages[str(message.message_id)] = message
            return message
        except Exception as e:
            self.logger.error(f"创建状态消息失败: {e}")
            raise

    async def update_status_message(self, message_id: str, text: str) -> bool:
        """更新状态消息"""
        try:
            if not self.bot:
                raise ValueError("Bot未初始化")

            message = self._status_messages.get(message_id)
            if not message:
                self.logger.warning(f"状态消息不存在: {message_id}")
                return False

            # 更新消息
            await message.edit_text(text)
            return True

        except Exception as e:
            self.logger.error(f"更新状态消息失败: {e}")
            return False

    async def delete_status_message(self, message_id: str) -> bool:
        """删除状态消息

        Args:
            message_id: 消息ID

        Returns:
            bool: 是否删除成功
        """
        try:
            if not self.bot:
                raise ValueError("Bot未初始化")

            message = self._status_messages.pop(message_id, None)
            if not message:
                return False

            await message.delete()
            return True

        except Exception as e:
            self.logger.error(f"删除状态消息失败: {e}")
            return False

    def get_status_message(self, message_id: str) -> Optional[Message]:
        """获取状态消息

        Args:
            message_id: 消息ID

        Returns:
            Message: 状态消息
            None: 如果消息不存在
        """
        return self._status_messages.get(message_id)

    def create_status(self, message_id: str, platform: str) -> Dict:
        """创建状态信息

        Args:
            message_id: 消息ID
            platform: 平台标识

        Returns:
            Dict: 状态信息
        """
        return {
            "message_id": message_id,
            "platform": platform,
            "start_time": datetime.now(),
            "status": "received",
            "progress": 0.0,
            "details": {},
        }

    def add_message(self, user_id: int, message_id: int) -> None:
        """添加用户消息记录

        Args:
            user_id: 用户ID
            message_id: 消息ID
        """
        if user_id not in self._user_messages:
            self._user_messages[user_id] = []
        self._user_messages[user_id].append(message_id)

    def get_user_messages(self, user_id: int) -> List[int]:
        """获取用户消息记录

        Args:
            user_id: 用户ID

        Returns:
            List[int]: 消息ID列表
        """
        return self._user_messages.get(user_id, [])

    def clear_user_messages(self, user_id: int) -> None:
        """清除用户消息记录

        Args:
            user_id: 用户ID
        """
        self._user_messages.pop(user_id, None)

    def set_menu_state(self, user_id: int, menu: str) -> None:
        """设置用户当前菜单状态

        Args:
            user_id: 用户ID
            menu: 菜单标识
        """
        self._menu_states[user_id] = menu

    def get_menu_state(self, user_id: int) -> Optional[str]:
        """获取用户当前菜单状态

        Args:
            user_id: 用户ID

        Returns:
            Optional[str]: 菜单标识
        """
        return self._menu_states.get(user_id)

    def clear_menu_state(self, user_id: int) -> None:
        """清除用户菜单状态

        Args:
            user_id: 用户ID
        """
        self._menu_states.pop(user_id, None)

    def format_status_text(
        self, progress: Optional[float], step: str, description: str, emoji: str = ""
    ) -> str:
        """格式化状态文本

        Args:
            progress: 进度值(0-1)或None
            step: 处理步骤
            description: 状态描述
            emoji: 状态emoji

        Returns:
            str: 格式化后的状态文本
        """
        # 构建状态文本
        if emoji:
            description = f"{emoji} {description}"

        # 如果有进度值，显示进度条
        if progress is not None:
            # 使用更短的进度条，并将百分比放在同一行
            bar_length = 10  # 减少进度条长度
            filled_length = int(progress * bar_length)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            # 进度条单独一行
            description = f"{description}\n{bar} {int(progress * 100)}%"

        return description

    async def update_status(
        self,
        message_id: str,
        status: str,
        step: str,
        progress: float,
        description: str,
        details: Dict = None,
    ) -> bool:
        """更新状态

        Args:
            message_id: 消息ID
            status: 状态
            step: 步骤
            progress: 进度
            description: 描述
            details: 详细信息

        Returns:
            bool: 是否更新成功
        """
        try:
            # 直接调用 update_status_message 方法更新消息文本
            return await self.update_status_message(
                message_id=message_id,
                text=description,  # 直接使用传入的描述作为消息文本
            )

        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")
            return False
