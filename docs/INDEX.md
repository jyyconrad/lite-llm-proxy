# 配置同步功能文档索引

**最后更新**：2026-03-20
**版本**：v1.0.0

---

## 文档导航

| 文档类型 | 文档名称 | 路径 |
|----------|----------|------|
| API 文档 | [配置同步 API](./05-api/config-sync-api.md) | `docs/05-api/config-sync-api.md` |
| 数据库设计 | [ConfigCheckpoint 表设计](./06-database/config-checkpoint-table.md) | `docs/06-database/config-checkpoint-table.md` |
| 模块设计 | [配置同步模块设计](./04-design/04.1-overview/config-sync-design.md) | `docs/04-design/04.1-overview/config-sync-design.md` |
| 详细设计 | [ConfigSyncService 详细设计](./04-design/04.2-detail/config-sync-detail.md) | `docs/04-design/04.2-detail/config-sync-detail.md` |
| 测试用例 | [配置同步测试用例](./07-test/config-sync-test.md) | `docs/07-test/config-sync-test.md` |
| 变更日志 | [v1.0.0 变更日志](./09-changelog/v1.0.0.md) | `docs/09-changelog/v1.0.0.md` |

---

## 功能概述

配置同步功能用于在应用启动时自动同步 `litellm_config.yaml` 配置文件与数据库中的模型配置。

### 核心特性

- **数据库优先**：数据库配置始终优先，避免 YAML 意外覆盖生产配置
- **增量同步**：只添加新模型，不更新已有模型配置
- **自动检测**：通过 SHA256 哈希自动检测配置变更
- **检查点机制**：记录同步状态，支持重启后断点续同步

### 同步策略

```
YAML 变更？ ──是──> 只添加新模型到数据库
   │
   └─ 否 ──> 数据库变更？ ──是──> 保持数据库版本
                    │
                    └─ 否 ──> 跳过同步
```

---

## 快速开始

### 查看同步状态

```bash
curl -X GET "http://localhost:8000/admin/config/sync-status" \
  -H "Authorization: Bearer sk-your-api-key"
```

### 手动触发同步

```bash
curl -X POST "http://localhost:8000/admin/config/sync" \
  -H "Authorization: Bearer sk-your-api-key"
```

---

## 核心代码文件

| 文件 | 路径 | 说明 |
|------|------|------|
| `config_sync_service.py` | `gateway/services/config_sync_service.py` | 配置同步服务主类 |
| `tables.py` | `data/tables.py` | ConfigCheckpoint ORM 模型 |
| `admin.py` | `gateway/routers/admin.py` | 同步 API 端点 |

---

## 文档结构说明

```
docs/
├── 05-api/                        # API 文档
│   └── config-sync-api.md         # 同步 API 接口定义
├── 06-database/                   # 数据库设计
│   └── config-checkpoint-table.md # 检查点表设计
├── 04-design/
│   ├── 04.1-overview/            # 模块设计
│   │   └── config-sync-design.md  # 同步模块设计
│   └── 04.2-detail/              # 详细设计
│       └── config-sync-detail.md  # 服务类详细实现
├── 07-test/                       # 测试用例
│   └── config-sync-test.md        # 单元/集成/边界测试
└── 09-changelog/                  # 变更日志
    └── v1.0.0.md                  # v1.0.0 版本变更
```

---

## 相关文档

- [项目 README](../../README.md)
- [API 文档总览](./05-api/README.md)（待创建）
- [数据库设计总览](./06-database/README.md)（待创建）
