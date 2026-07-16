"""
历史记录服务层
处理检测历史记录的查询和统计
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.entity.db_models import DetectionTask


class HistoryService:
    """历史记录服务"""

    @staticmethod
    def get_history_records(
        db: Session,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DetectionTask], int]:
        """
        获取历史检测记录列表（分页）
        返回: (任务列表, 总数)
        """
        offset = (page - 1) * page_size
        tasks = (
            db.query(DetectionTask)
            .options(joinedload(DetectionTask.scene))
            .order_by(DetectionTask.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        total = db.query(DetectionTask).count()
        return tasks, total

    @staticmethod
    def get_history_statistics(db: Session) -> dict:
        """
        获取历史记录统计信息
        """
        total_tasks = db.query(DetectionTask).count()
        total_images = db.query(func.sum(DetectionTask.total_images)).scalar() or 0
        total_objects = db.query(func.sum(DetectionTask.total_objects)).scalar() or 0

        return {
            "total_tasks": total_tasks,
            "total_images": total_images,
            "total_objects": total_objects,
        }

    @staticmethod
    def format_history_response(tasks: list[DetectionTask]) -> list[dict]:
        """
        格式化历史记录响应数据
        """
        return [
            {
                "id": task.id,
                "user_id": task.user_id,
                "scene_id": task.scene_id,
                "scene_name": task.scene.display_name if task.scene else None,
                "task_type": task.task_type,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "created_at": task.created_at,
            }
            for task in tasks
        ]


history_service = HistoryService()