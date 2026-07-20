"""
检测结果 API 路由
- GET    /api/results/{id}                 单条检测结果详情
- PUT    /api/results/{id}/review          人工复判（需认证）
- PUT    /api/results/{id}/severity        标注缺陷严重等级（需认证）
- GET    /api/results/{id}/repair-suggestion   获取维修建议（AI生成）
- PUT    /api/results/{id}/repair-suggestion   更新维修建议（需认证）
- GET    /api/tasks/{task_id}/results/summary  任务检测结果汇总
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user, get_current_active_user, check_permission
from app.api.utils import success_response
from app.entity.db_models import User
from app.entity.schemas import (
    ResultReviewRequest,
    ResultSeverityRequest,
    ResultRepairSuggestionRequest,
)
from app.services.result_service import result_service

router = APIRouter(prefix="/api/results", tags=["检测结果"])


@router.get("/{result_id}")
async def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    获取单条检测结果详情（含复判与维修信息）
    - **result_id**: 检测结果 ID
    """
    result = result_service.get_result_by_id(db=db, result_id=result_id)

    result_data = {
        "id": result.id,
        "task_id": result.task_id,
        "image_path": result.image_path,
        "annotated_image_url": result.annotated_image_url,
        "class_name": result.class_name,
        "class_name_cn": result.class_name_cn,
        "class_id": result.class_id,
        "confidence": result.confidence,
        "bbox": result.bbox,
        "inference_time": result.inference_time,
        "image_width": result.image_width,
        "image_height": result.image_height,
        "review_status": result.review_status.value
        if hasattr(result.review_status, "value")
        else result.review_status,
        "severity": result.severity.value
        if hasattr(result.severity, "value")
        else result.severity,
        "repair_suggestion": result.repair_suggestion,
        "reviewer_id": result.reviewer_id,
        "reviewer_name": result.reviewer.username if result.reviewer else None,
        "reviewed_at": result.reviewed_at,
        "defect_type_id": result.defect_type_id,
        "created_at": result.created_at,
    }

    return success_response(data=result_data)


@router.put("/{result_id}/review", dependencies=[Depends(check_permission("detection:review"))])
async def update_result_review(
    result_id: int,
    data: ResultReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    人工复判

    复判状态流转：
      pending(待复判) → pass(良品) | fail(不良品) | repair(待维修)

    - **review_status**: 复判状态（必填）
      - `pass`: 良品（OK）
      - `fail`: 不良品（NG）
      - `repair`: 待维修
    - **severity**: 缺陷严重等级（可选）
      - `minor`: 轻微（如划痕）
      - `major`: 严重（如焊点不良）
      - `critical`: 致命（如短路/开路）
    - **defect_type_id**: 缺陷类型 ID（可选）
    - **repair_suggestion**: 维修建议（可选）
    """
    result = result_service.update_review(
        db=db,
        result_id=result_id,
        review_status=data.review_status,
        reviewer_id=current_user.id,
        severity=data.severity,
        defect_type_id=data.defect_type_id,
        repair_suggestion=data.repair_suggestion,
    )

    return success_response(data={
        "id": result.id,
        "review_status": result.review_status.value
        if hasattr(result.review_status, "value")
        else result.review_status,
        "severity": result.severity.value
        if hasattr(result.severity, "value")
        else result.severity,
        "reviewer_id": result.reviewer_id,
        "reviewed_at": result.reviewed_at,
        "repair_suggestion": result.repair_suggestion,
    }, message="复判成功")


@router.put("/{result_id}/severity", dependencies=[Depends(check_permission("detection:review"))])
async def update_result_severity(
    result_id: int,
    data: ResultSeverityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    标注缺陷严重等级
    - **severity**: 缺陷严重等级
      - `minor`: 轻微（如划痕）
      - `major`: 严重（如焊点不良）
      - `critical`: 致命（如短路/开路）
    """
    result = result_service.update_severity(
        db=db,
        result_id=result_id,
        severity=data.severity,
    )

    return success_response(data={
        "id": result.id,
        "severity": result.severity.value
        if hasattr(result.severity, "value")
        else result.severity,
    }, message="缺陷等级标注成功")


@router.get("/{result_id}/repair-suggestion")
async def get_repair_suggestion(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    获取 AI 生成的维修建议
    - 根据缺陷类型、置信度等信息生成初步建议
    - 后续集成 LLM 可生成更精准的方案
    """
    suggestion_data = result_service.get_repair_suggestion_ai(
        db=db, result_id=result_id
    )

    return success_response(data=suggestion_data)


@router.put("/{result_id}/repair-suggestion")
async def update_repair_suggestion(
    result_id: int,
    data: ResultRepairSuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新维修建议（人工标注/修改）
    - **repair_suggestion**: 维修/调整建议内容
    """
    result = result_service.update_repair_suggestion(
        db=db,
        result_id=result_id,
        repair_suggestion=data.repair_suggestion,
    )

    return success_response(data={
        "id": result.id,
        "repair_suggestion": result.repair_suggestion,
    }, message="维修建议更新成功")
