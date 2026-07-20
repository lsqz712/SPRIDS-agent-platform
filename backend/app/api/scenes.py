"""
检测场景管理 API 路由
- POST /api/scenes     创建检测场景
- GET  /api/scenes     获取场景列表
- GET  /api/scenes/{id} 获取场景详情
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.database.session import get_db
from app.api.deps import get_current_user
from app.api.utils import success_response
from app.entity.db_models import User, DetectionScene, ModelVersion
from app.entity.schemas import SceneCreate, SceneResponse

router = APIRouter(prefix="/api/scenes", tags=["检测场景"])

@router.post("", status_code=201)
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
    
    return success_response(data=SceneResponse(**new_scene.__dict__), message="场景创建成功")

@router.get("")
async def get_scenes(
    category: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DetectionScene).options(
        joinedload(DetectionScene.model_versions)
    )
    
    if category:
        query = query.filter(DetectionScene.category == category)
    if is_active is not None:
        query = query.filter(DetectionScene.is_active == is_active)
    
    query = query.order_by(desc(DetectionScene.created_at))
    scenes = query.all()
    
    results = []
    for scene in scenes:
        default_model = None
        for mv in scene.model_versions:
            if mv.is_default and mv.status == "active":
                default_model = mv
                break
        
        scene_dict = scene.__dict__.copy()
        if default_model:
            scene_dict["default_model"] = {
                "id": default_model.id,
                "version": default_model.version,
                "model_name": default_model.model_name,
            }
        
        results.append(SceneResponse(**scene_dict))
    
    return success_response(data=results)

@router.get("/{scene_id}")
async def get_scene(
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scene = db.query(DetectionScene).options(
        joinedload(DetectionScene.model_versions)
    ).filter(DetectionScene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail=f"场景 ID {scene_id} 不存在")
    
    default_model = None
    for mv in scene.model_versions:
        if mv.is_default and mv.status == "active":
            default_model = mv
            break
    
    scene_dict = scene.__dict__.copy()
    if default_model:
        scene_dict["default_model"] = {
            "id": default_model.id,
            "version": default_model.version,
            "model_name": default_model.model_name,
        }
    
    return success_response(data=SceneResponse(**scene_dict))