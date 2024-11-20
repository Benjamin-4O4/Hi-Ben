from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from ...utils.logger import Logger
from ...utils.exceptions import ServiceError
from .dida_models import Task, ChecklistItem, TaskPriority, TaskStatus


class DidaAPI:
    """滴答清单 API 接口封装

    负责:
    1. API 调用的基础封装
    2. 错误处理和转换
    3. 数据格式转换
    """

    BASE_URL = "https://api.dida365.com/open/v1"

    def __init__(self, token: str):
        """初始化滴答清单 API 客户端

        Args:
            token: API访问令牌
        """
        self.logger = Logger("dida.api")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            }
        )

    async def get_projects(self) -> List[Dict]:
        """获取项目列表

        Returns:
            List[Dict]: 项目列表，每个项目包含:
                - id: 项目ID
                - name: 项目名称

        Raises:
            ServiceError: API调用失败
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/project")
            response.raise_for_status()
            projects = response.json()

            # 提取需要的字段并按sortOrder排序
            sorted_projects = sorted(projects, key=lambda x: x.get('sortOrder', 0))

            # 只保留id和name字段
            simplified_projects = [
                {'id': p['id'], 'name': p['name']} for p in sorted_projects
            ]

            self.logger.info(f"获取到 {len(simplified_projects)} 个项目")
            return simplified_projects

        except Exception as e:
            self.logger.error(f"获取项目列表失败: {str(e)}")
            raise ServiceError(f"获取项目列表失败: {str(e)}")

    async def create_project(self, name: str, color: Optional[str] = None) -> Dict:
        """创建新项目

        Args:
            name: 项目名称
            color: 项目颜色

        Returns:
            Dict: 创建的项目信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            data = {"name": name}
            if color:
                data["color"] = color

            response = self.session.post(f"{self.BASE_URL}/projects", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"创建项目失败: {str(e)}")
            raise ServiceError(f"创建项目失败: {str(e)}")

    async def get_tasks(
        self,
        project_id: Optional[str] = None,
        completed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """获取任务列表

        Args:
            project_id: 项目ID
            completed: 是否已完成
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[Dict]: 任务列表

        Raises:
            ServiceError: API调用失败
        """
        try:
            params = {}
            if project_id:
                params["projectId"] = project_id
            if completed is not None:
                params["completed"] = completed
            if start_date:
                params["startDate"] = start_date.isoformat()
            if end_date:
                params["endDate"] = end_date.isoformat()

            response = self.session.get(f"{self.BASE_URL}/tasks", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"获取任务列表失败: {str(e)}")
            raise ServiceError(f"获取任务列表失败: {str(e)}")

    async def create_task(self, task_data: Dict) -> Dict:
        """创建新任务

        Args:
            task_data: 任务数据字典，包含以下字段：
                - title: 任务标题 (必需)
                - content: 任务内容 (可选)
                - desc: 任务描述 (可选)
                - isAllDay: 是否全天任务 (可选)
                - startDate: 开始时间 (可选，格式："2024-03-21T03:00:00+0000")
                - dueDate: 截止时间 (可选，格式同上)
                - timeZone: 时区 (可选)
                - reminders: 提醒规则列表 (可选)
                - repeatFlag: 重复规则 (可选)
                - priority: 优先级，默认0 (可选)
                - projectId: 项目ID (可选)

        Returns:
            Dict: 创建的任务信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            self.logger.info(f"开始创建任务: {task_data.get('title', '')}")
            self.logger.debug(f"任务数据: {task_data}")

            # 修正API路径，直接使用/task
            response = self.session.post(f"{self.BASE_URL}/task", json=task_data)

            self.logger.debug(f"请求URL: {self.BASE_URL}/task")
            self.logger.debug(f"响应状态码: {response.status_code}")
            self.logger.debug(f"响应内容: {response.text[:1000]}")  # 只记录前1000个字符

            response.raise_for_status()
            result = response.json()

            self.logger.info(f"任务创建成功: {result.get('id', '')}")
            return result

        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ServiceError(error_msg)
        except ValueError as e:
            error_msg = f"解析响应失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ServiceError(error_msg)
        except Exception as e:
            error_msg = f"创建任务失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ServiceError(error_msg)

    async def update_task(self, task: Task) -> Task:
        """更新任务

        Args:
            task: 要更新的任务对象

        Returns:
            Task: 更新后的任务信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            response = self.session.post(
                f"{self.BASE_URL}/open/v1/task/{task.id}", json=task.to_dict()
            )
            response.raise_for_status()
            return Task.from_dict(response.json())
        except Exception as e:
            self.logger.error(f"更新任务失败: {str(e)}")
            raise ServiceError(f"更新任务失败: {str(e)}")

    async def complete_task(self, task_id: str) -> Dict:
        """完成任务

        Args:
            task_id: 任务ID

        Returns:
            Dict: 更新后的任务信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            response = self.session.post(f"{self.BASE_URL}/tasks/{task_id}/complete")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"完成任务失败: {str(e)}")
            raise ServiceError(f"完成任务失败: {str(e)}")

    async def get_tags(self) -> List[Dict]:
        """获取标签列表

        Returns:
            List[Dict]: 标签列表

        Raises:
            ServiceError: API调用失败
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/tags")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"获取标签列表失败: {str(e)}")
            raise ServiceError(f"获取标签列表失败: {str(e)}")

    async def get_task(self, project_id: str, task_id: str) -> Task:
        """获取单个任务详情

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            Task: 任务详情对象

        Raises:
            ServiceError: API调用失败
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/open/v1/project/{project_id}/task/{task_id}"
            )
            response.raise_for_status()
            return Task.from_dict(response.json())
        except Exception as e:
            self.logger.error(f"获取任务详情失败: {str(e)}")
            raise ServiceError(f"获取任务详情失败: {str(e)}")
