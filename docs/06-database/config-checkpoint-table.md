# ConfigCheckpoint 表设计文档

**最后更新**：2026-03-20
**版本**：v1.0.0

---

## 概述

`ConfigCheckpoint` 表用于记录 LiteLLM 配置文件的同步状态检查点，支持应用启动时自动检测 YAML 配置文件与数据库配置之间的差异。

---

## 表结构

```sql
CREATE TABLE config_checkpoints (
    id              VARCHAR(36) PRIMARY KEY,
    config_type     VARCHAR(50) NOT NULL UNIQUE DEFAULT 'litellm_config',
    yaml_hash       VARCHAR(64) NOT NULL,
    db_hash         VARCHAR(64),
    last_sync_source VARCHAR(20),
    last_sync_time  TIMESTAMP,
    yaml_updated_at TIMESTAMP,
    db_updated_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | VARCHAR(36) | 是 | 主键，UUID 格式 |
| `config_type` | VARCHAR(50) | 是 | 配置类型标识，当前仅支持 `litellm_config` |
| `yaml_hash` | VARCHAR(64) | 是 | YAML 配置文件内容的 SHA256 哈希值（64 位十六进制） |
| `db_hash` | VARCHAR(64) | 否 | 数据库配置内容的 SHA256 哈希值 |
| `last_sync_source` | VARCHAR(20) | 否 | 最后同步来源：`yaml`、`database`、`none` |
| `last_sync_time` | TIMESTAMP | 否 | 最后同步执行时间 |
| `yaml_updated_at` | TIMESTAMP | 否 | YAML 文件最后修改时间戳 |
| `db_updated_at` | TIMESTAMP | 否 | 数据库配置最后更新时间戳 |
| `created_at` | TIMESTAMP | 是 | 记录创建时间（数据库自动设置） |
| `updated_at` | TIMESTAMP | 是 | 记录更新时间（数据库自动更新） |

---

## 哈希计算逻辑

### YAML 哈希计算

```python
import hashlib

def compute_yaml_hash(config_path: str) -> str:
    """计算 YAML 配置文件内容的 SHA256 哈希"""
    if not os.path.exists(config_path):
        return ""

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    return hashlib.sha256(content.encode("utf-8")).hexdigest()
```

**说明**：
- 对文件**完整内容**进行哈希，包括空白字符
- 使用 SHA256 算法，输出 64 位十六进制字符串
- 文件不存在或读取失败时返回空字符串

### 数据库哈希计算

```python
import hashlib
import json

def compute_db_hash(db_configs: Dict[str, ModelConfig]) -> str:
    """计算数据库配置内容的 SHA256 哈希"""
    sorted_configs = {}
    for model_name, config in sorted(db_configs.items()):
        sorted_configs[model_name] = {
            'model_name': config.model_name,
            'litellm_params': config.litellm_params,
            'support_types': config.support_types,
            'default_rpm': config.default_rpm,
            'default_tpm': config.default_tpm,
            'default_max_tokens': config.default_max_tokens,
            'description': config.description,
            'is_active': config.is_active,
        }

    json_str = json.dumps(sorted_configs, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
```

**说明**：
- 将所有模型配置按模型名称排序后统一哈希
- 使用 `sort_keys=True` 确保 JSON 序列化的一致性
- 包含所有配置字段，确保变更检测的准确性

---

## 使用场景

### 1. 应用启动时同步检查

```python
async def sync_on_startup(self, db: AsyncSession) -> str:
    # 计算当前 YAML 哈希
    yaml_hash = self.compute_yaml_hash()

    # 获取数据库配置和哈希
    db_configs = await self.get_db_model_configs(db)
    db_hash = self.compute_db_hash(db_configs)

    # 获取检查点
    checkpoint = await self.get_checkpoint(db)

    if checkpoint is None:
        # 首次启动，执行同步
        await self.sync_yaml_to_db(db)
        await self.save_checkpoint(db, yaml_hash, db_hash, "yaml")

    # 检查是否有变更
    yaml_changed = yaml_hash != checkpoint.yaml_hash
    db_changed = db_hash != checkpoint.db_hash

    if yaml_changed:
        # YAML 有更新，执行同步
        ...
```

### 2. 同步状态查询

```python
async def get_sync_status(self, db: AsyncSession) -> dict:
    checkpoint = await self.get_checkpoint(db)
    yaml_hash = self.compute_yaml_hash()
    db_configs = await self.get_db_model_configs(db)
    db_hash = self.compute_db_hash(db_configs)

    yaml_changed = checkpoint and yaml_hash != checkpoint.yaml_hash
    db_changed = checkpoint and db_hash != checkpoint.db_hash

    return {
        "yaml_hash_short": yaml_hash[:16] if yaml_hash else None,
        "db_hash_short": db_hash[:16] if db_hash else None,
        "last_sync_time": checkpoint.last_sync_time.isoformat() if checkpoint else None,
        "last_sync_source": checkpoint.last_sync_source if checkpoint else None,
        "yaml_changed": yaml_changed or (checkpoint is None),
        "db_changed": db_changed,
        "is_synced": not yaml_changed and not db_changed and checkpoint is not None,
        "model_count": len(db_configs),
    }
```

---

## 索引设计

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `PRIMARY` | `id` | UNIQUE | 主键索引 |
| `idx_config_type` | `config_type` | UNIQUE | 配置类型唯一索引 |

---

## 数据示例

```sql
INSERT INTO config_checkpoints (
    id, config_type, yaml_hash, db_hash, last_sync_source, last_sync_time, yaml_updated_at, db_updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'litellm_config',
    'a1b2c3d4e5f6789012345678901234567890abcd',
    'a1b2c3d4e5f6789012345678901234567890abcd',
    'yaml',
    '2026-03-20 10:30:00+00:00',
    '2026-03-20 09:00:00+00:00',
    '2026-03-20 10:30:00+00:00'
);
```

---

## SQLAlchemy 模型定义

```python
class ConfigCheckpoint(Base):
    """配置同步检查点表，记录 YAML 与数据库配置的同步状态"""
    __tablename__ = "config_checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_type = Column(String(50), nullable=False, unique=True, default="litellm_config")
    yaml_hash = Column(String(64), nullable=False)
    db_hash = Column(String(64))
    last_sync_source = Column(String(20))
    last_sync_time = Column(DateTime)
    yaml_updated_at = Column(DateTime)
    db_updated_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## 相关文档

- [配置同步 API](../05-api/config-sync-api.md)
- [配置同步模块设计](../04-design/04.1-overview/config-sync-design.md)
- [ModelConfig 表设计](./model-config-table.md)
