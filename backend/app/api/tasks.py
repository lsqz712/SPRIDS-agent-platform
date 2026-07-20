"""
检测任务 API 路由
- GET    /api/tasks              任务列表（分页、筛选）
- POST   /api/tasks/single       单图检测（需认证）
- POST   /api/tasks/batch        批量检测（需认证）
- GET    /api/tasks/{id}         任务详情（含结果列表）
- DELETE /api/tasks/{id}         删除任务（需认证）
- GET    /api/tasks/{id}/results 任务检测结果列表
"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user, check_permission
from app.api.utils import success_response
from app.entity.db_models import User, DetectionTask, TaskStatus
from app.services.detection_service import detection_service

router = APIRouter(prefix="/api/tasks", tags=["检测任务"])


@router.get("")
async def list_tasks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    scene_id: int | None = Query(default=None, description="按场景筛选"),
    status: str | None = Query(
        default=None,
        description="按状态筛选：pending/processing/completed/failed/cancelled",
    ),
    task_type: str | None = Query(
        default=None, description="按类型筛选：single/batch"
    ),
    batch_id: int | None = Query(default=None, description="按PCB批次筛选"),
    keyword: str | None = Query(default=None, description="搜索任务 ID"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    获取检测任务列表（分页、多条件筛选）
    """
    user_id = current_user.id if current_user else None

    tasks, total = detection_service.list_tasks(
        db=db,
        page=page,
        page_size=page_size,
        scene_id=scene_id,
        status=status,
        task_type=task_type,
        user_id=user_id,
        batch_id=batch_id,
        keyword=keyword,
    )
    total_pages = (total + page_size - 1) // page_size

    return success_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": tasks,
    })


@router.post("/single", status_code=201, dependencies=[Depends(check_permission("detection:create"))])
async def create_single_task(
    scene_id: int = Form(..., description="检测场景 ID"),
    image: UploadFile = File(..., description="PCB 图像文件"),
    model_version_id: int | None = Form(default=None, description="模型版本 ID"),
    conf_threshold: float = Form(default=0.25, description="置信度阈值"),
    iou_threshold: float = Form(default=0.45, description="IoU 阈值"),
    batch_id: int | None = Form(default=None, description="关联 PCB 批次 ID"),
    source: str = Form(default="manual", description="任务来源：quick/batch/manual"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    单图检测 — 上传单张 PCB 图像进行缺陷检测

    - **scene_id**: 检测场景 ID（必填）
    - **image**: 上传的 PCB 图像文件（支持 jpg/png/bmp）
    - **conf_threshold**: 置信度阈值，默认 0.25
    - **iou_threshold**: NMS IoU 阈值，默认 0.45
    - **batch_id**: 关联的 PCB 批次 ID（可选）
    - **source**: 任务来源：quick（快捷检测）/batch（批次检测）/manual（手动创建）
    """
    user_id = current_user.id if current_user else None

    task = detection_service.create_single_task(
        db=db,
        scene_id=scene_id,
        user_id=user_id,
        model_version_id=model_version_id,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        batch_id=batch_id,
        source=source,
    )

    return success_response(data={
        "task_id": task.id,
        "scene_id": scene_id,
        "status": task.status.value,
        "filename": image.filename,
    }, message="检测任务创建成功（待推理引擎处理）", code=201)


@router.post("/batch", status_code=201, dependencies=[Depends(check_permission("detection:create"))])
async def create_batch_task(
    scene_id: int = Form(..., description="检测场景 ID"),
    images: list[UploadFile] = File(..., description="PCB 图像文件列表"),
    model_version_id: int | None = Form(default=None, description="模型版本 ID"),
    conf_threshold: float = Form(default=0.25, description="置信度阈值"),
    iou_threshold: float = Form(default=0.45, description="IoU 阈值"),
    batch_id: int | None = Form(default=None, description="关联 PCB 批次 ID"),
    source: str = Form(default="manual", description="任务来源：quick/batch/manual"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    批量检测 — 上传多张 PCB 图像进行缺陷检测
    """
    user_id = current_user.id if current_user else None

    task = detection_service.create_batch_task(
        db=db,
        scene_id=scene_id,
        user_id=user_id,
        model_version_id=model_version_id,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        batch_id=batch_id,
        image_count=len(images),
        source=source,
    )

    return success_response(data={
        "task_id": task.id,
        "scene_id": scene_id,
        "status": task.status.value,
        "image_count": len(images),
    }, message=f"批量检测任务创建成功，共 {len(images)} 张图像（待推理引擎处理）", code=201)


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    include_results: bool = Query(default=False, description="是否包含检测结果"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    获取检测任务详情（可选包含检测结果列表）
    """
    task = detection_service.get_task_by_id(db=db, task_id=task_id)

    task_data = {
        "id": task.id,
        "user_id": task.user_id,
        "scene_id": task.scene_id,
        "scene_name": task.scene.display_name if task.scene else None,
        "model_version_id": task.model_version_id,
        "task_type": task.task_type,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "total_images": task.total_images,
        "total_objects": task.total_objects,
        "total_inference_time": task.total_inference_time,
        "conf_threshold": task.conf_threshold,
        "iou_threshold": task.iou_threshold,
        "error_message": task.error_message,
        "batch_id": task.batch_id,
        "analysis_report": task.analysis_report,
        "analysis_suggestion": task.analysis_suggestion,
        "risk_level": task.risk_level,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }

    response_data = {"task": task_data}

    if include_results:
        results, _ = detection_service.get_task_results(db=db, task_id=task_id)
        response_data["results"] = results

    return success_response(data=response_data)


@router.delete("/{task_id}", dependencies=[Depends(check_permission("detection:delete"))])
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    删除检测任务（级联删除关联检测结果）
    """
    detection_service.delete_task(db=db, task_id=task_id)
    return success_response(message="任务已删除")


@router.get("/{task_id}/results")
async def get_task_results(
    task_id: int,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=200, description="每页数量"),
    class_name: str | None = Query(default=None, description="按缺陷类别筛选"),
    review_status: str | None = Query(
        default=None, description="按复判状态筛选"
    ),
    min_confidence: float | None = Query(
        default=None, ge=0, le=1, description="最低置信度"
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    获取指定任务的检测结果列表（分页、筛选）
    """
    detection_service.get_task_by_id(db=db, task_id=task_id)

    results, total = detection_service.get_task_results(
        db=db,
        task_id=task_id,
        page=page,
        page_size=page_size,
        class_name=class_name,
        review_status=review_status,
        min_confidence=min_confidence,
    )
    total_pages = (total + page_size - 1) // page_size

    return success_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": results,
    })
