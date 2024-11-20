import json
from typing import Any, Dict, List, Optional, Sequence, TypedDict
from enum import Enum, auto
from typing_extensions import Annotated
import operator

from langgraph.graph import StateGraph, END, START

from .base_agent import BaseAgent
from ..core.models.message import Message
from datetime import datetime
import logging
from langgraph.checkpoint.memory import MemorySaver

from ..utils.logger import Logger
from ..utils.config_manager import ConfigManager
from ..services.notion.daily_notes import DailyNotes
from ..services.llm.llm_service import LLMService
from ..core.status import StatusManager, MessageStatus, ProcessStep

from ..platforms.telegram.state_manager import TelegramStateManager


class ProcessStep(Enum):
    INITIALIZED = auto()
    PREPROCESSING = auto()
    CONTENT_ANALYSIS = auto()
    URL_PROCESSING = auto()
    TASK_EXTRACTION = auto()
    SAVING_TO_NOTION = auto()
    CREATING_TASKS = auto()
    COMPLETED = auto()
    ERROR = auto()


class AgentState(TypedDict):
    """智能体状态

    Attributes:
        message: 原始消息
        text_content: 文本内容
        media_files: 媒体文件列表
        background: 用户背景信息
        results: 处理结果
        errors: 错误列表
        status_message_id: 状态消息ID
        format_content_result: 格式化内容结果
        content_type: 内容类型
        precheck_result: 预检结果
        tasks: 提取的任务列表
    """

    message: Message  # 原始消息
    text_content: str  # 文本内容
    media_files: List[Dict]  # 媒体文件列表
    background: str  # 用户背景信息
    results: Dict[str, Any]  # 处理结果
    errors: List[str]  # 错误列表
    status_message_id: Optional[str]  # 状消息ID
    llm_result: Optional[Dict] = None  # LLM分析结果
    format_content_result: Optional[Dict] = None  # 格式化内容结果
    content_type: Optional[str] = None  # 内容类型
    precheck_result: Optional[Dict] = None  # 预检结果
    tasks: Optional[List[Dict]] = None  # 提取的任务列表
    next: str  # 下一步操作
    save_success: bool  # 保存是否成功
    error_message: Optional[str]  # 错误信息
    thread_id: str  # 线程ID


