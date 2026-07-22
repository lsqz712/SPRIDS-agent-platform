"""
模型管理 API 路由
- POST /api/models/versions     创建模型版本
- GET  /api/models/versions     获取模型版本列表
- GET  /api/models/versions/{id} 获取模型版本详情
- PUT  /api/models/versions/{id} 更新模型版本
- DELETE /api/models/versions/{id} 删除模型版本
- PUT  /api/models/versions/{id}/set-default 设置为默认模型
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.database.session import get_db
from app.api.deps import get_current_user, check_permission
from app.api.utils import success_response
from app.entity.db_models import User, ModelVersion, DetectionScene
from app.entity.schemas import ModelVersionCreate, ModelVersionResponse
import os

router = APIRouter(prefix="/api/models", tags=["模型管理"])

@router.post("/versions", status_code=201, dependencies=[Depends(check_permission("model:create"))])
async def create_model_version(
    request: ModelVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scene = db.query(DetectionScene).filter(DetectionScene.id == request.scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail=f"检测场景 ID {request.scene_id} 不存在")
    
    model_path = request.model_path
    if not os.path.isabs(model_path):
        model_path = os.path.abspath(model_path)
    
    if not os.path.exists(model_path):
        raise HTTPException(status_code=400, detail=f"模型文件不存在: {model_path}")
    
    if request.is_default:
        db.query(ModelVersion).filter(
            ModelVersion.scene_id == request.scene_id,
            ModelVersion.is_default == True
        ).update({"is_default": False})
    
    new_model = ModelVersion(
        scene_id=request.scene_id,
        version=request.version,
        model_name=request.model_name,
        model_type=request.model_type,
        model_path=request.model_path,
        is_default=request.is_default,
        description=request.description,
        status="active",
    )
    
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    
    return success_response(data=ModelVersionResponse(
        **new_model.__dict__,
        scene_name=scene.display_name
    ), message="模型版本创建成功")

@router.get("/versions", dependencies=[Depends(check_permission("model:read"))])
async def get_model_versions(
    scene_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ModelVersion).options(
        joinedload(ModelVersion.scene)
    )
    
    if scene_id:
        query = query.filter(ModelVersion.scene_id == scene_id)
    if status:
        query = query.filter(ModelVersion.status == status)
    
    query = query.order_by(desc(ModelVersion.created_at))
    models = query.all()
    
    results = []
    for model in models:
        results.append(ModelVersionResponse(
            **model.__dict__,
            scene_name=model.scene.display_name if model.scene else None
        ))
    
    return success_response(data=results)

@router.get("/versions/{model_id}", dependencies=[Depends(check_permission("model:read"))])
async def get_model_version(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(ModelVersion).options(
        joinedload(ModelVersion.scene)
    ).filter(ModelVersion.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"模型版本 ID {model_id} 不存在")
    
    return success_response(data=ModelVersionResponse(
        **model.__dict__,
        scene_name=model.scene.display_name if model.scene else None
    ))

@router.put("/versions/{model_id}", dependencies=[Depends(check_permission("model:update"))])
async def update_model_version(
    model_id: int,
    request: ModelVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(ModelVersion).options(
        joinedload(ModelVersion.scene)
    ).filter(ModelVersion.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"模型版本 ID {model_id} 不存在")
    
    scene = db.query(DetectionScene).filter(DetectionScene.id == request.scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail=f"检测场景 ID {request.scene_id} 不存在")
    
    if request.model_path and not os.path.exists(request.model_path):
        raise HTTPException(status_code=400, detail=f"模型文件不存在: {request.model_path}")
    
    if request.is_default and request.is_default != model.is_default:
        db.query(ModelVersion).filter(
            ModelVersion.scene_id == request.scene_id,
            ModelVersion.is_default == True
        ).update({"is_default": False})
    
    model.scene_id = request.scene_id
    model.version = request.version
    model.model_name = request.model_name
    model.model_type = request.model_type
    model.model_path = request.model_path
    model.is_default = request.is_default
    model.description = request.description
    
    db.commit()
    db.refresh(model)
    
    return success_response(data=ModelVersionResponse(
        **model.__dict__,
        scene_name=scene.display_name
    ), message="模型版本更新成功")

@router.delete("/versions/{model_id}", dependencies=[Depends(check_permission("model:delete"))])
async def delete_model_version(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"模型版本 ID {model_id} 不存在")
    
    model.status = "deleted"
    db.commit()
    
    return success_response(message="模型版本已删除")

@router.put("/versions/{model_id}/set-default", dependencies=[Depends(check_permission("model:update"))])
async def set_default_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(ModelVersion).options(
        joinedload(ModelVersion.scene)
    ).filter(ModelVersion.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"模型版本 ID {model_id} 不存在")
    
    db.query(ModelVersion).filter(
        ModelVersion.scene_id == model.scene_id,
        ModelVersion.is_default == True
    ).update({"is_default": False})
    
    model.is_default = True
    db.commit()
    db.refresh(model)
    
    return success_response(data=ModelVersionResponse(
        **model.__dict__,
        scene_name=model.scene.display_name if model.scene else None
    ), message="已设置为默认模型")