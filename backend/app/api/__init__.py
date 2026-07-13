# api/__init__.py
from fastapi import FastAPI
from . import auth, scenes, health, batch, tasks, results, defect_types, statistics


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