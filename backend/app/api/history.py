"""
历史记录相关 API 路由
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.deps import check_permission
from app.core.logger import get_logger
from app.database.session import get_db
from app.services.history_service import history_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/history", tags=["历史记录"])


@router.get("/records", dependencies=[Depends(check_permission("detection:read"))])
async def get_history_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="搜索关键词"),
    task_type: str = Query("", description="任务类型筛选"),
    status: str = Query("", description="状态筛选"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取历史检测记录列表（分页 + 筛选）"""
    tasks, total = history_service.get_history_records(
        db=db, page=page, page_size=page_size,
        user_id=current_user.id, keyword=keyword,
        task_type=task_type, status=status,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": history_service.format_history_response(tasks),
    }


@router.get("/statistics", dependencies=[Depends(check_permission("statistics:read"))])
async def get_history_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取历史记录统计信息"""
    return history_service.get_history_statistics(db=db)


@router.get("/tasks/{task_id}", dependencies=[Depends(check_permission("detection:read"))])
async def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取检测任务详情（含结果列表）"""
    from app.entity.db_models import DetectionTask, DetectionResult
    task = db.query(DetectionTask).filter(
        DetectionTask.id == task_id, DetectionTask.user_id == current_user.id
    ).first()
    if not task:
        return JSONResponse(status_code=404, content={"error": "任务不存在"})
    results = db.query(DetectionResult).filter(DetectionResult.task_id == task_id).all()
    return {
        "task": {
            "id": task.id, "user_id": task.user_id, "scene_id": task.scene_id,
            "task_type": task.task_type,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "total_images": task.total_images, "total_objects": task.total_objects,
            "total_inference_time": task.total_inference_time,
            "conf_threshold": task.conf_threshold, "iou_threshold": task.iou_threshold,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        "results": [
            {"id": r.id, "class_name": r.class_name, "class_name_cn": r.class_name_cn,
             "class_id": r.class_id, "confidence": r.confidence, "bbox": r.bbox,
             "image_path": r.image_path}
            for r in results
        ],
    }


@router.delete("/tasks/{task_id}", dependencies=[Depends(check_permission("detection:delete"))])
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除检测任务及其关联结果"""
    from app.entity.db_models import DetectionTask, DetectionResult
    task = db.query(DetectionTask).filter(
        DetectionTask.id == task_id, DetectionTask.user_id == current_user.id
    ).first()
    if not task:
        return JSONResponse(status_code=404, content={"error": "任务不存在"})
    db.query(DetectionResult).filter(DetectionResult.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    logger.info("用户 %s 删除检测任务 #%d", current_user.username, task_id)
    return {"message": f"任务 #{task_id} 已删除", "task_id": task_id}
