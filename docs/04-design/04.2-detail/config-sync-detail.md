# 配置同步详细设计文档

**最后更新**：2026-03-20
**版本**：v1.0.0

---

## 概述

本文档描述 `ConfigSyncService` 类的详细实现，包括核心方法、算法逻辑和异常处理。

---

## ConfigSyncService 类设计

### 类结构

```python
class ConfigSyncService:
    """配置同步服务"""

    def __init__(self, config_path: str = None)
    def compute_yaml_hash(self) -> str
    def compute_db_hash(self, db_configs: Dict[str, ModelConfig]) -> str
    def get_yaml_mtime(self) -> Optional[datetime]
    async def get_checkpoint(self, db: AsyncSession) -> Optional[ConfigCheckpoint]
    async def save_checkpoint(self, db: AsyncSession, ...) -> ConfigCheckpoint
    async def get_db_model_configs(self, db: AsyncSession) -> dict
    async def sync_yaml_to_db(self, db: AsyncSession) -> Tuple[bool, str]
    async def sync_on_startup(self, db: AsyncSession) -> str
    async def get_sync_status(self, db: AsyncSession) -> dict
```

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `config_path` | str | YAML 配置文件路径，默认 `./litellm_config.yaml` |

---

## 核心方法详解

### 1. compute_yaml_hash()

计算 YAML 配置文件内容的 SHA256 哈希。

```python
def compute_yaml_hash(self) -> str:
    """计算 YAML 配置文件内容的 SHA256 哈希"""
    try:
        if not os.path.exists(self.config_path):
            return ""

        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()

        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.warning(f"计算 YAML 哈希失败：{e}")
        return ""
```

**实现细节**：
- 文件不存在时返回空字符串
- 使用 UTF-8 编码读取文件
- 异常时记录警告日志并返回空字符串

---

### 2. compute_db_hash()

计算数据库配置内容的 SHA256 哈希。

```python
def compute_db_hash(self, db_configs: Dict[str, ModelConfig]) -> str:
    """计算数据库配置内容的 SHA256 哈希"""
    try:
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
    except Exception as e:
        logger.error(f"计算数据库哈希失败：{e}")
        return ""
```

**实现细节**：
- 使用 `sorted()` 确保模型顺序一致
- 使用 `sort_keys=True` 确保 JSON 键顺序一致
- 使用 `ensure_ascii=False` 支持中文字符
- 使用 `default=str` 处理非标准 JSON 类型（如 datetime）

---

### 3. get_checkpoint()

从数据库获取配置同步检查点。

```python
async def get_checkpoint(self, db: AsyncSession) -> Optional[ConfigCheckpoint]:
    """获取配置同步检查点"""
    try:
        stmt = select(ConfigCheckpoint).where(
            ConfigCheckpoint.config_type == "litellm_config"
        )
        result = await db.execute(stmt)
        return result.scalars().first()
    except Exception:
        return None
```

**实现细节**：
- 按 `config_type` 字段查询
- 异常时返回 `None`，不抛出异常

---

### 4. save_checkpoint()

保存或更新配置同步检查点。

```python
async def save_checkpoint(
    self,
    db: AsyncSession,
    yaml_hash: str,
    db_hash: str,
    sync_source: str,
) -> ConfigCheckpoint:
    """保存配置同步检查点"""
    try:
        stmt = select(ConfigCheckpoint).where(
            ConfigCheckpoint.config_type == "litellm_config"
        )
        result = await db.execute(stmt)
        checkpoint = result.scalars().first()

        if checkpoint is None:
            # 创建新记录
            checkpoint = ConfigCheckpoint(
                config_type="litellm_config",
                yaml_hash=yaml_hash,
                db_hash=db_hash,
                last_sync_source=sync_source,
                last_sync_time=datetime.now(timezone.utc),
                yaml_updated_at=self.get_yaml_mtime(),
                db_updated_at=datetime.now(timezone.utc),
            )
            db.add(checkpoint)
        else:
            # 更新现有记录
            checkpoint.yaml_hash = yaml_hash
            checkpoint.db_hash = db_hash
            checkpoint.last_sync_source = sync_source
            checkpoint.last_sync_time = datetime.now(timezone.utc)
            checkpoint.yaml_updated_at = self.get_yaml_mtime()
            checkpoint.db_updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(checkpoint)
        return checkpoint
    except Exception as e:
        logger.error(f"保存检查点失败：{e}")
        try:
            await db.rollback()
        except Exception as rollback_error:
            logger.error(f"回滚失败：{rollback_error}")
        raise
```

**实现细节**：
- 使用 upsert 模式（存在则更新，否则创建）
- 记录 YAML 文件修改时间戳
- 失败时显式回滚
- 回滚失败也记录日志

---

### 5. sync_yaml_to_db()

将 YAML 配置同步到数据库（只添加新模型）。

