from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import requests
from notion_client import Client
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager
from ...utils.exceptions import ServiceError


class NotionAPI:
    """Notion API 接口封装

    负责:
    1. API 调用的基础封装
    2. 错误处理和转换
    3. 数据格式转换
    """

    def __init__(self, api_key: str):
        """初始化 Notion API 客户端

        Args:
            api_key: Notion API Key
        """
        self.logger = Logger("notion.api")
        self.client = Client(auth=api_key)

    def _format_error(self, error: Exception) -> str:
        """格式化错误消息，去除冗余信息"""
        error_str = str(error)
        if "Request to Notion API" in error_str:
            return "Notion API 请求超时"

        # 移除错误消息链中的重复部分
        parts = error_str.split(": ")
        if len(parts) > 2:
            return ": ".join(parts[-2:])  # 只保留最后两部分
        return error_str

    async def get_database(self, database_id: str) -> Dict:
        """获取数据库信息

        Args:
            database_id: 数据库ID

        Returns:
            Dict: 数据库信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            return self.client.databases.retrieve(database_id=database_id)
        except Exception as e:
            error_msg = self._format_error(e)
            self.logger.error(f"获取数据库失败: {error_msg}")
            raise ServiceError(error_msg)

    async def update_database(self, database_id: str, properties: Dict) -> Dict:
        """更新数据库属性

        Args:
            database_id: 数据库ID
            properties: 属性配置

        Returns:
            Dict: 更新后的数据库信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            return self.client.databases.update(
                database_id=database_id, properties=properties
            )
        except Exception as e:
            self.logger.error(f"更新数据库失败: {str(e)}")
            raise ServiceError(f"更新数据库失败: {str(e)}")

    async def query_database(
        self,
        database_id: str,
        filter_conditions: Optional[Dict] = None,
        sorts: Optional[List] = None,
        page_size: int = 100,
    ) -> List[Dict]:
        """查询数据库

        Args:
            database_id: 数据库ID
            filter_conditions: 过滤条件
            sorts: 排序条件
            page_size: 每页数量

        Returns:
            List[Dict]: 查询结果

        Raises:
            ServiceError: API调用失败
        """
        try:
            self.logger.debug(f"开始查询数据库, database_id: {database_id}")
            if filter_conditions:
                self.logger.debug(f"过滤条件: {filter_conditions}")
            if sorts:
                self.logger.debug(f"排序条件: {sorts}")

            query = {"database_id": database_id, "page_size": page_size}
            if filter_conditions:
                query["filter"] = filter_conditions
            if sorts:
                query["sorts"] = sorts

            response = self.client.databases.query(**query)
            self.logger.info(f"查询到 {len(response.get('results', []))} 条记录")
            return response.get("results", [])

        except Exception as e:
            self.logger.error(f"查询数据库失败: {str(e)}", exc_info=True)
            raise ServiceError(f"查询数据库失败: {str(e)}")

    async def create_page(
        self, database_id: str, properties: Dict, children: Optional[List] = None
    ) -> Dict:
        """创建页面"""
        try:
            self.logger.debug(f"开始创建页面, database_id: {database_id}")
            self.logger.debug(f"页面属性: {properties}")
            if children:
                self.logger.debug(f"页面内容块数量: {len(children)}")

            # 获取数据库信息
            database = await self.get_database(database_id)
            database_properties = database.get("properties", {})

            # 确保 Content 字段存在且包含原始内容
            if "content" in properties:
                properties["Content"] = {
                    "rich_text": [{"text": {"content": properties.pop("content")}}]
                }

            # 创建页面
            page = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children if children else [],
            )

            self.logger.info(f"页面创建成功: {page.get('id')}")
            return page

        except Exception as e:
            self.logger.error(f"创建页面失败: {str(e)}", exc_info=True)
            raise ServiceError(f"创建页面失败: {str(e)}")

    async def update_page(self, page_id: str, properties: Dict) -> Dict:
        """更新页面

        Args:
            page_id: 页面ID
            properties: 要更新的属性

        Returns:
            Dict: 更新后的页面信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            return self.client.pages.update(page_id=page_id, properties=properties)
        except Exception as e:
            self.logger.error(f"更新页面失败: {str(e)}")
            raise ServiceError(f"更新页面失败: {str(e)}")

    async def append_blocks(self, page_id: str, blocks: List[Dict]) -> Dict:
        """添加内容块

        Args:
            page_id: 页面ID
            blocks: 内容块列表

        Returns:
            Dict: API响应

        Raises:
            ServiceError: API调用失败
        """
        try:
            return self.client.blocks.children.append(block_id=page_id, children=blocks)
        except Exception as e:
            self.logger.error(f"添加内容块失败: {str(e)}")
            raise ServiceError(f"添加内容块失败: {str(e)}")

    async def upload_file(self, page_id: str, file_info: Dict) -> Dict:
        """上传文件

        Args:
            page_id: 页面ID
            file_info: 文件信息

        Returns:
            Dict: 上传结果

        Raises:
            ServiceError: 上传失败
        """
        try:
            # TODO: 实现文件上传逻辑
            pass
        except Exception as e:
            self.logger.error(f"上传文件失败: {str(e)}")
            raise ServiceError(f"上传文件失败: {str(e)}")

    async def get_users(self) -> Dict:
        """获取用户信息（用于验证 API Key）

        Returns:
            Dict: 用户信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            # 尝试获取当前用户信息
            response = self.client.users.me()

            # 检查响应是否包含必要的字段
            if not response or 'id' not in response or 'type' not in response:
                raise ServiceError("无效的 API Key: 响应格式错误")

            return response

        except Exception as e:
            error_msg = str(e).lower()
            if 'unauthorized' in error_msg or 'invalid' in error_msg:
                raise ServiceError("无效的 API Key")
            self.logger.error(f"获取用户信息失败: {str(e)}")
            raise ServiceError(f"API Key 验证失败: {str(e)}")

    async def get_page(self, page_id: str) -> Dict:
        """获取页面信息

        Args:
            page_id: 页面ID

        Returns:
            Dict: 页面信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            self.logger.debug(f"获取页面信息: {page_id}")
            return self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            self.logger.error(f"获取页面失败: {str(e)}")
            raise ServiceError(f"获取页面失败: {str(e)}")

    async def list_databases(self, page_id: str) -> List[Dict]:
        """获取页面下的数据库列表

        Args:
            page_id: 页面ID

        Returns:
            List[Dict]: 数据库列表

        Raises:
            ServiceError: API调用失败
        """
        try:
            # 获取页面下的所有块
            blocks = self.client.blocks.children.list(block_id=page_id)

            # 过滤出数据库类型的块
            databases = []
            for block in blocks.get("results", []):
                if block["type"] == "child_database":
                    databases.append(
                        {
                            "id": block["id"],
                            "title": block.get("child_database", {}).get(
                                "title", "Untitled"
                            ),
                            "created_time": block.get("created_time"),
                            "last_edited_time": block.get("last_edited_time"),
                        }
                    )

            return databases

        except Exception as e:
            self.logger.error(f"获取数据库列表失败: {str(e)}")
            raise ServiceError(f"获取数据库列表失败: {str(e)}")

    async def create_database(
        self, page_id: str, title: str, description: str = ""
    ) -> Dict:
        """在页面下创建新数据库

        Args:
            page_id: 页面ID
            title: 数据库标题
            description: 数据库描述

        Returns:
            Dict: 创建的数据库信息

        Raises:
            ServiceError: API调用失败
        """
        try:
            # 创建数据库
            database = self.client.databases.create(
                parent={"type": "page_id", "page_id": page_id},
                title=[{"type": "text", "text": {"content": title}}],
                properties={
                    "Title": {"title": {}},  # 标题属性
                    "Description": {"rich_text": {}},  # 描述属性
                },
            )

            return database

        except Exception as e:
            self.logger.error(f"创建数据库失败: {str(e)}")
            raise ServiceError(f"创建数据库失败: {str(e)}")

    async def archive_page(self, page_id: str) -> None:
        """归档页面

        Args:
            page_id: 页面ID
        """
        try:
            self.logger.debug(f"开始归档页面: {page_id}")
            self.client.pages.update(page_id=page_id, archived=True)
            self.logger.info(f"页面归档成功: {page_id}")

        except Exception as e:
            self.logger.error(f"归档页面失败: {str(e)}", exc_info=True)
            raise

    async def upload_file(self, file_path: str) -> Optional[str]:
        """上传文件

        Args:
            file_path: 文件路径

        Returns:
            str: 文件URL
            None: 上传失败
        """
        try:
            self.logger.debug(f"开始上传文件: {file_path}")
            # TODO: 实现文件上传
            return None

        except Exception as e:
            self.logger.error(f"上传文件失败: {str(e)}", exc_info=True)
            return None

    async def init_database(self, database_id: str) -> None:
        """初始化数据库属性

        只在用户首次设置数据库时调用，避免重复初始化导致标签混乱
        """
        try:
            self.logger.info("开始初始化数据库属性")

            # 获取现有数据库属性
            database = await self.get_database(database_id)
            current_properties = database.get("properties", {})

            # 如果已经有基本属性，说明已经初始化过
            if all(
                prop in current_properties
                for prop in ["Title", "Type", "Source", "Tags", "Created", "Content"]
            ):
                self.logger.info("数据库已初始化，跳过")
                return

            # 定义基本属性
            properties = {
                "Title": {"title": {}},  # 标题(必需)
                "Type": {  # 内容类型
                    "select": {
                        "options": [
                            {"name": "Diary", "color": "green"},
                            {"name": "Thought", "color": "purple"},
                            {"name": "Note", "color": "yellow"},
                            {"name": "Favorite", "color": "pink"},
                        ]
                    }
                },
                "Source": {  # 来源（首字母大写）
                    "select": {
                        "options": [
                            {"name": "Telegram", "color": "blue"},
                            {"name": "Manual", "color": "gray"},
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
                            {"name": "Voice", "color": "orange"},
                        ]
                    }
                },
                "Content": {"rich_text": {}},  # 原始内容
                "Summary": {"rich_text": {}},  # 内容摘要
                "HasAttachment": {"checkbox": {}},  # 是否包含附件
            }

            # 更新数据库属性（只添加缺失的属性）
            for name, config in properties.items():
                if name not in current_properties:
                    current_properties[name] = config

            # 更新数据库
            await self.update_database(database_id, current_properties)
            self.logger.info("数据库属性初始化完成")

        except Exception as e:
            self.logger.error(f"初始化数据库属性失败: {e}", exc_info=True)
            raise ServiceError(f"初始化数据库属性失败: {str(e)}")
