"""
PCB批次服务层
处理 PCB 批次信息管理、良品率统计等业务逻辑
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from app.entity.db_models import PCBBatch
from app.entity.schemas import BatchCreate, BatchUpdate


class BatchService:
    """PCB批次服务"""

    @staticmethod
    def list_batches(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        pcb_type: str | None = None,
        production_line: str | None = None,
    ) -> tuple[list[PCBBatch], int]:
        """
        获取PCB批次分页列表
        返回: (批次列表, 总数)
        """
        query = db.query(PCBBatch)

        # 筛选条件
        if keyword:
            query = query.filter(
                or_(
                    PCBBatch.batch_no.ilike(f"%{keyword}%"),
                    PCBBatch.pcb_type.ilike(f"%{keyword}%"),
                )
            )
        if status:
            query = query.filter(PCBBatch.status == status)
        if pcb_type:
            query = query.filter(PCBBatch.pcb_type == pcb_type)
        if production_line:
            query = query.filter(PCBBatch.production_line == production_line)

        # 计算总数
        total = query.count()

        # 分页
        query = query.order_by(PCBBatch.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        batches = query.all()
        return batches, total

    @staticmethod
    def get_batch_by_id(db: Session, batch_id: int) -> PCBBatch:
        """根据 ID 获取批次"""
        batch = db.query(PCBBatch).filter(PCBBatch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="PCB批次不存在")
        return batch

    @staticmethod
    def create_batch(db: Session, data: BatchCreate, user_id: int) -> PCBBatch:
        """创建PCB批次"""
        # 检查批次号唯一性
        existing = (
            db.query(PCBBatch)
            .filter(PCBBatch.batch_no == data.batch_no)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="批次号已存在")

        batch = PCBBatch(
            batch_no=data.batch_no,
            pcb_type=data.pcb_type,
            production_line=data.production_line,
            total_count=data.total_count,
            inspected_count=0,
            pass_count=0,
            fail_count=0,
            pass_rate=0,
            status=data.status or "pending",
            created_by=user_id,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def update_batch(db: Session, batch_id: int, data: BatchUpdate) -> PCBBatch:
        """更新PCB批次信息"""
        batch = BatchService.get_batch_by_id(db, batch_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(batch, field, value)

        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def delete_batch(db: Session, batch_id: int) -> None:
        """物理删除PCB批次"""
        batch = BatchService.get_batch_by_id(db, batch_id)
        db.delete(batch)
        db.commit()

    @staticmethod
    def get_batch_statistics(db: Session, batch: PCBBatch) -> dict:
        """获取批次良品率统计"""
        from app.entity.db_models import DetectionTask, DetectionResult

        # 已完成的任务数（作为已检测数量）
        inspected_tasks = db.query(DetectionTask).filter(
            DetectionTask.batch_id == batch.id,
            DetectionTask.status == "completed",
        ).count()

        # 该批次所有检测结果中标记为 fail 的数量
        fail_count = (
            db.query(DetectionResult)
            .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
            .filter(
                DetectionTask.batch_id == batch.id,
                DetectionResult.review_status == "fail",
            )
            .count()
        )

        pass_count = max(0, inspected_tasks - fail_count)
        pass_rate = round(pass_count / inspected_tasks, 4) if inspected_tasks > 0 else 0

        return {
            "total_count": batch.total_count,
            "inspected_count": inspected_tasks,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": pass_rate,
            "fail_rate": round(1 - pass_rate, 4) if inspected_tasks > 0 else 0,
            "remaining_count": batch.total_count - inspected_tasks,
        }


# 全局单例
batch_service = BatchService()
