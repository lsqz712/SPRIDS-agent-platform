# SPRIDS 系统 API 设计文档

> 面向 SMT 生产线的 PCB 缺陷实时检测系统  
> 基于 FastAPI + YOLOv11 + PostgreSQL + Redis + MinIO  

---

## 1. 通用约定

### 1.1 响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 1.2 认证方式

```
Authorization: Bearer &lt;jwt_token&gt;
```

- Token 通过 `POST /api/auth/login` 获取，默认有效期 30 分钟
- 需要认证的接口在表格中标记 "🔒 需登录"

### 1.3 状态标记

| 标记 | 含义 |
|------|------|
| ✅ | 已实现（路由 + 服务层代码就绪） |
| ⬜ | 待实现 |

---

## 2. 用户与权限管理

### 2.1 认证（`auth.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 响应 | 状态 |
|------|------|------|------|--------|------|------|
| POST | `/api/auth/register` | 用户注册 | ❌ | `UserRegister` | `UserResponse` (201) | ✅ |
| POST | `/api/auth/login` | 用户登录（返回 JWT） | ❌ | `UserLogin` | `TokenResponse` | ✅ |
| GET | `/api/auth/me` | 获取当前用户信息 | 🔒 | - | `UserResponse` | ✅ |

`UserRegister`：`{username, email, password}`  
`UserLogin`：`{username, password}`  
`TokenResponse`：`{access_token, token_type, user: {id, username, email, avatar, roles}}`

---

### 2.2 用户管理（`users.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 响应 | 状态 |
|------|------|------|------|--------|------|------|
| GET | `/api/users` | 用户列表（分页、搜索） | 🔒 | Query | `PageResponse[UserResponse]` | ⬜ |
| GET | `/api/users/{id}` | 用户详情 | 🔒 | - | `UserResponse` | ⬜ |
| PUT | `/api/users/{id}` | 更新用户信息 | 🔒 | `UserUpdate` | `UserResponse` | ⬜ |
| PUT | `/api/users/{id}/password` | 修改密码 | 🔒 | `ChangePassword` | 200 | ⬜ |
| PUT | `/api/users/{id}/toggle-active` | 启用/禁用用户 | 🔒 | - | `UserResponse` | ⬜ |
| GET | `/api/users/{id}/roles` | 获取用户角色 | 🔒 | - | `list[RoleResponse]` | ⬜ |
| PUT | `/api/users/{id}/roles` | 分配/撤销用户角色 | 🔒 | `{role_ids: [int]}` | 200 | ⬜ |

**列表筛选：** `keyword`（用户名/邮箱）、`is_active`、`role_name`

---

### 2.3 角色管理（`roles.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 响应 | 状态 |
|------|------|------|------|--------|------|------|
| GET | `/api/roles` | 角色列表 | 🔒 | - | `list[RoleResponse]` | ⬜ |
| POST | `/api/roles` | 创建角色 | 🔒 | `RoleCreate` | `RoleResponse` (201) | ⬜ |
| PUT | `/api/roles/{id}` | 编辑角色 | 🔒 | `RoleCreate` | `RoleResponse` | ⬜ |
| DELETE | `/api/roles/{id}` | 删除角色（系统角色不可删） | 🔒 | - | 204 | ⬜ |
| GET | `/api/roles/{id}/permissions` | 获取角色权限 | 🔒 | - | `list[PermissionResponse]` | ⬜ |
| PUT | `/api/roles/{id}/permissions` | 分配角色权限 | 🔒 | `{permission_codes: [str]}` | 200 | ⬜ |

---

### 2.4 权限管理（`permissions.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 响应 | 状态 |
|------|------|------|------|------|------|
| GET | `/api/permissions` | 权限列表（按模块分组） | 🔒 | `dict[str, list[PermissionResponse]]` | ⬜ |

---

## 3. 检测业务

