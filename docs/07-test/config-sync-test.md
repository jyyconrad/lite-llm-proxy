# 配置同步测试用例文档

**最后更新**：2026-03-20
**版本**：v1.0.0

---

## 概述

本文档描述配置同步功能的测试用例，包括单元测试、集成测试和边界测试。

### 测试范围

| 模块 | 测试类型 | 优先级 |
|------|----------|--------|
| `ConfigSyncService` 类 | 单元测试 | P0 |
| 哈希计算方法 | 单元测试 | P0 |
| 检查点管理 | 单元测试 | P1 |
| YAML 到数据库同步 | 集成测试 | P0 |
| 启动同步流程 | 集成测试 | P0 |
| API 端点 | 集成测试 | P1 |
| 边界条件 | 边界测试 | P2 |

---

## 单元测试用例

### 1. compute_yaml_hash() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-001 | YAML 文件存在且有效 | `litellm_config.yaml` 存在 | 返回 64 位十六进制哈希字符串 |
| UT-002 | YAML 文件不存在 | 文件被删除或路径错误 | 返回空字符串 `""` |
| UT-003 | YAML 文件内容为空 | 文件存在但内容为空 | 返回空内容的 SHA256 哈希 |
| UT-004 | 相同内容哈希一致 | 两次读取同一文件 | 两次返回相同哈希值 |
| UT-005 | 不同内容哈希不同 | 修改文件内容后读取 | 返回不同的哈希值 |

**测试代码示例**：

```python
def test_compute_yaml_hash_file_exists():
    """UT-001: YAML 文件存在且有效"""
    service = ConfigSyncService(config_path="./test_data/valid_config.yaml")
    hash_result = service.compute_yaml_hash()

    assert len(hash_result) == 64
    assert all(c in '0123456789abcdef' for c in hash_result)


def test_compute_yaml_hash_file_not_exists():
    """UT-002: YAML 文件不存在"""
    service = ConfigSyncService(config_path="./nonexistent.yaml")
    hash_result = service.compute_yaml_hash()

    assert hash_result == ""
```

---

### 2. compute_db_hash() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-011 | 空配置字典 | 输入空字典 `{}` | 返回空字典的 SHA256 哈希 |
| UT-012 | 单个模型配置 | 输入包含一个模型的字典 | 返回正确的哈希值 |
| UT-013 | 多个模型配置 | 输入包含多个模型的字典 | 返回正确的哈希值 |
| UT-014 | 模型顺序不影响哈希 | 相同模型不同顺序输入 | 返回相同哈希值 |
| UT-015 | 配置变更哈希改变 | 修改任一配置字段 | 返回不同的哈希值 |

**测试代码示例**：

```python
def test_compute_db_hash_order_independent():
    """UT-014: 模型顺序不影响哈希"""
    service = ConfigSyncService()

    config1 = create_mock_model_config("model-a")
    config2 = create_mock_model_config("model-b")

    db_configs_1 = {"model-a": config1, "model-b": config2}
    db_configs_2 = {"model-b": config2, "model-a": config1}

    hash_1 = service.compute_db_hash(db_configs_1)
    hash_2 = service.compute_db_hash(db_configs_2)

    assert hash_1 == hash_2
```

---

### 3. get_checkpoint() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-021 | 检查点存在 | 数据库中有检查点记录 | 返回 `ConfigCheckpoint` 对象 |
| UT-022 | 检查点不存在 | 数据库为空 | 返回 `None` |
| UT-023 | 数据库连接失败 | 数据库不可用 | 返回 `None`，不抛出异常 |

---

### 4. save_checkpoint() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-031 | 创建新检查点 | 数据库中无记录 | 创建新记录并返回 |
| UT-032 | 更新现有检查点 | 数据库中已有记录 | 更新记录并返回 |
| UT-033 | 数据库提交失败 | 数据库约束冲突 | 回滚事务并抛出异常 |

---

### 5. sync_yaml_to_db() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-041 | YAML 无模型 | `model_list` 为空 | 返回 `(False, "YAML 配置中没有模型定义")` |
| UT-042 | 所有模型已存在 | 数据库中已有全部模型 | 返回 `(False, "没有需要同步的新模型")` |
| UT-043 | 有新模型需要添加 | YAML 有新模型 | 返回 `(True, "从 YAML 同步了 N 个新模型到数据库")` |
| UT-044 | 模型名称为空 | YAML 中有无名配置 | 跳过该配置，继续处理其他模型 |
| UT-045 | 模型名称过长 | 名称超过 100 字符 | 跳过该配置，记录警告日志 |
| UT-046 | support_types 为字符串 | YAML 中为字符串格式 | 自动转换为列表 |
| UT-047 | 使用 rpm 别名 | YAML 中使用 `rpm` 而非 `default_rpm` | 正确映射到 `default_rpm` 字段 |

**测试代码示例**：

