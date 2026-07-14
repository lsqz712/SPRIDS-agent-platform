"""
检测场景 API 路由
- GET    /api/scenes         场景列表（分页）
- POST   /api/scenes         创建场景（需认证）
- GET    /api/scenes/{id}    场景详情
- PUT    /api/scenes/{id}    编辑场景（需认证）
- DELETE /api/scenes/{id}    删除场景（需认证，软删除）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.entity.db_models import User, DetectionScene
from app.entity.schemas import SceneCreate, SceneUpdate, SceneResponse
from app.services.scene_service import scene_service

router = APIRouter(prefix="/api/scenes", tags=["检测场景"])


@router.get("", response_model=dict)
async def list_scenes(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(default=None, description="搜索关键词"),
    category: str | None = Query(default=None, description="按分类筛选"),
    is_active: bool | None = Query(default=None, description="按启用状态筛选"),
    db: Session = Depends(get_db),
):
    """
    获取检测场景列表（分页、搜索、筛选）
    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **keyword**: 搜索场景名称或标识
    - **category**: 按分类筛选
    - **is_active**: 按启用状态筛选
    """
    scenes, total = scene_service.list_scenes(
        db=db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        category=category,
        is_active=is_active,
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
            "items": [SceneResponse.model_validate(s).model_dump() for s in scenes],
        },
    }


@router.post("", response_model=SceneResponse, status_code=201)
async def create_scene(
    data: SceneCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    创建检测场景（需要登录）
    - **name**: 场景唯一标识，如 pcb_defect
    - **display_name**: 场景显示名，如 PCB缺陷检测
    - **category**: 场景分类
    - **class_names**: 类别列表
    - **class_names_cn**: 类别中文映射（可选）
    """
    user_id = current_user.id if current_user else None
    scene = scene_service.create_scene(db=db, data=data, user_id=user_id)
    return SceneResponse.model_validate(scene).model_dump()


@router.get("/{scene_id}", response_model=dict)
async def get_scene(
    scene_id: int,
    db: Session = Depends(get_db),
):
    """
    获取检测场景详情（含关联统计信息）
    - **scene_id**: 场景 ID
    """
    scene = scene_service.get_scene_by_id(db=db, scene_id=scene_id)
    statistics = scene_service.get_scene_statistics(db=db, scene=scene)

    scene_data = SceneResponse.model_validate(scene).model_dump()
    scene_data.update(statistics)

    return {
        "code": 200,
        "message": "success",
        "data": scene_data,
    }


@router.put("/{scene_id}", response_model=dict)
async def update_scene(
    scene_id: int,
    data: SceneUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    编辑检测场景（需要登录）
    - **scene_id**: 场景 ID
    - 所有字段可选，只传需要修改的字段
    """
    scene = scene_service.update_scene(db=db, scene_id=scene_id, data=data)
    return {
        "code": 200,
        "message": "场景更新成功",
        "data": SceneResponse.model_validate(scene).model_dump(),
    }


@router.delete("/{scene_id}", status_code=204)
async def delete_scene(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    删除检测场景（软删除）
    - **scene_id**: 场景 ID
    - 不会物理删除，仅标记 deleted_at 时间戳
    """
    scene_service.delete_scene(db=db, scene_id=scene_id)
    return None