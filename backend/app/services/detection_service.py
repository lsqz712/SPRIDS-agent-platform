"""
目标检测服务 — 封装 YOLOv11 推理逻辑

职责：
  - 单图检测（detect_single）
  - 批量检测（detect_batch）
  - ZIP 解压 + 批量检测（detect_zip）
  - 结果持久化（MinIO 存储标注图 + PostgreSQL 存储检测结果）

架构：
  DetectionService 是无状态的纯服务，被 Agent Tool 和快捷按钮 API 共同调用。
  每次检测都会：
    1. 创建 DetectionTask 记录
    2. 运行 YOLO 推理
    3. 上传标注图到 MinIO
    4. 保存 DetectionResult 记录

使用方式：
  from app.services.detection_service import detection_service

  result = detection_service.detect_single(image_path, scene_id, user_id)
"""

import base64
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime

import cv2
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import (
    DetectionResult,
    DetectionScene,
    DetectionTask,
    ModelVersion,
)
from app.storage.minio_client import MinIOClient

logger = get_logger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


class DetectionService:
    """目标检测服务 — 封装 YOLOv11 推理全流程"""

    @staticmethod
    def _get_default_model_path() -> str:
        db = SessionLocal()
        try:
            default_model = (
                db.query(ModelVersion).filter(ModelVersion.is_default == True).first()
            )
            if default_model and os.path.exists(default_model.model_path):
                return default_model.model_path

            from app.entity.db_models import TrainingTask

            latest_task = (
                db.query(TrainingTask)
                .filter(TrainingTask.status == "completed")
                .order_by(TrainingTask.completed_at.desc())
                .first()
            )
            if latest_task:
                weights_path = os.path.join(
                    os.getcwd(),
                    getattr(settings, "TRAIN_OUTPUT_DIR", "runs/train"),
                    f"task_{latest_task.task_uuid}",
                    "weights",
                    "best.pt",
                )
                if os.path.exists(weights_path):
                    return weights_path
        finally:
            db.close()

        return "yolo11n.pt"

    @staticmethod
    def _get_model(scene_id: int = None) -> YOLO:
        model_path = None

        if scene_id:
            db = SessionLocal()
            try:
                default_model = (
                    db.query(ModelVersion)
                    .filter(
                        ModelVersion.scene_id == scene_id,
                        ModelVersion.is_default == True,
                    )
                    .first()
                )
                if default_model and os.path.exists(default_model.model_path):
                    model_path = default_model.model_path
            finally:
                db.close()

        if not model_path:
            model_path = DetectionService._get_default_model_path()

        logger.info("加载检测模型: %s", model_path)
        return YOLO(model_path)

    @staticmethod
    def _save_task_and_results(
        db: Session,
        user_id: int,
        scene_id: int,
        task_type: str,
        detections: list,
        annotated_image: bytes,
        original_filename: str,
        inference_time: float,
        conf: float,
        iou: float,
    ) -> dict:
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            task_type=task_type,
            status="completed",
            total_images=1,
            total_objects=len(detections),
            total_inference_time=inference_time,
            conf_threshold=conf,
            iou_threshold=iou,
            completed_at=datetime.now(),
        )
        db.add(task)
        db.flush()

        annotated_image_url = None
        try:
            minio_client = MinIOClient()
            object_name = f"detections/{task.id}/{original_filename}"
            annotated_image_url = minio_client.upload_bytes(
                object_name, annotated_image, "image/jpeg"
            )
        except Exception as e:
            logger.warning("MinIO 上传失败（不影响检测结果）: %s", str(e))

        for det in detections:
            result = DetectionResult(
                task_id=task.id,
                image_path=original_filename,
                annotated_image_url=annotated_image_url,
                class_name=det["class_name"],
                class_name_cn=det.get("class_name_cn"),
                class_id=det["class_id"],
                confidence=det["confidence"],
                bbox=det["bbox"],
                inference_time=inference_time,
            )
            db.add(result)

        db.commit()
        return {"task_id": task.id, "annotated_image_url": annotated_image_url}

    def detect_single(
        self,
        image_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        db = SessionLocal()
        try:
            if not scene_id:
                default_scene = db.query(DetectionScene).first()
                if default_scene: scene_id = default_scene.id
            model = self._get_model(scene_id)

            results = model.predict(
                source=image_path,
                conf=conf,
                iou=iou,
                imgsz=640,
                device="cpu",
                save=False,
                verbose=False,
            )

            result = results[0]
            detections = []
            total_objects = 0

            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names.get(cls_id, f"class_{cls_id}")
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    detections.append(
                        {
                            "class_name": cls_name,
                            "class_id": cls_id,
                            "confidence": round(confidence, 4),
                            "bbox": [
                                round(x1, 1),
                                round(y1, 1),
                                round(x2, 1),
                                round(y2, 1),
                            ],
                        }
                    )
                    total_objects += 1

            annotated_img = result.plot()
            _, buffer = cv2.imencode(
                ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            annotated_base64 = base64.b64encode(buffer).decode("utf-8")

            class_counts = {}
            for det in detections:
                name = det["class_name"]
                class_counts[name] = class_counts.get(name, 0) + 1

            task_id = None
            annotated_image_url = None
            if user_id and scene_id:
                save_result = self._save_task_and_results(
                    db=db,
                    user_id=user_id,
                    scene_id=scene_id,
                    task_type="single",
                    detections=detections,
                    annotated_image=buffer.tobytes(),
                    original_filename=os.path.basename(image_path),
                    inference_time=float(result.speed.get("inference", 0)),
                    conf=conf,
                    iou=iou,
                )
                task_id = save_result["task_id"]
                annotated_image_url = save_result.get("annotated_image_url")

            logger.info(
                "单图检测完成: %s, 检测到 %d 个目标, 耗时 %.2fms",
                image_path,
                total_objects,
                float(result.speed.get("inference", 0)),
            )

            return {
                "total_objects": total_objects,
                "class_counts": class_counts,
                "detections": detections,
                "annotated_image_base64": annotated_base64,
                "annotated_image_url": annotated_image_url,
                "inference_time": round(float(result.speed.get("inference", 0)), 2),
                "task_id": task_id,
            }

        except Exception as e:
            logger.error("单图检测异常: %s", str(e), exc_info=True)
            return {"error": f"检测失败: {str(e)}"}
        finally:
            db.close()

    def detect_batch(
        self,
        image_paths: list[str],
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        db = SessionLocal()
        try:
            model = self._get_model(scene_id)

            if not scene_id:
                default_scene = db.query(DetectionScene).first()
                if default_scene:
                    scene_id = default_scene.id
                else:
                    return {"error": "数据库中没有可用的检测场景，请先创建检测场景"}

            task = DetectionTask(
                user_id=user_id or 0,
                scene_id=scene_id,
                task_type="batch",
                status="processing",
                total_images=len(image_paths),
                conf_threshold=conf,
            )
            db.add(task)
            db.flush()

            all_detections = []
            annotated_images = []
            total_objects = 0
            total_inference_time = 0
            class_counts = {}

            for i, image_path in enumerate(image_paths):
                results = model.predict(
                    source=image_path,
                    conf=conf,
                    iou=0.45,
                    imgsz=640,
                    device="cpu",
                    save=False,
                    verbose=False,
                )
                result = results[0]
                inference_time = float(result.speed.get("inference", 0))
                total_inference_time += inference_time

                annotated_img = result.plot()
                _, buffer = cv2.imencode(
                    ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85]
                )
                annotated_images.append({
                    "image_path": os.path.basename(image_path),
                    "annotated_image_base64": base64.b64encode(buffer).decode("utf-8"),
                })

                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = model.names.get(cls_id, f"class_{cls_id}")
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        det = {
                            "image_path": image_path,
                            "class_name": cls_name,
                            "class_id": cls_id,
                            "confidence": round(confidence, 4),
                            "bbox": [
                                round(x1, 1),
                                round(y1, 1),
                                round(x2, 1),
                                round(y2, 1),
                            ],
                            "inference_time": inference_time,
                        }
                        all_detections.append(det)
                        total_objects += 1

                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

                    for det in all_detections:
                        if det["image_path"] == image_path:
                            db_result = DetectionResult(
                                task_id=task.id,
                                image_path=image_path,
                                class_name=det["class_name"],
                                class_id=det["class_id"],
                                confidence=det["confidence"],
                                bbox=det["bbox"],
                                inference_time=inference_time,
                            )
                            db.add(db_result)

            task.status = "completed"
            task.total_objects = total_objects
            task.total_inference_time = total_inference_time
            task.completed_at = datetime.now()
            db.commit()

            logger.info(
                "批量检测完成: %d 张图, 共 %d 个目标, 总耗时 %.2fms",
                len(image_paths),
                total_objects,
                total_inference_time,
            )

            return {
                "task_id": task.id,
                "total_images": len(image_paths),
                "total_objects": total_objects,
                "class_counts": class_counts,
                "total_inference_time": round(total_inference_time, 2),
                "detections": all_detections,
                "annotated_images": annotated_images,
            }

        except Exception as e:
            logger.error("批量检测异常: %s", str(e), exc_info=True)
            return {"error": f"批量检测失败: {str(e)}"}
        finally:
            db.close()

    def detect_zip(
        self,
        zip_path: str,
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="rsod_zip_")
            logger.info("解压 ZIP 文件: %s → %s", zip_path, temp_dir)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            image_files = []
            for root, dirs, files in os.walk(temp_dir):
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                        image_files.append(os.path.join(root, fname))

            if not image_files:
                return {"error": "ZIP 文件中没有找到图片"}

            logger.info("ZIP 中包含 %d 张图片，开始批量检测", len(image_files))

            batch_result = self.detect_batch(
                image_paths=image_files,
                conf=conf,
                scene_id=scene_id,
                user_id=user_id,
            )

            batch_result["source"] = "zip"
            batch_result["zip_filename"] = os.path.basename(zip_path)
            batch_result["total_images_in_zip"] = len(image_files)

            return batch_result

        except zipfile.BadZipFile:
            return {"error": f"无效的 ZIP 文件: {zip_path}"}
        except Exception as e:
            logger.error("ZIP 检测异常: %s", str(e), exc_info=True)
            return {"error": f"ZIP 检测失败: {str(e)}"}
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)


    def detect_frame(self, frame, scene_id: int = None) -> dict:
        """Real-time frame detection for WebSocket camera."""
        model = self._get_model(scene_id)
        h, w = frame.shape[:2]
        results = model(frame, conf=0.25, iou=0.45, imgsz=640, device="cpu", verbose=False)
        objects = []
        for r in results:
            if r.boxes:
                for b in r.boxes:
                    cid = int(b.cls[0]); cf = float(b.conf[0])
                    x1,y1,x2,y2 = b.xyxy[0].tolist()
                    objects.append({"class_id":cid,"class_name":model.names.get(cid,"?"),"confidence":round(cf,4),"bbox":[round(x1,2),round(y1,2),round(x2,2),round(y2,2)]})
        return {"total_objects":len(objects),"objects":objects,"image_size":{"width":w,"height":h}}


    def detect_video(
        self,
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
    ) -> dict:
        """
        视频检测 — 支持两种模式：

        【模式 A】帧采样（use_scene_detection=False）：
          每 frame_sample_rate 帧取 1 帧 → YOLO 推理 → 非采样帧复用上次结果

        【模式 B】场景变化检测（use_scene_detection=True，默认）：
          灰度帧差 > scene_threshold → YOLO 推理 → 变化帧间复用结果

        Args:
            video_path: 视频文件路径
            conf: 置信度阈值
            iou: NMS IoU 阈值
            frame_sample_rate: 帧采样间隔（每 N 帧取 1 帧）
            max_frames: 最多处理的关键帧数量（防止视频过长）
            scene_id: 检测场景 ID
            user_id: 操作用户 ID
            task_id: 已创建的检测任务 ID（用于更新进度）

        Returns:
            视频检测结果字典：
            {
                "task_id": int,
                "total_frames": int,          # 视频总帧数
                "processed_frames": int,       # 处理的关键帧数
                "fps": float,                  # 视频原始 fps
                "duration_seconds": float,     # 视频时长（秒）
                "total_objects": int,          # 检测到目标总数
                "class_counts": {...},         # 各类别统计
                "key_frames": [...],           # 关键帧结果列表
                "total_inference_time": float, # 总推理耗时（ms）
            }
        """
        db = SessionLocal()
        try:
            # ── 加载模型 ──
            model = self._get_model(scene_id)

            # ── 打开视频 ──
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": f"无法打开视频文件: {video_path}"}

            # 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration_seconds = total_frames / fps if fps > 0 else 0

            logger.info(
                "视频信息: %d×%d, %.1ffps, %d 帧, %.1f 秒",
                width,
                height,
                fps,
                total_frames,
                duration_seconds,
            )

            # ── 如果没有传入 task_id，创建检测任务 ──
            if not task_id:
                task = DetectionTask(
                    user_id=user_id or 0,
                    scene_id=scene_id or 1,
                    task_type="video",
                    status="processing",
                    total_images=0,  # 后续更新
                    conf_threshold=conf,
                    iou_threshold=iou,
                )
                db.add(task)
                db.flush()
                task_id = task.id
            else:
                task = (
                    db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                )

            # ── 计算需要采样的帧索引 ──
            # 根据视频总帧数和 max_frames 动态计算采样间隔，
            # 确保帧均匀分布在整个视频时长内，避免密集采样导致重复帧
            effective_interval = max(frame_sample_rate, total_frames // max_frames)
            sample_indices = list(range(0, total_frames, effective_interval))
            if len(sample_indices) > max_frames:
                sample_indices = sample_indices[:max_frames]

            # 更新任务的总图像数
            if task:
                task.total_images = len(sample_indices)
                db.commit()

            # ── 逐帧处理 ──
            sample_set = set(sample_indices)
            key_frames = []
            total_objects = 0
            total_inference_time = 0
            class_counts = {}
            sampled_count = 0
            last_detections = []
            last_frame_gray = None
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

            def draw_detections_on_frame(frame, detections):
                annotated = frame.copy()
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    color = get_color(det["class_name"])
                    cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    label = f"{det['class_name']} {det['confidence']:.2f}"
                    cv2.putText(annotated, label, (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                return annotated

            def process_detections(result):
                nonlocal total_objects, total_inference_time, sampled_count
                frame_dets = []
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cid = int(box.cls[0])
                        cn = model.names.get(cid, f"class_{cid}")
                        cf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        det = {"class_name": cn, "class_id": cid, "confidence": round(cf, 4),
                               "bbox": [round(x1,1), round(y1,1), round(x2,1), round(y2,1)]}
                        frame_dets.append(det)
                        total_objects += 1
                        class_counts[cn] = class_counts.get(cn, 0) + 1
                itime = float(result.speed.get("inference", 0))
                total_inference_time += itime
                sampled_count += 1
                return frame_dets, itime

            def save_keyframe(fidx, fdets, itime, annotated_img):
                ab64 = None
                if len(key_frames) < 6:
                    _, buf = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    ab64 = base64.b64encode(buf).decode("utf-8")
                key_frames.append({"frame_index": fidx, "timestamp": round(fidx/fps,2),
                    "annotated_image_base64": ab64, "object_count": len(fdets),
                    "detections": fdets, "inference_time": round(itime,2)})
                for det in fdets:
                    db.add(DetectionResult(task_id=task_id, image_path=f"frame_{fidx}.jpg",
                        class_name=det["class_name"], class_id=det["class_id"],
                        confidence=det["confidence"], bbox=det["bbox"], inference_time=itime))

            # 创建临时文件用于输出标注视频
            output_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            output_video_path = output_tmp.name
            output_tmp.close()
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                should_detect = False
                if use_scene_detection:
                    # 场景变化检测
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, (100, 100))
                    if last_frame_gray is None:
                        should_detect = True
                    else:
                        diff = cv2.absdiff(last_frame_gray, gray).mean()
                        if diff > scene_threshold:
                            should_detect = True
                    last_frame_gray = gray.copy()
                else:
                    # 帧采样
                    should_detect = frame_idx in sample_set

                if should_detect:
                    results = model.predict(source=frame, conf=conf, iou=iou, imgsz=640,
                                            device="cpu", save=False, verbose=False)
                    fdets, itime = process_detections(results[0])
                    last_detections = fdets
                    annotated_img = draw_detections_on_frame(frame, fdets)
                    video_writer.write(annotated_img)
                    save_keyframe(frame_idx, fdets, itime, annotated_img)
                    if task:
                        task.total_objects = total_objects
                        db.commit()
                    logger.debug("视频检测: 帧%d 检测到%d个目标", frame_idx, len(fdets))
                else:
                    if last_detections:
                        video_writer.write(draw_detections_on_frame(frame, last_detections))
                    else:
                        video_writer.write(frame)

                frame_idx += 1

            # ── 释放资源 ──
            cap.release()
            video_writer.release()

            # ── 使用 ffmpeg 转码为浏览器可播放的 H.264 ──
            h264_video_path = output_video_path.replace(".mp4", "_h264.mp4")
            try:
                subprocess.run(
                    [
                        shutil.which("ffmpeg") or "ffmpeg",
                        "-y",
                        "-i", output_video_path,
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart",
                        h264_video_path,
                    ],
                    capture_output=True,
                    timeout=300,
                    check=True,
                )
                # 替换原文件
                os.replace(h264_video_path, output_video_path)
                logger.info("视频已转码为 H.264 格式")
            except Exception as e:
                logger.warning("ffmpeg 转码失败，使用原始 mp4v 视频: %s", str(e))
                try:
                    os.unlink(h264_video_path)
                except Exception:
                    pass

            # ── 上传标注视频到 MinIO ──
            annotated_video_url = None
            try:
                minio_client = MinIOClient()
                object_name = f"detections/{task_id}/annotated_video.mp4"
                annotated_video_url = minio_client.upload_file(
                    object_name, output_video_path
                )
                logger.info("标注视频已上传: %s", object_name)
            except Exception as e:
                logger.warning("标注视频上传 MinIO 失败: %s", str(e))

            # 清理临时视频文件
            try:
                os.unlink(output_video_path)
            except Exception:
                pass

            # ── 更新任务状态为完成 ──
            if task:
                task.status = "completed"
                task.total_objects = total_objects
                task.total_inference_time = total_inference_time
                task.completed_at = datetime.now()
                db.commit()

            logger.info(
                "视频检测完成: %d 帧处理, %d 关键帧采样, 共 %d 个目标, 总耗时 %.2fms",
                frame_idx,
                len(key_frames),
                total_objects,
                total_inference_time,
            )

            return {
                "task_id": task_id,
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
            }

        except Exception as e:
            logger.error("视频检测异常: %s", str(e), exc_info=True)
            # 更新任务状态为失败
            if task_id:
                task = (
                    db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                )
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    db.commit()
            return {"error": f"视频检测失败: {str(e)}"}
        finally:
            db.close()


detection_service = DetectionService()
