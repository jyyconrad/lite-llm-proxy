# LiteLLM API Gateway 完整接口文档

## 概述
本文档描述了LiteLLM API网关的所有可用接口，包括代理模型接口、用户管理接口和统计监控接口。

## 认证
所有接口都需要Bearer token认证：
```
Authorization: Bearer <api_token>
```

## 路由前缀
- 系统接口：无前缀
- OpenAI兼容接口：`/v1`
- 管理接口：`/admin`

## 1. 系统接口

### 1.1 健康检查
**GET** `/health`

返回系统健康状态。

**响应：**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-08T10:30:00Z",
  "version": "1.0.0"
}
```

### 1.2 获取可用模型列表
**GET** `/models`

返回系统配置的可用模型列表。

**响应：**
```json
{
  "models": ["GPT-4", "Claude-3", "Gemini-Pro"]
}
```

## 2. OpenAI兼容接口

### 2.1 文本补全
**POST** `/v1/completions`

代理各种AI模型的文本补全功能。

**请求体：**
```json
{
  "model": "GPT-4",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 100,
  "stream": false
}
```

**响应：**
```json
{
  "id": "chatcmpl-123",
  "model": "GPT-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'm doing well, thank you!"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  },
  "cost": 0.00036
}
```

### 2.2 向量嵌入
**POST** `/v1/embeddings`

代理各种AI模型的向量嵌入功能。

**请求体：**
```json
{
  "model": "text-embedding-ada-002",
  "input": "Hello world",
  "dimensions": 1536,
  "encoding_format": "float"
}
```

**响应：**
```json
{
  "id": "emb-123",
  "model": "text-embedding-ada-002",
  "data": [
    {
      "embedding": [0.1, 0.2, 0.3, ...],
      "index": 0
    }
  ],
  "usage": {
    "prompt_tokens": 2,
    "total_tokens": 2
  },
  "cost": 0.00002
}
```

## 3. 管理接口

### 3.1 用户管理

#### 创建用户
**POST** `/admin/users`

创建新用户。

**请求体：**
```json
{
  "username": "alice",
  "email": "alice@company.com",
  "role": "user",
  "budget_limit": 1000.0,
  "rpm_limit": 60,
  "tpm_limit": 60000
}
```

**响应：**
```json
{
  "id": "user_123",
  "username": "alice",
  "email": "alice@company.com",
  "role": "user",
  "budget_limit": 1000.0,
  "rpm_limit": 60,
  "tpm_limit": 60000,
  "created_at": "2024-01-08T10:30:00Z",
  "is_active": true
}
```

#### 创建API密钥
**POST** `/admin/api-keys`

为用户创建API密钥。

**请求体：**
```json
{
  "user_id": "user_123",
  "description": "Production API Key"
}
```

**响应：**
```json
{
  "id": "key_123",
  "api_key": "sk-lite-llm-gateway-xxxxx",
  "user_id": "user_123",
  "description": "Production API Key",
  "created_at": "2024-01-08T10:30:00Z",
  "is_active": true
}
```

### 3.2 统计接口

#### 系统概览统计
**GET** `/admin/stats/overview`

返回系统整体统计信息。

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

#### 模型使用统计
**GET** `/admin/stats/model-usage`

返回按模型分类的使用统计。

**响应：**
```json
[
  {
    "model_name": "GPT-4",
    "call_count": 45678,
    "total_tokens": 3456789,
    "total_cost": 912.34,
    "avg_response_time": 1240,
    "success_rate": 0.98,
    "status": "active"
  },
  {
    "model_name": "Claude-3",
    "call_count": 23456,
    "total_tokens": 1987654,
    "total_cost": 245.67,
    "avg_response_time": 980,
    "success_rate": 0.96,
    "status": "active"
  }
]
```

#### 最近活动记录
**GET** `/admin/stats/recent-activity`

返回最近的API调用活动记录。

**查询参数：**
- `limit` (可选)：返回记录数量（默认：20）

**响应：**
```json
[
  {
    "id": "req_12345",
    "user_email": "alice@company.com",
    "model_name": "GPT-4",
    "total_tokens": 1234,
    "cost": 0.0247,
    "timestamp": "2024-01-08T10:30:00Z",
    "success": true,
    "response_time": 1250
  },
  {
    "id": "req_12346",
    "user_email": "bob@company.com",
    "model_name": "Claude-3",
    "total_tokens": 876,
    "cost": 0.0088,
    "timestamp": "2024-01-08T10:25:00Z",
    "success": true,
    "response_time": 980
  }
]
```

#### 用户详细统计
**GET** `/admin/stats/user/{user_id}`

返回指定用户的详细统计信息。

**响应：**
```json
{
  "user_id": "user_123",
  "email": "alice@company.com",
  "total_calls": 1234,
  "total_tokens": 567890,
  "total_cost": 45.67,
  "active_models": ["GPT-4", "Claude-3"],
  "last_activity": "2024-01-08T10:30:00Z",
  "budget_used": 45.67,
  "budget_limit": 1000.00,
  "rate_limit_usage": 234,
  "rate_limit": 1000
}
```

#### 用户自服务统计
**GET** `/admin/stats/usage`

返回认证用户的个人使用统计（自服务）。

**响应：**
```json
{
  "user_id": "user_123",
  "total_calls": 1234,
  "total_tokens": 567890,
  "total_cost": 45.67,
  "budget_used": 45.67,
  "budget_limit": 1000.00,
  "rate_limit_usage": 234,
  "rate_limit": 1000
}
```

#### 使用趋势统计
**GET** `/admin/stats/usage-trend`

返回时间维度的使用统计。

**查询参数：**
- `period` (必需): "7d", "30d", "90d"
- `granularity` (可选): "hour", "day", "week"

**响应：**
```json
{
  "period": "7d",
  "data": [
    {
      "date": "2024-01-01",
      "calls": 1200,
      "tokens": 45000,
      "cost": 12.34,
      "users": 25
    },
    {
      "date": "2024-01-02",
      "calls": 1900,
      "tokens": 78000,
      "cost": 23.45,
      "users": 32
    }
  ]
}
```

## 错误响应

所有接口返回标准错误响应：

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": "Additional error details"
}
```

## 常见错误码

- `AUTH_REQUIRED`: 需要认证
- `INVALID_TOKEN`: 无效或过期的token
- `PERMISSION_DENIED`: 权限不足
- `NOT_FOUND`: 资源未找到
- `RATE_LIMITED`: 速率限制超出

## 实现说明

1. **缓存**: 统计接口建议实现缓存以提高性能
2. **分页**: 大数据集使用分页
3. **实时更新**: 考虑WebSocket连接实现实时仪表板更新
4. **数据聚合**: 预聚合统计数据以获得更好的性能
5. **速率限制**: 基于Redis实现RPM/TPM/预算限制
6. **使用统计**: 自动记录所有API调用的使用数据

## 使用流程

1. 创建用户 → 创建API密钥 → 使用API密钥调用代理接口 → 查看使用统计
2. 管理员可以通过管理接口查看所有用户的使用情况和系统统计
3. 用户可以通过自服务接口查看个人使用情况