"""
检测任务服务层
处理单图检测、批量检测、任务 CRUD 及结果管理等业务逻辑
"""
import uuid
import os
import json
import cv2
import zipfile
import tempfile
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.logger import get_logger
from app.entity.db_models import DetectionTask, DetectionResult, TaskStatus, DetectionScene, ModelVersion
from app.entity.schemas import DetectionTaskResponse, DetectionResultResponse
from app.services.yolo_inference import detect, batch_detect, load_model, list_camera_devices, DEFAULT_CLASS_NAMES

logger = get_logger(__name__)


class DetectionService:
    """检测任务服务"""

    @staticmethod
    def list_tasks(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        scene_id: int | None = None,
        status: str | None = None,
        task_type: str | None = None,
        user_id: int | None = None,
        batch_id: int | None = None,
        keyword: str | None = None,
    ) -> tuple[list[dict], int]:
        """
        获取检测任务分页列表
        返回: (任务列表, 总数)
        """
        query = db.query(DetectionTask).options(joinedload(DetectionTask.scene))

        # 筛选条件
        if scene_id:
            query = query.filter(DetectionTask.scene_id == scene_id)
        if status:
            query = query.filter(DetectionTask.status == status)
        if task_type:
            query = query.filter(DetectionTask.task_type == task_type)
        if user_id:
            query = query.filter(DetectionTask.user_id == user_id)
        if batch_id:
            query = query.filter(DetectionTask.batch_id == batch_id)
        if keyword:
            query = query.filter(
                or_(
                    DetectionTask.id.cast(str).ilike(f"%{keyword}%"),
                )
            )

        # 计算总数
        total = query.count()

        # 分页
        query = query.order_by(DetectionTask.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        tasks = query.all()
        
        # 转换为可序列化的字典列表
        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "user_id": task.user_id,
                "scene_id": task.scene_id,
                "scene_name": task.scene.display_name if task.scene else None,
                "model_version_id": task.model_version_id,
                "task_type": task.task_type,
                "source": task.source,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "conf_threshold": task.conf_threshold,
                "iou_threshold": task.iou_threshold,
                "error_message": task.error_message,
                "batch_id": task.batch_id,
                "analysis_report": task.analysis_report,
                "analysis_suggestion": task.analysis_suggestion,
                "risk_level": task.risk_level,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
            })
        
        return result, total

    @staticmethod
    def get_task_by_id(db: Session, task_id: int) -> DetectionTask:
        """根据 ID 获取任务详情（含检测结果）"""
        task = (
            db.query(DetectionTask)
            .options(joinedload(DetectionTask.results))
            .options(joinedload(DetectionTask.scene))
            .filter(DetectionTask.id == task_id)
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="检测任务不存在")
        return task

    @staticmethod
    def create_single_task(
        db: Session,
        scene_id: int,
        user_id: int | None,
        model_version_id: int | None = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        batch_id: int | None = None,
        source: str = "manual",
    ) -> DetectionTask:
        """创建单图检测任务"""
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            model_version_id=model_version_id,
            task_type="single",
            source=source,
            status=TaskStatus.PENDING,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            batch_id=batch_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def create_batch_task(
        db: Session,
        scene_id: int,
        user_id: int | None,
        model_version_id: int | None = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        batch_id: int | None = None,
        image_count: int = 0,
        source: str = "manual",
    ) -> DetectionTask:
        """创建批量检测任务"""
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            model_version_id=model_version_id,
            task_type="batch",
            source=source,
            status=TaskStatus.PENDING,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            batch_id=batch_id,
            total_images=image_count,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update_task_status(
        db: Session,
        task_id: int,
        status: TaskStatus,
        error_message: str | None = None,
    ) -> DetectionTask:
        """更新任务状态"""
        task = DetectionService.get_task_by_id(db, task_id)
        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
        if error_message:
            task.error_message = error_message
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete_task(db: Session, task_id: int) -> None:
        """删除检测任务（级联删除关联结果）"""
        task = DetectionService.get_task_by_id(db, task_id)
        db.delete(task)
        db.commit()

    @staticmethod
    def get_task_results(
        db: Session,
        task_id: int,
        page: int = 1,
        page_size: int = 50,
        class_name: str | None = None,
        review_status: str | None = None,
        min_confidence: float | None = None,
    ) -> tuple[list[DetectionResult], int]:
        """获取任务的检测结果列表"""
        task = DetectionService.get_task_by_id(db, task_id)

        query = db.query(DetectionResult).filter(DetectionResult.task_id == task_id)

        if class_name:
            query = query.filter(DetectionResult.class_name == class_name)
        if review_status:
            query = query.filter(DetectionResult.review_status == review_status)
        if min_confidence is not None:
            query = query.filter(DetectionResult.confidence >= min_confidence)

        total = query.count()
        query = query.order_by(DetectionResult.confidence.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        results = query.all()
        return results, total

    @staticmethod
    def save_result(
        db: Session,
        task_id: int,
        image_path: str,
        class_name: str,
        class_name_cn: str | None,
        class_id: int,
        confidence: float,
        bbox: list,
        annotated_image_url: str | None = None,
        inference_time: float | None = None,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> DetectionResult:
        """保存单条检测结果"""
        result = DetectionResult(
            task_id=task_id,
            image_path=image_path,
            annotated_image_url=annotated_image_url,
            class_name=class_name,
            class_name_cn=class_name_cn,
            class_id=class_id,
            confidence=confidence,
            bbox=bbox,
            inference_time=inference_time,
            image_width=image_width,
            image_height=image_height,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def save_results_batch(
        db: Session,
        task_id: int,
        results_data: list[dict],
    ) -> list[DetectionResult]:
        """批量保存检测结果"""
        results = []
        for data in results_data:
            result = DetectionResult(
                task_id=task_id,
                image_path=data["image_path"],
                annotated_image_url=data.get("annotated_image_url"),
                class_name=data["class_name"],
                class_name_cn=data.get("class_name_cn"),
                class_id=data["class_id"],
                confidence=data["confidence"],
                bbox=data["bbox"],
                inference_time=data.get("inference_time"),
                image_width=data.get("image_width"),
                image_height=data.get("image_height"),
            )
            db.add(result)
            results.append(result)

        db.commit()
        for r in results:
            db.refresh(r)
        return results

    @staticmethod
    def detect_single(
        image_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        单图快捷检测（跳过 LLM，直接调用 YOLO）
        
        Args:
            image_path: 图像文件路径
            conf: 置信度阈值
            iou: IoU 阈值
            scene_id: 检测场景 ID
            user_id: 用户 ID
        
        Returns:
            检测结果字典
        """
        db = SessionLocal()
        task = None
        try:
            scene_id = DetectionService._resolve_scene_id(db, scene_id)
            mv = DetectionService._get_default_model_version(db, scene_id)
            # 1. 先创建任务
            task = DetectionTask(user_id=user_id, scene_id=scene_id,
                task_type="single", status=TaskStatus.PENDING,
                model_version_id=mv.id if mv else None,
                conf_threshold=conf, iou_threshold=iou)
            db.add(task); db.flush()
            # 2. 推理
            model_path = DetectionService._get_model_path(db, scene_id)
            result = detect(model_path=model_path, image_path=image_path,
                            conf_threshold=conf, iou_threshold=iou)
            result["task_type"] = "single"; result["task_id"] = task.id
            # 3. 存结果
            for d in result.get("defects", []):
                db.add(DetectionResult(task_id=task.id, image_path=image_path,
                    class_name=d["class_name"], class_name_cn=d.get("class_name_cn"),
                    class_id=d["class_id"], confidence=d["confidence"], bbox=d["bbox"],
                    inference_time=d.get("inference_time"),
                    image_width=result.get("image_width"), image_height=result.get("image_height")))
            # 4. 更新状态
            task.status = TaskStatus.COMPLETED
            task.total_images = 1
            task.total_objects = len(result.get("defects", []))
            task.total_inference_time = result.get("inference_time", 0)
            task.completed_at = datetime.now()
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            if task:
                try:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    db.commit()
                except: pass
            raise
        finally:
            db.close()

    @staticmethod
    def detect_batch(
        image_paths: list[str],
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        批量快捷检测
        
        Args:
            image_paths: 图像文件路径列表
            conf: 置信度阈值
            scene_id: 检测场景 ID
            user_id: 用户 ID
        
        Returns:
            检测结果字典
        """
        db = SessionLocal()
        task = None
        try:
            scene_id = DetectionService._resolve_scene_id(db, scene_id)
            mv = DetectionService._get_default_model_version(db, scene_id)
            # 1. 先创建任务
            task = DetectionTask(user_id=user_id, scene_id=scene_id,
                task_type="batch", status=TaskStatus.PENDING,
                model_version_id=mv.id if mv else None,
                total_images=len(image_paths), conf_threshold=conf)
            db.add(task); db.flush()
            # 2. 推理
            model_path = DetectionService._get_model_path(db, scene_id)
            results = batch_detect(model_path=model_path, image_paths=image_paths, conf_threshold=conf)
            total_objects = sum(len(r.get("defects", [])) for r in results)
            total_inference_time = sum(r.get("inference_time", 0) for r in results)
            # 3. 存结果
            for r in results:
                for d in r.get("defects", []):
                    db.add(DetectionResult(task_id=task.id, image_path=r.get("image_path", ""),
                        class_name=d["class_name"], class_name_cn=d.get("class_name_cn"),
                        class_id=d["class_id"], confidence=d["confidence"], bbox=d["bbox"],
                        inference_time=d.get("inference_time"),
                        image_width=r.get("image_width"), image_height=r.get("image_height")))
            # 4. 更新状态
            task.status = TaskStatus.COMPLETED
            task.total_images = len(results)
            task.total_objects = total_objects
            task.total_inference_time = total_inference_time
            task.completed_at = datetime.now()
            db.commit()
            return {
                "success": True, "task_type": "batch", "task_id": task.id,
                "total_images": len(results), "total_objects": total_objects,
                "total_inference_time": total_inference_time, "results": results,
            }
        except Exception as e:
            db.rollback()
            if task:
                try:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    db.commit()
                except: pass
            raise
        finally:
            db.close()

    @staticmethod
    def detect_zip(
        zip_path: str,
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        ZIP 文件检测：解压 ZIP 并批量检测其中所有图像
        
        Args:
            zip_path: ZIP 文件路径
            conf: 置信度阈值
            scene_id: 检测场景 ID
            user_id: 用户 ID
        
        Returns:
            检测结果字典
        """
        db = SessionLocal()
        try:
            scene_id = DetectionService._resolve_scene_id(db, scene_id)
            mv = DetectionService._get_default_model_version(db, scene_id)
            model_path = DetectionService._get_model_path(db, scene_id)

            image_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(tmp_dir)

                image_paths = []
                for root, dirs, files in os.walk(tmp_dir):
                    for f in files:
                        if f.lower().endswith(image_extensions):
                            image_paths.append(os.path.join(root, f))

                if not image_paths:
                    return {
                        "success": False,
                        "error": "ZIP 文件中没有找到图像文件",
                    }

                # 1. 先创建任务
                task = DetectionTask(user_id=user_id, scene_id=scene_id,
                    task_type="zip", status=TaskStatus.PENDING,
                    model_version_id=mv.id if mv else None,
                    total_images=len(image_paths), conf_threshold=conf)
                db.add(task); db.flush()

                # 2. 推理
                results = batch_detect(
                    model_path=model_path,
                    image_paths=image_paths,
                    conf_threshold=conf,
                )

                total_objects = sum(len(r.get("defects", [])) for r in results)
                total_inference_time = sum(r.get("inference_time", 0) for r in results)

                try:
                    # 2. 存结果
                    for r in results:
                        for d in r.get("defects", []):
                            db.add(DetectionResult(task_id=task.id, image_path=r.get("image_path", ""),
                                class_name=d["class_name"], class_name_cn=d.get("class_name_cn"),
                                class_id=d["class_id"], confidence=d["confidence"], bbox=d["bbox"],
                                inference_time=d.get("inference_time"),
                                image_width=r.get("image_width"), image_height=r.get("image_height")))
                    # 3. 更新状态
                    task.status = TaskStatus.COMPLETED
                    task.total_images = len(results)
                    task.total_objects = total_objects
                    task.total_inference_time = total_inference_time
                    task.completed_at = datetime.now()
                    db.commit()
                except Exception as e:
                    db.rollback()
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    db.commit()
                    raise

                return {
                    "success": True, "task_type": "zip", "task_id": task.id,
                    "total_images": len(results), "total_objects": total_objects,
                    "total_inference_time": total_inference_time, "results": results,
                }
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def detect_video(
        video_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        frame_sample_rate: int = 5,
        max_frames: int = 50,
        use_scene_detection: bool = True,
        scene_threshold: float = 10.0,
        scene_id: int = None,
        user_id: int = None,
        task_id: int = None,
        progress_callback=None,
    ) -> dict:
        """
        视频检测 — 支持两种模式：

        【模式 A】帧采样（use_scene_detection=False）：
          每 frame_sample_rate 帧取 1 帧 → YOLO 推理 → 非采样帧复用上次结果

        【模式 B】场景变化检测（use_scene_detection=True，默认）：
          灰度帧差 > scene_threshold → YOLO 推理 → 变化帧间复用结果
          去重策略：灰度图相似度 + 类别分布双重比对（防止 YOLO 抖动导致重复帧）
        """
        import base64 as b64
        import subprocess, shutil
        from app.storage.minio_client import MinIOClient

        db = SessionLocal()
        try:
            model = load_model(DetectionService._get_model_path(db, scene_id))

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": f"无法打开视频文件: {video_path}"}

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration_seconds = total_frames / fps if fps > 0 else 0

            logger.info("视频信息: %d×%d, %.1ffps, %d 帧, %.1f 秒",
                        width, height, fps, total_frames, duration_seconds)

            # 1. 复用已有任务或创建新任务
            if task_id:
                task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                if not task:
                    return {"error": f"任务不存在: {task_id}"}
                task.status = TaskStatus.PROCESSING
            else:
                task = DetectionTask(user_id=user_id,
                    scene_id=DetectionService._resolve_scene_id(db, scene_id),
                    task_type="video", status=TaskStatus.PENDING,
                    conf_threshold=conf, iou_threshold=iou)
                db.add(task); db.flush(); task_id = task.id

            # 计算采样帧索引（帧采样模式用）
            effective_interval = max(frame_sample_rate, total_frames // max_frames)
            sample_indices = list(range(0, total_frames, effective_interval))
            if len(sample_indices) > max_frames:
                sample_indices = sample_indices[:max_frames]
            sample_set = set(sample_indices)

            if task:
                task.total_images = len(sample_indices)
                db.commit()

            # 2. 逐帧处理
            key_frames = []; total_objects = 0; total_inference_time = 0; class_counts = {}
            last_detections = []; last_frame_gray = None
            last_kf_gray = None; last_class_dist = None

            # 按类别分色（与本地代码一致）
            class_colors = {
                "missing_hole": (0, 255, 0),
                "mouse_bite": (255, 0, 0),
                "open_circuit": (0, 0, 255),
                "short": (255, 255, 0),
                "spur": (255, 0, 255),
                "spurious_copper": (0, 255, 255),
            }

            def get_color(cls_name):
                return class_colors.get(cls_name, (255, 128, 0))

            def draw_detections_on_frame(fr, dets):
                annotated = fr.copy()
                for d in dets:
                    x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
                    color = get_color(d["class_name"])
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    label = f"{d['class_name']} {d['confidence']:.2f}"
                    cv2.putText(annotated, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                return annotated

            def process_detections(result):
                """从 YOLO 结果中提取检测列表和推理时间"""
                fdets = []
                if result.boxes is not None:
                    for box in result.boxes:
                        cid = int(box.cls[0])
                        cn = model.names.get(cid, f"class_{cid}")
                        cf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        fdets.append({"class_name": cn, "class_id": cid, "confidence": round(cf, 4),
                                      "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]})
                itime = float(result.speed.get("inference", 0))
                return fdets, itime

            def save_keyframe(fidx, fdets, itime, annotated_img):
                """保存关键帧结果并写入数据库"""
                nonlocal total_objects, total_inference_time
                ab64 = b64.b64encode(
                    cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 70])[1]
                ).decode("utf-8")
                key_frames.append({
                    "frame_index": fidx, "timestamp": round(fidx / fps, 2),
                    "annotated_image_base64": ab64, "object_count": len(fdets),
                    "detections": fdets, "inference_time": round(itime, 2),
                })
                for d in fdets:
                    total_objects += 1
                    class_counts[d["class_name"]] = class_counts.get(d["class_name"], 0) + 1
                    db.add(DetectionResult(task_id=task_id or task.id,
                        image_path=f"frame_{fidx}.jpg",
                        class_name=d["class_name"], class_id=d["class_id"],
                        confidence=d["confidence"], bbox=d["bbox"], inference_time=itime))

            # 创建标注视频输出
            project_tmp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
            os.makedirs(project_tmp, exist_ok=True)
            out_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, dir=project_tmp)
            output_video_path = out_tmp.name; out_tmp.close()
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret: break

                # 灰度缩略图（场景检测 + 去重用）
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_small = cv2.resize(gray, (100, 100))

                should_detect = False
                if use_scene_detection:
                    # 场景变化：灰度帧差 > 阈值
                    if last_frame_gray is None:
                        should_detect = True
                    elif cv2.absdiff(last_frame_gray, gray_small).mean() > scene_threshold:
                        should_detect = True
                else:
                    # 帧采样模式
                    should_detect = frame_idx in sample_set
                last_frame_gray = gray_small.copy()

                if should_detect:
                    results = model.predict(source=frame, conf=conf, iou=iou, imgsz=640,
                                            device="cpu", save=False, verbose=False)
                    fdets, itime = process_detections(results[0])
                    last_detections = fdets
                    total_inference_time += itime
                    annotated = draw_detections_on_frame(frame, fdets)
                    video_writer.write(annotated)

                    # 去重：灰度相似 + 类别分布双重比对
                    is_dup_gray = False
                    if last_kf_gray is not None:
                        is_dup_gray = cv2.absdiff(last_kf_gray, gray_small).mean() <= scene_threshold
                    cur_dist = {}
                    for d in fdets:
                        cur_dist[d["class_name"]] = cur_dist.get(d["class_name"], 0) + 1
                    is_dup_class = (cur_dist == last_class_dist)

                    if not is_dup_gray or not is_dup_class:
                        last_kf_gray = gray_small.copy()
                        last_class_dist = cur_dist
                        save_keyframe(frame_idx, fdets, itime, annotated)
                        if task:
                            task.total_objects = total_objects
                            db.commit()
                else:
                    if last_detections:
                        video_writer.write(draw_detections_on_frame(frame, last_detections))
                    else:
                        video_writer.write(frame)

                frame_idx += 1

            cap.release(); video_writer.release()

            # 3. ffmpeg H.264 转码
            h264_path = output_video_path.replace(".mp4", "_h264.mp4")
            try:
                subprocess.run([
                    shutil.which("ffmpeg") or "ffmpeg", "-y",
                    "-i", output_video_path, "-c:v", "libx264",
                    "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", h264_path,
                ], capture_output=True, timeout=300, check=True)
                os.replace(h264_path, output_video_path)
                logger.info("视频已转码为 H.264 格式")
            except Exception as e:
                logger.warning("ffmpeg 转码失败: %s", str(e))
                try: os.unlink(h264_path)
                except: pass

            # 4. MinIO 上传
            annotated_video_url = None
            try:
                minio_client = MinIOClient()
                annotated_video_url = minio_client.upload_file(
                    f"detections/{task_id or task.id}/annotated_video.mp4", output_video_path)
                logger.info("标注视频已上传: detections/%d/annotated_video.mp4", task_id or task.id)
            except Exception as e:
                logger.warning("标注视频上传 MinIO 失败: %s", str(e))
            try: os.unlink(output_video_path)
            except: pass

            # 5. 更新任务
            if task:
                task.status = TaskStatus.COMPLETED
                task.total_objects = total_objects
                task.total_inference_time = total_inference_time
                task.completed_at = datetime.now()
                db.commit()

            logger.info("视频检测完成: %d 帧处理, %d 关键帧, %d 目标, %.2fms",
                        frame_idx, len(key_frames), total_objects, total_inference_time)

            return {
                "task_id": task_id or (task.id if task else None),
                "total_frames": total_frames,
                "processed_frames": len(key_frames),
                "frame_sample_rate": frame_sample_rate,
                "fps": round(fps, 2),
                "duration_seconds": round(duration_seconds, 2),
                "video_resolution": {"width": width, "height": height},
                "total_objects": total_objects,
                "class_counts": class_counts,
                "key_frames": key_frames,
                "annotated_video_url": annotated_video_url,
                "total_inference_time": round(total_inference_time, 2),
                "success": True, "task_type": "video",
                "results": [d for kf in key_frames for d in kf.get("detections", [])],
            }

        except Exception as e:
            logger.error("视频检测异常: %s", str(e), exc_info=True)
            if task_id:
                try:
                    t = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                    if t: t.status = TaskStatus.FAILED; t.error_message = str(e); db.commit()
                except: pass
            return {"error": f"视频检测失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def create_video_task(user_id: int, scene_id: int = None, conf: float = 0.25) -> int:
        """创建视频检测任务（由 API 层调用）"""
        db = SessionLocal()
        try:
            scene_id = DetectionService._resolve_scene_id(db, scene_id)
            task = DetectionTask(user_id=user_id, scene_id=scene_id,
                task_type="video", status=TaskStatus.PENDING, conf_threshold=conf)
            db.add(task); db.flush(); task_id = task.id; db.commit()
            return task_id
        finally:
            db.close()

    @staticmethod
    def _resolve_scene_id(db: Session, scene_id: int = None) -> int:
        """解析场景 ID：未传入时自动查询第一个可用场景"""
        if scene_id:
            return scene_id
        scene = db.query(DetectionScene).filter(DetectionScene.deleted_at == None).first()
        if scene:
            return scene.id
        return 1

    @staticmethod
    def _get_default_model_version(db: Session, scene_id: int):
        """获取场景的默认模型版本"""
        return db.query(ModelVersion).filter(
            ModelVersion.scene_id == scene_id,
            ModelVersion.is_default == True,
            ModelVersion.status == "active",
        ).first() or db.query(ModelVersion).filter(
            ModelVersion.status == "active",
        ).order_by(ModelVersion.created_at.desc()).first()

    @staticmethod
    def list_cameras() -> list:
        """
        枚举可用的摄像头设备
        
        Returns:
            设备列表
        """
        return list_camera_devices()

    @staticmethod
    def save_camera_session(user_id: int, scene_id: int, conf: float, iou: float,
                            total_objects: int, class_counts: dict, snapshot_frames: list) -> dict:
        """保存摄像头检测会话到数据库"""
        db = SessionLocal()
        try:
            task = DetectionTask(user_id=user_id,
                scene_id=DetectionService._resolve_scene_id(db, scene_id),
                task_type="camera", status=TaskStatus.COMPLETED,
                total_images=len(snapshot_frames), total_objects=total_objects,
                conf_threshold=conf, iou_threshold=iou,
                completed_at=datetime.now())
            db.add(task); db.flush()
            task.analysis_report = json.dumps(
                {"class_counts": class_counts, "snapshot_frames": snapshot_frames},
                ensure_ascii=False)
            db.commit()
            logger.info("Camera session saved: task_id=%d, objects=%d", task.id, total_objects)
            return {"task_id": task.id, "total_objects": total_objects, "class_counts": class_counts}
        except Exception as e:
            logger.error("Camera session save error: %s", str(e))
            db.rollback(); raise
        finally:
            db.close()

    @staticmethod
    def _get_model(scene_id: int = None):
        """加载模型实例（用于摄像头等需要模型对象的场景）"""
        from app.services.yolo_inference import load_model
        model_path = DetectionService._get_model_path(scene_id=scene_id)
        return load_model(model_path)

    @staticmethod
    def _get_model_path(db: Session = None, scene_id: int = None) -> str:
        """
        获取场景的默认模型路径

        Args:
            db: 数据库会话（可选）
            scene_id: 检测场景 ID

        Returns:
            模型文件路径
        """
        default_model = None

        if scene_id:
            db_session = db or SessionLocal()
            try:
                default_model = db_session.query(ModelVersion).filter(
                    ModelVersion.scene_id == scene_id,
                    ModelVersion.is_default == True,
                    ModelVersion.status == "active",
                ).first()
            finally:
                if not db:
                    db_session.close()

        if not default_model:
            db_session = db or SessionLocal()
            try:
                default_model = db_session.query(ModelVersion).filter(
                    ModelVersion.status == "active",
                ).order_by(ModelVersion.created_at.desc()).first()
            finally:
                if not db:
                    db_session.close()

        if default_model and os.path.exists(default_model.model_path):
            return default_model.model_path

        default_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "models",
            "best.pt",
        )
        
        if os.path.exists(default_path):
            return default_path
        
        raise HTTPException(status_code=500, detail="未找到可用的模型文件")


from app.database.session import SessionLocal

# 全局单例
detection_service = DetectionService()
