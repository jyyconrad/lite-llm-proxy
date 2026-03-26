# 模型配置表单详细设计

> **版本**: v1.0
> **创建日期**: 2026-03-25
> **状态**: 实施中

---

## 需求概述

将现有的 JSON 编辑器替换为用户友好的表单界面，支持单节点和多节点两种模式配置模型终端节点。

---

## 数据结构

### 单节点模式
```json
{
  "model": "gpt-4-turbo",
  "api_key": "${OPENAI_API_KEY}",
  "base_url": "https://api.openai.com/v1",
  "max_tokens": 8192,
  "rpm": 60,
  "tpm": 100000,
  "weight": 1,
  "provider": "openai"
}
```

### 多节点模式
```json
{
  "endpoints": [
    {
      "model": "gpt-4-turbo",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1",
      "max_tokens": 8192,
      "rpm": 60,
      "tpm": 100000,
      "weight": 1,
      "provider": "openai"
    },
    {
      "model": "claude-3-opus",
      "api_key": "${ANTHROPIC_API_KEY}",
      "base_url": "https://api.anthropic.com",
      "max_tokens": 4096,
      "rpm": 30,
      "tpm": 50000,
      "weight": 1,
      "provider": "anthropic"
    }
  ]
}
```

---

## 组件设计

### 1. SingleNodeForm 组件

**文件**: `frontend/src/components/models/SingleNodeForm.jsx`

**职责**: 单个终端节点配置表单

**Props**:
- `value`: object - 当前节点值
- `onChange`: function - 值变化回调
- `errors`: object - 验证错误
- `disabled`: boolean - 是否禁用

**字段**:
| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| provider | select | 是 | 'openai' | 供应商选择 |
| model | text | 是 | '' | 模型名称 |
| api_key | password | 是 | '' | API Key |
| base_url | url | 是 | 根据 provider 自动填充 | Base URL |
| max_tokens | number | 否 | 4096 | 最大 Token 数 |
| rpm | number | 否 | 60 | 每分钟请求数 |
| tpm | number | 否 | 100000 | 每分钟 Token 数 |
| weight | number | 否 | 1 | 权重 |

**供应商配置**:
```javascript
const PROVIDER_CONFIG = {
  openai: {
    label: 'OpenAI',
    defaultBaseUrl: 'https://api.openai.com/v1',
    placeholder: 'sk-...'
  },
  anthropic: {
    label: 'Anthropic',
    defaultBaseUrl: 'https://api.anthropic.com',
    placeholder: 'sk-ant-...'
  },
  azure: {
    label: 'Azure',
    defaultBaseUrl: 'https://{resource}.openai.azure.com',
    placeholder: 'Azure API Key'
  },
  gemini: {
    label: 'Gemini',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com',
    placeholder: 'Google API Key'
  },
  ollama: {
    label: 'Ollama',
    defaultBaseUrl: 'http://localhost:11434',
    placeholder: 'Ollama 模型名称'
  },
  local: {
    label: '本地部署',
    defaultBaseUrl: 'http://localhost:8000',
    placeholder: '本地 API Key'
  },
  custom: {
    label: '自定义',
    defaultBaseUrl: '',
    placeholder: 'API Key'
  }
}
```

### 2. MultiNodeForm 组件

**文件**: `frontend/src/components/models/MultiNodeForm.jsx`

**职责**: 多终端节点配置表单

**Props**:
- `value`: array - 节点数组
- `onChange`: function - 值变化回调
- `errors`: object - 验证错误

**功能**:
- 动态添加/删除节点
- 节点上移/下移排序
- 每个节点使用 SingleNodeForm 的简化版

**状态**:
```javascript
const [nodes, setNodes] = useState(value?.endpoints || [createDefaultNode()])
```

**操作**:
- `addNode()`: 添加新节点
- `removeNode(index)`: 删除指定节点
- `moveNodeUp(index)`: 节点上移
- `moveNodeDown(index)`: 节点下移
- `updateNode(index, data)`: 更新节点数据

### 3. Models.jsx 修改

**新增状态**:
```javascript
const [formMode, setFormMode] = useState('single') // 'single' | 'multi'
const [nodeData, setNodeData] = useState({}) // 单节点数据
const [multiNodeData, setMultiNodeData] = useState({ endpoints: [] }) // 多节点数据
```

**新增函数**:
- `convertToFormData(litellmParams)`: 将 API 数据转换为表单数据
- `convertToSubmitData()`: 将表单数据转换为 API 提交数据
- `handleFormModeChange(mode)`: 切换单/多节点模式

---

## UI 布局

