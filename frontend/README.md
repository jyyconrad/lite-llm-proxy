# Lite LLM Proxy — Frontend

This folder contains a minimal React + Vite frontend scaffold for the admin UI.

Quick start:

1. cd frontend
2. npm install
3. npm run dev

The app will run at http://localhost:5173 by default and attempts to fetch `/stats/overview`.

Adjust API base paths if your backend is served from a different prefix.
# LiteLLM 前端界面

## 概述

这是LiteLLM API网关的前端管理面板，基于API文档进行了全面更新，确保与后端API完全兼容。

## 主要功能

### 1. 用户认证
- **登录**: 使用API密钥进行Bearer token认证
- **注册**: 创建新用户账户
- **自动识别用户角色**: 自动检测管理员和普通用户权限

### 2. 仪表盘
- **系统概览统计**: 显示总调用次数、令牌数、活跃用户和总费用
- **模型使用图表**: 可视化展示各模型的使用情况
- **最近活动**: 显示最近的API调用记录

### 3. 用户管理 (仅管理员)
- **创建用户**: 支持创建新用户并自动生成API密钥
- **用户角色管理**: 支持设置用户和管理员角色
- **预算和速率限制**: 可配置预算限制、RPM和TPM限制

### 4. 使用统计
- **个人使用统计**: 显示当前用户的使用情况
- **模型过滤器**: 按模型筛选使用数据
- **使用趋势图表**: 可视化展示时间维度的使用趋势

### 5. 设置
- **个人设置**: 查看和重新生成API密钥
- **系统设置**: 管理员专属的系统配置选项

## API兼容性

前端已根据API文档更新了所有端点调用：

### 系统接口
- `GET /health` - 健康检查
- `GET /models` - 获取可用模型列表

### 管理接口
- `POST /admin/users` - 创建用户
- `POST /admin/api-keys` - 创建API密钥
- `GET /admin/stats/overview` - 系统概览统计
- `GET /admin/stats/model-usage` - 模型使用统计
- `GET /admin/stats/recent-activity` - 最近活动记录
- `GET /admin/stats/user/{user_id}` - 用户详细统计
- `GET /admin/stats/usage` - 用户自服务统计
- `GET /admin/stats/usage-trend` - 使用趋势统计

## 技术实现

- **前端框架**: 原生JavaScript + HTML5 + CSS3
- **图表库**: Chart.js 用于数据可视化
- **认证方式**: Bearer token认证
- **响应式设计**: 支持桌面端和移动端

## 启动方式

```bash
# 进入前端目录
cd frontend

# 启动HTTP服务器
python3 -m http.server 8080

# 访问地址
http://localhost:8080
```

## 使用说明

1. **首次使用**: 使用有效的API密钥登录
2. **管理员功能**: 管理员账户可以访问用户管理和系统设置
3. **创建用户**: 管理员可以创建新用户并获取生成的API密钥
4. **查看统计**: 所有用户都可以查看个人使用统计，管理员可以查看系统级统计

## 注意事项

- 所有API请求都需要Bearer token认证
- 用户管理功能需要管理员权限
- 某些统计功能需要后端API支持相应的端点
- 建议在支持现代JavaScript的浏览器中使用