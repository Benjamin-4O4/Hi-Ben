# Hi-Ben API 文档

## 平台服务 API

### Telegram Bot

Hi-Ben 的主要交互界面是通过 Telegram Bot 实现的。Bot 服务包含以下主要组件：

#### 消息路由 (MessageRouter)
负责根据消息类型和内容将用户消息路由到相应的处理器。

#### 状态管理 (StateManager)
管理用户会话状态，支持多轮对话和上下文保持。

#### 处理器管理 (ProcessorManager)
管理和协调不同类型消息的处理器，包括文本、语音等类型的消息处理。

#### 响应管理 (ResponseManager)
处理和格式化发送给用户的响应消息。

## 核心服务 API

### LLM 服务
集成 OpenAI 的 GPT 模型，提供智能对话和内容分析能力。

### Whisper 服务
集成 OpenAI 的 Whisper 模型，提供语音转文字功能。

### Notion 服务
提供与 Notion 集成的功能，用于笔记管理。

### 滴答清单服务 (Dida365)
提供与滴答清单集成的功能，用于任务管理。

## 授权服务

### AuthGateway
提供基于 Web 的授权服务，运行在本地 8000 端口，用于处理认证相关功能。

## 错误处理

系统实现了统一的错误处理机制，主要包括：
- 服务启动异常处理
- API 调用异常处理
- 消息处理异常处理

## 系统配置

系统配置位于 `data/config/system_config.yml`：

#### OpenAI 配置
```yaml
openai:
  api_key: your_api_key     # OpenAI API密钥
  base_url: your_api_base   # API基础URL
  model: gpt-4             # 使用的模型
```

#### Telegram 配置
```yaml
telegram:
  bot_token: your_bot_token  # Telegram Bot令牌
  allowed_users:             # 允许使用的用户列表
    - "your_username"
```

#### 第三方服务配置
```yaml
dida:
  redirect_uri: "http://127.0.0.1:8000/dida/callback"  # 滴答清单授权回调地址

whisper:
  model: "base"  # 语音识别模型 (tiny/base/small/medium/large)
  device: "cuda" # 运行设备 (cuda/cpu)
```

## 使用建议

1. 错误处理
   - 确保正确配置所有必需的配置项
   - 监控服务日志以及时发现问题

2. 安全性
   - 保护好各类API密钥
   - 只允许授权用户访问系统
   - 使用HTTPS进行安全通信

3. 性能优化
   - 系统使用异步架构，支持并发处理
   - 合理控制API调用频率
   - 适当设置超时时间