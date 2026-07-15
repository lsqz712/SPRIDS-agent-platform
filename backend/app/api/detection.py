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
import asyncio
import threading
import time
import json
import base64
import cv2
import numpy as np
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionTask
from app.services.detection_service import detection_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/detection", tags=["快捷检测"])
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

# ── Redis 视频任务进度存储 ──
from app.storage.redis_client import redis_client


@router.post("/video", summary="视频检测")
async def detect_video_api(
    file: UploadFile = File(..., description="视频文件（mp4/avi/mov）"),
    conf: float = Form(0.25, description="置信度阈值"),
    frame_sample_rate: int = Form(5, description="帧采样间隔（每 N 帧取 1 帧）"),
    max_frames: int = Form(50, description="最多处理的关键帧数量"),
    scene_id: int = Form(None, description="场景 ID"),
    current_user=Depends(get_current_user),
):
    """
    视频检测：上传视频文件，后台异步处理，通过 status 接口轮询进度

    支持格式：mp4, avi, mov, mkv, wmv, flv
    文件大小限制：50MB
    """
    # ── 校验文件格式 ──
    allowed_video_types = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_video_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": f"不支持的视频格式: {suffix}，"
                f"支持的格式: {', '.join(allowed_video_types)}"
            },
        )

    # ── 保存视频到临时文件 ──
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    logger.info(
        "视频文件已保存: %s (%.2f MB), 用户: %s",
        tmp_path,
        len(content) / (1024 * 1024),
        current_user.username,
    )

    # ── 先创建检测任务记录 ──
    db = SessionLocal()
    try:
        task = DetectionTask(
            user_id=current_user.id,
            scene_id=scene_id or 1,
            task_type="video",
            status="processing",
            conf_threshold=conf,
        )
        db.add(task)
        db.flush()
        task_id = task.id
        db.commit()
    finally:
        db.close()

    # ── 初始化进度信息 ──
    redis_client.set_json(f"video_task:{task_id}", {
        "status": "processing",
        "progress": 0,
        "message": "视频处理中...",
    }, expire=3600)

    def run_video_detection():
        """后台线程：执行视频检测"""
        try:
            result = detection_service.detect_video(
                video_path=tmp_path,
                conf=conf,
                frame_sample_rate=frame_sample_rate,
                max_frames=max_frames,
                scene_id=scene_id,
                user_id=current_user.id,
                task_id=task_id,
            )

            if "error" in result:
                redis_client.set_json(f"video_task:{task_id}", {
                    "status": "failed",
                    "progress": 0,
                    "message": result["error"],
                }, expire=3600)
            else:
                redis_client.set_json(f"video_task:{task_id}", {
                    "status": "completed",
                    "progress": 100,
                    "message": f"检测完成，共处理 {result['processed_frames']} 帧，"
                    f"发现 {result['total_objects']} 个目标",
                    "result": result,
                }, expire=3600)
        except Exception as e:
            logger.error("视频后台检测异常: %s", str(e), exc_info=True)
            redis_client.set_json(f"video_task:{task_id}", {
                "status": "failed",
                "progress": 0,
                "message": f"视频检测异常: {str(e)}",
            }, expire=3600)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    thread = threading.Thread(target=run_video_detection, daemon=True)
    thread.start()

    return {
        "task_id": task_id,
        "status": "processing",
        "message": "视频已上传，正在后台处理中，请通过 status 接口轮询进度",
        "filename": file.filename,
    }


@router.get("/video/status/{task_id}", summary="查询视频检测进度")
async def get_video_detection_status(
    task_id: int,
    current_user=Depends(get_current_user),
):
    """
    查询视频检测任务的实时进度和结果

    轮询间隔建议：1-2 秒
    """
    # 从 Redis 获取进度信息
    progress_info = redis_client.get_json(f"video_task:{task_id}")

    if progress_info:
        return {
            "task_id": task_id,
            **progress_info,
        }

    # 回退：从数据库查询
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "任务不存在"},
            )

        result = {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects or 0,
        }

        # 如果已完成，查询完整结果
        if task.status == "completed":
            from app.entity.db_models import DetectionResult

            results = (
                db.query(DetectionResult)
                .filter(DetectionResult.task_id == task_id)
                .all()
            )

            class_counts = {}
            for r in results:
                class_counts[r.class_name] = class_counts.get(r.class_name, 0) + 1

            result["class_counts"] = class_counts
            result["total_inference_time"] = task.total_inference_time

        return result
    finally:
        db.close()

