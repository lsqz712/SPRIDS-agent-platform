from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.auth import router as auth_router
from app.core.exceptions import register_exception_handlers
from app.middleware.request_logger import RequestLogMiddleware
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.chat_phrolova import router as chat_phrolova_router
from app.api.models import router as models_router
from app.api.scenes import router as scenes_router
from app.api.detection import router as detection_router
from app.api.training import router as training_router
from app.api.history import router as history_router
from app.api.storage import router as storage_router
from app.api.tasks import router as tasks_router
from app.api.batch import router as batch_router
from app.api.statistics import router as statistics_router
from app.api.defect_types import router as defect_types_router
from app.api.results import router as results_router
from app.api.websocket import router as websocket_router
from app.api.dashboard import router as dashboard_router
from app.api.user import router as user_router
from app.api.knowledge import router as knowledge_router
from app.api.roles import router as roles_router
from app.middleware.rate_limiter import RateLimiterMiddleware

def init_minio():
    from app.storage.minio_client import MinIOClient
    try:
        minio_client = MinIOClient()
        print(f"MinIO 存储桶 '{minio_client.bucket_name}' 初始化完成")
    except Exception as e:
        print(f"MinIO 初始化失败: {e}")

def init_roles_and_permissions():
    from app.database.session import get_db
    from app.services.init_service import init_service
    try:
        db = next(get_db())
        result = init_service.init_all(db)
        print(f"角色权限初始化完成: {result['permissions_created']} 个权限, {result['roles_created']} 个角色")
    except Exception as e:
        print(f"角色权限初始化失败: {e}")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("正在初始化服务...")
    init_minio()
    init_roles_and_permissions()
    yield
    print("服务已关闭")

app = FastAPI(
    title="RSOD Agent Platform",
    version="0.1.0",
    description="基于 YOLOv11 的目标检测智能体平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(RateLimiterMiddleware)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(chat_phrolova_router)
app.include_router(detection_router)
app.include_router(models_router)
app.include_router(scenes_router)
app.include_router(training_router)
app.include_router(history_router)
app.include_router(storage_router)
app.include_router(tasks_router)
app.include_router(batch_router)
app.include_router(statistics_router)
app.include_router(defect_types_router)
app.include_router(results_router)
app.include_router(websocket_router)
app.include_router(dashboard_router)
app.include_router(user_router)
app.include_router(knowledge_router)
app.include_router(roles_router)

@app.get("/")
def root():
    return {
        "message": "欢迎使用 RSOD Agent Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)