### 3.1 检测场景（`scenes.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 响应 | 状态 |
|------|------|------|------|--------|------|------|
| GET | `/api/scenes` | 场景列表（分页、搜索、筛选） | ❌ | Query | `PageResponse` | ✅ |
| POST | `/api/scenes` | 创建检测场景 | 🔒 | `SceneCreate` | `SceneResponse` (201) | ✅ |
| GET | `/api/scenes/{id}` | 场景详情（含统计信息） | ❌ | - | 详情 | ✅ |
| PUT | `/api/scenes/{id}` | 编辑检测场景 | 🔒 | `SceneUpdate` | `SceneResponse` | ✅ |
| DELETE | `/api/scenes/{id}` | 删除场景（软删除） | 🔒 | - | 204 | ✅ |

**列表筛选：** `keyword`、`category`、`is_active`  
**详情包含：** `model_count`、`task_count`、`dataset_count`、`default_model`、`latest_model`

---

### 3.2 PCB 批次管理（`batch.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 状态 |
|------|------|------|------|--------|------|
| GET | `/api/batches` | 批次列表（分页、状态筛选） | 🔒 | Query | ✅ |
| POST | `/api/batches` | 创建批次 | 🔒 | `BatchCreate` | ✅ |
| GET | `/api/batches/{id}` | 批次详情（含良品率统计） | 🔒 | - | ✅ |
| PUT | `/api/batches/{id}` | 编辑批次 | 🔒 | `BatchUpdate` | ✅ |
| DELETE | `/api/batches/{id}` | 删除批次 | 🔒 | - | ✅ |
| GET | `/api/batches/{id}/statistics` | 批次良品率统计 | 🔒 | - | ✅ |

**列表筛选：** `keyword`(批次号/PCB型号)、`status`(pending/in_progress/completed)、`pcb_type`、`production_line`  
**数据库表：** `pcb_batches` — `{batch_no, pcb_type, production_line, total_count, inspected_count, pass_count, fail_count, pass_rate, status}`

---

### 3.3 检测任务（`tasks.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 状态 |
|------|------|------|------|--------|------|
| GET | `/api/tasks` | 任务列表（分页、筛选） | 🔒 | Query | ✅ |
| POST | `/api/tasks/single` | 单图检测（上传单张 PCB 图像） | 🔒 | multipart + JSON | ✅ |
| POST | `/api/tasks/batch` | 批量检测（多张图像） | 🔒 | multipart + JSON | ✅ |
| GET | `/api/tasks/{id}` | 任务详情（含结果列表） | 🔒 | - | ✅ |
| DELETE | `/api/tasks/{id}` | 删除任务 | 🔒 | - | ✅ |
| GET | `/api/tasks/{id}/results` | 任务检测结果列表 | 🔒 | Query | ✅ |

**列表筛选：** `scene_id`、`status`(pending/processing/completed/failed/cancelled)、`task_type`(single/batch)、`batch_id`、`keyword`(任务ID)  
**任务详情可选参数：** `include_results`(bool) — 是否包含检测结果列表  
**数据库表：** `detection_tasks`  

**单图检测请求：**
```json
// multipart/form-data
{
  "scene_id": 1,
  "image": &lt;file&gt;,
  "conf_threshold": 0.25,
  "iou_threshold": 0.45,
  "batch_id": null
}
```

**批量检测请求：**
```json
// multipart/form-data
{
  "scene_id": 1,
  "images": [&lt;file1&gt;, &lt;file2&gt;, ...],
  "conf_threshold": 0.25,
  "iou_threshold": 0.45,
  "batch_id": 1
}
```

---

### 3.4 检测结果（`results.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 状态 |
|------|------|------|------|--------|------|
| GET | `/api/tasks/{id}/results` | 任务的所有检测结果 | 🔒 | - | ✅ |
| GET | `/api/results/{id}` | 单条检测结果详情 | 🔒 | - | ✅ |
| PUT | `/api/results/{id}/review` | 人工复判 | 🔒 | `{review_status, severity?, defect_type_id?, repair_suggestion?}` | ✅ |
| PUT | `/api/results/{id}/severity` | 标注缺陷严重等级 | 🔒 | `{severity: minor|major|critical}` | ✅ |
| GET | `/api/results/{id}/repair-suggestion` | 获取维修建议（AI 生成） | 🔒 | - | ✅ |
| PUT | `/api/results/{id}/repair-suggestion` | 更新维修建议 | 🔒 | `{repair_suggestion: str}` | ✅ |