@router.get("/list", summary="Detection history")
def list_detections(page: int = 1, page_size: int = 20, current_user=Depends(get_current_user)):
    from app.entity.db_models import DetectionResult
    db = SessionLocal()
    try:
        total = db.query(DetectionTask).filter(DetectionTask.user_id == current_user.id).count()
        tasks = db.query(DetectionTask).filter(DetectionTask.user_id == current_user.id).order_by(DetectionTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        items = []
        for t in tasks:
            results = db.query(DetectionResult).filter(DetectionResult.task_id == t.id).all()
            items.append({"id": t.id, "task_type": t.task_type, "status": t.status, "total_images": t.total_images, "total_objects": t.total_objects, "inference_time": t.total_inference_time, "class_names": list(set(r.class_name for r in results)), "created_at": str(t.created_at)})
        return {"total": total, "page": page, "page_size": page_size, "items": items}
    finally:
        db.close()


@router.get("/detail/{task_id}", summary="Detection detail")
def detection_detail(task_id: int, current_user=Depends(get_current_user)):
    from app.entity.db_models import DetectionResult
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id, DetectionTask.user_id == current_user.id).first()
        if not task: return JSONResponse(status_code=404, content={"error": "Not found"})
        results = db.query(DetectionResult).filter(DetectionResult.task_id == task_id).all()
        kf = []
        if task.analysis_report:
            try: kf = json.loads(task.analysis_report) if isinstance(task.analysis_report, str) else task.analysis_report
            except: pass

        snapshots = kf.get("snapshot_frames", []) if isinstance(kf, dict) else []
        return {"task": {"id": task.id, "task_type": task.task_type, "total_images": task.total_images, "total_objects": task.total_objects, "created_at": str(task.created_at)}, "results": [{"class_name": r.class_name, "confidence": r.confidence, "bbox": r.bbox, "image_path": r.image_path} for r in results], "key_frames": kf if not isinstance(kf, dict) else kf.get("class_counts", {}), "snapshot_frames": snapshots}
    finally:
        db.close()


_camera_frame_buffer = {}

