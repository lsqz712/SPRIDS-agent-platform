# SPRIDS Agent Platform

基于 YOLOv11 的目标检测智能体平台，集成多智能体协作系统，提供智能对话、视觉检测、模型训练等一站式 AI 质检解决方案。

## ✨ 功能特性

### 🤖 智能对话（飞讯）
- 基于 LangGraph 的多智能体协作系统
- 支持检测智能体、分析智能体、问答智能体
- RAG 知识库检索（混合搜索：60% 向量 + 40% BM25）
- 对话历史持久化存储

### 📸 检测工作台
- 单图检测、批量检测、视频检测
- 实时摄像头检测（WebSocket 传输）
- 缺陷标注可视化（Bounding Box）
- 人工复判功能（良品/不良品/待维修）

### 🧠 模型训练
- YOLOv11 模型训练与微调
- 训练进度实时监控
- 训练指标可视化（Loss、mAP、Precision、Recall）
- 模型版本管理

### 📊 批次管理
- SMT 产线批次跟踪
- 良品率统计与分析
- 批次检测结果汇总

### 🔐 RBAC 权限系统
- 四种内置角色：管理员、质检操作员、数据工程师、普通访客
- 细粒度权限控制
- 角色审批流程

## 🛠️ 技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.110.0 | Web 框架 |
| SQLAlchemy | 2.0.0 | ORM |
| PostgreSQL + PgVector | 15+ | 数据库与向量检索 |
| Redis | 7 | 缓存与会话管理 |
| MinIO | latest | 对象存储 |
| YOLOv11 (Ultralytics) | 8.3.0 | 目标检测 |
| LangChain | 0.3.0 | LLM 应用框架 |
| LangGraph | 0.2+ | 多智能体协作 |
| JWT | HS256 | 认证 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5+ | 前端框架 |
| Element Plus | 2.14+ | UI 组件库 |
| Vue Router | 4.6+ | 路由管理 |
| Pinia | 3.0+ | 状态管理 |
| Vite | 8.1+ | 构建工具 |
| ECharts | 6.1+ | 图表可视化 |
| Pixi.js | 6.5+ | Canvas 渲染 |

## 📁 项目结构

```
SPRIDS-agent-platform/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agent/              # 智能体模块
│   │   │   ├── agents/         # 具体智能体实现
│   │   │   ├── tools/          # 智能体工具
│   │   │   ├── core.py         # 智能体核心
│   │   │   ├── graph.py        # 多智能体图
│   │   │   ├── memory.py       # 对话记忆
│   │   │   └── supervisor.py   # 任务调度器
│   │   ├── api/                # API 路由
│   │   │   ├── auth.py         # 认证接口
│   │   │   ├── chat.py         # 对话接口
│   │   │   ├── detection.py    # 检测接口
│   │   │   ├── training.py     # 训练接口
│   │   │   ├── model.py        # 模型接口
│   │   │   ├── scenes.py       # 场景接口
│   │   │   ├── batch.py        # 批次接口
│   │   │   ├── roles.py        # 角色权限接口
│   │   │   └── websocket.py    # WebSocket 接口
│   │   ├── config/             # 配置管理
│   │   ├── core/               # 核心组件（异常、日志、安全）
│   │   ├── database/           # 数据库会话
│   │   ├── entity/             # 实体定义（模型、Schema）
│   │   ├── middleware/         # 中间件（限流、日志）
│   │   ├── rag/                # RAG 检索模块
│   │   ├── services/           # 业务逻辑层
│   │   ├── storage/            # 存储客户端（MinIO、Redis）
│   │   └── vectorstore/        # 向量数据库客户端
│   ├── alembic/                # 数据库迁移
│   ├── knowledge_base/         # RAG 知识库
│   ├── tests/                  # 测试用例
│   ├── main.py                 # 应用入口
│   ├── requirements.txt        # 依赖列表
│   └── .env.example            # 环境变量示例
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── api/                # API 调用封装
│   │   ├── components/         # 组件库
│   │   │   ├── detection/      # 检测相关组件
│   │   │   ├── feixun/         # 飞讯对话组件
│   │   │   ├── layout/         # 布局组件
│   │   │   └── training/       # 训练相关组件
│   │   ├── router/             # 路由配置
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── views/              # 页面视图
│   │   ├── utils/              # 工具函数
│   │   └── assets/             # 静态资源
│   ├── tests/                  # 前端测试
│   ├── package.json            # 前端依赖
│   ├── vite.config.js          # Vite 配置
│   └── Dockerfile              # 前端 Docker 镜像
│
├── docker-compose.yml          # 开发环境 Docker Compose
├── docker-compose.server.yml   # 生产环境 Docker Compose
└── .github/workflows/          # CI/CD 工作流
```

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 1. 克隆项目

```bash
git clone <repository-url>
cd SPRIDS-agent-platform
```

### 2. 启动基础设施（开发环境）

```bash
docker-compose up -d
```

这将启动：
- PostgreSQL (5432)
- Redis (6379)
- MinIO (9000, 9001)

### 3. 配置后端环境

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键项：

```env
# LLM 配置（必填）
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=SPRIDS_agent
DB_USER=admin
DB_PASSWORD=Lty120712!

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=sprids-agent-images

# JWT 配置
JWT_SECRET_KEY=your-super-secret-key-change-in-production
```

### 4. 安装后端依赖

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 5. 数据库迁移

```bash
alembic upgrade head
```

### 6. 启动后端服务

```bash
python main.py
```

后端服务将在 `http://localhost:8000` 启动，API 文档在 `http://localhost:8000/docs`。

### 7. 启动前端服务

