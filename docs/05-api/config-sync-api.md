# 配置同步 API 文档

**最后更新**：2026-03-20
**版本**：v1.0.0
**负责人**：后端团队

---

## 概述

配置同步 API 用于管理 LiteLLM 代理的配置文件（`litellm_config.yaml`）与数据库配置之间的同步状态。提供状态查询和手动触发同步功能。

### 权限要求

所有配置同步接口**仅管理员**（`role=admin`）可访问，需要有效的 API 密钥认证。

---

## API 端点

### GET /admin/config/sync-status

获取当前配置同步状态，包括 YAML 文件与数据库的哈希对比、最后同步时间等信息。

#### 请求头

| 头名称 | 必填 | 说明 |
|--------|------|------|
| `Authorization` | 是 | Bearer Token 格式，值为 `sk-xxxxxxxx` |

#### 请求参数

无

#### 响应格式

```json
{
  "yaml_hash_short": "a1b2c3d4e5f67890",
  "db_hash_short": "a1b2c3d4e5f67890",
  "last_sync_time": "2026-03-20T10:30:00+00:00",
  "last_sync_source": "yaml",
  "yaml_changed": false,
  "db_changed": false,
  "is_synced": true,
  "model_count": 5
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `yaml_hash_short` | string \| null | YAML 配置文件内容 SHA256 哈希的前 16 位 |
| `db_hash_short` | string \| null | 数据库配置内容 SHA256 哈希的前 16 位 |
| `last_sync_time` | string \| null | 最后同步时间（ISO 8601 格式） |
| `last_sync_source` | string \| null | 最后同步来源：`yaml`（从 YAML 同步）、`database`（数据库更新）、`none`（无变更） |
| `yaml_changed` | boolean | YAML 文件是否自上次同步后有变更 |
| `db_changed` | boolean | 数据库配置是否自上次同步后有变更 |
| `is_synced` | boolean | 是否已同步（YAML 和数据库均无变更） |
| `model_count` | integer | 当前数据库中激活的模型数量 |

#### 状态码

| 状态码 | 说明 |
|--------|------|
| `200 OK` | 成功获取同步状态 |
| `401 Unauthorized` | 未提供认证或认证失败 |
| `403 Forbidden` | 非管理员用户访问 |

#### 使用示例

```bash
# 请求示例
curl -X GET "http://localhost:8000/admin/config/sync-status" \
  -H "Authorization: Bearer sk-abc12345"

# 响应示例（已同步）
{
  "yaml_hash_short": "a1b2c3d4e5f67890",
  "db_hash_short": "a1b2c3d4e5f67890",
  "last_sync_time": "2026-03-20T10:30:00+00:00",
  "last_sync_source": "yaml",
  "yaml_changed": false,
  "db_changed": false,
  "is_synced": true,
  "model_count": 5
}

# 响应示例（YAML 有变更）
{
  "yaml_hash_short": "b2c3d4e5f6789012",
  "db_hash_short": "a1b2c3d4e5f67890",
  "last_sync_time": "2026-03-19T08:00:00+00:00",
  "last_sync_source": "yaml",
  "yaml_changed": true,
  "db_changed": false,
  "is_synced": false,
  "model_count": 5
}
```

---

### POST /admin/config/sync

手动触发配置同步，将 YAML 配置文件中的新模型同步到数据库。

#### 请求头

| 头名称 | 必填 | 说明 |
|--------|------|------|
| `Authorization` | 是 | Bearer Token 格式，值为 `sk-xxxxxxxx` |

#### 请求体

无（空请求体）

#### 响应格式

```json
{
  "message": "同步完成",
  "result": "从 YAML 同步了 2 个新模型到数据库"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `message` | string | 同步操作总体状态 |
| `result` | string | 详细同步结果描述 |

#### 状态码

| 状态码 | 说明 |
|--------|------|
| `200 OK` | 同步操作完成 |
| `401 Unauthorized` | 未提供认证或认证失败 |
| `403 Forbidden` | 非管理员用户访问 |

#### 使用示例

```bash
# 请求示例
curl -X POST "http://localhost:8000/admin/config/sync" \
  -H "Authorization: Bearer sk-abc12345" \
  -H "Content-Type: application/json"

# 响应示例（成功同步新模型）
{
  "message": "同步完成",
  "result": "从 YAML 同步了 2 个新模型到数据库"
}

# 响应示例（无新模型）
{
  "message": "同步完成",
  "result": "没有需要同步的新模型"
}

# 响应示例（YAML 文件不存在）
{
  "message": "同步完成",
  "result": "YAML 配置文件不存在"
}
```

#### 同步结果类型

| 结果描述 | 说明 |
|----------|------|
| `首次启动同步：从 YAML 同步了 N 个新模型到数据库` | 首次启动时的同步 |
| `YAML 更新同步：从 YAML 同步了 N 个新模型到数据库` | 检测到 YAML 变更，同步新模型 |
| `YAML 有变更但无新模型：...` | YAML 有变更但没有新模型（可能修改了现有模型） |
| `数据库配置已更新，保持当前版本` | 数据库有变更，保持数据库版本 |
| `配置无变化` | YAML 和数据库均无变化 |
| `YAML 配置文件不存在` | 配置文件不存在 |
| `同步失败：...` | 同步过程中发生错误 |

---

## 同步策略说明

### 数据库优先原则

配置同步遵循**数据库绝对优先**原则：

1. **YAML 有新增模型** → 只添加新模型到数据库，不更新已有模型
2. **YAML 修改现有模型** → 忽略，保持数据库版本
3. **数据库有变更** → 保持数据库版本，更新检查点

### 哈希计算

- **YAML 哈希**：对 `litellm_config.yaml` 文件内容进行 SHA256 哈希
- **数据库哈希**：对所有激活的模型配置进行标准化后 SHA256 哈希

### 检查点机制

同步状态记录在 `config_checkpoints` 表中，包含：
- YAML 哈希值
- 数据库哈希值
- 最后同步时间
- 同步来源

---

## 错误处理

### 常见错误响应

```json
{
  "detail": "Invalid authentication credentials"
}
```

```json
{
  "detail": "User does not have admin role"
}
```

### 同步失败处理

同步失败时，不会保存检查点，下次启动时会重试同步。

---

## 相关文档

- [配置同步模块设计](../04-design/04.1-overview/config-sync-design.md)
- [配置同步详细设计](../04-design/04.2-detail/config-sync-detail.md)
- [ConfigCheckpoint 表设计](../06-database/config-checkpoint-table.md)
