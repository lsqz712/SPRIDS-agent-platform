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
import json
import base64
import time
import threading
import tempfile
import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.deps import get_current_active_user, check_permission
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.schemas import SceneResponse
from app.services.detection_service import detection_service
from app.services.scene_service import scene_service
from app.storage.redis_client import redis_client

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
    current_user=Depends(get_current_active_user),
    _perm=Depends(check_permission("detection:create")),
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
    current_user=Depends(get_current_active_user),
    _perm=Depends(check_permission("detection:create")),
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
    current_user=Depends(get_current_active_user),
    _perm=Depends(check_permission("detection:create")),
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
    frame_sample_rate: int = Form(5, description="帧采样间隔（每N帧取1帧）"),
    max_frames: int = Form(50, description="最多关键帧数"),
    use_scene_detection: bool = Form(True, description="开启场景变化检测"),
    scene_threshold: float = Form(10.0, description="场景变化阈值（灰度差）"),
    current_user=Depends(get_current_active_user),
    _perm=Depends(check_permission("detection:create")),
):
    """视频检测：上传后异步处理，通过 status 接口轮询进度"""
    # 格式校验
    _VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}
    suffix = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if suffix not in _VIDEO_EXTENSIONS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"不支持的视频格式: {suffix}，支持: {', '.join(sorted(_VIDEO_EXTENSIONS))}"},
        )

    project_tmp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
    os.makedirs(project_tmp, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=project_tmp) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # 通过 Service 层创建任务
    task_id = detection_service.create_video_task(
        user_id=current_user.id, scene_id=scene_id or 1, conf=conf)

    redis_client.set_json(f"video_task:{task_id}", {
        "status": "PROCESSING", "progress": 0, "message": "视频处理中..."
    }, expire=3600)

    def _run():
        try:
            result = detection_service.detect_video(
                video_path=tmp_path, conf=conf, scene_id=scene_id,
                user_id=current_user.id, frame_sample_rate=frame_sample_rate,
                max_frames=max_frames, use_scene_detection=use_scene_detection,
                scene_threshold=scene_threshold, task_id=task_id,
            )
            if "error" in result:
                redis_client.set_json(f"video_task:{task_id}", {
                    "status": "FAILED", "progress": 0, "message": result["error"]
                }, expire=3600)
            else:
                redis_client.set_json(f"video_task:{task_id}", {
                    "status": "COMPLETED", "progress": 100,
                    "message": f"检测完成，{result.get('processed_frames',0)}帧，{result.get('total_objects',0)}个目标",
                    "result": result,
                }, expire=3600)
        except Exception as e:
            redis_client.set_json(f"video_task:{task_id}", {
                "status": "FAILED", "progress": 0, "message": str(e)
            }, expire=3600)
        finally:
            try: os.unlink(tmp_path)
            except: pass

    threading.Thread(target=_run, daemon=True).start()

    return {
        "task_id": task_id, "status": "PROCESSING",
        "message": "视频已上传，后台处理中，请通过 status 接口轮询",
        "filename": file.filename,
    }