**复判状态枚举：** `pending`(待复判) → `pass`(良品) → `fail`(不良品) → `repair`(待维修)  
**缺陷等级枚举：** `minor`(轻微) → `major`(严重) → `critical`(致命)  
**数据库表：** `detection_results`

---

### 3.5 检测统计（`statistics.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| GET | `/api/statistics/overview` | 总览统计 | 🔒 | ✅ |
| GET | `/api/statistics/daily-trend` | 每日检测趋势 | 🔒 | ✅ |
| GET | `/api/statistics/defect-distribution` | 缺陷类型分布 | 🔒 | ✅ |
| GET | `/api/statistics/scene-distribution` | 各场景检测次数 | 🔒 | ✅ |

**daily-trend 参数：** `days`(int, 默认7) — 查询最近N天趋势

---

### 3.6 缺陷类型字典（`defect_types.py` ✅）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| GET | `/api/defect-types` | 缺陷类型列表（搜索、筛选） | ❌ | ✅ |
| POST | `/api/defect-types` | 创建缺陷类型 | 🔒 | ✅ |
| PUT | `/api/defect-types/{id}` | 编辑缺陷类型 | 🔒 | ✅ |
| DELETE | `/api/defect-types/{id}` | 删除缺陷类型 | 🔒 | ✅ |

**列表筛选：** `keyword`(编码/名称/中文名)、`severity`(minor/major/critical)、`is_active`  
**数据库表：** `defect_types` — `{code, name, name_cn, severity, description, is_active}`

---

## 4. 模型与数据集管理（MLOps）

### 4.1 数据集版本（`datasets.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| GET | `/api/datasets` | 数据集版本列表（按场景筛选） | 🔒 | ⬜ |
| POST | `/api/datasets` | 创建数据集版本 | 🔒 | ⬜ |
| GET | `/api/datasets/{id}` | 数据集详情 | 🔒 | ⬜ |
| PUT | `/api/datasets/{id}/activate` | 设为当前活跃数据集 | 🔒 | ⬜ |
| DELETE | `/api/datasets/{id}` | 删除数据集版本 | 🔒 | ⬜ |

**数据库表：** `dataset_versions`

---

### 4.2 训练任务（`training_tasks.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| GET | `/api/training-tasks` | 训练任务列表（分页、筛选） | 🔒 | ⬜ |
| POST | `/api/training-tasks` | 创建训练任务 | 🔒 | ⬜ |
| GET | `/api/training-tasks/{id}` | 训练任务详情 | 🔒 | ⬜ |
| POST | `/api/training-tasks/{id}/start` | 启动训练 | 🔒 | ⬜ |
| POST | `/api/training-tasks/{id}/cancel` | 取消训练 | 🔒 | ⬜ |
| GET | `/api/training-tasks/{id}/metrics` | 训练指标（所有 epoch） | 🔒 | ⬜ |
| GET | `/api/training-tasks/{id}/metrics/latest` | 最新训练指标（实时） | 🔒 | ⬜ |

**数据库表：** `training_tasks`、`training_metrics`

---

### 4.3 模型版本（`models.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| GET | `/api/models` | 模型版本列表（按场景筛选） | 🔒 | ⬜ |
| GET | `/api/models/{id}` | 模型版本详情 | 🔒 | ⬜ |
| POST | `/api/models/upload` | 手动上传模型版本 | 🔒 | ⬜ |
| PUT | `/api/models/{id}` | 编辑模型版本信息 | 🔒 | ⬜ |
| PUT | `/api/models/{id}/default` | 设为场景默认模型 | 🔒 | ⬜ |
| POST | `/api/models/{id}/export` | 导出模型（ONNX/TRT） | 🔒 | ⬜ |
| DELETE | `/api/models/{id}` | 删除/归档模型（软删除） | 🔒 | ⬜ |

