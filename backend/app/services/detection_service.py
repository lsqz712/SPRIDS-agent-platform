"""
检测任务服务层
处理单图检测、批量检测、任务 CRUD 及结果管理等业务逻辑
"""
import uuid
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.entity.db_models import DetectionTask, DetectionResult, TaskStatus
from app.entity.schemas import DetectionTaskResponse, DetectionResultResponse


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
    ) -> tuple[list[DetectionTask], int]:
        """
        获取检测任务分页列表
        返回: (任务列表, 总数)
        """
        query = db.query(DetectionTask)

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
        return tasks, total

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
    ) -> DetectionTask:
        """创建单图检测任务"""
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            model_version_id=model_version_id,
            task_type="single",
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
    ) -> DetectionTask:
        """创建批量检测任务"""
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            model_version_id=model_version_id,
            task_type="batch",
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


# 全局单例
detection_service = DetectionService()
