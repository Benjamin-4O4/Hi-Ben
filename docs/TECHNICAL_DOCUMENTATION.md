# Hi-Ben 技术文档

## 1. 系统架构

### 1.1 核心组件

#### 消息系统 (src/core/models/message.py)
- **统一消息模型**：处理不同平台的消息格式
- **消息类型**：支持文本、语音、图片、视频、文件等
- **元数据管理**：包含平台无关的通用元数据和平台特定元数据
- **消息转换**：提供平台消息和统一格式之间的转换

#### 处理器系统 (src/core/processors/)
- **基础处理器**：提供消息处理的基本框架
- **文本处理器**：处理文本消息，支持分析和转换
- **语音处理器**：处理语音消息，支持语音识别
- **处理器管理器**：管理和协调不同类型的处理器

#### 平台适配系统 (src/platforms/)
- **适配器基类**：定义平台适配器的接口
- **Telegram适配器**：实现Telegram平台的消息处理
- **元数据转换器**：处理不同平台的元数据格式
- **工厂模式**：管理不同平台的适配器实例

### 1.2 工具组件

#### 配置管理 (src/utils/config.py)
- 支持多环境配置
- 配置项验证和访问
- 敏感信息保护

#### 日志系统 (src/utils/logger.py)
- 结构化日志记录
- 不同级别的日志支持
- 自定义日志格式

#### 异常处理 (src/utils/exceptions.py)
- 自定义异常层次结构
- 统一的错误处理机制
- 错误信息标准化

## 2. 功能特性

### 2.1 消息处理
- 支持多种消息类型
- 消息预处理和后处理
- 媒体组消息处理
- 消息编辑和删除

### 2.2 交互功能
- 按钮和菜单组件
- 表单处理
- 交互状态管理
- 回调处理

### 2.3 文件处理
- 文件上传和下载
- 媒体文件处理
- 文件类型识别
- 文件元数据管理

## 3. 开发指南

### 3.1 环境设置
```bash
# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r tests/requirements.txt
```

### 3.2 配置文件
```ini
[telegram]
bot_token = your_bot_token
allowed_users = ["user1", "user2"]

[openai]
api_key = your_api_key
model = gpt-4
```

### 3.3 运行测试
```bash
# 运行所有测试
python scripts/run_tests.py

# 运行带覆盖率的测试
python scripts/run_tests.py --coverage
```

## 4. API 参考

### 4.1 消息处理
```python
# 发送消息
await adapter.send_message(
    chat_id="123",
    message="Hello, world!",
    reply_to=original_message
)

# 编辑消息
await adapter.edit_message(
    chat_id="123",
    message_id="456",
    new_content="Updated message"
)
```

### 4.2 处理器API
```python
# 注册处理器
processor_manager.register_processor(
    MessageType.TEXT,
    TextProcessor()
)

# 处理消息
result = await processor_manager.process(message)
```

### 4.3 交互组件
```python
# 创建按钮
button = Button(
    id="confirm",
    text="确认",
    action="confirm_action"
)

# 创建菜单
menu = Menu(
    id="options",
    title="选择选项",
    options=[{"text": "选项1", "value": "1"}]
)
```

## 5. 最佳实践

### 5.1 错误处理
```python
try:
    await adapter.send_message(chat_id, message)
except ServiceError as e:
    logger.error("服务错误", {"error": str(e)})
    # 进行错误恢复
```

### 5.2 日志记录
```python
logger.info("处理消息", {
    "message_id": message.id,
    "type": message.type,
    "content": message.content
})
```

### 5.3 配置管理
```python
config = Config()
token = config.get("telegram", "bot_token")
allowed_users = config.get("telegram", "allowed_users")
```

## 6. 故障排除

### 6.1 常见问题
1. 消息发送失败
   - 检查网络连接
   - 验证bot token
   - 确认用户权限

2. 处理器错误
   - 检查消息格式
   - 验证处理器注册
   - 查看错误日志

### 6.2 调试技巧
1. 启用详细日志
2. 使用测试模式
3. 检查原始消息数据

## 7. 贡献指南

### 7.1 代码规范
- 遵循PEP 8
- 使用类型注解
- 编写单元测试

### 7.2 提交流程
1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 发起Pull Request

## 8. 更新日志

### v0.1.0
- 初始版本
- 基础消息处理
- Telegram平台支持

### v0.2.0 (计划中)
- 添加更多平台支持
- 改进错误处理
- 增强交互功能