```python
async def sync_yaml_to_db(self, db: AsyncSession) -> Tuple[bool, str]:
    """
    将 YAML 配置同步到数据库（只添加新模型，不更新已有模型）

    Returns:
        Tuple[是否执行了同步，同步结果描述]
    """
    try:
        # 从 YAML 文件加载配置
        if not os.path.exists(self.config_path):
            return False, "YAML 配置文件不存在"

        with open(self.config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        model_list = yaml_config.get("model_list", [])
        if not model_list:
            return False, "YAML 配置中没有模型定义"

        # 获取数据库中的现有配置
        db_configs = await self.get_db_model_configs(db)
        db_model_names = set(db_configs.keys())

        # 需要同步的模型
        yaml_model_names = set()
        created_count = 0

        for model_dict in model_list:
            model_name = model_dict.get("model_name", "").strip()
            if not model_name:
                logger.warning("跳过无名的模型配置")
                continue
            if len(model_name) > 100:
                logger.warning(f"模型名称过长，跳过：{model_name[:50]}...")
                continue

            yaml_model_names.add(model_name)

            # 数据库优先策略：只添加新模型，不更新已有模型
            if model_name in db_model_names:
                # 数据库中已存在，跳过不更新
                continue

            # 数据库中不存在，创建新配置
            try:
                # 转换配置格式
                litellm_params = model_dict.get("litellm_params", {})
                support_types = model_dict.get("support_types", ["text"])
                if isinstance(support_types, str):
                    support_types = [support_types]

                default_rpm = model_dict.get("default_rpm", model_dict.get("rpm", 10))
                default_tpm = model_dict.get("default_tpm", model_dict.get("tpm", 100000))
                default_max_tokens = model_dict.get("default_max_tokens", model_dict.get("max_tokens", 32768))
                description = model_dict.get("description", f"模型 {model_name}")

                new_config = ModelConfig(
                    id=str(hashlib.md5(model_name.encode()).hexdigest()),
                    model_name=model_name,
                    litellm_params=litellm_params,
                    support_types=support_types,
                    default_rpm=default_rpm,
                    default_tpm=default_tpm,
                    default_max_tokens=default_max_tokens,
                    description=description,
                    is_active=True,
                )
                db.add(new_config)
                created_count += 1
            except Exception as e:
                logger.warning(f"创建模型配置失败 {model_name}: {e}")
                continue

        if created_count > 0:
            await db.commit()
            return True, f"从 YAML 同步了 {created_count} 个新模型到数据库"
        else:
            return False, "没有需要同步的新模型"

    except Exception as e:
        logger.error(f"同步 YAML 到数据库失败：{e}")
        try:
            await db.rollback()
        except Exception as rollback_error:
            logger.error(f"回滚失败：{rollback_error}")
        return False, f"同步失败：{str(e)}"
```

**实现细节**：
- 使用 `set` 进行高效的模型名称存在性检查
- 单个模型创建失败不影响其他模型
- 使用 MD5 哈希生成模型 ID（基于模型名称）
- 支持 YAML 中的别名格式（`rpm`/`default_rpm` 等）

---

### 6. sync_on_startup()

应用启动时执行配置同步。

```python
async def sync_on_startup(self, db: AsyncSession) -> str:
    """
    应用启动时执行配置同步

    Returns:
        同步结果描述
    """
    try:
        # 计算当前 YAML 哈希
        yaml_hash = self.compute_yaml_hash()
        if not yaml_hash:
            logger.warning("YAML 配置文件不存在或读取失败")
            return "YAML 配置文件不存在"

        # 获取数据库配置和哈希
        db_configs = await self.get_db_model_configs(db)
        db_hash = self.compute_db_hash(db_configs)

        # 获取检查点
        checkpoint = await self.get_checkpoint(db)

        if checkpoint is None:
            # 首次启动，执行同步
            logger.info("首次启动，执行配置同步...")
            synced, message = await self.sync_yaml_to_db(db)

            # 重新计算数据库哈希（如果执行了同步）
            if synced:
                db_configs = await self.get_db_model_configs(db)
                db_hash = self.compute_db_hash(db_configs)
                await self.save_checkpoint(db, yaml_hash, db_hash, "yaml")
                logger.info(f"启动同步完成：{message}")
                return f"首次启动同步：{message}"
            else:
                # 同步失败，不保存检查点，下次启动重试
                logger.warning(f"首次启动同步失败：{message}")
                return f"首次启动同步失败：{message}"

        # 检查 YAML 是否有更新
        yaml_changed = yaml_hash != checkpoint.yaml_hash
        # 检查数据库是否有更新
        db_changed = db_hash != checkpoint.db_hash

        if yaml_changed:
            logger.info("检测到 YAML 配置有更新，执行同步...")
            synced, message = await self.sync_yaml_to_db(db)

            # 重新计算数据库哈希
            if synced:
                db_configs = await self.get_db_model_configs(db)
                db_hash = self.compute_db_hash(db_configs)
                await self.save_checkpoint(db, yaml_hash, db_hash, "yaml")
                logger.info(f"YAML 同步完成：{message}")
                return f"YAML 更新同步：{message}"
            else:
                # YAML 有更新但没有新模型（可能只是修改了现有模型）
                await self.save_checkpoint(db, yaml_hash, db_hash, "none")
                logger.info(f"YAML 有变更但无新模型：{message}")
                return f"YAML 有变更但无新模型：{message}"

        elif db_changed:
            # 数据库有更新，保持动，只更新检查点
            logger.info("检测到数据库配置有更新，保持数据库版本")
            await self.save_checkpoint(db, yaml_hash, db_hash, "database")
            return "数据库配置已更新，保持当前版本"

        else:
            # 都没有变化
            logger.info("配置无变化，跳过同步")
            return "配置无变化"

    except Exception as e:
        logger.error(f"启动同步失败：{e}", exc_info=True)
        return f"同步失败：{str(e)}"
```

