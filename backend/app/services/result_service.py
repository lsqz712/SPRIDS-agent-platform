"""
检测结果服务层
处理检测结果查询、人工复判、缺陷严重等级标注、维修建议生成等业务逻辑
"""
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.entity.db_models import DetectionResult, ReviewStatus, DefectSeverity, User, DefectType


class ResultService:
    """检测结果服务"""

    @staticmethod
    def get_result_by_id(db: Session, result_id: int) -> DetectionResult:
        """根据 ID 获取单条检测结果"""
        result = (
            db.query(DetectionResult)
            .options(joinedload(DetectionResult.reviewer))
            .filter(DetectionResult.id == result_id)
            .first()
        )
        if not result:
            raise HTTPException(status_code=404, detail="检测结果不存在")
        return result

    @staticmethod
    def update_review(
        db: Session,
        result_id: int,
        review_status: str,
        reviewer_id: int,
        severity: str | None = None,
        defect_type_id: int | None = None,
        repair_suggestion: str | None = None,
    ) -> DetectionResult:
        """
        人工复判
        - 更新复判状态（pending → pass/fail/repair）
        - 可选同步更新缺陷严重等级、缺陷类型、维修建议
        """
        result = ResultService.get_result_by_id(db, result_id)

        # 验证复判状态值
        if review_status not in [s.value for s in ReviewStatus]:
            raise HTTPException(
                status_code=400,
                detail=f"无效的复判状态：{review_status}，可选值：pending/pass/fail/repair",
            )

        # 如果设置严重等级，验证值
        if severity:
            if severity not in [s.value for s in DefectSeverity]:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的缺陷等级：{severity}，可选值：minor/major/critical",
                )

        # 如果设置缺陷类型，验证存在
        if defect_type_id is not None:
            defect_type = db.query(DefectType).filter(DefectType.id == defect_type_id).first()
            if not defect_type:
                raise HTTPException(status_code=404, detail="缺陷类型不存在")

        result.review_status = review_status
        result.reviewer_id = reviewer_id
        result.reviewed_at = datetime.now()

        if severity is not None:
            result.severity = severity
        if repair_suggestion is not None:
            result.repair_suggestion = repair_suggestion
        if defect_type_id is not None:
            result.defect_type_id = defect_type_id

        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def update_severity(
        db: Session,
        result_id: int,
        severity: str,
    ) -> DetectionResult:
        """标注缺陷严重等级"""
        result = ResultService.get_result_by_id(db, result_id)

        if severity not in [s.value for s in DefectSeverity]:
            raise HTTPException(
                status_code=400,
                detail=f"无效的缺陷等级：{severity}，可选值：minor/major/critical",
            )

        result.severity = severity
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def update_repair_suggestion(
        db: Session,
        result_id: int,
        repair_suggestion: str,
    ) -> DetectionResult:
        """更新维修建议"""
        result = ResultService.get_result_by_id(db, result_id)

        result.repair_suggestion = repair_suggestion
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def get_repair_suggestion_ai(
        db: Session,
        result_id: int,
    ) -> dict:
        """
        获取 AI 生成的维修建议（占位实现）
        后续集成 LLM 后根据 defect_type + severity + bbox 等信息生成
        """
        result = ResultService.get_result_by_id(db, result_id)

        # TODO: 集成 LLM 生成维修建议
        suggestion = (
            f"检测到 {result.class_name_cn or result.class_name} "
            f"(置信度: {result.confidence:.2f})，"
            f"建议人工确认后制定维修方案。"
        )

        return {
            "result_id": result.id,
            "class_name": result.class_name,
            "class_name_cn": result.class_name_cn,
            "confidence": result.confidence,
            "severity": result.severity,
            "ai_suggestion": suggestion,
        }

    @staticmethod
    def get_task_summary(db: Session, task_id: int) -> dict:
        """获取任务的检测结果汇总"""
        from sqlalchemy import func

        # 总目标数
        total = db.query(func.count(DetectionResult.id)).filter(
            DetectionResult.task_id == task_id
        ).scalar() or 0

        # 各复判状态分布
        review_dist = (
            db.query(
                DetectionResult.review_status,
                func.count(DetectionResult.id).label("count"),
            )
            .filter(DetectionResult.task_id == task_id)
            .group_by(DetectionResult.review_status)
            .all()
        )

        # 各类别分布
        class_dist = (
            db.query(
                DetectionResult.class_name,
                func.count(DetectionResult.id).label("count"),
            )
            .filter(DetectionResult.task_id == task_id)
            .group_by(DetectionResult.class_name)
            .all()
        )

        # 各严重等级分布
        severity_dist = (
            db.query(
                DetectionResult.severity,
                func.count(DetectionResult.id).label("count"),
            )
            .filter(
                DetectionResult.task_id == task_id,
                DetectionResult.severity.isnot(None),
            )
            .group_by(DetectionResult.severity)
            .all()
        )

        return {
            "total_results": total,
            "review_distribution": {r.review_status: r.count for r in review_dist},
            "class_distribution": {c.class_name: c.count for c in class_dist},
            "severity_distribution": {s.severity: s.count for s in severity_dist},
        }


# 全局单例
result_service = ResultService()
