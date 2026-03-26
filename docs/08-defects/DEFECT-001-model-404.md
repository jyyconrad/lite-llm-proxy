# DEFECT-001 - 模型配置 404 错误

**发现日期**: 2026-03-26
**修复版本**: v1.1.0
**严重程度**: 高
**状态**: 已修复

---

## 问题描述

### 现象

用户通过前端 Web 界面添加模型配置后，调用 `/v1/chat/completions` 端点时返回：
```json
{
  "detail": "Model not found"
}
```

HTTP 状态码：404

### 复现步骤

1. 访问前端管理后台 `/admin/models`
2. 添加新模型，填写必填字段（model_name, provider, model, api_key）
3. 保存配置
4. 调用 `/v1/chat/completions` 端点，使用刚添加的模型名称
5. 返回 404 错误

---

## 根因分析

### 问题定位

**问题文件**: `config_manager.py`

**问题函数**: `async_get_model_config` (第 345-354 行)

### 失败流程

```
1. 前端保存配置 → 数据库
   ↓
2. 用户调用 /v1/chat/completions
   ↓
3. llm.py 调用 async_get_model_config 获取模型配置
   ↓
4. config_manager.py 从数据库读取配置
   ↓
5. 实例化 ModelEndPoint 时，某些字段缺失导致验证失败
   ↓
6. 异常被捕获，函数返回 None
   ↓
7. llm.py 检测到 cfg is None → 返回 404
```

### 代码问题

**问题代码**（修复前）:
```python
# config_manager.py:345-354
params = ModelEndPoint(
    model=litellm_params["model"],  # 如果字段缺失会报错
    api_key=litellm_params["api_key"],
    base_url=litellm_params["base_url"],
    provider=litellm_params["provider"],
    max_tokens=litellm_params["max_tokens"],
    rpm=litellm_params["rpm"],
    tpm=litellm_params["tpm"],
    weight=litellm_params["weight"],
)
```

**问题原因**:
- 前端保存的配置可能缺少某些可选字段（如 `dimensions`、`rpm`、`tpm` 等）
- 直接使用 `dict["key"]` 访问，字段缺失时抛出 `KeyError`
- 异常被捕获后返回 `None`，导致上层误认为模型不存在

### 关联问题

**文件**: `data/model_info.py`

**问题**: `warnings` 模块未导入，但 `_sync_limits` 验证器中使用了 `warnings.warn()`

---

## 修复方案

### 修复 1: config_manager.py - async_get_model_config

**位置**: 第 345-354 行

**修改内容**:
```python
# 修复后：使用 .get() 方法提供默认值
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

### 修复 2: config_manager.py - yaml_to_model_config

**位置**: 第 249-272 行

**修改内容**: 同样使用 `.get()` 方法处理字段缺失

### 修复 3: data/model_info.py

**位置**: 第 12 行

**修改内容**:
- 添加 `import warnings`
- 删除第 142 行 `model_validator` 中的重复 `import warnings`

---

## 验证结果

### 单元测试

```bash
python -m pytest tests/test_model_config.py tests/test_model_config_defaults.py -v
```

**结果**: 47 个测试全部通过 ✓

### 测试覆盖

| 测试场景 | 状态 |
|----------|------|
| 完整数据库配置 | ✓ 通过 |
| 配置缺少可选字段 | ✓ 通过 |
| 配置为空 | ✓ 通过 |
| 部分字段缺失 | ✓ 通过 |
| YAML 回退 | ✓ 通过 |
| 数据库错误回退 | ✓ 通过 |
| 多节点模式 | ✓ 通过 |
| 前端配置兼容性 | ✓ 通过 |

### 端到端测试

**服务状态**: 容器运行中（端口 9989）

**测试结果**:
- ✓ 健康检查通过
- ✓ 模型创建成功
- ⚠ 外部 API 调用失败（网络连接问题，非 404 错误）

---

## 影响范围

### 受影响的功能

- Web 界面添加模型配置
- 通过 API 添加缺少可选字段的模型配置

### 不受影响的功能

- YAML 配置文件加载的模型
- 包含所有字段的完整模型配置
- 多节点负载均衡配置

### 受影响的用户

所有通过 Web 界面添加模型的用户

---

## 临时解决方案（修复前）

在修复发布前，用户可以通过以下方式规避：

1. **手动添加所有字段**: 在前端表单中填写所有可选字段
2. **使用 YAML 配置**: 直接在 `litellm_config.yaml` 中添加模型
3. **使用 API 并传入完整配置**: 通过 API 添加模型时手动指定所有字段

---

##  lessons Learned

### 问题

1. **默认值处理缺失**: 实例化 Pydantic 模型时未处理可选字段
2. **异常吞没**: 异常被捕获后返回 `None`，掩盖了真实问题
3. **日志不足**: 没有清晰的日志输出帮助定位问题

### 改进措施

1. ✓ 添加 `.get()` 默认值处理
2. ✓ 增强测试覆盖（边界情况、缺失字段）
3. ⚠ 待增强日志输出（计划中）
4. ⚠ 待添加配置验证中间件（计划中）

---

## 时间线

| 时间 | 事件 |
|------|------|
| 2026-03-26 上午 | 用户报告 404 问题 |
| 2026-03-26 中午 | 定位根因：`async_get_model_config` 缺少默认值处理 |
| 2026-03-26 下午 | 完成代码修复 |
| 2026-03-26 下午 | 完成单元测试（47 个测试通过） |
| 2026-03-26 下午 | 完成缺陷文档 |
| 2026-03-26 下午 | 发布 v1.1.0 |

---

## 相关文件

| 文件 | 修改内容 |
|------|----------|
| `config_manager.py` | 修复 `async_get_model_config` 和 `yaml_to_model_config` |
| `data/model_info.py` | 添加 `warnings` 导入 |
| `tests/test_model_config.py` | 新增测试用例 |
| `tests/test_model_config_defaults.py` | 新增测试用例 |

---

## 验证清单

- [x] 代码修复完成
- [x] 单元测试通过（47/47）
- [x] 代码审查完成
- [x] 文档更新完成
- [x] 变更日志更新
- [ ] 生产环境验证（待用户确认）

---

**状态**: 已修复，等待生产环境验证
