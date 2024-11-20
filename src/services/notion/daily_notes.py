from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager
from .notion_api import NotionAPI


class DailyNotes:
    """Notion 日常笔记服务

    职责:
    1. 笔记保存和管理
    2. 文件上传
    3. 标签管理
    4. 内容格式化
    """

    def __init__(self):
        """初始化日常笔记服务"""
        self.logger = Logger("services.notion.daily_notes")
        self.config = ConfigManager()
        self.api = None  # 延迟初始化，只在需要时创建

    async def _ensure_api(self, user_id: str) -> NotionAPI:
        """确保 API 实例可用

        Args:
            user_id: 用户ID

        Returns:
            NotionAPI: API实例

        Raises:
            ValueError: 如果缺少必要配置
        """
        try:
            # 获取配置
            api_key = self.config.get_user_value(user_id, "notion.api_key")
            database_id = self.config.get_user_value(user_id, "notion.database_id")

            if not api_key:
                raise ValueError("请先配置 Notion API Key")
            if not database_id:
                raise ValueError("请先配置 Notion Database ID")

            # 创建API实例
            api = NotionAPI(api_key=api_key)

            # 初始化数据库属性
            await api.init_database(database_id)

            return api

        except Exception as e:
            self.logger.error(f"初始化 Notion API 失败: {e}", exc_info=True)
            raise

    async def add_note(
        self,
        user_id: str,
        content: str,
        raw_content: str,
        content_type: str,
        files: Optional[List[Dict]] = None,
        source: str = "unknown",
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Optional[Dict]:
        """添加笔记"""
        try:
            self.logger.debug(f"开始添加笔记, user_id: {user_id}")
            self.logger.debug(f"标题: {title}")
            self.logger.debug(f"内容类型: {content_type}")
            self.logger.debug(f"来源: {source}")
            self.logger.debug(f"标签: {tags}")
            if files:
                self.logger.debug(f"文件数量: {len(files)}")

            # 获取API实例
            api = await self._ensure_api(user_id)

            # 获取数据库ID
            database_id = self.config.get_user_value(user_id, "notion.database_id")
            if not database_id:
                raise ValueError("请先配置 Notion Database ID")

            # 准备标签
            tags = tags or []

            # 生成标题
            if not title:
                title = (
                    f"{content_type} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

            # 构建页面属性
            properties = {
                "Title": {"title": [{"text": {"content": title}}]},
                "Type": {"select": {"name": content_type}},
                "Source": {"select": {"name": source.title()}},
                "Tags": {"multi_select": [{"name": tag} for tag in tags]},
                "Content": {"rich_text": [{"text": {"content": raw_content}}]},
                "HasAttachment": {"checkbox": bool(files)},
            }

            if summary:
                properties["Summary"] = {
                    "rich_text": [{"text": {"content": summary[:2000]}}]
                }

            self.logger.debug(f"页面属性: {properties}")

            # 构建页面内容块
            page_content = [
                # 如果有摘要，先显示摘要
                {
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": "📋 内容摘要"}}]},
                },
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": summary or "无摘要"}}]
                    },
                },
                {"type": "divider", "divider": {}},
                # 显示主要内容
                {
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": "📝 内容"}}]},
                },
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]},
                },
            ]

            # 如果有文件，添加文件区域
            if files:
                page_content.extend(
                    [
                        {"type": "divider", "divider": {}},
                        {
                            "type": "heading_2",
                            "heading_2": {
                                "rich_text": [{"text": {"content": "📎 附件"}}]
                            },
                        },
                    ]
                )

                # 上传文件
                uploaded_files = []
                for file in files:
                    try:
                        file_block = await self._upload_file(file)
                        if file_block:
                            uploaded_files.append(file_block)
                    except Exception as e:
                        self.logger.error(f"上传文件失败: {str(e)}")

                page_content.extend(uploaded_files)

            self.logger.debug(f"页面内容块数量: {len(page_content)}")

            # 创建页面
            page = await api.create_page(
                database_id=database_id,
                properties=properties,
                children=page_content,
            )

            self.logger.info(f"创建笔记成功: {title}")
            return page

        except Exception as e:
            self.logger.error(f"添加笔记失败: {str(e)}", exc_info=True)
            raise

    async def _upload_file(self, file: Dict) -> Optional[Dict]:
        """上传文件到 Notion

        Args:
            file: 文件信息

        Returns:
            Dict: 文件块配置
            None: 上传失败
        """
        try:
            file_path = file.get("path")
            if not file_path:
                return None

            # 上传文件
            file_url = await self.api.upload_file(file_path)
            if not file_url:
                return None

            # 根据文件类型创建不同的块
            file_type = file.get("type", "file")

            if file_type == "image":
                return {
                    "type": "image",
                    "image": {"type": "external", "external": {"url": file_url}},
                }
            elif file_type in ["audio", "voice"]:
                return {
                    "type": "audio",
                    "audio": {"type": "external", "external": {"url": file_url}},
                }
            elif file_type == "video":
                return {
                    "type": "video",
                    "video": {"type": "external", "external": {"url": file_url}},
                }
            else:
                return {
                    "type": "file",
                    "file": {"type": "external", "external": {"url": file_url}},
                }

        except Exception as e:
            self.logger.error(f"上传文件失败: {str(e)}")
            return None

    async def get_notes(
        self,
        user_id: str,
        content_type: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取笔记列表

        Args:
            user_id: 用户ID
            content_type: 内容类型过滤
            source: 来源过滤
            tags: 标签过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            List[Dict]: 笔记列表
        """
        try:
            # 获取API实例
            api = await self._ensure_api(user_id)

            # 获取数据库ID
            database_id = self.config.get_user_value(user_id, "notion.database_id")
            if not database_id:
                raise ValueError("请先配置 Notion Database ID")

            # 构建过滤条件
            filter_conditions = []

            if content_type:
                filter_conditions.append(
                    {"property": "Type", "select": {"equals": content_type}}
                )

            if source:
                filter_conditions.append(
                    {"property": "Source", "select": {"equals": source}}
                )

            if tags:
                filter_conditions.append(
                    {
                        "property": "Tags",
                        "multi_select": {"contains": tags[0]},  # Notion API限制
                    }
                )

            if start_date:
                filter_conditions.append(
                    {
                        "property": "Created",
                        "date": {"on_or_after": start_date.isoformat()},
                    }
                )

            if end_date:
                filter_conditions.append(
                    {
                        "property": "Created",
                        "date": {"on_or_before": end_date.isoformat()},
                    }
                )

            # 查询数据库
            results = await api.query_database(
                database_id=database_id,
                filter={"and": filter_conditions} if filter_conditions else None,
                page_size=limit,
            )

            return results

        except Exception as e:
            self.logger.error(f"获取笔记失败: {str(e)}")
            raise

    async def delete_note(self, user_id: str, page_id: str) -> bool:
        """删除笔记

        Args:
            user_id: 用户ID
            page_id: 页面ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取API实例
            api = await self._ensure_api(user_id)

            await api.archive_page(page_id)
            self.logger.info(f"删除笔记成功: {page_id}")
            return True
        except Exception as e:
            self.logger.error(f"删除笔记失败: {str(e)}")
            return False
