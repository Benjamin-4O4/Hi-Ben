from typing import Dict, List, Optional, Any
from datetime import datetime
from .dida_api import DidaAPI
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager
from ...utils.exceptions import ServiceError


class DidaService:
    """滴答清单服务

    负责:
    1. 业务逻辑处理
    2. 数据转换和验证
    3. 配置管理
    4. 错误处理
    """

    def __init__(self):
        """初始化滴答清单服务"""
        self.logger = Logger("dida.service")
        self.config_manager = ConfigManager()
        self._apis: Dict[str, DidaAPI] = {}  # 用户ID -> API实例的映射

    def _get_api(self, user_id: str) -> DidaAPI:
        """获取用户的 API 实例

        Args:
            user_id: 用户ID

        Returns:
            DidaAPI: API实例

        Raises:
            ServiceError: 配置无效
        """
        try:
            if user_id not in self._apis:
                token_info = self.config_manager.get_user_value(user_id, "dida.token")
                if not token_info:
                    raise ServiceError("未配置滴答清单访问令牌")

                # 获取access_token
                access_token = token_info.get('access_token')
                if not access_token:
                    raise ServiceError("无效的访问令牌")

                self.logger.debug(f"获取到access_token: {access_token[:10]}...")
                self._apis[user_id] = DidaAPI(access_token)

            return self._apis[user_id]

        except Exception as e:
            self.logger.error(f"获取API实例失败: {str(e)}")
            raise ServiceError(f"获取API实例失败: {str(e)}")

    async def add_task(
        self,
        user_id: str,
        title: str,
        content: Optional[str] = None,
        project_id: Optional[str] = None,
        desc: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: Optional[int] = None,
        is_all_day: bool = False,
        reminders: Optional[List[str]] = None,
    ) -> Dict:
        """添加任务

        Args:
            user_id: 用户ID
            title: 任务标题
            content: 任务内容
            project_id: 项目ID
            desc: 任务描述
            due_date: 截止日期
            priority: 优先级 (0-5)
            is_all_day: 是否全天任务
            reminders: 提醒规则列表

        Returns:
            Dict: 创建的任务信息

        Raises:
            ServiceError: 添加失败
        """
        try:
            api = self._get_api(user_id)

            # 获取默认标签
            default_tag = self.config_manager.get_user_value(
                user_id, "dida.default_tag"
            )
            self.logger.debug(f"获取到默认标签: {default_tag}")

            # 构建任务数据
            task_data = {
                "title": title,
                "isAllDay": is_all_day,
                "priority": priority if priority is not None else 0,
                "timeZone": "Asia/Shanghai",
            }

            if content:
                task_data["content"] = content
            if project_id:
                task_data["projectId"] = project_id
            if desc:
                task_data["desc"] = desc
            if due_date:
                task_data["dueDate"] = due_date.strftime("%Y-%m-%dT%H:%M:%S+0800")
            if reminders:
                task_data["reminders"] = reminders
            if default_tag:
                task_data["tags"] = [default_tag]  # 添加默认标签
                self.logger.debug(f"已添加默认标签到任务: {default_tag}")

            # 创建任务
            self.logger.debug(f"创建任务: {task_data}")
            created_task = await api.create_task(task_data)

            self.logger.info(f"添加任务成功: {title}")
            return created_task

        except Exception as e:
            self.logger.error(f"添加任务失败: {str(e)}")
            raise ServiceError(f"添加任务失败: {str(e)}")

    async def get_tasks(
        self,
        user_id: str,
        project_name: Optional[str] = None,
        completed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """获取任务列表

        Args:
            user_id: 用户ID
            project_name: 项目名称
            completed: 是否已完成
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[Dict]: 任务列表

        Raises:
            ServiceError: 获取失败
        """
        try:
            api = self._get_api(user_id)

            # 获取项目ID
            project_id = None
            if project_name:
                projects = await api.get_projects()
                project = next((p for p in projects if p["name"] == project_name), None)
                if project:
                    project_id = project["id"]
                else:
                    raise ServiceError(f"项目不存在: {project_name}")

            # 获取任务列表
            tasks = await api.get_tasks(
                project_id=project_id,
                completed=completed,
                start_date=start_date,
                end_date=end_date,
            )

            return tasks

        except Exception as e:
            self.logger.error(f"获取任务列表失败: {str(e)}")
            raise ServiceError(f"获取任务列表失败: {str(e)}")