```python
@pytest.mark.asyncio
async def test_sync_yaml_to_db_new_models():
    """UT-043: 有新模型需要添加"""
    async with get_test_session() as db:
        service = ConfigSyncService(config_path="./test_data/new_models.yaml")

        synced, message = await service.sync_yaml_to_db(db)

        assert synced == True
        assert "同步了" in message
        assert "个新模型" in message


@pytest.mark.asyncio
async def test_sync_yaml_to_db_support_types_string():
    """UT-046: support_types 为字符串"""
    async with get_test_session() as db:
        service = ConfigSyncService(config_path="./test_data/string_support_types.yaml")

        await service.sync_yaml_to_db(db)

        # 验证转换后的配置
        config = await get_model_config(db, "test-model")
        assert config.support_types == ["text", "image"]
```

---

### 6. sync_on_startup() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-051 | 首次启动 | 检查点不存在 | 执行全量同步，保存检查点 |
| UT-052 | YAML 有更新 | YAML 哈希与检查点不同 | 同步新模型，更新检查点 |
| UT-053 | 数据库有更新 | 数据库哈希与检查点不同 | 保持数据库版本，更新检查点 |
| UT-054 | 无变更 | 哈希值均匹配 | 跳过同步，返回"配置无变化" |
| UT-055 | YAML 文件不存在 | 配置文件缺失 | 返回"YAML 配置文件不存在" |

**测试代码示例**：

```python
@pytest.mark.asyncio
async def test_sync_on_startup_first_time():
    """UT-051: 首次启动"""
    async with get_test_session() as db:
        # 确保检查点不存在
        await clear_checkpoints(db)

        service = ConfigSyncService(config_path="./test_data/valid_config.yaml")
        result = await service.sync_on_startup(db)

        assert "首次启动同步" in result

        # 验证检查点已保存
        checkpoint = await service.get_checkpoint(db)
        assert checkpoint is not None


@pytest.mark.asyncio
async def test_sync_on_startup_no_changes():
    """UT-054: 无变更"""
    async with get_test_session() as db:
        service = ConfigSyncService(config_path="./test_data/valid_config.yaml")

        # 先执行一次同步
        await service.sync_on_startup(db)

        # 再次执行，应无变化
        result = await service.sync_on_startup(db)

        assert "配置无变化" in result
```

---

### 7. get_sync_status() 测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| UT-061 | 已同步状态 | YAML 和数据库哈希一致 | `is_synced=True`, `yaml_changed=False`, `db_changed=False` |
| UT-062 | YAML 有变更 | YAML 哈希与检查点不同 | `yaml_changed=True`, `is_synced=False` |
| UT-063 | 数据库有变更 | 数据库哈希与检查点不同 | `db_changed=True`, `is_synced=False` |
| UT-064 | 无检查点 | 首次启动 | `yaml_changed=True`（需要首次同步） |
| UT-065 | 返回模型数量 | 数据库有 N 个模型 | `model_count=N` |

**测试代码示例**：

```python
@pytest.mark.asyncio
async def test_get_sync_status_synced():
    """UT-061: 已同步状态"""
    async with get_test_session() as db:
        service = ConfigSyncService(config_path="./test_data/valid_config.yaml")

        # 先执行同步
        await service.sync_on_startup(db)

        # 获取状态
        status = await service.get_sync_status(db)

        assert status["is_synced"] == True
        assert status["yaml_changed"] == False
        assert status["db_changed"] == False
        assert status["yaml_hash_short"] is not None
        assert status["db_hash_short"] is not None
```

---

## 集成测试用例

### 1. API 端点测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| IT-001 | 获取同步状态 - 管理员 | 有效管理员 API 密钥 | 返回 200，包含同步状态 JSON |
| IT-002 | 获取同步状态 - 未认证 | 无 API 密钥 | 返回 401 Unauthorized |
| IT-003 | 获取同步状态 - 非管理员 | 普通用户 API 密钥 | 返回 403 Forbidden |
| IT-004 | 触发同步 - 管理员 | 有效管理员 API 密钥 | 返回 200，包含同步结果 |
| IT-005 | 触发同步 - YAML 有新模型 | YAML 包含新模型 | 同步成功，数据库新增模型 |
| IT-006 | 触发同步 - 无新模型 | YAML 与数据库一致 | 返回"没有需要同步的新模型" |

**测试代码示例**：

```python
@pytest.mark.asyncio
async def test_get_sync_status_api_admin():
    """IT-001: 获取同步状态 - 管理员"""
    admin_api_key = get_admin_api_key()

    async with AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/admin/config/sync-status",
            headers={"Authorization": f"Bearer {admin_api_key}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_synced" in data
        assert "model_count" in data


@pytest.mark.asyncio
async def test_trigger_sync_api():
    """IT-005: 触发同步 - YAML 有新模型"""
    admin_api_key = get_admin_api_key()

    # 先修改 YAML 添加新模型
    add_model_to_yaml("new-test-model")

    async with AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/admin/config/sync",
            headers={"Authorization": f"Bearer {admin_api_key}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "同步了" in data["result"]
```

---

### 2. 端到端流程测试

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| IT-011 | 完整同步流程 | 全新环境启动应用 | 配置正确同步，应用正常运行 |
| IT-012 | 配置变更后重启 | 修改 YAML 后重启应用 | 检测到变更并同步新模型 |
| IT-013 | 数据库独立变更 | 通过 API 修改配置后重启 | 保持数据库版本，不同步 YAML |

