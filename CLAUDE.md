## 项目概述

LiteLLM Proxy 是一个兼容 OpenAI 的 API 网关，提供对多个大语言模型提供商的统一访问。它包含用户管理、速率限制、用量追踪以及基于 React 的管理后台。

## 开发命令

### 运行应用程序

```bash
# 启动后端（Python）
python main.py

# 使用 Docker 启动
docker-compose up -d

# 启动前端开发服务器
cd frontend && npm run dev

# 构建前端生产版本
cd frontend && npm run build
```

### 依赖安装

```bash
# Python 依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 数据库初始化

```bash
# 运行数据库初始化和种子数据
python scripts/seed_test_data.py
```

## 架构

### 后端结构

`main.py` - 入口文件，初始化 FastAPI 应用并启动 uvicorn 服务器

`gateway/` - 核心 FastAPI 应用
  - `app.py` - FastAPI 应用初始化、中间件以及启动/关闭事件
  - `config.py` - 从环境变量和 YAML 文件读取的配置设置
  - `dependencies.py` - 用于认证和速率限制的 FastAPI 依赖注入
  - `local_model_manage.py` - 本地/独立模型管理
  - `routers/` - API 端点处理器
    - `admin.py` - 管理端点（用户管理、API 密钥、统计数据）
    - `llm.py` - 兼容 OpenAI 的大语言模型 API 端点（`/v1/completions`、`/v1/embeddings`）
    - `system.py` - 系统端点（`/health`、`/models`）

`data/` - 数据层
  - `db.py` - SQLAlchemy 数据库引擎和会话管理
  - `tables.py` - SQLAlchemy ORM 模型定义（User、ApiKey、RequestLog）
  - `model_info.py` - 模型信息和定价数据

`config_manager.py` - 管理 litellm_config.yaml 的模型提供商配置

### 前端结构

`frontend/` - React + Chakra UI 管理后台
  - 使用 Vite 构建、Chakra UI 作为组件库、Recharts 用于数据可视化
  - 提供静态文件服务并与后端 API 通信

### 数据流

1. **认证**：通过存储在数据库中的 JWT 令牌验证 API 密钥
2. **速率限制**：基于 Redis 的速率限制（RPM/TPM）并执行预算控制
3. **大语言模型代理**：请求通过 LiteLLM 代理到各个提供商
4. **用量追踪**：所有请求记录到 PostgreSQL，包含令牌数量和费用

### 配置

- `.env` 文件：数据库、Redis、JWT 密钥
- `litellm_config.yaml`：模型提供商配置（OpenAI 密钥、本地模型等）
- `litellm_config.yaml` 通过 `config_manager.py` 以编程方式管理

### 核心概念

- **模型别名**：内部模型名称映射到提供商特定的模型（例如，"GPT-4" -> "openai/gpt-4"）
- **预算限制**：通过请求日志执行每个用户的金额限制
- **速率限制**：通过 Redis 滑动窗口执行 RPM/TPM 限制
- **费用计算**：从提供商响应中解析令牌数量，并乘以 `model_info.py` 中的定价