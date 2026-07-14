"""
历史记录相关 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.entity.db_models import DetectionTask, DetectionResult

router = APIRouter(prefix="/api/history", tags=["历史记录"])


@router.get("/records")
async def get_history_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    tasks = (
        db.query(DetectionTask)
        .order_by(DetectionTask.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total = db.query(DetectionTask).count()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": task.id,
                "user_id": task.user_id,
                "scene_id": task.scene_id,
                "scene_name": task.scene_name,
                "task_type": task.task_type,
                "status": task.status,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "created_at": task.created_at,
            }
            for task in tasks
        ],
    }


@router.get("/statistics")
async def get_history_statistics(db: Session = Depends(get_db)):
    total_tasks = db.query(DetectionTask).count()
    total_images = db.query(DetectionTask.total_images).sum() or 0
    total_objects = db.query(DetectionTask.total_objects).sum() or 0
    
    return {
        "total_tasks": total_tasks,
        "total_images": total_images,
        "total_objects": total_objects,
    }