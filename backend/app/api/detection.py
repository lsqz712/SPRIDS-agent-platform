"""
检测 API 路由 — 快捷检测接⼝（跳过 LLM，直接调⽤ YOLO）
接⼝列表：
  - POST /api/detection/single     
  - POST /api/detection/batch      
  - POST /api/detection/zip      
单图检测
批量检测
  ZIP ⽂件检测
  - GET  /api/detection/status/:id 查询任务状态
"""
import os
import tempfile
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import SessionLocal, get_db
from app.entity.db_models import DetectionTask, DetectionScene, ModelVersion
from app.entity.schemas import SceneResponse
from app.services.detection_service import detection_service
logger = get_logger(__name__)
router = APIRouter(prefix="/api/detection", tags=["快捷检测"])


@router.get("/scenes", response_model=list[SceneResponse])
async def get_detection_scenes(
    category: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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
@router.post("/single", summary="单图检测")
async def detect_single_api(
file: UploadFile = File(..., description="检测图⽚"),
conf: float = Form(0.25, description="置信度阈值"),
scene_id: int = Form(None, description="场景 ID"),
current_user=Depends(get_current_user),
):
    """
    快捷单图检测（跳过 LLM，直接调⽤ YOLO）
    """
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = detection_service.detect_single(
            image_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
        )
        result["filename"] = file.filename
        return result
    finally:
        os.unlink(tmp_path)
@router.post("/batch", summary="批量检测")
async def detect_batch_api(
    files: list[UploadFile] = File(..., description="多张图⽚"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    快捷批量检测
    """
    temp_paths = []
    try:
        for file in files:
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_paths.append(tmp.name)
        result = detection_service.detect_batch(
            image_paths=temp_paths,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
        )
        return result
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except Exception:
                pass
@router.post("/zip", summary="ZIP ⽂件检测")
async def detect_zip_api(
    file: UploadFile = File(..., description="ZIP 压缩包"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    快捷 ZIP 检测：解压 ZIP 并批量检测其中所有图⽚
    """
    suffix = os.path.splitext(file.filename)[1] or ".zip"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = detection_service.detect_zip(
            zip_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
        )
        return result
    finally:
        os.unlink(tmp_path)
@router.get("/status/{task_id}", summary="查询检测任务状态")
async def get_detection_status(
    task_id: int,
    current_user=Depends(get_current_user),
):
    """查询检测任务状态"""
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "任务不存在"},
            )
        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
    finally:
        db.close()


@router.post("/video", summary="视频检测")
async def detect_video_api(
    file: UploadFile = File(..., description="视频文件"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    视频检测（预留接口）
    """
    return {
        "message": "视频检测功能暂未实现",
        "filename": file.filename,
        "status": "pending",
    }


@router.get("/tasks/{task_id}", summary="获取检测任务详情")
async def get_detection_task_detail(
    task_id: int,
    current_user=Depends(get_current_user),
):
    """获取检测任务详情及结果"""
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "任务不存在"},
            )
        return {
            "id": task.id,
            "user_id": task.user_id,
            "scene_id": task.scene_id,
            "scene_name": task.scene_name,
            "model_version_id": task.model_version_id,
            "task_type": task.task_type,
            "status": task.status,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "total_inference_time": task.total_inference_time,
            "conf_threshold": task.conf_threshold,
            "iou_threshold": task.iou_threshold,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    finally:
        db.close()