# Hi-Ben 系统架构文档

## 系统架构概述

Hi-Ben 是一个基于 Python 异步架构的智能助手系统，主要通过 Telegram Bot 提供服务。系统采用模块化设计，分为以下几个主要部分：

### 1. 平台层 (Platforms)
位于 `src/platforms/` 目录，目前主要实现了 Telegram 平台的集成：

#### Telegram Bot 实现
- `telegram_bot.py`: Bot 的核心实现
- `message_router.py`: 消息路由系统
- `state_manager.py`: 状态管理
- `processor_manager.py`: 处理器管理
- `response_manager.py`: 响应管理
- `adapter.py`: 平台适配器

### 2. 服务层 (Services)
位于 `src/services/` 目录，提供核心服务能力：

#### LLM 服务
集成 OpenAI 的 GPT 模型，提供：
- 智能对话
- 内容分析
- 任务理解

#### Whisper 服务
集成 OpenAI 的 Whisper 模型，提供：
- 语音转文字
- 多语言支持

#### Notion 服务
提供笔记管理功能：
- 笔记创建
- 内容同步
- 知识管理

#### 滴答清单服务
提供任务管理功能：
- 任务创建
- 任务更新
- 任务同步

### 3. Agents服务 (Agents)
位于 `src/agents/` 目录，实现智能代理功能：
- 任务分析
- 行为决策
- 响应生成

### 4. 核心层 (Core)
位于 `src/core/` 目录，提供系统核心功能：
- 配置管理
- 状态管理
- 消息处理

### 5. 工具层 (Utils)
位于 `src/utils/` 目录，提供通用工具：
- 日志系统
- 工具函数
- 辅助功能

## 系统流程

### 1. 启动流程
1. 初始化日志系统
2. 启动授权网关服务 (AuthGateway)
3. 初始化并启动 Telegram Bot
4. 注册信号处理器实现优雅关闭

### 2. 消息处理流程
1. Telegram Bot 接收消息
2. 消息路由器分发消息
3. 处理器管理器选择合适的处理器
4. 调用相关服务处理消息
5. 响应管理器格式化并发送响应

## 关键组件

### 1. AuthGateway
- 提供基于 Web 的授权服务
- 运行在本地 8000 端口
- 处理用户认证

### 2. TelegramBot
- 实现与 Telegram 平台的交互
- 管理消息的接收和发送
- 维护用户会话状态

### 3. MessageRouter
- 实现消息的智能路由
- 支持多种消息类型
- 处理消息的优先级

## 配置管理

系统配置通过 `data/config/system_config.yml` 文件管理，包含以下主要配置项：

### OpenAI 配置
```yaml
openai:
  api_key: your_api_key
  base_url: your_api_base_url
  model: gpt-4  # 默认模型
```

### Telegram 配置
```yaml
telegram:
  bot_token: your_bot_token
  allowed_users:
    - "user1"
    - "user2"
```

### 滴答清单配置
```yaml
dida:
  redirect_uri: "http://127.0.0.1:8000/dida/callback"
```

### Whisper 配置
```yaml
whisper:
  model: "base"  # tiny, base, small, medium, large
  device: "cuda"  # cuda 或 cpu
```

⚠️ 安全建议：
1. 在生产环境中使用真实的 API 密钥
2. 不要将包含真实密钥的配置文件提交到版本控制系统
3. 定期更新 API 密钥
4. 适当限制配置文件的访问权限

## 异常处理

系统实现了完整的异常处理机制：

### 1. 服务级异常
- 服务启动异常
- API 调用异常
- 网络连接异常

### 2. 消息处理异常
- 消息解析异常
- 处理超时异常
- 响应发送异常

## 扩展性设计

系统的扩展性主要体现在：

### 1. 平台扩展
- 模块化的平台适配器设计
- 统一的消息处理接口
- 可插拔的处理器系统

### 2. 服务扩展
- 松耦合的服务接口
- 标准化的服务集成方式
- 可配置的服务启用/禁用

## 部署说明

系统支持以下部署方式：

### 1. 直接运行
- 安装依赖
- 配置环境变量
- 运行 main.py

### 2. 后台服务
- 使用 supervisor 等工具
- 支持开机自启
- 实现进程监控

## 安全考虑

系统实现了多层面的安全保护：

### 1. 访问控制
- 用户白名单机制
- API 密钥保护
- 本地授权服务

### 2. 数据安全
- HTTPS 通信
- 敏感信息保护