"""
PCB批次 API 路由
- GET    /api/batches             批次列表（分页、筛选）
- POST   /api/batches             创建批次（需认证）
- GET    /api/batches/{id}        批次详情（含良品率统计）
- PUT    /api/batches/{id}        编辑批次（需认证）
- DELETE /api/batches/{id}        删除批次（需认证）
- GET    /api/batches/{id}/statistics  批次良品率统计
"""
from fastapi import APIRouter, Depends, Query
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
    data: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建PCB批次（需要登录）
    - **batch_no**: 批次号，如 BATCH-20250701-001
    - **pcb_type**: PCB型号，如 PCB-V2.1
    - **production_line**: 产线编号，如 LINE-A01
    - **total_count**: 批次总数量
    """
    batch = batch_service.create_batch(db=db, data=data, user_id=current_user.id)
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

    batch_data = BatchResponse.model_validate(batch).model_dump()
    batch_data.update(statistics)

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
