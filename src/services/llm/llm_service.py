import re
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers import XMLOutputParser
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager


class LLMService:
    """LLM 服务

    职责:
    1. 内容分析和分类
    2. 文本校对和优化
    3. 任务提取
    4. 多模态内容理解
    """

    def __init__(self):
        """初始化 LLM 服务"""
        self.logger = Logger("services.llm")
        self.config = ConfigManager()

        # 获取配置
        openai_config = {
            'api_key': self.config.get('openai', 'api_key'),
            'base_url': self.config.get('openai', 'base_url'),
            'model': self.config.get('openai', 'model', default='gpt-4o'),
        }

        self.logger.info(f"使用模型: {openai_config['model']}")

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=openai_config['model'],
            api_key=openai_config['api_key'],
            base_url=openai_config['base_url'],
            temperature=0,
        )

        # 初始化 JSON 解析器
        self.json_parser = JsonOutputParser()

    def replace_json_booleans_to_python(func):
        """装饰器: 替换JSON字符串中的布尔值表示

        将JSON字符串中的'true'/'false'替换为Python风格的'True'/'False'

        Args:
            func: 被装饰的函数

        Returns:
            wrapper: 装饰器函数,返回处理后的结果

        Example:
            @replace_json_booleans_to_python
            async def url_text_analyzer(self, text: str) -> str:
                # 返回JSON字符串
                return '{"contains_url": true, "contains_text": false}'

            # 调用后自动将结果转换为:
            # '{"contains_url": True, "contains_text": False}'
        """

        async def wrapper(*args, **kwargs):
            """装饰器内部包装函数"""
            # 调用原始函数获取结果
            result = await func(*args, **kwargs)

            # 如果结果是字符串,替换布尔值表示
            if isinstance(result, str):
                return result.replace("true", "True").replace("false", "False")

            # 非字符串结果直接返回
            return result

        return wrapper

    @replace_json_booleans_to_python
    async def url_text_analyzer(self, user_text: str) -> str:
        """分析是否包含url

        Args:
            user_text (str): 用户输入的文本

        Returns:
            str: 返回JSON格式的分析结果，包含以下字段:
                - contains_url (bool): 是否包含URL链接
                - contains_text (bool): 是否包含可读文本内容
                - urls (List[str]): 文本中包含的所有URL列表，仅当contains_url为true时存在

            示例:
                {
                    "contains_url": true,
                    "contains_text": true,
                    "urls": ["https://www.example.com"]
                }
        """
        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "human",
                        """
                        You are a text analysis AI tasked with examining a given text to determine if it contains URLs and/or readable content. Additionally, you will extract any URLs present in the text. Here's the text you need to analyze:
                        <user_text>
                        {user_text}
                        </user_text>
                        Please follow these steps to analyze the text:
                        1. Examine the text for the presence of URLs and readable content.
                        2. If URLs are present, extract them.
                        3. Determine the boolean values for "contains_url" and "contains_text".
                        4. Format the results as a JSON string.
                        After your examination, provide the final output as a JSON string. The JSON should have the following structure: 
                        {{
                        "contains_url": boolean,
                        "contains_text": boolean,
                        "urls": [array of strings, only present if contains_url is true]
                        }}
                        Where:
                        - "contains_url" is true if the text contains at least one URL, and false otherwise.
                        - "contains_text" is true if the text contains any normal, readable content (excluding URLs), and false otherwise.
                        - "urls" is an array of strings containing all URLs found in the text, only present if contains_url is true.
                        Remember to base your analysis solely on the provided user_text and do not make any assumptions about content that isn't present in the input.
                        """,
                    ),
                ]
            )

            chain = prompt | self.llm | self.json_parser

            result = await chain.ainvoke({"user_text": user_text})
            return result
        except Exception as e:
            self.logger.error(f"文本预检失败: {e}", exc_info=True)
            raise

    async def format_content(self, content: str, background: str = "") -> Dict:
        """格式化内容

        Args:
            content: 要分析的内容
            background: 用户背景信息

        Returns:
            Dict: {
                "content_type": str,  # Diary/Thought/Note/Favorite
                "title": str,  # 标题
                "summary": str,  # 摘要
                "content": str,  # 格式化后的内容
                "tags": List[str],  # 标签
                "has_tasks": bool,  # 是否包含任务
            }
        """
        try:
            current_time = datetime.now()

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "human",
                        """
                    你是一个内容分析助手，专门用于分析用户生成的内容并提供结构化的JSON输出。请仔细阅读以下信息和指令：
                    当前时间：
                    <current_time>
                    {current_time}
                    </current_time>
                    用户背景：
                    <background>
                    {background}
                    </background>

                    需要分析的内容：
                    <user_content>
                    {content}
                    </user_content>

                    你的任务是分析上述内容，并生成一个包含以下字段的JSON输出：

                    1. content_type: 根据以下类别确定内容类型：
                    - "Diary"：记录今天的事件
                    - "Thought"：突发的想法或反思
                    - "Note"：一般性笔记
                    - "Favorite"：需要收藏的内容（通常包含URL）

                    2. title: 生成一个反映内容的简短标题：
                    - 最多20个字符
                    - 突出关键信息
                    - 易于理解和记忆
                    - 保持客观，避免推测

                    3. summary: 提供内容的简明摘要：
                    - 不超过100个字符
                    - 包括主要观点和关键信息
                    - 清晰简洁
                    - 保持客观，避免推测

                    4. format_content: 格式化原始内容：
                    - 保持原意
                    - 优化布局和结构
                    - 添加适当的段落和标点
                    - 修正明显错误

                    5. tags: 创建一个标签数组：
                    - 3-5个关键词标签
                    - 反映内容主题和类型
                    - 便于分类和检索

                    格式要求：
                    - 对所有字符串使用双引号
                    - 对布尔值使用true/false
                    - 确保输出是有效的JSON格式

                    在提供最终JSON输出之前，请在<analysis>标签内进行详细分析。在你的分析中，请按照以下步骤进行：

                    1. 内容类型分析：
                    - 列出支持每种可能内容类型的关键词或特征
                    - 确定最可能的内容类型
                    - 如果可能是"收藏"类型，检查是否包含URL

                    2. 标题创建：
                    - 列出3-5个可能的标题选项
                    - 解释每个选项如何反映内容
                    - 选择最佳标题并说明原因

                    3. 摘要生成：
                    - 列出内容中的主要观点和关键信息
                    - 将这些信息压缩成不超过100个字符的摘要
                    - 确保摘要客观且不包含推测

                    4. 内容格式化：
                    - 指出需要优化的部分
                    - 说明如何改进布局和结构
                    - 列出任何需要修正的明显错误
                    - 按照user_content原语种，保持原意不变

                    5. 标签生成：
                    - 列出6-8个可能的标签
                    - 解释每个标签如何反映内容的主题或类型
                    - 选择最合适的3-5个标签

                    请提供你的分析和最终输出。使用<json>和</json>标签包围最终的JSON输出。

                    以下是预期输出的结构示例（请注意，这只是一个通用的结构示例，你的实际输出应该基于给定的内容）：
                    <result>
                        <analysis>
                        </analysis>
                        <json>
                        {{
                        "content_type": "类型",
                        "title": "标题",
                        "summary": "摘要",
                        "format_content": "格式化后的内容",
                        "tags": ["标签1", "标签2", "标签3"]
                        }}
                        </json>
                    </result>
                    现在，请开始你的分析和输出。
                    """,
                    ),
                ]
            )

            # 创建一个LangChain链,将prompt和llm模型串联起来
            # prompt: 包含系统提示和用户输入的提示模板
            # self.llm: LLM模型实例
            # | 操作符用于将prompt和llm连接成一个处理链
            chain = prompt | self.llm

            # 1. 获取原始结果
            raw_result = await chain.ainvoke(
                {
                    "current_time": current_time,
                    "background": background,
                    "content": content,
                }
            )

            try:
                # 获取原始内容
                xml_content = (
                    raw_result.content
                    if hasattr(raw_result, 'content')
                    else str(raw_result)
                )

                # 使用正则表达式提取 json 标签中的内容
                json_pattern = r'<json>\s*({[\s\S]*?})\s*</json>'
                json_match = re.search(json_pattern, xml_content, re.DOTALL)

                if json_match:
                    json_str = json_match.group(1).strip()
                    # 解析 JSON 字符串
                    result = json.loads(json_str)

                    return result
                else:
                    self.logger.error("无法找到json标签内容")
                    raise ValueError("无法找到json标签内容")

            except Exception as e:
                self.logger.error(f"解析结果失败: {e}", exc_info=True)
                raise

        except Exception as e:
            self.logger.error(f"内容分析失败: {e}", exc_info=True)
            raise

    async def proofread_text(self, text: str) -> str:
        """校对和优化文本

        Args:
            text: 原始文本

        Returns:
            str: 优化后的文本
        """
        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """你是一个文本校对助手。
                        请对输入的文本进行校对和优化:
                        1. 修正错别字和语法错误
                        2. 优化语言表达
                        3. 保持原意不变
                        4. 确保文本通顺易读

                        直接返回优化后的文本，不需要解释修改内容。""",
                    ),
                    ("human", "{text}"),
                ]
            )

            chain = prompt | self.llm

            result = await chain.ainvoke({"text": text})
            return result.content.strip()

        except Exception as e:
            self.logger.error(f"文本校对失败: {e}", exc_info=True)
            raise

    async def extract_tasks(
        self, content: str, profile: str, projects: str
    ) -> List[Dict]:
        """提取任务

        Args:
            content: 文本内容
            profile: 用户介绍，默认为空字符串
            projecs: 项目列表的JSON字符串，默认为空数组字符串

        Returns:
            List[Dict]: 任务列表，每个任务包含:
                - title: 任务标题
                - content: 任务详情
                - due_date: 截止日期
                - priority: 优先级(0-3)
        """
        try:
            current_time = datetime.now()

            # 构建详细的时间映射
            weekday_map = {
                0: {
                    "cn": "周一",
                    "next": current_time + timedelta(days=(7 - current_time.weekday())),
                },
                1: {
                    "cn": "周二",
                    "next": current_time
                    + timedelta(days=(7 - current_time.weekday() + 1)),
                },
                2: {
                    "cn": "周三",
                    "next": current_time
                    + timedelta(days=(7 - current_time.weekday() + 2)),
                },
                3: {
                    "cn": "周四",
                    "next": current_time
                    + timedelta(days=(7 - current_time.weekday() + 3)),
                },
                4: {
                    "cn": "周五",
                    "next": current_time
                    + timedelta(days=(7 - current_time.weekday() + 4)),
                },
                5: {
                    "cn": "周六",
                    "next": current_time
                    + timedelta(days=(7 - current_time.weekday() + 5)),
                },
                6: {
                    "cn": "周日",
                    "next": current_time
                    + timedelta(days=(7 - current_time.weekday() + 6)),
                },
            }

            # 构建时间信息字典
            time_info = {
                "current": {
                    "datetime": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "date": current_time.strftime("%Y-%m-%d"),
                    "time": current_time.strftime("%H:%M:%S"),
                    "hour": current_time.hour,
                    "weekday": weekday_map[current_time.weekday()]["cn"],
                },
                "tomorrow": {
                    "date": (current_time + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "weekday": weekday_map[(current_time.weekday() + 1) % 7]["cn"],
                },
                "next_week": {
                    "monday": (
                        current_time + timedelta(days=(7 - current_time.weekday()))
                    ).strftime("%Y-%m-%d"),
                    "dates": {
                        day["cn"]: day["next"].strftime("%Y-%m-%d")
                        for _, day in weekday_map.items()
                    },
                },
            }

            # 1. 首先构建所有需要的时间相关变量
            current_datetime = current_time.strftime("%Y-%m-%d %H:%M:%S")
            current_weekday = weekday_map[current_time.weekday()]["cn"]
            tomorrow_date = (current_time + timedelta(days=1)).strftime("%Y-%m-%d")
            tomorrow_weekday = weekday_map[(current_time.weekday() + 1) % 7]["cn"]
            next_week_monday = (
                current_time + timedelta(days=(7 - current_time.weekday()))
            ).strftime("%Y-%m-%d")
            next_week_friday = weekday_map[4]["next"].strftime("%Y-%m-%d")

            # 构建时间映射响应
            next_week_dates = []
            for i in range(7):
                date_str = weekday_map[i]["next"].strftime("%Y-%m-%d")
                next_week_dates.append(f"- {weekday_map[i]['cn']}: {date_str}")

            response = "\n".join(next_week_dates)

            # 2. 构建下周日期字符串
            next_week_dates = response

            # 3. 使用更简单的变量名在提示词模板中
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "human",
                        """
                        你是一名任务分析助手。你的工作是仔细阅读给定的文本，并提取其中提到或隐含的所有可能的任务，这将有助于用户从各类文档中明确行动事项和责任。
                        以下是时间和星期信息:
                        <time>
                        - 现在是: {datetime} {weekday}
                        - 明天是: {tomorrow} {tomorrow_weekday}
                        - 下周一: {next_monday}
                        - 下周五: {next_friday}
                        - 下周日期对应:
                        {week_dates}
                        </time>
                        用户资料：
                        <user_profile>
                        {profile}
                        </user_profile>
                        重要说明：
                        1. 不要基于背景信息添加额外的任务
                        2. 背景信息仅用于更好地理解上下文
                        以下是需要分析的文本：
                        <text>
                        {text}
                        </text>
                        文本中提到的任何明确或隐含的任务、行动、想法,都需要仔细分析是否包含以下任务：
                        A. 显式任务：
                            - 明确的时间安排（如：明天下午3点开会）
                            - 明确的待办事项（如：需要修复bug）
                            - 明确的截止时间（如：本周五前完成）
                        B. 隐式任务：
                            - 记录中提到的后续工作和前置任务（如：之后要跟进这个问题）
                            - 计划和打算（如：打算研究一下个技术）
                            - 需要关注的事项（如：这个方案值得研究）
                            - 需要收集的信息（如：收集一些资料）
                            - 想要做的事情（如：想要研究一下新技术）
                        C. 学习任务：
                            - 技术学习（如：要学习Redis）
                            - 研究计划（如：研究性能优化方案）
                            - 知识积累（如：了解新特性）
                        D. 复习任务：
                            - 需要回顾的内容
                            - 需要整理的笔记
                            - 需要复习的知识点

                        对于每一个识别出的任务，你必须仔细分析提取原因、任务类型、时间安排，并在1到10的范围内给定一个置信分数。只有置信分数大于6的任务才应包含在最终输出结果中。

                        以下是项目列表，请从中选择一个项目，完整引用：
                        <projec_list>
                        {projects}
                        </projec_list>

                        对于每个符合置信度阈值的任务，创建一个具有以下结构的JSON对象：
                        {{
                        "projectId": "字符串",
                        "title": "字符串",
                        "isAllDay": 布尔值,
                        "content": "字符串",
                        "dueDate": "字符串（日期时间格式）",
                        "priority": 整数,
                        "reminders": []
                        }}
                        在构建JSON时，请遵循以下准则：
                        1. 对于日期时间字段，使用格式“yyyy-MM-dd'T'HH:mm:ssZ”（例如，“2023-06-15T14:30:00+0800”）。
                            时间理解规则：
                            1. 基础时间段默认值：
                            - 早上/上午: 09:00:00
                            - 中午: 12:00:00
                            - 下午: 14:00:00
                            - 晚上: 19:00:00

                            2. 周期性时间计算规则：
                            A. "下周X"的计算：
                                - 必须从下一个完整自然周的周一开始计算
                                - 示例（今天是）：{datetime} {weekday}
                                    * "下周一" = {next_monday}
                                    * "下周五" = {next_friday}
                                - 特殊情况：即使当前是周日，"下周X"仍从下一个完整周计算

                            B. "本周X"的计算：
                                - 默认指代本周对应日期
                                - 如果指定日期已过，自动顺延到下周对应日期
                                - 示例（假设今天是周三）：
                                    * "本周二" = 已过，顺延到下周二
                                    * "本周五" = 本周五
                                - 特殊情况：周日被视为一周的最后一天

                            3. 相对时间计算：
                            A. "明天/后天"规则：
                                - 凌晨时段(0:00-5:00)提到"明天"：保持当天日期
                                - 其他时段：自然日+1
                                - 示例：
                                    * 凌晨2点说"明天上午"：当天上午
                                    * 下午说"明天上午"：次日上午

                            B. "X天后"规则：
                                - 精确按自然日计算
                                - 示例：
                                    * "3天后" = 当前日期+3天

                            4. 模糊时间处理：
                            - 只有日期没有具体时间：设置为全天事件(isAllDay=true)
                            - "月底"：当月最后一天23:59:59
                            - "月初"：次月1日09:00:00
                            - "晚些时候"：当天19:00:00
                            - "过几天"：3天后09:00:00
                        2. 对于优先级，使用以下取值：无：0，低：1，中：3，高：5。
                        3. projectId只能有一个,从projec_list中选取，完整引用。
                        4. reminders 是提醒规则。Example : [ "TRIGGER:P0DT1H0M0S", "TRIGGER:PT0S" ]。解释：在事件开始前1小时，和事件发生时提醒。由你来灵活分析提醒时间，需要合理规划，给出理由。
                        5. 未明确说明时间的，去除dueDate，reminders，isAllDay字段。

                        以下是表示一个任务的示例：
                        {{
                        "projectId": "购物",
                        "title": "购买食品杂货",
                        "isAllDay": false,
                        "content": "购买牛奶、鸡蛋和面包",
                        "dueDate": "2023-06-16T18:00:00+0800",
                        "reminders": ["TRIGGER:PT0S"]
                        "priority": 3,
                        }}
                        在创建最终的JSON对象之前，将你的任务提取过程用<task_extraction_process>标签包裹起来。
                        分析完文本后，请按以下格式输出结果：
                        <result>
                        <task_extraction_process>
                        [对每个任务的详细分析，包括时间计算和推理过程，特别注意周几，下周几的推算规则，下周X一律按下一个完整周计算
                        </task_extraction_process>
                        <tasks>
                        [
                        {{任务1的JSON对象}},
                        {{任务2的JSON对象}},
                        ...
                        ]
                        </tasks>

                        如果文本中未发现任务，则输出一个空数组：
                        <tasks>
                        []
                        </tasks>
                        </result>
                        """,
                    ),
                ]
            )

            chain = prompt | self.llm
            # 在调用 chain.ainvoke() 之前，我们可以先获取并打印提示词
            formatted_prompt = await prompt.ainvoke(
                {
                    "datetime": current_datetime,
                    "weekday": current_weekday,
                    "tomorrow": tomorrow_date,
                    "tomorrow_weekday": tomorrow_weekday,
                    "next_monday": next_week_monday,
                    "next_friday": next_week_friday,
                    "week_dates": next_week_dates,
                    "profile": profile,
                    "text": content,
                    "projects": projects,
                }
            )

            result = await chain.ainvoke(
                {
                    "datetime": current_datetime,
                    "weekday": current_weekday,
                    "tomorrow": tomorrow_date,
                    "tomorrow_weekday": tomorrow_weekday,
                    "next_monday": next_week_monday,
                    "next_friday": next_week_friday,
                    "week_dates": next_week_dates,
                    "profile": profile,
                    "text": content,
                    "projects": projects,
                }
            )

            # 获取原始内容
            xml_content = result.content if hasattr(result, 'content') else str(result)

            # 使用正则表达式提取 tasks 标签中的内容
            json_pattern = r'<tasks>\s*\[([\s\S]*?)\]\s*</tasks>'
            json_match = re.search(json_pattern, xml_content, re.DOTALL)

            result = []
            if json_match:
                json_str = f"[{json_match.group(1).strip()}]"
                # 解析 JSON 字符串为任务列表
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON解析失败: {e}")
                    result = []

            self.logger.info(f"提取到 {len(result)} 个任务 \n {result}")
            return result

        except Exception as e:
            self.logger.error(f"提取任务失败: {e}", exc_info=True)
            raise

    async def analyze_text_with_media(self, text: str, media_files: List[Dict]) -> Dict:
        """分析文本和媒体内容

        Args:
            text: 文本内容
            media_files: 媒体文件列表

        Returns:
            Dict: {
                "text": str,  # 分析后的文本
                "summary": str,  # 内容总结
                "media_analysis": List[Dict]  # 媒体分析结果
            }
        """
        try:
            # 构建媒体文件描述
            media_desc = "\n".join(
                [
                    f"- {file.get('type', 'unknown')}: {file.get('description', '')}"
                    for file in media_files
                ]
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """你是一个多模态内容分析助手。

需要分析的内容:
1. 文本内容
2. 媒体文件:
{media_desc}

请提供JSON格式的分析结果，包含:
1. text: 分析后的文本
2. summary: 100字以内的内容总结
3. media_analysis: 媒体分析结果数组，每项包含:
   - type: 文件类型
   - description: 分析描述

格式要求:
- 所有字符串使用双引号
- 确保输出是有效的JSON格式""",
                    ),
                    ("human", "{text}"),
                ]
            )

            chain = prompt | self.llm | self.json_parser

            result = await chain.ainvoke({"media_desc": media_desc, "text": text})

            self.logger.info("多模态内容分析完成")
            return result

        except Exception as e:
            self.logger.error(f"多模态分析失败: {e}", exc_info=True)
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量

        Args:
            text: 输入文本

        Returns:
            List[float]: 嵌入向量
        """
        try:
            # 使用 text-embedding-ada-002 模型
            embeddings = ChatOpenAI(
                model="text-embedding-ada-002",
                api_key=self.config.get('openai', 'api_key'),
                base_url=self.config.get('openai', 'base_url'),
            )

            result = await embeddings.ainvoke(text)
            return result.data[0].embedding

        except Exception as e:
            self.logger.error(f"获取嵌入向量失败: {e}", exc_info=True)
            raise