**列表筛选：** `scene_id`(必填)、`status`(active/archived/deleted)、`model_type`  
**数据库表：** `model_versions`

---

## 5. 智能体对话

### 5.1 对话管理（`chat.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 请求体 | 状态 |
|------|------|------|------|--------|------|
| GET | `/api/chat/sessions` | 对话会话列表 | 🔒 | - | ⬜ |
| POST | `/api/chat/sessions` | 创建新会话 | 🔒 | `{title?}` | ⬜ |
| GET | `/api/chat/sessions/{id}` | 会话详情（含消息历史） | 🔒 | - | ⬜ |
| PUT | `/api/chat/sessions/{id}` | 更新会话（标题、存档） | 🔒 | `{title?, status?}` | ⬜ |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 | 🔒 | - | ⬜ |
| POST | `/api/chat/messages` | 发送消息（AI 问答） | 🔒 | `ChatMessageRequest` | ⬜ |
| GET | `/api/chat/sessions/{id}/messages` | 获取消息历史 | 🔒 | Query | ⬜ |
| POST | `/api/chat/analyze` | AI 分析检测任务结果 | 🔒 | `{task_id: int}` | ⬜ |

**`POST /api/chat/messages` 请求/响应：**
```json
// 请求
{ "session_id": null, "content": "分析任务 #1024 的检测结果" }

// 响应
{
  "id": 1, "session_id": 1,
  "role": "assistant", "content": "...",
  "agent_used": "detection_analyzer",
  "tokens_used": 1024, "latency_ms": 2340
}
```

**`POST /api/chat/analyze` 响应：**
```json
{ "analysis_report": "## 报告...", "analysis_suggestion": "建议...", "risk_level": "medium" }
```

**数据库表：** `chat_sessions`、`chat_messages`

---

## 6. 系统运维

### 6.1 操作日志（`logs.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| GET | `/api/logs` | 操作日志列表（分页、筛选） | 🔒 | ⬜ |
| GET | `/api/logs/{id}` | 日志详情 | 🔒 | ⬜ |
| GET | `/api/logs/statistics` | 日志统计（按模块/操作类型聚合） | 🔒 | ⬜ |

**列表筛选：** `user_id`、`module`、`action`、`status`(success/failure)、`start_time`、`end_time`  
**数据库表：** `operation_logs`

---

## 7. 通用接口

### 7.1 系统（`health.py` ✅ / 根路由 ✅）

| 方法 | 路径 | 功能 | 认证 | 响应 | 状态 |
|------|------|------|------|------|------|
| GET | `/` | 欢迎页 + API 文档链接 | ❌ | `{message, version, docs, redoc}` | ✅ |
| GET | `/api/health` | 基础健康检查（应用状态） | ❌ | `HealthResponse` | ✅ |
| GET | `/api/health/detail` | 详细健康检查（DB/Redis/MinIO） | ❌ | `HealthResponse + services` | ✅ |

### 7.2 文件上传（`upload.py` ⬜）

| 方法 | 路径 | 功能 | 认证 | 状态 |
|------|------|------|------|------|
| POST | `/api/upload/image` | 上传图像到 MinIO | 🔒 | ⬜ |
| GET | `/api/upload/{file_path}` | 获取已上传文件（MinIO 代理） | ❌ | ⬜ |

---

## 8. 路由注册中心（`__init__.py` ✅）

```python
def register_routers(app: FastAPI):
    """统一注册所有 API 路由"""
    app.include_router(auth.router)
    app.include_router(scenes.router)
    app.include_router(health.router)
    app.include_router(batch.router)
    app.include_router(tasks.router)
    app.include_router(results.router)
    app.include_router(defect_types.router)
    app.include_router(statistics.router)
```

