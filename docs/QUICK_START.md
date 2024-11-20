# Hi-Ben 快速入门指南

## 1. 环境准备

### 1.1 基础环境
- Python 3.8+
- pip 或 uv 包管理器
- Git

### 1.2 依赖服务
- OpenAI API 账号和密钥
- Telegram Bot Token (通过 @BotFather 获取)
- Notion API Key (可选)
- 滴答清单开发者账号 (可选)

## 2. 安装步骤

### 2.1 获取代码
```bash
git clone https://github.com/yourusername/Hi-Ben.git
cd Hi-Ben
```

### 2.2 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 2.3 安装依赖
```bash
pip install -r requirements.txt
```

## 3. 基础配置

### 3.1 创建配置文件
```bash
cp config/config.example.yml config/config.yml
cp .env.example .env
```

### 3.2 配置必要参数

编辑 `.env` 文件:
```ini
# OpenAI 配置
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=user_id1,user_id2

# Notion 配置 (可选)
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_database_id
```

### 3.3 配置第三方服务

#### Notion 配置
1. 创建 Notion 集成
2. 获取 API Key
3. 创建或选择数据库
4. 配置数据库访问权限

#### 滴答清单配置
1. 注册开发者账号
2. 创建应用获取 Client ID 和 Secret
3. 配置 OAuth 回调地址

## 4. 启动服务

### 4.1 开发环境启动
```bash
python run.py
```

### 4.2 生产环境启动
```bash
# 使用 supervisor
supervisord -c supervisor.conf

# 或使用 systemd
sudo systemctl start hi-ben
```

## 5. 功能验证

### 5.1 Telegram Bot 验证
1. 在 Telegram 中搜索你的 bot
2. 发送 `/start` 命令
3. 测试基本消息响应

### 5.2 功能测试
1. 发送文本消息测试分类
2. 发送语音消息测试转写
3. 发送图片测试多模态分析
4. 测试任务提取功能

## 6. 常见问题

### 6.1 服务启动问题
- 检查配置文件格式
- 确认环境变量加载
- 查看日志文件

### 6.2 Bot 响应问题
- 确认 bot token 正确
- 检查用户权限设置
- 查看 Telegram API 连接状态

### 6.3 第三方服务集成问题
- 验证 API 密钥有效性
- 检查服务权限配置
- 确认网络连接状态

## 7. 下一步

- 查看 [技术文档](TECHNICAL_DOCUMENTATION.md) 了解更多细节
- 参考 [配置文档](CONFIGURATION.md) 进行高级配置
- 阅读 [开发指南](DEVELOPMENT.md) 开始贡献代码 