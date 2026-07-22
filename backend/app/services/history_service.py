"""
历史记录服务层
处理检测历史记录的查询和统计
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.entity.db_models import DetectionTask, TaskStatus


class HistoryService:
    """历史记录服务"""

    @staticmethod
    def get_history_records(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        user_id: int = None,
        keyword: str = "",
        task_type: str = "",
        status: str = "",
    ) -> tuple[list[DetectionTask], int]:
        """获取历史检测记录列表（分页 + 筛选）"""
        query = db.query(DetectionTask).options(joinedload(DetectionTask.scene))

        if user_id:
            query = query.filter(DetectionTask.user_id == user_id)

        if keyword:
            try:
                task_id = int(keyword)
                query = query.filter(DetectionTask.id == task_id)
            except ValueError:
                query = query.filter(
                    or_(
                        DetectionTask.id.cast(str).ilike(f"%{keyword}%"),
                    )
                )

        if task_type:
            if task_type == "batch":
                query = query.filter(DetectionTask.task_type.in_(["batch", "zip"]))
            else:
                query = query.filter(DetectionTask.task_type == task_type)

        if status:
            try:
                status_val = getattr(TaskStatus, status.upper())
                query = query.filter(DetectionTask.status == status_val)
            except (AttributeError, TypeError):
                pass  # Invalid status, skip filter

        total = query.count()
        tasks = (
            query.order_by(DetectionTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return tasks, total

    @staticmethod
    def get_history_statistics(db: Session) -> dict:
        """获取历史记录统计信息"""
        total_tasks = db.query(DetectionTask).count()
        total_images = db.query(func.sum(DetectionTask.total_images)).scalar() or 0
        total_objects = db.query(func.sum(DetectionTask.total_objects)).scalar() or 0

        return {
            "total_tasks": total_tasks,
            "total_images": int(total_images),
            "total_objects": int(total_objects),
        }

    @staticmethod
    def format_history_response(tasks: list[DetectionTask]) -> list[dict]:
        """格式化历史记录响应数据"""
        return [
            {
                "id": task.id,
                "user_id": task.user_id,
                "scene_id": task.scene_id,
                "scene_name": task.scene.display_name if task.scene else None,
                "task_type": task.task_type,
                "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task in tasks
        ]


history_service = HistoryService()
