"""
检测任务服务层
处理单图检测、批量检测、任务 CRUD 及结果管理等业务逻辑
"""
import uuid
import os
import zipfile
import tempfile
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.entity.db_models import DetectionTask, DetectionResult, TaskStatus, DetectionScene, ModelVersion
from app.entity.schemas import DetectionTaskResponse, DetectionResultResponse
from app.services.yolo_inference import detect, batch_detect, detect_video, list_camera_devices, DEFAULT_CLASS_NAMES


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
        try:
            model_path = DetectionService._get_model_path(db, scene_id)
            
            result = detect(
                model_path=model_path,
                image_path=image_path,
                conf_threshold=conf,
                iou_threshold=iou,
            )
            
            result["task_type"] = "single"
            return result
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
        try:
            model_path = DetectionService._get_model_path(db, scene_id)
            
            results = batch_detect(
                model_path=model_path,
                image_paths=image_paths,
                conf_threshold=conf,
            )
            
            total_objects = sum(r.get("defects", []).__len__() for r in results)
            total_inference_time = sum(r.get("inference_time", 0) for r in results)
            
            return {
                "success": True,
                "task_type": "batch",
                "total_images": len(results),
                "total_objects": total_objects,
                "total_inference_time": total_inference_time,
                "results": results,
            }
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
                
                results = batch_detect(
                    model_path=model_path,
                    image_paths=image_paths,
                    conf_threshold=conf,
                )
                
                total_objects = sum(r.get("defects", []).__len__() for r in results)
                total_inference_time = sum(r.get("inference_time", 0) for r in results)
                
                return {
                    "success": True,
                    "task_type": "zip",
                    "total_images": len(results),
                    "total_objects": total_objects,
                    "total_inference_time": total_inference_time,
                    "results": results,
                }
        finally:
            db.close()

    @staticmethod
    def detect_video(
        video_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        scene_id: int = None,
        user_id: int = None,
        frame_interval: int = 10,
        progress_callback=None,
    ) -> dict:
        """
        视频检测（按帧间隔采样检测）
        
        Args:
            video_path: 视频文件路径
            conf: 置信度阈值
            iou: IoU 阈值
            scene_id: 检测场景 ID
            user_id: 用户 ID
            frame_interval: 检测帧间隔
            progress_callback: 进度回调函数
        
        Returns:
            检测结果字典
        """
        db = SessionLocal()
        try:
            model_path = DetectionService._get_model_path(db, scene_id)
            
            result = detect_video(
                model_path=model_path,
                video_path=video_path,
                conf_threshold=conf,
                iou_threshold=iou,
                frame_interval=frame_interval,
                progress_callback=progress_callback,
            )
            
            return result
        finally:
            db.close()

    @staticmethod
    def list_cameras() -> list:
        """
        枚举可用的摄像头设备
        
        Returns:
            设备列表
        """
        return list_camera_devices()

    @staticmethod
    def _get_model_path(db: Session, scene_id: int = None) -> str:
        """
        获取场景的默认模型路径
        
        Args:
            db: 数据库会话
            scene_id: 检测场景 ID
        
        Returns:
            模型文件路径
        """
        default_model = None
        
        if scene_id:
            default_model = db.query(ModelVersion).filter(
                ModelVersion.scene_id == scene_id,
                ModelVersion.is_default == True,
                ModelVersion.status == "active",
            ).first()
        
        if not default_model:
            default_model = db.query(ModelVersion).filter(
                ModelVersion.status == "active",
            ).order_by(ModelVersion.created_at.desc()).first()
        
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
