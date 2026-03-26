# LiteLLM Proxy 全量部署指南

> **版本**: v1.0.0
> **更新日期**: 2026-03-26
> **适用范围**: 生产环境部署

---

## 目录

1. [部署前准备](#1-部署前准备)
2. [环境要求](#2-环境要求)
3. [部署架构](#3-部署架构)
4. [部署步骤](#4-部署步骤)
5. [数据库初始化](#5-数据库初始化)
6. [配置管理](#6-配置管理)
7. [服务启动](#7-服务启动)
8. [健康检查](#8-健康检查)
9. [故障排查](#9-故障排查)
10. [版本升级](#10-版本升级)

---

## 1. 部署前准备

### 1.1 获取代码

```bash
# 克隆仓库
git clone https://github.com/jyyconrad/lite-llm-proxy.git
cd lite-llm-proxy

# 切换到指定版本（可选）
git checkout v1.1.0
```

### 1.2 准备环境变量文件

复制环境变量模板并编辑：

```bash
# 本地开发环境
cp .env-local .env

# 生产环境
cp .env-prod .env  # 注意：.env-prod 不在版本控制中
```

### 1.3 环境变量说明

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql+asyncpg://postgres:admin1234@localhost:5433/litellm_gateway` | ✓ |
| `REDIS_URL` | Redis 连接字符串 | `redis://admin1234@localhost:6379` | ✓ |
| `MASTER_KEY` | 主 API 密钥 | `admin1234` | ✓ |
| `JWT_SECRET` | JWT 密钥 | 自动生成 | ✓ |
| `ADMIN_PASSWORD` | 管理员初始密码 | - | ✗ |
| `PORT` | 服务端口 | `8000` | ✗ |
| `HTTP_PROXY` | HTTP 代理地址 | - | ✗ |
| `HTTP_PROXYS` | HTTPS 代理地址 | - | ✗ |

### 1.4 数据库配置示例

```bash
# 本地开发（Docker）
DATABASE_URL=postgresql+asyncpg://postgres:admin1234@localhost:5433/litellm_gateway
REDIS_URL=redis://admin1234@localhost:6379

# 生产环境（外部数据库）
DATABASE_URL=postgresql+asyncpg://user:password@db.example.com:5432/litellm_gateway
REDIS_URL=redis://:password@redis.example.com:6379
```

---

## 2. 环境要求

### 2.1 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核心 | 4+ 核心 |
| 内存 | 2GB | 8GB+ |
| 存储 | 10GB | 50GB+ SSD |
| 操作系统 | Linux/macOS/Windows | Linux (Ubuntu 22.04+) |

### 2.2 软件依赖

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.10+ | 3.11+ |
| Node.js | 18.x | 20.x |
| PostgreSQL | 14+ | 15+ |
| Redis | 6.x | 7.x |
| Docker (可选) | 20.x | 24.x |

### 2.3 Python 依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `sqlalchemy` - ORM
- `asyncpg` - PostgreSQL 异步驱动
- `bcrypt` - 密码哈希
- `pydantic` - 数据验证
- `litellm` - LLM 代理

### 2.4 前端依赖

```bash
cd frontend
npm install
```

主要依赖：
- `react` - UI 框架
- `chakra-ui` - 组件库
- `recharts` - 图表库
- `axios` - HTTP 客户端

---

## 3. 部署架构

### 3.1 架构图

```
                    ┌─────────────────────────────────────┐
                    │          Load Balancer (可选)        │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │       LiteLLM Proxy 应用程序         │
                    │  ┌─────────────────────────────┐    │
                    │  │   FastAPI + Uvicorn         │    │
                    │  │   - /v1/chat/completions    │    │
                    │  │   - /v1/completions         │    │
                    │  │   - /admin/*                │    │
                    │  └─────────────────────────────┘    │
                    └───────┬─────────────┬───────────────┘
                            │             │
              ┌─────────────▼─────┐ ┌─────▼───────────────┐
              │   PostgreSQL      │ │      Redis          │
              │   - 用户数据      │ │   - 速率限制        │
              │   - API 密钥      │ │   - 缓存            │
              │   - 模型配置      │ │                     │
              │   - 使用统计      │ │                     │
              └───────────────────┘ └─────────────────────┘
```

### 3.2 组件说明

| 组件 | 作用 | 端口 |
|------|------|------|
| LiteLLM Proxy | API 网关和模型代理 | 8000 |
| PostgreSQL | 持久化存储（用户、配置、日志） | 5432/5433 |
| Redis | 速率限制和缓存 | 6379 |

---

## 4. 部署步骤

### 4.1 方案 A：Docker 完整部署（推荐）

适合快速部署和开发环境。

```bash
# 1. 确保 .env 文件已配置
cp .env-local .env

# 2. 一键启动所有服务（app + db + redis）
./docker-start.sh

# 或者使用 docker-compose 直接启动
docker-compose --profile db --profile redis up -d
```

**服务端口**:
- 应用：`http://localhost:8000`
- PostgreSQL：`localhost:5433`
- Redis：`localhost:6379`

### 4.2 方案 B：Docker 只部署应用（使用外部数据库）

适合生产环境，数据库和 Redis 独立部署。

```bash
# 1. 配置外部数据库连接
# 编辑 .env 文件，设置 DATABASE_URL 和 REDIS_URL

# 2. 只启动应用容器
./docker-start.sh app

# 或者
docker-compose up -d app
```

### 4.3 方案 C：本地直接部署

适合开发和测试环境。

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. 启动数据库和 Redis（假设已安装）
# PostgreSQL: localhost:5432
# Redis: localhost:6379

# 3. 初始化数据库
python -c "from data.db import init_database; import asyncio; asyncio.run(init_database())"

# 4. 启动后端服务
./run.sh          # 开发模式（单 worker）
./run.sh prod     # 生产模式（多 worker）

# 5. 启动前端开发服务器（可选）
cd frontend && npm run dev
```

### 4.4 方案 D：开发模式一键启动

适合本地开发。

```bash
# 启动完整开发环境（db + redis + app）
./dev.sh

# 停止开发环境
./dev.sh stop

# 停止并删除数据（谨慎使用）
./dev.sh down
```

---

## 5. 数据库初始化

### 5.1 自动初始化

应用程序首次启动时会自动执行数据库初始化：

1. 创建所有表（Users, APIKeys, ModelConfigs, etc.）
2. 创建默认管理员账户（ID: admin001）
3. 创建初始 API 密钥

### 5.2 手动初始化

```bash
# 方法 1：通过 Python 脚本
python -c "
from data.db import init_database
import asyncio
asyncio.run(init_database())
"

# 方法 2：通过启动脚本
./run.sh --init-db
```

### 5.3 初始化测试数据（可选）

```bash
# 插入示例用户和日志数据
python scripts/seed_test_data.py --users 4 --days 30 --entries-per-day 10
```

**参数说明**:
- `--users`: 创建的用户数（1-4）
- `--days`: 生成多少天的数据
- `--entries-per-day`: 每天的日志条目数
- `--seed`: 随机种子（可复现数据）

### 5.4 验证数据库

```bash
# 连接到数据库
psql -h localhost -p 5433 -U postgres -d litellm_gateway

# 查看表
\dt

# 查看管理员用户
SELECT * FROM users WHERE username = 'admin';

# 查看 API 密钥
SELECT * FROM api_keys WHERE user_id = 'admin001';
```

---

## 6. 配置管理

### 6.1 模型配置

模型配置通过数据库管理，可通过以下方式配置：

**方式 1：前端界面**

1. 访问 `http://localhost:8000/admin`
2. 登录管理员账户
3. 导航到「模型管理」页面
4. 添加/编辑模型配置

**方式 2：API 接口**

```bash
# 创建模型配置
curl -X POST http://localhost:8000/admin/models \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "GPT-4",
    "litellm_params": {
      "model": "gpt-4",
      "api_key": "sk-xxx",
      "provider": "openai"
    },
    "support_types": ["text"],
    "default_rpm": 10,
    "default_tpm": 100000
  }'
```

### 6.2 配置文件

| 文件 | 用途 | 位置 |
|------|------|------|
| `.env` | 环境变量 | 项目根目录 |
| `litellm_config.yaml` | LiteLLM 配置（兼容模式） | 项目根目录 |
| `docker-compose.yml` | Docker 编排配置 | 项目根目录 |

### 6.3 配置同步

系统支持数据库配置和 YAML 配置的双向同步：

```bash
# 查看同步状态
curl http://localhost:8000/admin/config/sync/status

# 从 YAML 同步到数据库
curl -X POST http://localhost:8000/admin/config/sync --data '{"source": "yaml"}'

# 从数据库同步到 YAML
curl -X POST http://localhost:8000/admin/config/sync --data '{"source": "database"}'
```

---

## 7. 服务启动

### 7.1 启动命令汇总

| 场景 | 命令 | 说明 |
|------|------|------|
| 开发模式 | `./dev.sh` | 一键启动 db + redis + app |
| 本地生产 | `./run.sh prod` | 多 worker 模式 |
| Docker 完整 | `./docker-start.sh` | app + db + redis |
| Docker 应用 | `./docker-start.sh app` | 只启动应用 |

### 7.2 生产模式配置

```bash
# 编辑 .env 文件
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com:5432/litellm
REDIS_URL=redis://:pass@redis.example.com:6379
MASTER_KEY=your-master-key-here
JWT_SECRET=your-jwt-secret-here
PORT=8000

# 生产环境建议配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
EOF

# 启动生产服务
./run.sh prod
```

### 7.3 后台运行

```bash
# 使用 nohup
nohup python main.py > logs/app.log 2>&1 &

# 使用 systemd（推荐）
# /etc/systemd/system/litellm-proxy.service
[Unit]
Description=LiteLLM Proxy Service
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=litellm
WorkingDirectory=/opt/litellm-proxy
ExecStart=/opt/litellm-proxy/.venv/bin/python main.py
Restart=always
Environment=PATH=/opt/litellm-proxy/.venv/bin

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl enable litellm-proxy
sudo systemctl start litellm-proxy
```

---

## 8. 健康检查

### 8.1 基础健康检查

```bash
# 检查服务是否存活
curl http://localhost:8000/health

# 预期响应
# {"status": "healthy"}
```

### 8.2 完整健康检查

```bash
# 检查数据库连接
curl http://localhost:8000/health/db

# 检查 Redis 连接
curl http://localhost:8000/health/redis

# 检查所有依赖
curl http://localhost:8000/health/full
```

### 8.3 Docker 健康检查

Docker Compose 配置中包含健康检查：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

查看健康状态：

```bash
docker inspect --format='{{.State.Health.Status}}' litellm_app
```

---

## 9. 故障排查

### 9.1 常见问题

#### 问题 1：数据库连接失败

```bash
# 检查数据库是否运行
docker ps | grep postgres
# 或
pg_isready -h localhost -p 5433

# 检查连接字符串
echo $DATABASE_URL

# 测试连接
psql $DATABASE_URL -c "SELECT 1"
```

#### 问题 2：Redis 连接失败

```bash
# 检查 Redis 是否运行
docker ps | grep redis
# 或
redis-cli ping

# 测试连接
redis-cli -a admin1234 ping
```

#### 问题 3：端口被占用

```bash
# 查看端口占用
lsof -i :8000
lsof -i :5433
lsof -i :6379

# 修改端口（编辑 .env 文件）
PORT=8001
```

#### 问题 4：模型调用返回 404

**原因**: 模型配置中缺少必要的默认值

**解决**: 确保配置中所有字段都有值，或升级到 v1.1.0+ 版本（自动补充默认值）

### 9.2 日志查看

```bash
# Docker 日志
docker logs -f litellm_app

# 应用日志
tail -f logs/app.log

# 系统日志（systemd）
journalctl -u litellm-proxy -f
```

### 9.3 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
./run.sh
```

---

## 10. 版本升级

### 10.1 升级到 v1.1.0

v1.1.0 是 Bug 修复版本，主要修复模型配置 404 问题。

```bash
# 1. 备份当前配置和数据库
docker-compose down
cp -r data/postgres_data backup/postgres_data_$(date +%Y%m%d)

# 2. 拉取最新代码
git pull origin main

# 3. 安装依赖
pip install -r requirements.txt --upgrade
cd frontend && npm install && cd ..

# 4. 重启服务
./docker-start.sh

# 5. 验证升级
curl http://localhost:8000/health
```

### 10.2 数据库迁移

当前版本（v1.1.0）**无需数据库迁移**，所有变更向后兼容。

### 10.3 回滚步骤

```bash
# 1. 停止服务
./docker-stop.sh

# 2. 恢复代码
git checkout <previous-version>

# 3. 恢复依赖
pip install -r requirements.txt

# 4. 重启服务
./docker-start.sh
```

---

## 附录

### A. 端口清单

| 服务 | 端口 | 协议 |
|------|------|------|
| LiteLLM Proxy | 8000 | HTTP |
| PostgreSQL (Docker) | 5433 | TCP |
| Redis (Docker) | 6379 | TCP |

### B. 默认账户

| 账户类型 | 值 |
|----------|-----|
| 管理员 ID | admin001 |
| 管理员用户名 | admin |
| 默认 API 密钥 | admin1234 (可在 .env 中覆盖) |

### C. 环境变量完整清单

```bash
# 必需
DATABASE_URL=postgresql+asyncpg://postgres:admin1234@localhost:5433/litellm_gateway
REDIS_URL=redis://admin1234@localhost:6379
MASTER_KEY=admin1234
JWT_SECRET=your-secret-key

# 可选
ADMIN_PASSWORD=admin1234
PORT=8000
HTTP_PROXY=http://proxy.example.com:8080
HTTP_PROXYS=https://proxy.example.com:8080

# 数据库连接池（高级）
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_SYNC_POOL_SIZE=5
```

### D. 相关文件路径

| 文件 | 路径 |
|------|------|
| 主程序 | `main.py` |
| 数据库模型 | `data/tables.py` |
| 配置管理 | `config_manager.py` |
| API 路由 | `gateway/routers/` |
| 前端源码 | `frontend/src/` |
| 环境变量 | `.env` |
| Docker 配置 | `docker-compose.yml` |

---

**最后更新**: 2026-03-26
**版本**: v1.1.0