已注册模块：`auth`、`scenes`、`health`、`batch`、`tasks`、`results`、`defect_types`、`statistics`  
在 `main.py` 中通过 `register_routers(app)` 单行调用。

---

## 9. 公共依赖注入（`deps.py` ✅）

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `get_current_user` | `User \| None` | 从 JWT 解析用户，无 token 时返回 None |
| `get_current_active_user` | `User` | 验证已登录且未被禁用 |

---

## 10. 文件清单

### 已创建的文件

| 文件 | 模块 | 状态 |
|------|------|------|
| `api/auth.py` | 认证路由 | ✅ |
| `api/scenes.py` | 检测场景路由 | ✅ |
| `api/health.py` | 健康检查路由 | ✅ |
| `api/batch.py` | PCB 批次路由 | ✅ |
| `api/tasks.py` | 检测任务路由 | ✅ |
| `api/results.py` | 检测结果路由 | ✅ |
| `api/defect_types.py` | 缺陷类型字典路由 | ✅ |
| `api/statistics.py` | 检测统计路由 | ✅ |
| `api/deps.py` | 公共依赖注入 | ✅ |
| `api/__init__.py` | 路由注册中心 | ✅ |
| `api/APIList.MD` | API 设计文档 | ✅ |
| `services/user_service.py` | 用户认证服务 | ✅ |
| `services/scene_service.py` | 检测场景服务 | ✅ |
| `services/batch_service.py` | PCB 批次服务 | ✅ |
| `services/detection_service.py` | 检测任务服务 | ✅ |
| `services/result_service.py` | 检测结果服务 | ✅ |
| `services/defect_type_service.py` | 缺陷类型字典服务 | ✅ |
| `services/statistics_service.py` | 检测统计服务 | ✅ |

### 待创建的文件（建议开发顺序）

```
第一优先级（用户体系）：
  api/users.py          + services/user_management_service.py  用户管理
  api/roles.py          + services/role_service.py            角色管理
  api/permissions.py    + services/permission_service.py      权限管理

第二优先级（AI 能力）：
  api/chat.py           + services/chat_service.py            智能体对话

第三优先级（MLOps）：
  api/datasets.py       + services/dataset_service.py         数据集
  api/training_tasks.py + services/training_service.py        训练任务
  api/models.py         + services/model_service.py           模型版本

第四优先级（辅助功能）：
  api/logs.py           + services/log_service.py             操作日志
  api/upload.py                                              文件上传
```

---

## 附录：API 总计

| 模块 | 文件 | 已实现 | 待实现 | 合计 |
|------|------|--------|--------|------|
| 认证 | `auth.py` | 3 | 0 | 3 |
| 用户管理 | `users.py` | 0 | 7 | 7 |
| 角色管理 | `roles.py` | 0 | 6 | 6 |
| 权限管理 | `permissions.py` | 0 | 1 | 1 |
| 检测场景 | `scenes.py` | 5 | 0 | 5 |
| PCB批次 | `batch.py` | 6 | 0 | 6 |
| 检测任务 | `tasks.py` | 6 | 0 | 6 |
| 检测结果 | `results.py` | 6 | 0 | 6 |
| 检测统计 | `statistics.py` | 4 | 0 | 4 |
| 缺陷类型 | `defect_types.py` | 4 | 0 | 4 |
| 数据集 | `datasets.py` | 0 | 5 | 5 |
| 训练任务 | `training_tasks.py` | 0 | 7 | 7 |
| 模型版本 | `models.py` | 0 | 7 | 7 |
| 智能体对话 | `chat.py` | 0 | 8 | 8 |
| 操作日志 | `logs.py` | 0 | 3 | 3 |
| 健康检查 | `health.py` | 2 | 0 | 2 |
| 文件上传 | `upload.py` | 0 | 2 | 2 |
| 根路由 | `main.py` | 1 | 0 | 1 |
| **总计** | | **37** | **46** | **83** |
