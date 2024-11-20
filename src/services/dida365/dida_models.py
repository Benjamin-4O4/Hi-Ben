from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import IntEnum


class TaskPriority(IntEnum):
    """任务优先级枚举"""

    NONE = 0
    LOW = 1
    MEDIUM = 3
    HIGH = 5


class TaskStatus(IntEnum):
    """任务状态枚举"""

    NORMAL = 0
    COMPLETED = 2


@dataclass
class ChecklistItem:
    """子任务数据模型"""

    id: str
    title: str
    status: TaskStatus
    sort_order: Optional[int] = None
    start_date: Optional[datetime] = None
    is_all_day: bool = False
    time_zone: Optional[str] = None
    completed_time: Optional[datetime] = None


@dataclass
class Task:
    """任务数据模型"""

    id: str
    project_id: str
    title: str
    status: TaskStatus
    is_all_day: bool = False
    content: Optional[str] = None
    desc: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    time_zone: Optional[str] = None
    priority: TaskPriority = TaskPriority.NONE
    sort_order: Optional[int] = None
    repeat_flag: Optional[str] = None
    reminders: List[str] = None
    items: List[ChecklistItem] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """从字典创建任务对象"""
        items = None
        if data.get('items'):
            items = [
                ChecklistItem(
                    id=item['id'],
                    title=item['title'],
                    status=TaskStatus(item['status']),
                    sort_order=item.get('sortOrder'),
                    start_date=(
                        datetime.fromisoformat(item['startDate'].replace('Z', '+00:00'))
                        if item.get('startDate')
                        else None
                    ),
                    is_all_day=item.get('isAllDay', False),
                    time_zone=item.get('timeZone'),
                    completed_time=(
                        datetime.fromisoformat(
                            item['completedTime'].replace('Z', '+00:00')
                        )
                        if item.get('completedTime')
                        else None
                    ),
                )
                for item in data['items']
            ]

        return cls(
            id=data['id'],
            project_id=data['projectId'],
            title=data['title'],
            status=TaskStatus(data['status']),
            is_all_day=data.get('isAllDay', False),
            content=data.get('content'),
            desc=data.get('desc'),
            start_date=(
                datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
                if data.get('startDate')
                else None
            ),
            due_date=(
                datetime.fromisoformat(data['dueDate'].replace('Z', '+00:00'))
                if data.get('dueDate')
                else None
            ),
            completed_time=(
                datetime.fromisoformat(data['completedTime'].replace('Z', '+00:00'))
                if data.get('completedTime')
                else None
            ),
            time_zone=data.get('timeZone'),
            priority=TaskPriority(data.get('priority', 0)),
            sort_order=data.get('sortOrder'),
            repeat_flag=data.get('repeatFlag'),
            reminders=data.get('reminders', []),
            items=items,
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        data = {
            'id': self.id,
            'projectId': self.project_id,
            'title': self.title,
            'status': self.status.value,
            'isAllDay': self.is_all_day,
        }

        if self.content:
            data['content'] = self.content
        if self.desc:
            data['desc'] = self.desc
        if self.start_date:
            data['startDate'] = self.start_date.strftime("%Y-%m-%dT%H:%M:%S%z")
        if self.due_date:
            data['dueDate'] = self.due_date.strftime("%Y-%m-%dT%H:%M:%S%z")
        if self.completed_time:
            data['completedTime'] = self.completed_time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if self.time_zone:
            data['timeZone'] = self.time_zone
        if self.priority != TaskPriority.NONE:
            data['priority'] = self.priority.value
        if self.sort_order is not None:
            data['sortOrder'] = self.sort_order
        if self.repeat_flag:
            data['repeatFlag'] = self.repeat_flag
        if self.reminders:
            data['reminders'] = self.reminders
        if self.items:
            data['items'] = [
                {
                    'id': item.id,
                    'title': item.title,
                    'status': item.status.value,
                    'sortOrder': item.sort_order,
                    'startDate': (
                        item.start_date.strftime("%Y-%m-%dT%H:%M:%S%z")
                        if item.start_date
                        else None
                    ),
                    'isAllDay': item.is_all_day,
                    'timeZone': item.time_zone,
                    'completedTime': (
                        item.completed_time.strftime("%Y-%m-%dT%H:%M:%S%z")
                        if item.completed_time
                        else None
                    ),
                }
                for item in self.items
            ]

        return data
