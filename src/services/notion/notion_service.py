from typing import Dict, List, Optional, Any
from datetime import datetime
from .notion_api import NotionAPI
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager
from ...utils.exceptions import ServiceError


class NotionService:
    """Notion 服务

    负责:
    1. 业务逻辑处理
    2. 数据转换和验证
    3. 配置管理
    4. 错误处理
    """

    def __init__(self):
        """初始化 Notion 服务"""
        self.logger = Logger("notion.service")
        self.config_manager = ConfigManager()
        self._apis: Dict[str, NotionAPI] = {}  # 用户ID -> API实例的映射

    def _get_api(self, user_id: str) -> NotionAPI:
        """获取用户的 API 实例

        Args:
            user_id: 用户ID

        Returns:
            NotionAPI: API实例

        Raises:
            ServiceError: 配置无效
        """
        if user_id not in self._apis:
            api_key = self.config_manager.get_user_value(user_id, "notion.api_key")
            if not api_key:
                raise ServiceError("未配置 Notion API Key")
            self._apis[user_id] = NotionAPI(api_key)
        return self._apis[user_id]

    async def initialize_database(self, user_id: str) -> None:
        """初始化数据库

        Args:
            user_id: 用户ID

        Raises:
            ServiceError: 初始化失败
        """
        try:
            database_id = self.config_manager.get_user_value(
                user_id, "notion.database_id"
            )
            if not database_id:
                raise ServiceError("未配置数据库ID")

            api = self._get_api(user_id)

            # 获取当前数据库属性
            database = await api.get_database(database_id)
            current_properties = database.get("properties", {})

            # 定义需要的属性
            required_properties = {
                "Title": {"title": {}},  # 标题
                "Content": {"rich_text": {}},  # 内容
                "Type": {  # 内容类型
                    "select": {
                        "options": [
                            {"name": "Diary", "color": "green"},  # 日记
                            {"name": "Thought", "color": "purple"},  # 闪念
                            {"name": "Note", "color": "yellow"},  # 笔记
                            {"name": "Favorite", "color": "pink"},  # 收藏
                        ]
                    }
                },
                "Tags": {  # 标签
                    "multi_select": {
                        "options": [
                            {"name": "Work", "color": "blue"},
                            {"name": "Study", "color": "green"},
                            {"name": "Idea", "color": "purple"},
                            {"name": "Life", "color": "yellow"},
                            {"name": "Reading", "color": "orange"},
                            {"name": "Learning", "color": "pink"},
                        ]
                    }
                },
                "Summary": {"rich_text": {}},  # 摘要
                "Source": {  # 来源
                    "select": {
                        "options": [
                            {"name": "Telegram", "color": "blue"},
                            {"name": "Manual", "color": "gray"},
                        ]
                    }
                },
            }

            # 合并属性
            merged_properties = await self._merge_properties(
                current_properties, required_properties
            )

            # 更新数据库
            await api.update_database(database_id, merged_properties)
            self.logger.info(f"数据库初始化成功: {database_id}")

        except Exception as e:
            self.logger.error(f"初始化数据库失败: {str(e)}")
            raise ServiceError(f"初始化数据库失败: {str(e)}")

    async def add_entry(
        self,
        user_id: str,
        title: str,
        content: str,
        content_type: str,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: str = "Telegram",
        files: Optional[List[Dict]] = None,
    ) -> Dict:
        """添加条目

        Args:
            user_id: 用户ID
            title: 标题
            content: 内容
            content_type: 内容类型
            summary: 摘要
            tags: 标签列表
            source: 来源
            files: 文件列表

        Returns:
            Dict: 创建的页面信息

        Raises:
            ServiceError: 添加失败
        """
        try:
            api = self._get_api(user_id)
            database_id = self.config_manager.get_user_value(
                user_id, "notion.database_id"
            )
            if not database_id:
                raise ServiceError("未配置数据库ID")

            # 构建页面属性
            properties = {
                "Title": {"title": [{"type": "text", "text": {"content": title}}]},
                "Content": {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                },
                "Type": {"select": {"name": content_type}},
                "Source": {"select": {"name": source}},
            }

            if summary:
                properties["Summary"] = {
                    "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]
                }

            if tags:
                properties["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}

            # 创建页面
            page = await api.create_page(database_id, properties)

            # 添加内容块
            await api.append_blocks(
                page["id"],
                [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": content}}
                            ]
                        },
                    }
                ],
            )

            # 处理文件
            if files:
                for file_info in files:
                    await api.upload_file(page["id"], file_info)

            self.logger.info(f"添加条目成功: {title}")
            return page

        except Exception as e:
            self.logger.error(f"添加条目失败: {str(e)}")
            raise ServiceError(f"添加条目失败: {str(e)}")

    async def _merge_properties(self, current: Dict, required: Dict) -> Dict:
        """合并属性配置

        Args:
            current: 当前属性
            required: 需要的属性

        Returns:
            Dict: 合并后的属性
        """
        merged = current.copy()
        for name, config in required.items():
            if name not in merged:
                merged[name] = config
            elif name in ["Tags", "Type", "Source"]:
                # 合并选项
                if "options" in config.get("select", {}) or "options" in config.get(
                    "multi_select", {}
                ):
                    current_options = set()
                    if "select" in merged[name]:
                        current_options = {
                            opt["name"]
                            for opt in merged[name]["select"].get("options", [])
                        }
                    elif "multi_select" in merged[name]:
                        current_options = {
                            opt["name"]
                            for opt in merged[name]["multi_select"].get("options", [])
                        }

                    new_options = []
                    if "select" in config:
                        new_options = config["select"]["options"]
                    elif "multi_select" in config:
                        new_options = config["multi_select"]["options"]

                    # 添加新选项
                    for option in new_options:
                        if option["name"] not in current_options:
                            if "select" in merged[name]:
                                merged[name]["select"]["options"].append(option)
                            elif "multi_select" in merged[name]:
                                merged[name]["multi_select"]["options"].append(option)
        return merged