```bash
cd ../frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 启动。

## 🔐 初始账户

系统启动后会自动创建默认管理员账户：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |

## 📋 角色权限说明

| 角色 | 权限范围 | 可访问页面 |
|------|----------|------------|
| **管理员** | 全部权限 | 所有页面 |
| **质检操作员** | 创建检测、查看结果、人工复判、摄像头检测 | 飞讯、检测工作台、历史记录、批次管理 |
| **数据工程师** | 场景管理、模型管理、训练、数据集管理、缺陷类型 | 飞讯、模型训练、缺陷类型 |
| **普通访客** | 检测、摄像头检测 | 飞讯、检测工作台 |

## 📡 API 文档

启动后端后，访问以下地址查看 API 文档：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 主要 API 模块

| 模块 | 路径 | 功能 |
|------|------|------|
| 认证 | `/api/auth/` | 登录、注册、刷新 Token |
| 对话 | `/api/chat/` | 智能对话、会话管理 |
| 检测 | `/api/detection/` | 检测任务、实时检测 |
| 训练 | `/api/training/` | 训练任务、指标查询 |
| 模型 | `/api/models/` | 模型版本管理 |
| 场景 | `/api/scenes/` | 检测场景配置 |
| 批次 | `/api/batches/` | PCB 批次管理 |
| 角色 | `/api/roles/` | 角色权限管理 |
| WebSocket | `/ws/detection/` | 实时摄像头检测 |

## 🐳 Docker 部署

### 开发环境

```bash
# 启动所有服务（PostgreSQL、Redis、MinIO）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 生产环境

#### 1. 服务器准备

```bash
# 创建项目目录
mkdir -p /opt/pcb-web-platform

# 创建数据目录
mkdir -p /data/postgres /data/redis /data/minio

# 安装 Docker
curl -fsSL https://get.docker.com | sh
```

#### 2. 创建环境变量文件

在服务器上创建 `/opt/pcb-web-platform/.env`：

```env
# 数据库配置
DB_HOST=postgres
DB_PORT=5432
DB_NAME=SPRIDS_agent
DB_USER=admin
DB_PASSWORD=your-secure-password

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO 配置
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=sprids-agent-images
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_PUBLIC_ENDPOINT=your-server-ip:9000

# JWT 配置
JWT_SECRET_KEY=your-production-secret-key

# LLM 配置
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# CORS 配置
ALLOWED_ORIGINS=http://your-server-ip
```

#### 3. 手动启动

```bash
# 拉取最新镜像
docker compose -f docker-compose.server.yml pull

# 启动服务
docker compose -f docker-compose.server.yml up -d

# 查看服务状态
docker compose -f docker-compose.server.yml ps

# 查看日志
docker compose -f docker-compose.server.yml logs -f
```

生产环境包含：
- Nginx 前端代理（80端口）
- FastAPI 后端（含 PyTorch YOLO 推理）
- PostgreSQL 数据库（含 PgVector）
- Redis 缓存
- MinIO 对象存储

## 🏗️ CI/CD

项目使用 GitHub Actions 实现持续集成和部署：

| 工作流 | 触发条件 | 功能 |
|--------|----------|------|
| `build-backend.yml` | 后端代码变更（push到main分支） | 构建后端 Docker 镜像并推送到 GHCR 和阿里云 ACR |
| `build-frontend.yml` | 前端代码变更（push到main分支） | 构建前端 Docker 镜像并推送到 GHCR |
| `ci.yml` | 推送到 main/develop 分支或 PR | 运行前端构建检查和后端语法检查 |
| `deploy.yml` | 构建工作流成功完成后触发 | 自动部署到生产服务器 |

### GitHub Secrets 配置

部署工作流需要配置以下 Secrets：

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 服务器公网 IP 地址 |
| `SERVER_USERNAME` | SSH 登录用户名 |
| `SERVER_PASSWORD` | SSH 登录密码 |
| `SERVER_PORT` | SSH 端口（默认 22） |
| `ACR_USERNAME` | 阿里云 ACR 用户名 |
| `ACR_PASSWORD` | 阿里云 ACR 密码 |
| `ACR_REGISTRY` | 阿里云 ACR 地址 |

配置路径：仓库 → Settings → Secrets and variables → Actions → New repository secret

## 🧪 测试

### 后端测试

```bash
cd backend
pytest tests/ -v
```

### 前端测试

```bash
cd frontend
npm run test:run
```

## 📝 环境变量说明

### LLM 配置
```env
LLM_API_KEY=          # LLM API Key（优先 DEEPSEEK > QWEN > OPENAI）
LLM_BASE_URL=         # LLM API 基础地址
LLM_MODEL_NAME=       # LLM 模型名称
LLM_TEMPERATURE=0.1   # 温度参数
LLM_MAX_TOKENS=4096   # 最大 Token 数
```

### 数据库配置
```env
DB_HOST=localhost     # 数据库主机
DB_PORT=5432          # 数据库端口
DB_NAME=SPRIDS_agent  # 数据库名称
DB_USER=admin         # 数据库用户名
DB_PASSWORD=          # 数据库密码
```

### 存储配置
```env
REDIS_HOST=localhost  # Redis 主机
REDIS_PORT=6379       # Redis 端口
MINIO_ENDPOINT=       # MinIO 地址
MINIO_ACCESS_KEY=     # MinIO Access Key
MINIO_SECRET_KEY=     # MinIO Secret Key
MINIO_BUCKET=         # MinIO 存储桶名称
```

## 📚 知识库

RAG 知识库位于 `backend/knowledge_base/` 目录，包含：
- `remote_sensing.md` - 遥感基础知识
- `yolo_basics.md` - YOLO 模型基础知识
- `evaluation_metrics.md` - 评估指标说明

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！