### SingleNodeForm 布局
```
┌─────────────────────────────────────────┐
│  供应商选择  [OpenAI ▼]                 │
├─────────────────────────────────────────┤
│  模型名称 *  [gpt-4-turbo         ]     │
│  API Key *   [sk-...              ] 👁  │
│  Base URL *  [https://api.openai... ]   │
├─────────────────────────────────────────┤
│  高级设置                                │
│  ┌─────────────────────────────────┐    │
│  │ Max Tokens  [8192]              │    │
│  │ RPM         [60   ]             │    │
│  │ TPM         [100000]            │    │
│  │ Weight      [1    ]             │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### MultiNodeForm 布局
```
┌─────────────────────────────────────────┐
│  节点 1                          [-] [↑] │
│  ┌─────────────────────────────────┐    │
│  │ SingleNodeForm                  │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  节点 2                          [-] [↓] │
│  ┌─────────────────────────────────┐    │
│  │ SingleNodeForm                  │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  [+ 添加节点]                           │
└─────────────────────────────────────────┘
```

---

## 数据转换逻辑

### API 数据 → 表单数据
```javascript
function convertToFormData(litellmParams) {
  if (!litellmParams) return { mode: 'single', data: {} }

  // 检测是否为多节点
  if (litellmParams.endpoints && Array.isArray(litellmParams.endpoints)) {
    return {
      mode: 'multi',
      data: { endpoints: litellmParams.endpoints }
    }
  }

  // 单节点
  return {
    mode: 'single',
    data: {
      provider: litellmParams.provider || 'openai',
      model: litellmParams.model || '',
      api_key: litellmParams.api_key || '',
      base_url: litellmParams.base_url || '',
      max_tokens: litellmParams.max_tokens || 4096,
      rpm: litellmParams.rpm || 60,
      tpm: litellmParams.tpm || 100000,
      weight: litellmParams.weight || 1
    }
  }
}
```

### 表单数据 → API 提交数据
```javascript
function convertToSubmitData(formMode, nodeData, multiNodeData) {
  if (formMode === 'multi') {
    return {
      endpoints: multiNodeData.endpoints.map(ep => ({
        ...ep,
        provider: ep.provider || 'openai'
      }))
    }
  }

  return {
    ...nodeData,
    provider: nodeData.provider || 'openai'
  }
}
```

---

## 验证规则

### SingleNodeForm 验证
```javascript
function validateNode(node) {
  const errors = {}

  if (!node.model?.trim()) {
    errors.model = '模型名称不能为空'
  }

  if (!node.api_key?.trim()) {
    errors.api_key = 'API Key 不能为空'
  }

  if (!node.base_url?.trim()) {
    errors.base_url = 'Base URL 不能为空'
  } else if (!isValidUrl(node.base_url)) {
    errors.base_url = '请输入有效的 URL'
  }

  if (node.max_tokens && node.max_tokens <= 0) {
    errors.max_tokens = 'Max Tokens 必须大于 0'
  }

  if (node.rpm && node.rpm <= 0) {
    errors.rpm = 'RPM 必须大于 0'
  }

  if (node.tpm && node.tpm <= 0) {
    errors.tpm = 'TPM 必须大于 0'
  }

  if (node.weight && node.weight < 0) {
    errors.weight = 'Weight 必须大于等于 0'
  }

  return errors
}
```

---

## 测试策略

### 单元测试
1. SingleNodeForm 组件测试
   - 渲染测试：所有字段正确显示
   - 供应商切换：Base URL 自动更新
   - 表单验证：必填字段验证
   - 值变化：onChange 回调正确触发

2. MultiNodeForm 组件测试
   - 添加节点测试
   - 删除节点测试
   - 节点排序测试
   - 数据传递测试

### 集成测试
1. 表单提交测试
   - 单节点模式提交
   - 多节点模式提交
   - 数据转换正确性

2. 编辑回显测试
   - 单节点数据回显
   - 多节点数据回显

### E2E 测试
1. 创建模型流程
   - 选择单节点模式
   - 填写表单
   - 提交保存
   - 验证列表显示

2. 编辑模型流程
   - 打开编辑
   - 修改数据
   - 保存验证

---

## 实施步骤

1. 创建 `frontend/src/components/models/` 目录
2. 创建 `SingleNodeForm.jsx` 组件（含测试）
3. 创建 `MultiNodeForm.jsx` 组件（含测试）
4. 修改 `Models.jsx` 集成新组件
5. 运行测试验证
6. 手动测试验证

---

## 相关文件

- `frontend/src/pages/Models.jsx` - 主页面
- `frontend/src/services/api.js` - API 服务
