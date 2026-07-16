"""
检测 API 路由 — 快捷检测接⼝（跳过 LLM，直接调⽤ YOLO）
接⼝列表：
  - POST /api/detection/single     单图检测
  - POST /api/detection/batch      批量检测
  - POST /api/detection/zip        ZIP ⽂件检测
  - POST /api/detection/video      视频检测
  - GET  /api/detection/scenes     获取检测场景列表
  - GET  /api/detection/cameras    枚举摄像头设备
  - GET  /api/detection/status/:id 查询任务状态
  - GET  /api/detection/tasks/:id  获取检测任务详情
"""
import os
import tempfile
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.schemas import SceneResponse
from app.services.detection_service import detection_service
from app.services.scene_service import scene_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/detection", tags=["快捷检测"])


@router.get("/scenes", response_model=list[SceneResponse])
async def get_detection_scenes(
    category: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取检测场景列表"""
    scenes, _ = scene_service.list_scenes(
        db=db,
        category=category,
        is_active=is_active,
        page=1,
        page_size=100,
    )
    
    results = []
    for scene in scenes:
        scene_dict = scene.__dict__.copy()
        scene_dict["default_model"] = scene_service.get_scene_statistics(db, scene).get("default_model")
        results.append(SceneResponse(**scene_dict))
    
    return results


@router.post("/single", summary="单图检测")
async def detect_single_api(
    file: UploadFile = File(..., description="检测图⽚"),
    conf: float = Form(0.25, description="置信度阈值"),
    scene_id: int = Form(None, description="场景 ID"),
    current_user=Depends(get_current_user),
):
    """快捷单图检测（跳过 LLM，直接调⽤ YOLO）"""
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
    """快捷批量检测"""
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
    """快捷 ZIP 检测：解压 ZIP 并批量检测其中所有图⽚"""
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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查询检测任务状态"""
    task = detection_service.get_task_by_id(db=db, task_id=task_id)
    return {
        "task_id": task.id,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "task_type": task.task_type,
        "total_images": task.total_images,
        "total_objects": task.total_objects,
        "completed_at": (
            task.completed_at.isoformat() if task.completed_at else None
        ),
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.post("/video", summary="视频检测")
async def detect_video_api(
    file: UploadFile = File(..., description="视频文件"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    frame_interval: int = Form(10, description="检测帧间隔"),
    current_user=Depends(get_current_user),
):
    """视频检测（按帧间隔采样检测）"""
    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = detection_service.detect_video(
            video_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
            frame_interval=frame_interval,
        )
        result["filename"] = file.filename
        return result
    finally:
        os.unlink(tmp_path)


@router.get("/cameras", summary="枚举摄像头设备")
async def list_camera_devices_api(
    current_user=Depends(get_current_user),
):
    """枚举可用的摄像头设备（包括USB连接的手机摄像头）"""
    devices = detection_service.list_cameras()
    return {
        "success": True,
        "devices": devices,
    }


@router.get("/tasks/{task_id}", summary="获取检测任务详情")
async def get_detection_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取检测任务详情及结果"""
    task = detection_service.get_task_by_id(db=db, task_id=task_id)
    return {
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
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }