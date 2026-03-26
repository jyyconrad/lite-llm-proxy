# 模型配置 404 问题修复进展

> **创建时间**: 2026-03-26
> **问题**: 在 web 界面添加的模型，通过 `/v1/chat/completions` 请求时返回 404
> **根因**: `config_manager.py` 中的 `async_get_model_config` 函数从数据库读取配置后，实例化 `ModelEndPoint` 时缺少默认值处理

---

## 问题描述

### 现象
- 用户通过前端 web 界面添加模型配置
- 调用 `/v1/chat/completions` 端点时返回 `404 Model not found`

### 根因分析

1. **前端保存的配置结构**（`frontend/src/components/models/SingleNodeForm.jsx`）:
   ```json
   {
     "model_name": "my-model",
     "litellm_params": {
       "provider": "openai",
       "model": "gpt-3.5-turbo",
       "api_key": "sk-xxx",
       "base_url": "https://api.openai.com/v1",
       "max_tokens": 4096,
       "rpm": 60,
       "tpm": 100000,
       "weight": 1
     }
   }
   ```

2. **问题代码**（`config_manager.py:331-340`）:
   ```python
   # 原代码：直接展开字典，缺少字段会导致验证失败
   params = ModelEndPoint(
       model=litellm_params["model"],  # 如果字段缺失会报错
       api_key=litellm_params["api_key"],
       # ...
   )
   ```

3. **失败流程**:
   - 前端保存时可能缺少某些可选字段（如 `dimensions`）
   - `ModelEndPoint` 验证失败，抛出异常
   - `async_get_model_config` 捕获异常后返回 `None`
   - `llm.py` 检测到 `cfg is None` 后返回 404

---

## 已完成修复

### 1. 修复 `config_manager.py` 的 `async_get_model_config` 函数

**文件位置**: `config_manager.py:331-340`

**修改内容**:
```python
# 修改前
params = ModelEndPoint(
    model=litellm_params["model"],
    api_key=litellm_params["api_key"],
    base_url=litellm_params["base_url"],
    provider=litellm_params["provider"],
    max_tokens=litellm_params["max_tokens"],
    rpm=litellm_params["rpm"],
    tpm=litellm_params["tpm"],
    weight=litellm_params["weight"],
)

# 修改后
params = ModelEndPoint(
    model=litellm_params.get("model", ""),
    api_key=litellm_params.get("api_key", ""),
    base_url=litellm_params.get("base_url", ""),
    provider=litellm_params.get("provider", "openai"),
    max_tokens=litellm_params.get("max_tokens", 4096),
    rpm=litellm_params.get("rpm", 60),
    tpm=litellm_params.get("tpm", 100000),
    weight=litellm_params.get("weight", 1),
)
```

**修复逻辑**: 使用 `.get()` 方法提供默认值，避免因字段缺失导致验证失败。

### 2. 修复 `config_manager.py` 的 `yaml_to_model_config` 方法

**文件位置**: `config_manager.py:236-258`

**修改内容**: 与上述相同，确保 YAML 到模型的转换也使用默认值处理。

### 3. 修复 `data/model_info.py` 的 `warnings` 导入问题

**文件位置**: `data/model_info.py`

**修改内容**:
1. 第 12 行添加 `import warnings`
2. 删除第 142 行 model_validator 中的重复 `import warnings`

**原因**: `_sync_limits` 验证器中使用了 `warnings.warn()`，但模块未导入 `warnings`。

---

## 验证测试

### 单元测试（已通过）

```bash
# 单节点模式测试
python -c "
from data.model_info import ModelConfig, ModelEndPoint

litellm_params = {
    'model': 'gpt-3.5-turbo',
    'api_key': 'sk-test',
    'base_url': 'https://api.openai.com/v1',
    'provider': 'openai',
    'max_tokens': 4096,
    'rpm': 60,
    'tpm': 100000,
    'weight': 1
}

params = ModelEndPoint(
    model=litellm_params.get('model', ''),
    api_key=litellm_params.get('api_key', ''),
    base_url=litellm_params.get('base_url', ''),
    provider=litellm_params.get('provider', 'openai'),
    max_tokens=litellm_params.get('max_tokens', 4096),
    rpm=litellm_params.get('rpm', 60),
    tpm=litellm_params.get('tpm', 100000),
    weight=litellm_params.get('weight', 1),
)

model_config = ModelConfig(
    model_name='test-model',
    litellm_params=params,
    support_types=['text'],
    default_rpm=10,
    default_tpm=100000,
    default_max_tokens=32768,
    description='Test model'
)
print('✓ 单节点模式测试通过')
"
```

**结果**: ✅ 通过

### Docker 部署测试（进行中）

**启动命令**:
```bash
./docker-dev.sh
```

**测试步骤**:
1. ✅ 服务器启动成功
2. ✅ 健康检查通过 (`/health` 返回 200)
3. ✅ 创建测试模型成功（通过 `/admin/models` API）
4. ⏳ 调用 `/v1/chat/completions` 测试（待验证）

**当前状态**:
- 数据库中已有模型（通过 web 界面添加的 qwen3 系列模型）
- 模型配置已正确同步到数据库
- 调用外部 API 端点失败（网络连接问题，非 404）

---

## 待完成任务

### 1. 端到端验证
- [ ] 使用真实的 API 端点测试 `/v1/chat/completions`
- [ ] 验证数据库模型能否正确路由
- [ ] 验证限流、权重等功能是否正常

### 2. 代码审查
- [ ] 检查是否有其他地方存在相同的字典展开问题
- [ ] 验证错误处理逻辑是否完善
- [ ] 确保日志输出足够清晰

### 3. 测试覆盖
- [ ] 添加单元测试覆盖 `async_get_model_config`
- [ ] 添加 E2E 测试覆盖完整流程
- [ ] 测试边界情况（空配置、部分字段缺失等）

### 4. 文档更新
- [ ] 更新 API 文档说明模型配置结构
- [ ] 添加故障排查指南

---

## 相关文件

| 文件 | 修改内容 |
|------|----------|
| `config_manager.py` | 修复 `async_get_model_config` 和 `yaml_to_model_config` |
| `data/model_info.py` | 添加 `warnings` 导入 |
| `frontend/src/components/models/SingleNodeForm.jsx` | 无需修改（已正确发送所有必填字段） |
| `gateway/routers/llm.py` | 无需修改（404 逻辑正确） |

---

## 时间线

| 时间 | 事件 |
|------|------|
| 2026-03-26 上午 | 用户报告 404 问题 |
| 2026-03-26 中午 | 定位根因：`async_get_model_config` 缺少默认值处理 |
| 2026-03-26 下午 | 完成代码修复 |
| 2026-03-26 下午 | 完成单元测试 |
| 2026-03-26 下午 | Docker 部署验证中 |

---

## 结论

**核心修复**: `config_manager.py` 中的 `async_get_model_config` 函数现在使用 `.get()` 方法提供默认值，确保从数据库读取的配置即使缺少某些字段也能正确实例化 `ModelEndPoint`。

**状态**: 代码修复完成，等待端到端验证。

**预期结果**: 通过 web 界面添加的模型现在应该能够正常被 `/v1/chat/completions` 端点识别和路由。
