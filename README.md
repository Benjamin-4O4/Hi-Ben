# Hi-Ben

> 🤖 一个基于 Cursor + Windsurf 实现的个人 AI 助手实验项目

## 这是啥？

这是我用来实验和学习的个人 AI 助手项目。代码可能有点凌乱，全AI写，我只负责提想法和点击Apply，但基本功能都能用。主要是通过 Telegram 机器人（设计了多平台兼容，我也不晓得到底能兼容不）来交互，主要实现以下功能：

### 🤖 智能助手工作流

1. 发送任何消息给机器人
2. AI 自动分析消息内容：
   - 📝 自动整理并保存到 Notion 的对应分类中
   - ✅ 智能提取任务并创建到滴答清单

举个栗子：
> 你：明天下午3点要开会讨论新项目方案
> 
> 机器人：
> - ✍️ 已保存到 Notion 的"Note"分类
> - ⏰ 已在滴答清单创建提醒：「新项目方案讨论会议」- 明天 15:00

## 用了啥？

### 编程语言
- Python 3.10+

### 框架
- LangChain（AI 应用框架）
- LangGraph（AI 工作流框架）
- FastAPI（后端框架）

### API 服务
- OpenAI API）
- Telegram Bot API（机器人服务）
- Notion API（笔记服务）
- 滴答清单 API（任务管理）

## 怎么用？

1. 克隆代码
```bash
git clone https://github.com/Benjamin-4O4/Hi-Ben.git
cd Hi-Ben
```

2. 装依赖
```bash
pip install -r requirements.txt
```

3. 配置 system_config.yml（在 data/config 目录下）
```yaml
openai:
  api_key: your_api_key
  base_url: your_api_base_url
  model: gpt-4  # 或其他模型

telegram:
  bot_token: your_bot_token
  allowed_users:
    - "your_telegram_username"

dida:
  redirect_uri: "http://127.0.0.1:8000/dida/callback" # 授权滴答清单的回调地址


whisper:
  model: "base"  # tiny/base/small/medium/large
  device: "cuda"  # 或 cpu
```

4. 运行
```bash
python run.py
```

## 代码结构

```
Hi-Ben/
├── src/           # 主要代码
├── data/          # 配置和数据
├── docs/          # 文档（如果你感兴趣的话）
└── tests/         # 测试（也许会写）
```

## 许可证

[MIT License](LICENSE) - 随便用，不负责，能用就用，不能用就改 😄

## 说明

- 代码质量不太高，主要是用来学习和实验
- 基于 Cursor 和 Windsurf 实现，感谢这些优秀的工具
- 欢迎优化和改进，但别指望我会立刻修复问题
- 如果你觉得有用，点个星星就行，不用太客气
- 这个文档也是ai写的（除了这句）

## 相关文档

- [API 文档](docs/API.md)
- [架构说明](docs/ARCHITECTURE.md)
- [部署指南](docs/DEPLOYMENT.md)

## 贡献

随便提 PR，看到了我会看的。不过我是个垃圾佬，所以别期望太高 😅