---

## 边界测试用例

### 1. 文件边界

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| BT-001 | YAML 文件 0 字节 | 空文件 | 返回空内容哈希或错误 |
| BT-002 | YAML 文件超大 | 文件>10MB | 正常处理或超时 |
| BT-003 | YAML 语法错误 | 无效的 YAML 格式 | 抛出解析异常 |
| BT-004 | 文件权限不足 | 文件不可读 | 返回空哈希，记录日志 |

### 2. 数据库边界

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| BT-011 | 数据库连接超时 | 数据库不可达 | 返回空结果，不崩溃 |
| BT-012 | 检查点表不存在 | 表被删除 | 返回 `None`，视为首次启动 |
| BT-013 | 模型配置表为空 | 无现有配置 | 正常同步所有模型 |

### 3. 数据边界

| 用例 ID | 测试场景 | 前置条件 | 预期结果 |
|---------|----------|----------|----------|
| BT-021 | 模型名称含特殊字符 | 名称含 `-`、`_`、`.` 等 | 正常处理 |
| BT-022 | 模型名称含中文 | 名称为中文字符 | 正常处理，UTF-8 编码 |
| BT-023 | 模型数量极大 | YAML 含 1000+ 模型 | 分批处理，不超时 |
| BT-024 | litellm_params 为空 | 参数为空对象 | 使用默认值 |
| BT-025 | support_types 缺失 | YAML 无此字段 | 使用默认值 `["text"]` |

**测试代码示例**：

```python
@pytest.mark.asyncio
async def test_sync_with_special_characters_in_name():
    """BT-021: 模型名称含特殊字符"""
    async with get_test_session() as db:
        service = ConfigSyncService(config_path="./test_data/special_chars.yaml")

        synced, message = await service.sync_yaml_to_db(db)

        assert synced == True

        # 验证特殊字符名称的模型已创建
        config = await get_model_config(db, "gpt-4-turbo-preview")
        assert config is not None


@pytest.mark.asyncio
async def test_sync_with_chinese_model_name():
    """BT-022: 模型名称含中文"""
    async with get_test_session() as db:
        service = ConfigSyncService(config_path="./test_data/chinese_names.yaml")

        synced, message = await service.sync_yaml_to_db(db)

        assert synced == True

        # 验证中文名称的模型已创建
        config = await get_model_config(db, "通义千问")
        assert config is not None
        assert config.model_name == "通义千问"
```

---

## 性能测试用例

| 用例 ID | 测试场景 | 性能指标 | 预期结果 |
|---------|----------|----------|----------|
| PT-001 | 百模型同步 | 100 个模型 | 同步时间 < 5 秒 |
| PT-002 | 千模型同步 | 1000 个模型 | 同步时间 < 30 秒 |
| PT-003 | 哈希计算延迟 | 大配置文件 | 计算时间 < 100ms |
| PT-004 | 并发同步请求 | 同时触发多次同步 | 幂等处理，无数据损坏 |

---

## 测试数据准备

### YAML 测试文件

```yaml
# test_data/valid_config.yaml
model_list:
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: os.environ/OPENAI_API_KEY
    support_types: ["text"]
    default_rpm: 10
    default_tpm: 100000
    default_max_tokens: 32768
    description: "OpenAI GPT-4"

  - model_name: claude-3
    litellm_params:
      model: anthropic/claude-3-opus-20240229
      api_key: os.environ/ANTHROPIC_API_KEY
    support_types: ["text", "image"]
    default_rpm: 20
    default_tpm: 200000
    default_max_tokens: 64000
    description: "Anthropic Claude 3"
```

### 数据库测试数据

```python
# 创建模拟模型配置
def create_mock_model_config(model_name: str) -> ModelConfig:
    return ModelConfig(
        id=str(uuid.uuid4()),
        model_name=model_name,
        litellm_params={"model": f"test/{model_name}"},
        support_types=["text"],
        default_rpm=10,
        default_tpm=100000,
        default_max_tokens=32768,
        description=f"Test model {model_name}",
        is_active=True,
    )
```

---

## 测试执行

### 运行单元测试

```bash
# 运行所有配置同步单元测试
pytest tests/unit/config_sync_test.py -v

# 运行特定测试用例
pytest tests/unit/config_sync_test.py::test_compute_yaml_hash_file_exists -v

# 带覆盖率报告
pytest tests/unit/config_sync_test.py --cov=gateway/services/config_sync_service --cov-report=html
```

### 运行集成测试

```bash
# 启动测试数据库
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
pytest tests/integration/config_sync_api_test.py -v

# 清理测试数据
docker-compose -f docker-compose.test.yml down -v
```

---

## 相关文档

- [配置同步模块设计](../04-design/04.1-overview/config-sync-design.md)
- [配置同步详细设计](../04-design/04.2-detail/config-sync-detail.md)
- [配置同步 API](../../05-api/config-sync-api.md)