@router.get("/video/status/{task_id}", summary="查询视频检测进度")
async def get_video_detection_status(task_id: int, db: Session = Depends(get_db)):
    """查询视频检测任务进度（Redis优先 → DB回退）."""
    cached = redis_client.get_json(f"video_task:{task_id}")
    if cached:
        return {"task_id": task_id, **cached}
    task = detection_service.get_task_by_id(db, task_id)
    return {
        "task_id": task.id, "status": task.status.value if hasattr(task.status, "value") else task.status,
        "total_objects": task.total_objects, "total_inference_time": task.total_inference_time,
        "message": task.error_message or "",
    }


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
    """获取检测任务详情及结果（含 key_frames / snapshot_frames）"""
    from app.entity.db_models import DetectionResult
    task = detection_service.get_task_by_id(db=db, task_id=task_id)
    results = db.query(DetectionResult).filter(DetectionResult.task_id == task_id).all()
    class_counts = {}
    for r in results:
        class_counts[r.class_name] = class_counts.get(r.class_name, 0) + 1
    # 解析 analysis_report 中的 key_frames / snapshot_frames
    key_frames = []
    if task.analysis_report:
        try:
            report = json.loads(task.analysis_report) if isinstance(task.analysis_report, str) else task.analysis_report
            key_frames = report if isinstance(report, list) else report.get("key_frames", [])
        except: pass
    return {
        "task": {
            "id": task.id, "user_id": task.user_id, "scene_id": task.scene_id,
            "scene_name": task.scene.display_name if task.scene else None,
            "model_version_id": task.model_version_id, "task_type": task.task_type,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "total_images": task.total_images, "total_objects": task.total_objects,
            "total_inference_time": task.total_inference_time,
            "conf_threshold": task.conf_threshold, "iou_threshold": task.iou_threshold,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        "class_counts": class_counts,
        "results": [{"id": r.id, "class_name": r.class_name, "class_name_cn": r.class_name_cn,
                      "class_id": r.class_id, "confidence": r.confidence, "bbox": r.bbox,
                      "image_path": r.image_path, "inference_time": r.inference_time}
                     for r in results],
        "key_frames": key_frames,
    }


@router.get("/list", summary="获取检测任务列表")
async def list_detection_tasks(
    page: int = 1,
    page_size: int = 20,
    status_filter: str = None,
    task_type: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取当前用户的检测任务分页列表"""
    from app.entity.db_models import DetectionTask as DT, DetectionResult, TaskStatus
    query = db.query(DT).filter(DT.user_id == current_user.id)
    if status_filter:
        # 兼容大小写（DB 存 UPPERCASE enum，前端传 lowercase）
        try:
            status_val = getattr(TaskStatus, status_filter.upper())
        except (AttributeError, TypeError):
            status_val = status_filter
        query = query.filter(DT.status == status_val)
    if task_type:
        query = query.filter(DT.task_type == task_type)
    total = query.count()
    tasks = query.order_by(DT.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for t in tasks:
        results = db.query(DetectionResult).filter(DetectionResult.task_id == t.id).all()
        items.append({
            "id": t.id, "task_type": t.task_type,
            "status": t.status.value if hasattr(t.status, "value") else t.status,
            "total_images": t.total_images, "total_objects": t.total_objects,
            "total_inference_time": t.total_inference_time,
            "class_names": list(set(r.class_name for r in results)),
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })
    return {"code": 200, "data": {"total": total, "page": page, "page_size": page_size, "items": items}}


# ── Camera WebSocket ────────────────────────────────────────────
_camera_frame_buffer = {}

@router.websocket("/camera")
async def camera_detection_ws(websocket: WebSocket):
    """摄像头实时检测 WebSocket（config/frame/close协议）"""
    from app.core.security import decode_access_token
    from jose import JWTError

    token = websocket.query_params.get("token")
    if not token: await websocket.close(code=4001); return
    try:
        payload = decode_access_token(token)
        uid = int(payload.get("sub", 0))
        if not uid: raise JWTError("Invalid")
    except (JWTError, ValueError): await websocket.close(code=4001); return

    await websocket.accept()
    connection_id = id(websocket)
    logger.info("Camera WS connected: id=%d user=%d", connection_id, uid)
    mode = "cpu"; conf = 0.25; iou = 0.45; model = None
    scene_id = None; total_objects = 0; class_counts = {}; snapshot_frames = []
    frame_count = 0; fps_start_time = time.time(); fps_frame_count = 0

    async def _finalize_and_notify():
        """关闭时保存会话到 Service 层并通知前端"""
        nonlocal total_objects, class_counts, snapshot_frames
        try:
            result = detection_service.save_camera_session(
                user_id=uid, scene_id=scene_id or 1,
                conf=conf, iou=iou,
                total_objects=total_objects,
                class_counts=class_counts,
                snapshot_frames=snapshot_frames,
            )
            await websocket.send_json({
                "type": "close_ok", "task_id": result["task_id"],
                "total_objects": result["total_objects"],
                "class_counts": result["class_counts"],
            })
        except Exception as e:
            logger.error("Camera session save error: %s", str(e))

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "config":
                mode = data.get("mode", "cpu"); conf = data.get("conf", 0.25)
                iou = data.get("iou", 0.45); scene_id = data.get("scene_id")
                try:
                    model = detection_service._get_model(scene_id)
                    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
                    model.predict(source=dummy, conf=conf, iou=iou, imgsz=640,
                                  device="cpu" if mode == "cpu" else "0", save=False, verbose=False)
                    logger.info("Camera model warmed up, mode: %s", mode)
                except Exception as e:
                    logger.error("Camera model load failed: %s", str(e))
                    await websocket.send_json({"type": "error", "message": f"Model load failed: {str(e)}"})
                    continue
                await websocket.send_json({"type": "config_ok", "mode": mode, "message": f"Config OK, mode: {mode}"})

            elif msg_type == "frame":
                if model is None:
                    await websocket.send_json({"type": "error", "message": "Send config first"}); continue
                frame_b64 = data.get("data", "")
                if not frame_b64: continue
                try:
                    img_bytes = base64.b64decode(frame_b64)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is None: continue
                    device = "cpu" if mode == "cpu" else "0"
                    imgsz = 416 if mode == "cpu" else 640
                    results = model.predict(source=frame, conf=conf, iou=iou, imgsz=imgsz,
                                            device=device, save=False, verbose=False, half=False)
                    result = results[0]
                    inference_time = float(result.speed.get("inference", 0))
                    annotated_img = result.plot()
                    _, buffer = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    annotated_b64 = base64.b64encode(buffer).decode("utf-8")
                    detections = []
                    if result.boxes is not None and len(result.boxes) > 0:
                        for box in result.boxes:
                            cls_id = int(box.cls[0])
                            cls_name = model.names.get(cls_id, f"class_{cls_id}")
                            cf = float(box.conf[0])
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            detections.append({"class_name": cls_name, "class_id": cls_id,
                                               "confidence": round(cf, 4),
                                               "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]})
                            total_objects += 1
                            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                        if len(snapshot_frames) < 10:
                            snapshot_frames.append(annotated_b64)
                    # FPS 计算
                    fps_frame_count += 1
                    elapsed = time.time() - fps_start_time
                    current_fps = round(fps_frame_count / elapsed, 1) if elapsed >= 1.0 else 0
                    if elapsed >= 1.0: fps_frame_count = 0; fps_start_time = time.time()
                    frame_count += 1
                    await websocket.send_json({
                        "type": "result", "annotated_frame": annotated_b64,
                        "detections": detections, "object_count": len(detections),
                        "inference_time": round(inference_time, 2),
                        "fps": current_fps, "frame_count": frame_count,
                    })
                except Exception as e:
                    logger.error("Camera frame error: %s", str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif msg_type == "close":
                logger.info("Camera WS closed by client: id=%d", connection_id)
                await _finalize_and_notify()
                await websocket.close()
                return

    except WebSocketDisconnect:
        logger.info("Camera WS disconnected: id=%d", connection_id)
        await _finalize_and_notify()
    except Exception as e:
        logger.error("Camera WS error: %s", str(e), exc_info=True)
    finally:
        _camera_frame_buffer.pop(connection_id, None)
        logger.info("Camera WS ended: id=%d, frames=%d", connection_id, frame_count)