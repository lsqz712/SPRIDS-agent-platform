"""
检测统计服务层
提供总览统计、每日趋势、缺陷分布等数据分析能力
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.entity.db_models import DetectionTask, DetectionResult, DetectionScene, ReviewStatus, DefectSeverity


class StatisticsService:
    """检测统计服务"""

    @staticmethod
    def get_overview(db: Session) -> dict:
        """
        总览统计
        - 总任务数、总检测图像数、总检测目标数
        - 各类别缺陷分布、各复判状态分布、各严重等级分布
        """
        # 任务统计
        total_tasks = db.query(func.count(DetectionTask.id)).scalar() or 0
        completed_tasks = (
            db.query(func.count(DetectionTask.id))
            .filter(DetectionTask.status == "completed")
            .scalar()
            or 0
        )
        failed_tasks = (
            db.query(func.count(DetectionTask.id))
            .filter(DetectionTask.status == "failed")
            .scalar()
            or 0
        )

        # 图像与目标统计
        total_images = (
            db.query(func.sum(DetectionTask.total_images))
            .filter(DetectionTask.status == "completed")
            .scalar()
            or 0
        )
        total_objects = (
            db.query(func.sum(DetectionTask.total_objects))
            .filter(DetectionTask.status == "completed")
            .scalar()
            or 0
        )

        # 平均推理时间
        avg_inference_time = (
            db.query(func.avg(DetectionTask.total_inference_time))
            .filter(DetectionTask.status == "completed")
            .scalar()
            or 0
        )

        # 缺陷类别分布（按检测结果中 class_name 统计）
        class_dist = (
            db.query(
                DetectionResult.class_name,
                func.count(DetectionResult.id).label("count"),
            )
            .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
            .filter(DetectionTask.status == "completed")
            .group_by(DetectionResult.class_name)
            .order_by(func.count(DetectionResult.id).desc())
            .all()
        )

        # 复判状态分布
        review_dist = (
            db.query(
                DetectionResult.review_status,
                func.count(DetectionResult.id).label("count"),
            )
            .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
            .filter(DetectionTask.status == "completed")
            .group_by(DetectionResult.review_status)
            .all()
        )

        # 严重等级分布
        severity_dist = (
            db.query(
                DetectionResult.severity,
                func.count(DetectionResult.id).label("count"),
            )
            .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
            .filter(
                DetectionTask.status == "completed",
                DetectionResult.severity.isnot(None),
            )
            .group_by(DetectionResult.severity)
            .all()
        )

        # 场景分布
        scene_dist = (
            db.query(
                DetectionScene.display_name,
                func.count(DetectionTask.id).label("count"),
            )
            .join(DetectionScene, DetectionTask.scene_id == DetectionScene.id)
            .group_by(DetectionScene.display_name)
            .order_by(func.count(DetectionTask.id).desc())
            .all()
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_images": total_images,
            "total_objects": total_objects,
            "avg_inference_time_ms": round(float(avg_inference_time), 2),
            "class_distribution": {
                row.class_name: row.count for row in class_dist
            },
            "review_distribution": {
                row.review_status.value if hasattr(row.review_status, "value") else row.review_status: row.count
                for row in review_dist
            },
            "severity_distribution": {
                row.severity.value if hasattr(row.severity, "value") else row.severity: row.count
                for row in severity_dist
            },
            "scene_distribution": {
                row.display_name: row.count for row in scene_dist
            },
        }

    @staticmethod
    def get_daily_trend(
        db: Session, days: int = 30
    ) -> list[dict]:
        """
        每日检测趋势（最近 N 天）
        - 每日任务数、检测图像数、检测目标数
        """
        start_date = datetime.now() - timedelta(days=days)

        # 按日期分组统计
        daily_stats = (
            db.query(
                cast(DetectionTask.created_at, Date).label("date"),
                func.count(DetectionTask.id).label("task_count"),
                func.sum(DetectionTask.total_images).label("image_count"),
                func.sum(DetectionTask.total_objects).label("object_count"),
            )
            .filter(DetectionTask.created_at >= start_date)
            .group_by(cast(DetectionTask.created_at, Date))
            .order_by(cast(DetectionTask.created_at, Date))
            .all()
        )

        return [
            {
                "date": str(row.date),
                "task_count": row.task_count,
                "image_count": row.image_count or 0,
                "object_count": row.object_count or 0,
            }
            for row in daily_stats
        ]

    @staticmethod
    def get_defect_distribution(db: Session) -> dict:
        """
        缺陷类型分布（按 detection_results 中的 class_name 统计）
        """
        class_dist = (
            db.query(
                DetectionResult.class_name,
                func.count(DetectionResult.id).label("count"),
            )
            .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
            .filter(DetectionTask.status == "completed")
            .group_by(DetectionResult.class_name)
            .order_by(func.count(DetectionResult.id).desc())
            .all()
        )

        return {
            "items": [
                {"class_name": row.class_name, "count": row.count}
                for row in class_dist
            ],
            "total": sum(row.count for row in class_dist),
        }

    @staticmethod
    def get_scene_distribution(db: Session) -> list[dict]:
        """
        各场景检测次数统计
        """
        scene_dist = (
            db.query(
                DetectionScene.display_name,
                DetectionScene.id,
                func.count(DetectionTask.id).label("task_count"),
                func.sum(DetectionTask.total_images).label("image_count"),
                func.sum(DetectionTask.total_objects).label("object_count"),
            )
            .join(DetectionScene, DetectionTask.scene_id == DetectionScene.id)
            .filter(DetectionTask.status == "completed")
            .group_by(DetectionScene.id, DetectionScene.display_name)
            .order_by(func.count(DetectionTask.id).desc())
            .all()
        )

        return [
            {
                "scene_id": row.id,
                "scene_name": row.display_name,
                "task_count": row.task_count,
                "image_count": row.image_count or 0,
                "object_count": row.object_count or 0,
            }
            for row in scene_dist
        ]


# 全局单例
statistics_service = StatisticsService()