**实现细节**：
- 首次启动时执行全量同步
- YAML 变更时只添加新模型
- 数据库变更时保持数据库版本
- 任何异常都不会阻止应用启动

---

### 7. get_sync_status()

获取当前同步状态。

```python
async def get_sync_status(self, db: AsyncSession) -> dict:
    """获取当前同步状态"""
    checkpoint = await self.get_checkpoint(db)
    yaml_hash = self.compute_yaml_hash()
    db_configs = await self.get_db_model_configs(db)
    db_hash = self.compute_db_hash(db_configs)

    yaml_changed = checkpoint and yaml_hash != checkpoint.yaml_hash
    db_changed = checkpoint and db_hash != checkpoint.db_hash

    return {
        "yaml_hash_short": yaml_hash[:16] if yaml_hash else None,
        "db_hash_short": db_hash[:16] if db_hash else None,
        "last_sync_time": checkpoint.last_sync_time.isoformat() if checkpoint and checkpoint.last_sync_time else None,
        "last_sync_source": checkpoint.last_sync_source if checkpoint else None,
        "yaml_changed": yaml_changed or (checkpoint is None),
        "db_changed": db_changed,
        "is_synced": not yaml_changed and not db_changed and checkpoint is not None,
        "model_count": len(db_configs),
    }
```

**实现细节**：
- 返回哈希值的前 16 位用于展示
- `checkpoint is None` 时认为 YAML 有变更（需要首次同步）
- `is_synced` 为 `True` 表示完全同步状态

---

## 异常处理

### 异常处理策略

| 异常场景 | 处理方式 |
|----------|----------|
| YAML 文件不存在 | 返回空哈希，记录警告日志 |
| YAML 解析失败 | 抛出异常，同步失败 |
| 数据库查询失败 | 返回空结果或空字典 |
| 数据库写入失败 | 回滚事务，记录错误日志 |
| 单个模型创建失败 | 跳过该模型，继续处理其他模型 |

### 日志记录

```python
# 警告级别 - 非阻断性问题
logger.warning("跳过无名的模型配置")
logger.warning(f"模型名称过长，跳过：{model_name[:50]}...")
logger.warning(f"创建模型配置失败 {model_name}: {e}")

# 错误级别 - 阻断性问题
logger.error(f"计算数据库哈希失败：{e}")
logger.error(f"保存检查点失败：{e}")
logger.error(f"同步 YAML 到数据库失败：{e}")

# 信息级别 - 正常流程
logger.info("首次启动，执行配置同步...")
logger.info("检测到 YAML 配置有更新，执行同步...")
logger.info("配置无变化，跳过同步")
```

---

## 单例模式

服务使用全局单例模式：

```python
# 全局单例
_config_sync_service: Optional[ConfigSyncService] = None


def get_config_sync_service() -> ConfigSyncService:
    """获取配置同步服务单例"""
    global _config_sync_service
    if _config_sync_service is None:
        _config_sync_service = ConfigSyncService()
    return _config_sync_service
```

**使用方式**：

```python
# 在 API 端点中
from gateway.services.config_sync_service import get_config_sync_service

sync_service = get_config_sync_service()
status = await sync_service.get_sync_status(db)
```

---

## 边界条件处理

### 1. 空模型名称

```python
if not model_name:
    logger.warning("跳过无名的模型配置")
    continue
```

### 2. 模型名称过长

```python
if len(model_name) > 100:
    logger.warning(f"模型名称过长，跳过：{model_name[:50]}...")
    continue
```

### 3. support_types 格式兼容

```python
support_types = model_dict.get("support_types", ["text"])
if isinstance(support_types, str):
    support_types = [support_types]
```

### 4. RPM/TPM 参数别名

```python
default_rpm = model_dict.get("default_rpm", model_dict.get("rpm", 10))
default_tpm = model_dict.get("default_tpm", model_dict.get("tpm", 100000))
default_max_tokens = model_dict.get("default_max_tokens", model_dict.get("max_tokens", 32768))
```

---

## 相关文档

- [配置同步模块设计](../04.1-overview/config-sync-design.md)
- [配置同步 API](../../05-api/config-sync-api.md)
- [配置同步测试用例](../../07-test/config-sync-test.md)
