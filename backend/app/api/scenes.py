"""
检测场景管理 API 路由
- POST /api/scenes     创建检测场景
- GET  /api/scenes     获取场景列表
- GET  /api/scenes/{id} 获取场景详情
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.api.auth import get_current_user
from app.entity.db_models import User, DetectionScene, ModelVersion
from app.entity.schemas import SceneCreate, SceneResponse

router = APIRouter(prefix="/api/scenes", tags=["检测场景"])

@router.post("", response_model=SceneResponse, status_code=201)
async def create_scene(
    request: SceneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_scene = db.query(DetectionScene).filter(DetectionScene.name == request.name).first()
    if existing_scene:
        raise HTTPException(status_code=400, detail=f"场景 '{request.name}' 已存在")
    
    new_scene = DetectionScene(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        class_names=request.class_names,
        class_names_cn=request.class_names_cn,
        created_by=current_user.id,
    )
    
    db.add(new_scene)
    db.commit()
    db.refresh(new_scene)
    
    return SceneResponse(**new_scene.__dict__)

@router.get("", response_model=list[SceneResponse])
async def get_scenes(
    category: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DetectionScene)
    
    if category:
        query = query.filter(DetectionScene.category == category)
    if is_active is not None:
        query = query.filter(DetectionScene.is_active == is_active)
    
    query = query.order_by(desc(DetectionScene.created_at))
    scenes = query.all()
    
    results = []
    for scene in scenes:
        default_model = db.query(ModelVersion).filter(
            ModelVersion.scene_id == scene.id,
            ModelVersion.is_default == True,
            ModelVersion.status == "active"
        ).first()
        
        scene_dict = scene.__dict__.copy()
        if default_model:
            scene_dict["default_model"] = {
                "id": default_model.id,
                "version": default_model.version,
                "model_name": default_model.model_name,
            }
        
        results.append(SceneResponse(**scene_dict))
    
    return results

@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail=f"场景 ID {scene_id} 不存在")
    
    default_model = db.query(ModelVersion).filter(
        ModelVersion.scene_id == scene.id,
        ModelVersion.is_default == True,
        ModelVersion.status == "active"
    ).first()
    
    scene_dict = scene.__dict__.copy()
    if default_model:
        scene_dict["default_model"] = {
            "id": default_model.id,
            "version": default_model.version,
            "model_name": default_model.model_name,
        }
    
    return SceneResponse(**scene_dict)