"""
PCB批次 API 路由
- GET    /api/batches             批次列表（分页、筛选）
- POST   /api/batches             创建批次（需认证，支持图片上传）
- GET    /api/batches/{id}        批次详情（含良品率统计）
- PUT    /api/batches/{id}        编辑批次（需认证）
- DELETE /api/batches/{id}        删除批次（需认证）
- GET    /api/batches/{id}/statistics  批次良品率统计
- POST   /api/batches/{id}/upload     向批次导入图片
- POST   /api/batches/{id}/detect     批次一键检测
- GET    /api/batches/{id}/images     获取批次图片列表
"""
from fastapi import APIRouter, Depends, Query, File, UploadFile, Form
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.entity.db_models import User
from app.entity.schemas import BatchCreate, BatchUpdate, BatchResponse
from app.services.batch_service import batch_service

router = APIRouter(prefix="/api/batches", tags=["PCB批次"])


@router.get("", response_model=dict)
async def list_batches(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(default=None, description="搜索批次号/PCB型号"),
    status: str | None = Query(default=None, description="状态：pending/in_progress/completed"),
    pcb_type: str | None = Query(default=None, description="按PCB型号筛选"),
    production_line: str | None = Query(default=None, description="按产线编号筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取PCB批次列表（分页、搜索、筛选）
    """
    batches, total = batch_service.list_batches(
        db=db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        pcb_type=pcb_type,
        production_line=production_line,
    )
    total_pages = (total + page_size - 1) // page_size

    return {
        "code": 200,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": [BatchResponse.model_validate(b).model_dump() for b in batches],
        },
    }


@router.post("", response_model=dict, status_code=201)
async def create_batch(
    batch_no: str = Form(..., description="批次号，如 BATCH-20250701-001"),
    pcb_type: str = Form(..., description="PCB型号，如 PCB-V2.1"),
    production_line: str = Form(..., description="产线编号，如 LINE-A01"),
    total_count: int = Form(default=0, description="批次总数量（不传则根据导入图片数量自动计算）"),
    files: list[UploadFile] = File(default=None, description="批次图片（可选，支持多张）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建PCB批次（需要登录）
    - 支持创建时导入图片
    - 如果不传total_count，会根据导入的图片数量自动计算
    """
    batch = batch_service.create_batch_with_images(
        db=db,
        batch_no=batch_no,
        pcb_type=pcb_type,
        production_line=production_line,
        total_count=total_count,
        files=files or [],
        user_id=current_user.id,
    )
    return {
        "code": 201,
        "message": "批次创建成功",
        "data": BatchResponse.model_validate(batch).model_dump(),
    }


@router.get("/{batch_id}", response_model=dict)
async def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取PCB批次详情（含良品率统计）
    """
    batch = batch_service.get_batch_by_id(db=db, batch_id=batch_id)
    statistics = batch_service.get_batch_statistics(db=db, batch=batch)
    images = batch_service.get_batch_images(db=db, batch_id=batch_id)

    # 每张图片的检测结果（按 image_path 匹配）
    from app.entity.db_models import DetectionResult, DetectionTask
    latest_task = db.query(DetectionTask).filter(
        DetectionTask.batch_id == batch_id
    ).order_by(DetectionTask.id.desc()).first()
    all_dets = db.query(DetectionResult).filter(
        DetectionResult.task_id == latest_task.id
    ).all() if latest_task else []

    # 按批次图片路径分组检测结果
    for img in images:
        img_path = img.get("image_path", "")
        img["detections"] = [
            {"class_name": d.class_name, "class_name_cn": d.class_name_cn,
             "confidence": d.confidence, "bbox": d.bbox}
            for d in all_dets if d.image_path == img_path
        ]

    batch_data = BatchResponse.model_validate(batch).model_dump()
    batch_data.update(statistics)
    batch_data["images"] = images

    return {
        "code": 200,
        "message": "success",
        "data": batch_data,
    }


@router.put("/{batch_id}", response_model=dict)
async def update_batch(
    batch_id: int,
    data: BatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    编辑PCB批次（需要登录）
    - 所有字段可选，只传需要修改的字段
    """
    batch = batch_service.update_batch(db=db, batch_id=batch_id, data=data)
    return {
        "code": 200,
        "message": "批次更新成功",
        "data": BatchResponse.model_validate(batch).model_dump(),
    }


@router.delete("/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除PCB批次
    - 物理删除（因为批次创建错误通常需要彻底清理）
    """
    batch_service.delete_batch(db=db, batch_id=batch_id)
    return None


@router.get("/{batch_id}/statistics", response_model=dict)
async def get_batch_statistics(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取PCB批次良品率统计
    - 返回实时计算的良品率、不良品率等指标
    """
    batch = batch_service.get_batch_by_id(db=db, batch_id=batch_id)
    statistics = batch_service.get_batch_statistics(db=db, batch=batch)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            **statistics,
        },
    }


@router.post("/{batch_id}/upload", response_model=dict)
async def upload_batch_images(
    batch_id: int,
    files: list[UploadFile] = File(..., description="批次图片（支持多张）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    向批次导入图片
    - 支持一次导入多张图片
    - 图片会存储到MinIO
    """
    result = batch_service.upload_batch_images(
        db=db,
        batch_id=batch_id,
        files=files,
        user_id=current_user.id,
    )
    return {
        "code": 200,
        "message": "图片上传成功",
        "data": result,
    }


@router.get("/{batch_id}/images", response_model=dict)
async def get_batch_images(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取批次图片列表
    """
    images = batch_service.get_batch_images(db=db, batch_id=batch_id)
    return {
        "code": 200,
        "message": "success",
        "data": images,
    }


@router.post("/{batch_id}/detect", response_model=dict)
async def detect_batch(
    batch_id: int,
    conf: float = Form(default=0.25, description="置信度阈值"),
    scene_id: int = Form(default=None, description="场景ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    批次一键检测
    - 将批次中的所有图片打包发送到检测工作台进行检测
    - 检测结果自动关联到该批次
    """
    result = batch_service.detect_batch(
        db=db,
        batch_id=batch_id,
        conf=conf,
        scene_id=scene_id,
        user_id=current_user.id,
    )
    return {
        "code": 200,
        "message": "批次检测任务已创建",
        "data": result,
    }