class NoteTakerAgent(BaseAgent):
    """笔记处理智能体

    职责:
    1. 分析和分类文本内容
    2. 将文本内容和媒体文件保存到 Notion
    3. 提取和创建任务
    4. 实时状态反馈
    """

    def __init__(self, status_manager=None, telegram_status_updater=None):
        """初始化智能体

        Args:
            status_manager: 状态管理器
            telegram_status_updater: Telegram状态更新器
        """
        super().__init__(
            name="note_taker",
            status_manager=status_manager,
        )
        self.daily_notes = DailyNotes()
        self.llm_service = LLMService()
        self.user_background = ""
        self.telegram_status_updater = telegram_status_updater

        # 配置日志记录器
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        try:
            # 创建工作流图
            self.workflow = self._create_workflow()

            # 配置 checkpointer
            memory = MemorySaver()

            # 编译工作流 - 修复编译方式
            self.app = self.workflow.compile()  # 移除额外的编译参数

        except Exception as e:
            self.logger.error(f"工作流初始化失败: {e}", exc_info=True)
            raise RuntimeError(f"初始化失败: {str(e)}")

    def _get_user_background(self, user_id: str) -> str:
        """获取用户背景信息并构建成JSON格式

        从配置中获取用户的背景信息，包括:
        - 用户个人资料
        - 滴答清单项目列表
        - 滴答清单标签

        Args:
            user_id: 用户ID

        Returns:
            str: JSON格式的用户背景信息
        """
        try:
            # 获取用户配置
            profile = self.config.get_user_value(user_id, "user.profile", default="")
            dida_projects = self.config.get_user_value(
                user_id, "dida.projects", default=[]
            )
            dida_tags = self.config.get_user_value(user_id, "dida.tags", default=[])

            # 构建JSON结构
            background_json = {
                "profile": profile,
                "dida": {
                    "projects": [
                        {"name": p.get("name")} for p in dida_projects if p.get("name")
                    ],
                    "tags": dida_tags,
                },
            }

            # 转换为JSON字符串
            full_background = json.dumps(background_json, ensure_ascii=False)

            self.logger.info(f"获取到用户背景信息: {full_background[:100]}...")
            return full_background

        except Exception as e:
            self.logger.error(f"获取用户背景信息失败: {e}", exc_info=True)
            return ""

    def _format_tasks(self, state: AgentState) -> Dict:
        """处理任务并生成结构化内容"""
        pass

    def _route_after_extract(self, state: AgentState) -> str:
        """任务提取后的路由决策

        Args:
            state: 当前状态对象

        Returns:
            str: 下一个节点名称
        """
        # 移除任务检查，始终进入 create_tasks
        return "create_tasks"

    def _create_workflow(self) -> StateGraph:
        """创建工作流程图"""
        workflow = StateGraph(AgentState)

        # 1. 定义处理节点
        workflow.add_node("precheck", self._content_precheck)  # 内容预检
        workflow.add_node("url_summary", self._url_summary)  # URL处理
        workflow.add_node("format_content", self._format_content)  # 内容格式化
        workflow.add_node("save_notion", self._save_to_notion)  # 保存到Notion
        workflow.add_node("extract_tasks", self._extract_tasks)  # 提取任务
        workflow.add_node("create_tasks", self._create_tasks)  # 创建任务

        # 2. 设置工作流路径
        # 从开始到预检
        workflow.add_edge(START, "precheck")

        # 预检后的URL处理路由
        workflow.add_conditional_edges(
            "precheck",
            lambda x: self._route_after_url_check(x),
            {
                "url_summary": "url_summary",  # 有URL，进行处理
                "format_content": "format_content",  # 无URL，直接格式化
            },
        )

        # URL处理到内容格式化
        workflow.add_edge("url_summary", "format_content")

        # 内容格式化到保存Notion
        workflow.add_edge("format_content", "save_notion")

        # 保存后的任务处理路由
        workflow.add_conditional_edges(
            "save_notion",
            lambda x: self._route_after_save(x),
            {
                "extract_tasks": "extract_tasks",  # 有文本内容，提取任务
                "create_tasks": "create_tasks",  # 无文本内容，直接到创建任务生成报告
            },
        )

        # 任务提取到创建任务（无条件）
        workflow.add_edge("extract_tasks", "create_tasks")

        # 创建任务到结束
        workflow.add_edge("create_tasks", END)

        return workflow

    def _route_after_url_check(self, state: AgentState) -> str:
        """URL检查后的路由决策

        Args:
            state: 当前状态对象

        Returns:
            str: 下一个节点名称
        """
        precheck_result = state.get("precheck_result", {})
        has_url = precheck_result.get("contains_url", False)

        if has_url:
            return "url_summary"
        return "format_content"

    def _route_after_save(self, state: AgentState) -> str:
        """保存后的路由决策

        Args:
            state: 当前状态对象

        Returns:
            str: 下一个节点名称
        """
        precheck_result = state.get("precheck_result", {})
        has_text = precheck_result.get("contains_text", False)
        save_success = state.get("save_success", False)

        if has_text and save_success:
            return "extract_tasks"
        return END

    async def _parallel_process(self, state: AgentState) -> Dict:
        """并行处理节点

        同时触发URL处理和内容处理流程

        Args:
            state: 当前状态对象

        Returns:
            Dict: 更新后的状态对象
        """
        # 这里可以添加并行处理的逻辑
        return state

    def _get_precheck_status_text(self, precheck_result: Dict) -> str:
        """根据预检结果生成状态文本

        Args:
            precheck_result: 预检分析结果

        Returns:
            str: 状态文本
        """
        has_url = precheck_result.get("contains_url", False)
        has_content = precheck_result.get("contains_text", False)

        if has_url and has_content:
            return "检测到URL和文本内容"
        elif has_url:
            return "检测到URL链接"
        elif has_content:
            return "检测到文本内容"
        else:
            return "未检测到有效内容"

    async def _content_precheck(self, state: AgentState) -> Dict:
        """内容预检"""
        try:
            self.logger.info("开始内容预检...")
            message = state["message"]
            status_message_id = state.get("status_message_id")
            text_content = state["text_content"]

            self.logger.debug(f"预检输入: text_content={text_content[:100]}...")

            # 更新状态：开始预检
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.PREPROCESSING,
                    progress=0.2,
                    description="正在预检内容...",
                    status_message_id=status_message_id,
                    emoji="🔍",
                )

            # 分析内容
            precheck_result = await self.llm_service.url_text_analyzer(text_content)
            self.logger.debug(f"预检结: {precheck_result}")

            # 更新状态：预检完成
            status_text = self._get_precheck_status_text(precheck_result)
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.PREPROCESSING,
                    progress=0.3,
                    description=status_text,
                    status_message_id=status_message_id,
                    emoji="✨",
                )

            self.logger.info("内容预检完成")
            return {**state, "precheck_result": precheck_result}

        except Exception as e:
            self.logger.error(f"内容预检失败: {e}", exc_info=True)
            raise

    def _url_summary(self, state: AgentState) -> Dict:
        """处理URL容并生成摘要"""
        pass

    async def _format_content(self, state: AgentState) -> Dict:
        """格式化内容节点

        Args:
            state: 当前状对象

        Returns:
            Dict: 更新后的状态对象
        """
        try:
            text_content = state["text_content"]

            result = await self.llm_service.format_content(
                content=text_content,
                background=self.user_background,
            )

            return {**state, "format_content_result": result, "next": "save_notion"}

        except Exception as e:
            self.logger.error(f"格式化内容失败: {e}", exc_info=True)
            return {**state, "error_message": str(e), "next": END}

    async def _save_to_notion(self, state: AgentState) -> Dict:
        """保存到 Notion

        Args:
            state: 当前状态对象

        Returns:
            Dict: 更新后的状态对象
        """
        try:
            message = state["message"]
            status_message_id = state.get("status_message_id")
            text_content = state["text_content"]
            format_content_result = state.get("format_content_result")

            # 更新状态：开始保存
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.SAVING_TO_NOTION,
                    progress=0.7,
                    description="💾 正在保存到 Notion...",
                    status_message_id=status_message_id,
                )

            if not format_content_result:
                raise ValueError("格式化结果为空")

            # 格式化内容文本
            full_content = self._format_content_text(
                text_content=text_content, llm_result=format_content_result
            )

            # 保存到 Notion
            entry = await self.daily_notes.add_note(
                user_id=message.metadata.user_id,
                raw_content=text_content,
                content=full_content,
                content_type=format_content_result.get("content_type", "未分类"),
                files=state.get("media_files", []),
                source=message.metadata.platform,
                tags=format_content_result.get("tags", []),
                title=format_content_result.get("title"),
                summary=format_content_result.get("summary"),
            )

            if not entry:
                raise ValueError("保存到 Notion 失败")

            # 更新状态：保存完成
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.SAVING_TO_NOTION,
                    progress=0.8,
                    description="已保存到 Notion",
                    status_message_id=status_message_id,
                    emoji="✅",
                )

            # 返回更新后的状态
            return {
                **state,
                "save_success": True,
                "notion_page": entry,
                "next": "extract_tasks",  # 继续执行任务提取
            }

        except Exception as e:
            error_msg = str(e)
            if ": " in error_msg:
                error_msg = error_msg.split(": ")[-1]  # 简化错误消息

            self.logger.error(f"保存到 Notion 失败: {error_msg}", exc_info=True)

            # 更新错误态
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.FAILED,
                    step=ProcessStep.SAVING_TO_NOTION,
                    progress=0.0,
                    description=f"❌ {error_msg}",
                    status_message_id=status_message_id,
                    show_progress=False,  # 错误时不显示进度条
                )

            # 返回错误状态
            return {
                **state,
                "error_message": error_msg,
                "save_success": False,
                "next": END,
            }

    async def _extract_tasks(self, state: AgentState) -> Dict:
        """提取任务"""
        try:
            message = state["message"]
            status_message_id = state.get("status_message_id")

            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.TASK_EXTRACTION,
                    progress=0.95,
                    description="正在提取任务...",
                    status_message_id=status_message_id,
                    emoji="📌",
                )

            self.logger.debug(f"提取任务背景: {self.user_background}")
            content = state["text_content"]

            # 解析背景信息JSON
            try:
                background_data = json.loads(self.user_background)
                profile = background_data.get("profile", "")
                projects_data = background_data.get("dida", {}).get("projects", [])
                project_names = str([p["name"] for p in projects_data if "name" in p])
            except json.JSONDecodeError:
                self.logger.warning("背景信息JSON解析失败，使用空值")
                profile = ""
                project_names = []

            tasks = await self.llm_service.extract_tasks(
                content=content,
                profile=profile,
                projects=project_names,
            )

            # 修改这里：无论是否有任务，都进入 create_tasks
            # 让 create_tasks 负责生成最终报告
            return {**state, "tasks": tasks, "next": "create_tasks"}

        except Exception as e:
            self.logger.error(f"提取任务: {e}", exc_info=True)
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.FAILED,
                    step=ProcessStep.ERROR,
                    progress=0.0,
                    description=f"❌ 提取任务失败: {str(e)}",
                    status_message_id=status_message_id,
                    show_progress=False,
                )
            return {**state, "error_message": f"提取任务失败: {str(e)}", "next": END}

    async def _create_tasks(self, state: AgentState) -> Dict:
        """创建任务"""
        try:
            message = state["message"]
            status_message_id = state.get("status_message_id")
            tasks = state.get("tasks", [])
            user_id = message.metadata.user_id
            format_content_result = state.get("format_content_result", {})

            # 如果有任务，才进行任务创建
            if tasks:
                # 更新状态：开始创建任务
                if self.telegram_status_updater and status_message_id:
                    await self._update_status(
                        message=message,
                        status=MessageStatus.PROCESSING,
                        step=ProcessStep.CREATING_TASKS,
                        progress=0.98,
                        description="正在创建任务...",
                        status_message_id=status_message_id,
                    )

                # 获取滴答清单服务
                self.logger.info(f"正在获取滴答清单服务: user_id={user_id}")

                # 检查用户配置
                token_info = self.config.get_user_value(user_id, "dida.token")
                self.logger.debug(f"用户token配置: {token_info}")

                projects_config = self.config.get_user_value(user_id, "dida.projects")
                self.logger.debug(f"用户项目配置: {projects_config}")

                dida_service = self.config.get_service("dida365", user_id)
                if not dida_service:
                    self.logger.error(f"获取滴答清单服务失败: user_id={user_id}")
                    return {
                        **state,
                        "error_message": "请先配置滴答清单服务",
                        "next": END,
                    }

                # 获取用户的项目列表配置
                projects_config = self.config.get_user_value(
                    user_id, "dida.projects", default=[]
                )
                self.logger.debug(f"项目配置: {projects_config}")

                # 创建项目名称到ID的映射
                project_map = {p["name"]: p["id"] for p in projects_config}
                self.logger.debug(f"项目映射: {project_map}")

                results = []
                for task in tasks:
                    try:
                        # 从task中提取所需字段
                        project_name = task.get('projectId')
                        # 根据项目名称获取项目ID
                        project_id = project_map.get(project_name)
                        if not project_id and project_name:
                            self.logger.warning(f"找不到项目ID: {project_name}")
                            results.append(f"⚠️ 找不到项目: {project_name}")
                            continue

                        title = task.get('title')
                        content = task.get('content')
                        due_date = (
                            datetime.fromisoformat(
                                task['dueDate'].replace('Z', '+00:00')
                            )
                            if task.get('dueDate')
                            else None
                        )
                        priority = task.get('priority', 0)
                        is_all_day = task.get('isAllDay', False)
                        reminders = task.get('reminders', [])
                        desc = task.get('desc', '')

                        # 创建任务
                        created_task = await dida_service.add_task(
                            user_id=user_id,
                            title=title,
                            content=content,
                            project_id=project_id,  # 使用项目ID而不是名称
                            desc=desc,
                            due_date=due_date,
                            priority=priority,
                            is_all_day=is_all_day,
                            reminders=reminders,
                        )

                        if created_task:
                            # 构建任务描述
                            task_desc = f"✅ 已创建任务: {title}"
                            if project_name:
                                task_desc += f"\n📁 项目: {project_name}"
                            if due_date:
                                formatted_date = due_date.strftime("%Y-%m-%d %H:%M")
                                task_desc += f"\n⏰ 截止时间: {formatted_date}"
                            if priority > 0:
                                priority_map = {1: "低", 3: "中", 5: "高"}
                                task_desc += (
                                    f"\n🔥 优先级: {priority_map.get(priority, '普通')}"
                                )

                            results.append(task_desc)
                            self.logger.info(f"成功创建任务: {title}")

                    except Exception as e:
                        error_msg = f"❌ 创建任务 '{title}' 失败: {str(e)}"
                        results.append(error_msg)
                        self.logger.error(f"创建任务失败: {str(e)}")

            # 无论是否有任务，都生成完成报告
            if self.telegram_status_updater and status_message_id:
                # 构建完成报告
                report_lines = []

                # 添加顶部标题
                report_lines.append("✨ 处理完成")
                report_lines.append("")  # 空行分隔

                # Notion保存信息
                if state.get("save_success"):
                    content_type = format_content_result.get("content_type", "未分类")
                    tags = format_content_result.get("tags", [])
                    title = format_content_result.get("title", "")

                    report_lines.append("├─ 📝 笔记信息")
                    report_lines.append("│  ├─ ✅ 已保存到 Notion")
                    if title:
                        report_lines.append(f"│  ├─ 📌 {title}")
                    report_lines.append(f"│  ├─ 📑 分类: #{content_type}")
                    if tags:
                        formatted_tags = " ".join([f"#{tag}" for tag in tags])
                        # 如果标签太长，进行换行处理
                        max_length = 30
                        if len(formatted_tags) > max_length:
                            tags_lines = []
                            current_line = "│  ├─ 🏷️ 标签: "
                            for i, tag in enumerate([f"#{tag}" for tag in tags]):
                                if len(current_line + tag) > max_length:
                                    if i == len(tags) - 1:
                                        tags_lines.append(
                                            current_line.replace("├─", "└─")
                                        )
                                    else:
                                        tags_lines.append(current_line)
                                    current_line = "│  │  " + tag
                                else:
                                    current_line += f" {tag}"
                            tags_lines.append(current_line.replace("├─", "└─"))
                            report_lines.extend(tags_lines)
                        else:
                            report_lines.append(f"│  └─ 🏷️ 标签: {formatted_tags}")
                    else:
                        report_lines.append("│  └─ 🏷️ 无标签")

                # 任务信息（即使没有任务也显示）
                if tasks:
                    report_lines.append("")  # 空行分隔
                    report_lines.append(f"├─ 📋 任务信息 ({len(tasks)})")
                    # 添加每个任务的详细信息
                    for i, task in enumerate(tasks, 1):
                        title = task.get('title', '')
                        project = task.get('projectId', '')
                        due_date = task.get('dueDate')
                        priority = task.get('priority', 0)
                        content = task.get('content', '')

                        is_last_task = i == len(tasks)
                        prefix = "└─" if is_last_task else "├─"
                        detail_prefix = "   " if is_last_task else "│  "

                        # 任务标题
                        report_lines.append(f"│  {prefix} {i}. {title}")

                        # 任务详细信息
                        details = []
                        if project:
                            details.append(f"│  {detail_prefix}├─  {project}")
                        if due_date:
                            date = datetime.fromisoformat(
                                due_date.replace('Z', '+00:00')
                            )
                            formatted_date = date.strftime("%Y-%m-%d %H:%M")
                            details.append(f"│  {detail_prefix}├─ ⏰ {formatted_date}")
                        if priority > 0:
                            priority_map = {1: "低", 3: "中", 5: "高"}
                            priority_text = priority_map.get(priority, '普通')
                            details.append(
                                f"│  {detail_prefix}├─ 🔥 {priority_text}优先级"
                            )
                        if content:
                            max_content_length = 40
                            displayed_content = (
                                f"{content[:max_content_length]}..."
                                if len(content) > max_content_length
                                else content
                            )
                            details.append(
                                f"│  {detail_prefix}└─ 📝 {displayed_content}"
                            )
                        elif details:  # 如果有其他详情，将最后一项改为 └─
                            details[-1] = details[-1].replace("├─", "└─")

                        report_lines.extend(details)

                        if not is_last_task:
                            report_lines.append("│")
                else:
                    # 如果没有任务，也添加任务信息部分
                    report_lines.append("")  # 空行分隔
                    report_lines.append("└─ 📋 未检测到任务")

                # 添加结尾分隔符
                report_lines.append("")  # 空行
                report_lines.append("· · · · · ·")  # 优雅的点状分隔符

                # 更新状态消息为完成报告
                await self._update_status(
                    message=message,
                    status=MessageStatus.COMPLETED,
                    step=ProcessStep.COMPLETED,
                    progress=None,
                    description="\n".join(report_lines).strip(),
                    status_message_id=status_message_id,
                    show_progress=False,
                )

            return {
                **state,
                "next": END,
            }

        except Exception as e:
            self.logger.error(f"创建任务失败: {str(e)}", exc_info=True)
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.FAILED,
                    step=ProcessStep.ERROR,
                    progress=0.0,
                    description=f"❌ 创建任务失败: {str(e)}",
                    status_message_id=status_message_id,
                    show_progress=False,
                )
            return {**state, "error_message": str(e), "next": END}

    async def _update_status(
        self,
        message: Message,
        status: MessageStatus,
        step: ProcessStep,
        progress: float,
        description: str,
        status_message_id: Optional[str] = None,
        emoji: str = "",
        show_progress: bool = True,
    ) -> Optional[Message]:
        """更新处理状态

        Args:
            message: 消息对象
            status: 消息状态
            step: 处理步骤
            progress: 进度值(0-1)
            description: 状态描述
            status_message_id: 状态消息ID
            emoji: 状态emoji
            show_progress: 是否显示进度条
        """
        try:
            if not self.telegram_status_updater:
                return None

            # 构建状态文本
            status_text = self.telegram_status_updater.format_status_text(
                progress=progress if show_progress else None,
                step=step.value,
                description=description,
                emoji=emoji,
            )

            if status_message_id:
                success = await self.telegram_status_updater.update_status_message(
                    message_id=status_message_id, text=status_text
                )
                if not success:
                    self.logger.warning(f"更新状态消息失败: {status_message_id}")
                return None
            else:
                return await self.telegram_status_updater.create_status_message(
                    chat_id=str(message.metadata.chat_id),
                    text=status_text,
                    reply_to_message_id=message.metadata.message_id,
                )

        except Exception as e:
            self.logger.error(f"更新状态失败: {e}", exc_info=True)
            return None

    async def process(
        self,
        message: Message,
        background: Optional[str] = None,
        telegram_status_updater: Optional['TelegramStateManager'] = None,
    ) -> Dict[str, Any]:
        """处理消息的主要方法"""
        status_message = None
        status_message_id = None
        try:
            self.logger.info("开始处理新消息...")

            # 获取用户背景信息
            user_id = str(message.metadata.user_id)  # 确保 user_id 是字符串
            self.user_background = self._get_user_background(user_id)
            if background:  # 如果提供了额外的背景信息，添加到现有背景中
                self.user_background = (
                    f"{self.user_background}\n{background}"
                    if self.user_background
                    else background
                )

            self.logger.info(f"用户背景: {self.user_background}")

            # 设置或更新状态管理器
            if telegram_status_updater:
                self.telegram_status_updater = telegram_status_updater

                # 创建始状态消息
                status_message = await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.INITIALIZED,
                    progress=0.1,
                    description="🚀 开始处理...",
                )
                if status_message:
                    status_message_id = str(status_message.message_id)
                    self.logger.info(f"创建状态消息: {status_message_id}")

            # 设置初始状态
            state = AgentState(
                message=message,
                text_content=message.content.data.get("text", ""),
                media_files=message.files,
                background=background or "",
                results={},
                errors=[],
                status_message_id=status_message_id,
                messages=[],
                next=START,
                thread_id=str(message.metadata.chat_id),
            )

            self.logger.info("开始执行工作流...")

            # 配置运行时参数
            config = {
                "configurable": {
                    "thread_id": str(message.metadata.chat_id),
                    "run_id": str(message.metadata.message_id),
                }
            }

            # 执行工作流
            final_state = await self.app.ainvoke(state, config)

            self.logger.info("工作流执行完成")

            # 移除这里的状态更新，因为已经在 _create_tasks 中处理了
            self.logger.info("消息处理完成")
            return final_state.get("results", {})

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}", exc_info=True)
            if self.telegram_status_updater and status_message_id:
                error_msg = str(e)
                if ": " in error_msg:
                    error_msg = error_msg.split(": ")[-1]
                await self._update_status(
                    message=message,
                    status=MessageStatus.FAILED,
                    step=ProcessStep.ERROR,
                    progress=0.0,
                    description=f"❌ {error_msg}",
                    status_message_id=status_message_id,
                    show_progress=False,
                )
            return {"error": str(e)}

    async def _process_url(self, state: AgentState) -> Dict:
        """处理URL内容

        1. 获取URL内容
        2. 生成摘要
        3. 提取关键信息
        """
        try:
            message = state["message"]
            status_message_id = state.get("status_message_id")
            precheck_result = state.get("precheck_result", {})
            urls = precheck_result.get("urls", [])

            if not urls:
                return {**state, "next": "merge_results"}

            # 更新状态
            if self.telegram_status_updater and status_message_id:
                await self._update_status(
                    message=message,
                    status=MessageStatus.PROCESSING,
                    step=ProcessStep.URL_PROCESSING,
                    progress=0.4,
                    description="🔗 正在处理URL...",
                    status_message_id=status_message_id,
                )

            # 处理每个URL
            url_results = []
            for url in urls:
                # 这里添加实际的URL处理逻辑
                # 例如: 获取内容、生成摘要等
                pass

            return {**state, "url_results": url_results, "next": "merge_results"}

        except Exception as e:
            self.logger.error(f"处理URL失败: {e}", exc_info=True)
            return {**state, "error_message": str(e), "next": END}

    def _format_content_text(self, text_content: str, llm_result: Dict) -> str:
        """格式化内容文本

        Args:
            text_content: 原始文本
            llm_result: LLM分析结果

        Returns:
            str: 格式化后的文本
        """
        # 获取分析结果
        summary = llm_result.get("summary", "")
        formatted_content = llm_result.get("content", text_content)
        tags = llm_result.get("tags", [])

        # 构建完整内容
        sections = [
            "📝 原始内容：",
            text_content,
            "",
            "✨ 格式化内容：",
            formatted_content,
            "",
            "📋 内容总结：",
            summary,
            "",
            "🏷️ 标签：",
            "、".join(tags) if tags else "无标签",
        ]

        return "\n".join(sections)
