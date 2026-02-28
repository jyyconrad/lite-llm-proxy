# LiteLLM API 网关 - 用户指南

## 📖 介绍

欢迎使用 LiteLLM API 网关！本综合指南将帮助您了解如何使用 API 网关来管理多个 LLM 模型、跟踪使用情况并控制访问权限。

## 🚀 快速开始

### 前置要求
- 已安装 Docker 和 Docker Compose
- 所需 LLM 提供商的 API 密钥（OpenAI、Anthropic 等）

### 快速设置

1. **克隆并配置**
```bash
# 复制环境模板
cp .env.example .env

# 使用您的 API 密钥编辑 .env 文件
nano .env
```

2. **启动服务**
```bash
# 启动所有服务
docker-compose up -d

# 验证服务是否正在运行
docker-compose ps
```

3. **访问系统**
- **API 网关**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **Web 仪表板**: 在浏览器中打开 `web_dashboard.html`

## 👤 用户管理

### 创建第一个用户

首先创建一个管理员用户：

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@company.com",
    "role": "admin",
    "budget_limit": 10000.0,
    "rpm_limit": 100,
    "tpm_limit": 100000
  }'
```

**响应：**
```json
{
  "id": "user-uuid",
  "username": "admin",
  "email": "admin@company.com",
  "role": "admin",
  "budget_limit": 10000.0,
  "rpm_limit": 100,
  "tpm_limit": 100000,
  "created_at": "2024-01-08T10:30:00Z",
  "is_active": true
}
```

### 生成 API 密钥

为您的用户生成 API 密钥：

```bash
curl -X POST http://localhost:8000/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid-from-above",
    "description": "Admin API Key"
  }'
```

**响应：**
```json
{
  "id": "key-uuid",
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "user_id": "user-uuid",
  "description": "Admin API Key",
  "created_at": "2024-01-08T10:35:00Z",
  "is_active": true
}
```

**重要提示**：安全保存 `api_key` 值 - 它只会显示一次！

## 🤖 使用模型

### 列出可用模型

检查哪些模型可用：

```bash
curl -X GET http://localhost:8000/models \
  -H "Authorization: Bearer your-api-key"