@router.websocket("/camera")
async def camera_detection_ws(websocket: WebSocket):
    """Camera real-time detection WebSocket per Day 09 guide."""
    from app.core.security import decode_access_token
    from app.entity.db_models import DetectionResult
    from jose import JWTError
    import base64, numpy as np, time
    token = websocket.query_params.get("token")
    if not token: await websocket.close(code=4001); return
    try:
        payload = decode_access_token(token)
        uid = int(payload.get("sub", 0))
        if not uid: raise JWTError("Invalid")
    except (JWTError, ValueError): await websocket.close(code=4001); return
    await websocket.accept()
    connection_id = id(websocket)
    logger.info("Camera WS connected: id=%d", connection_id)
    mode = "cpu"; conf = 0.25; iou = 0.45; scene_id = None; model = None
    frame_count = 0; fps_start_time = time.time(); fps_frame_count = 0
    last_frame_time = 0  # CPU 帧丢弃：上次完成处理的时间
    task_id = None; db = None; total_objects = 0; class_counts = {}
    snapshot_frames = []  # 存储缺陷截图 base64
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
                    model.predict(source=dummy, conf=conf, iou=iou, imgsz=640, device="cpu" if mode == "cpu" else "0", save=False, verbose=False)
                    logger.info("Camera model warmed up, mode: %s", mode)
                except Exception as e:
                    logger.error("Model load failed: %s", str(e))
                    await websocket.send_json({"type": "error", "message": f"Model load failed: {str(e)}"})
                    continue
                # 创建数据库任务记录
                db = SessionLocal()
                task = DetectionTask(user_id=uid, scene_id=scene_id or 1, task_type="camera", status="processing", total_images=0, conf_threshold=conf, iou_threshold=iou)
                db.add(task); db.flush(); task_id = task.id; db.commit()
                logger.info("Camera task created: %d", task_id)
                await websocket.send_json({"type": "config_ok", "mode": mode, "message": f"Config OK, mode: {mode}"})
            elif msg_type == "frame":
                if model is None: await websocket.send_json({"type": "error", "message": "Send config first"}); continue
                frame_b64 = data.get("data", "")
                if not frame_b64: continue
                # 记录帧到达时间（用于 CPU 帧丢弃策略的扩展点）
                last_frame_time = time.time()
                try:
                    img_bytes = base64.b64decode(frame_b64)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is None: continue
                    device = "cpu" if mode == "cpu" else "0"
                    imgsz = 416 if mode == "cpu" else 640
                    results = model.predict(source=frame, conf=conf, iou=iou, imgsz=imgsz, device=device, save=False, verbose=False, half=False)
                    result = results[0]
                    inference_time = float(result.speed.get("inference", 0))
                    annotated_img = result.plot()
                    _, buffer = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    annotated_b64 = base64.b64encode(buffer).decode("utf-8")
                    detections = []
                    if result.boxes is not None and len(result.boxes) > 0:
                        for box in result.boxes:
                            cls_id = int(box.cls[0]); cls_name = model.names.get(cls_id, f"class_{cls_id}")
                            cf = float(box.conf[0]); x1,y1,x2,y2 = box.xyxy[0].tolist()
                            detections.append({"class_name": cls_name, "class_id": cls_id, "confidence": round(cf, 4), "bbox": [round(x1,1),round(y1,1),round(x2,1),round(y2,1)]})
                            total_objects += 1
                            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                        # 保存截图（限制最多 10 张）
                        if len(snapshot_frames) < 10:
                            snapshot_frames.append(annotated_b64)
                        # 保存到数据库
                        if db and task_id:
                            for d in detections:
                                db.add(DetectionResult(task_id=task_id, image_path=f"frame_{frame_count}.jpg", class_name=d["class_name"], class_id=d["class_id"], confidence=d["confidence"], bbox=d["bbox"], inference_time=inference_time))
                    fps_frame_count += 1; elapsed = time.time() - fps_start_time
                    current_fps = round(fps_frame_count / elapsed, 1) if elapsed >= 1.0 else 0
                    if elapsed >= 1.0: fps_frame_count = 0; fps_start_time = time.time()
                    frame_count += 1
                    await websocket.send_json({"type": "result", "annotated_frame": annotated_b64, "detections": detections, "object_count": len(detections), "inference_time": round(inference_time, 2), "fps": current_fps, "frame_count": frame_count})
                except Exception as e:
                    logger.error("Camera frame error: %s", str(e))
                    await websocket.send_json({"type": "error", "message": f"Frame failed: {str(e)}"})
            elif msg_type == "close":
                # 关闭摄像头 → 提交历史记录
                if db and task_id:
                    try:
                        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                        if task:
                            task.status = "completed"; task.total_objects = total_objects
                            task.total_inference_time = 0; task.completed_at = datetime.now()
                            task.analysis_report = json.dumps({"class_counts": class_counts, "snapshot_frames": snapshot_frames}, ensure_ascii=False)
                            db.commit()
                            logger.info("Camera task %d completed: %d objects, %d snapshots", task_id, total_objects, len(snapshot_frames))
                            await websocket.send_json({"type": "close_ok", "task_id": task_id, "total_objects": total_objects, "class_counts": class_counts})
                    except Exception as e:
                        logger.error("Camera task finalize error: %s", str(e))
                logger.info("Camera WS closed by client: id=%d", connection_id)
                await websocket.close()
                return
    except WebSocketDisconnect:
        logger.info("Camera WS disconnected: id=%d", connection_id)
    except Exception as e:
        logger.error("Camera WS error: %s", str(e), exc_info=True)
    finally:
        if db:
            try: db.close()
            except: pass
        _camera_frame_buffer.pop(connection_id, None)
        logger.info("Camera WS ended: id=%d, frames=%d", connection_id, frame_count)