```

**响应：**
```json
{
  "models": [
    "gpt-4o",
    "gpt-3.5-turbo", 
    "claude-3-5-sonnet",
    "claude-3-haiku",
    "llama3",
    "mistral"
  ]
}
```

### 进行 API 调用

通过统一接口使用任何支持的模型：

```bash
curl -X POST http://localhost:8000/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "您是一个有用的助手。"},
      {"role": "user", "content": "用简单的术语解释量子计算。"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

**响应：**
```json
{
  "id": "chatcmpl-123",
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "量子计算是一种使用量子比特（qubits）而不是经典比特的计算类型..."
      }
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175
  },
  "cost": 0.00035
}
```

### 高级使用示例

#### 流式响应
```bash
curl -X POST http://localhost:8000/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "user", "content": "写一个关于 AI 的短故事。"}
    ],
    "stream": true
  }'
```

#### 不同的模型提供商
```bash
# 使用 Anthropic Claude
curl -X POST http://localhost:8000/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "messages": [
      {"role": "user", "content": "可再生能源有哪些好处？"}
    ]
  }'

# 使用本地 Ollama
curl -X POST http://localhost:8000/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [
      {"role": "user", "content": "解释机器学习。"}
    ]
  }'
```

## 📊 监控使用情况

### 个人使用统计

检查您自己的使用情况：

```bash
curl -X GET http://localhost:8000/stats/usage \
  -H "Authorization: Bearer your-api-key"
```

**响应：**
```json
{
  "user_id": "your-user-id",
  "total_calls": 1234,
  "total_tokens": 567890,
  "total_cost": 45.67,
  "budget_used": 45.67,
  "budget_limit": 1000.00,
  "rate_limit_usage": 234,
  "rate_limit": 1000,
  "recent_calls": [
    {
      "model_name": "GPT-4",
      "timestamp": "2024-01-08T10:30:00Z",
      "tokens": 1234,
      "cost": 0.0247,
      "success": true
    }
  ]
}
```

### 详细用户统计（仅限管理员）

管理员可以查看详细统计信息：

```bash
curl -X GET http://localhost:8000/admin/stats/overview \
  -H "Authorization: Bearer admin-api-key"
```

**响应：**
```json
{
  "total_calls": 124567,
  "total_tokens": 8923456,
  "active_users": 42,
  "total_users": 156,
  "total_cost": 1245.67,
  "cost_trend": "+8.2%",
  "success_rate": 0.96,
  "avg_response_time": 1120
}
```

## 🖥️ Web 仪表板

### 访问仪表板

1. 在您的 Web 浏览器中打开 `web_dashboard.html`
2. 仪表板提供：
   - 实时系统统计
   - 用户管理界面
   - 模型配置
   - 使用分析图表
   - 最近活动监控

### 仪表板功能

#### 统计概览
- 总 API 调用和令牌使用量
- 活跃用户数和成本跟踪
- 性能指标和成功率

#### 用户管理
- 查看和管理所有用户
- 创建新用户并分配角色
- 生成和撤销 API 密钥
- 设置预算和速率限制

#### 模型配置
- 启用/禁用模型
- 配置每个模型的速率限制
- 监控模型性能
- 查看提供商信息

#### 分析
- 使用趋势的交互式图表
- 按模型分类的成本明细
- 用户活动模式
- 性能指标

## ⚙️ 配置管理

### 模型配置

编辑 `litellm_config.yaml` 以添加或修改模型：

```yaml
model_list:
  - model_name: "your-new-model"
    litellm_params:
      model: "model-name"
      api_key: "os.environ/MODEL_API_KEY"
    rpm: 50
    tpm: 50000
    model_info:
      description: "您的模型描述"
      max_tokens: 4000
      provider: "your-provider"
```

### 环境变量

`.env` 中的关键环境变量：

```bash
# 必需：LLM 提供商密钥
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# 可选：其他提供商
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_KEY=your-key

# 安全
MASTER_KEY=your-master-key
JWT_SECRET=your-jwt-secret

# 速率限制默认值
DEFAULT_RPM_LIMIT=60
DEFAULT_TPM_LIMIT=60000
DEFAULT_BUDGET_LIMIT=1000.0
```

## 🔒 安全最佳实践

### API 密钥安全
- 将 API 密钥安全存储在环境变量中
- 切勿将 API 密钥提交到版本控制
- 定期轮换 API 密钥
- 为不同环境使用不同的密钥

### 速率限制
- 为用户设置适当的 RPM 和 TPM 限制
- 监控异常使用模式
- 使用预算限制来控制成本

### 访问控制
- 使用基于角色的访问控制
- 授予最低必要权限
- 定期审查用户访问级别

## 🚨 故障排除

### 常见问题

**认证错误**
```bash
# 错误：无效的 API 密钥
# 解决方案：验证您的 API 密钥并确保格式正确
curl -H "Authorization: Bearer your-correct-key" ...
```

**超出速率限制**
```bash
# 错误：超出速率限制
# 解决方案：等待或增加用户的速率限制
```

**模型不可用**
```bash
# 错误：找不到模型
# 解决方案：检查 litellm_config.yaml 中的模型名称和配置
```

**超出预算**
```bash
# 错误：超出预算限制
# 解决方案：增加预算限制或等待重置周期
```

### 调试技巧

1. **检查服务健康状态**
```bash
curl http://localhost:8000/health
```

2. **查看服务日志**
```bash
docker-compose logs api-gateway
docker-compose logs postgres
docker-compose logs redis
```

3. **验证数据库连接**
```bash
docker-compose exec postgres psql -U user -d litellm_gateway -c "SELECT version();"
```

## 📈 最佳实践

### 对于开发者
1. 使用有意义的 API 密钥描述
2. 在您的应用程序中实现适当的错误处理
3. 监控使用模式并相应调整限制
4. 对长时间运行的响应使用流式传输

### 对于管理员
1. 定期备份数据库
2. 监控系统健康和性能
3. 审查和更新模型配置
4. 设置适当的安全策略

### 对于用户
1. 保持您的 API 密钥安全
2. 监控您的使用情况和成本
3. 为您的任务使用适当的模型
4. 及时报告任何问题

## 🔄 高级功能

### 自定义模型端点

通过扩展配置添加自定义模型端点：

```yaml
model_list:
  - model_name: "custom-model"
    litellm_params:
      model: "custom/your-model"
      api_base: "https://your-custom-endpoint.com/v1"
      api_key: "os.environ/CUSTOM_API_KEY"
```

### Webhook 集成

设置用于通知的 webhook：
- 预算限制警报
- 速率限制警告
- 系统健康通知

### 多租户支持

通过适当的配置和角色管理，系统支持多个组织。

## 📞 支持

如需帮助：
1. 在 `http://localhost:8000/docs` 查看 API 文档
2. 查看系统日志以获取错误详情
3. 联系您的系统管理员
4. 参考项目文档文件

---

*本用户指南是 LiteLLM API 网关项目的一部分。有关更多信息，请参阅完整的项目文档。*