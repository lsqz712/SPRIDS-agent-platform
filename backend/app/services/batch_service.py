"""
PCB批次服务层
处理 PCB 批次信息管理、良品率统计、图片上传、批次检测等业务逻辑
"""
import os
import uuid
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from PIL import Image

from app.entity.db_models import PCBBatch, BatchImage, DetectionTask
from app.entity.schemas import BatchCreate, BatchUpdate
from app.storage.minio_client import minio_client
from app.services.detection_service import detection_service


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
    def create_batch_with_images(
        db: Session,
        batch_no: str,
        pcb_type: str,
        production_line: str,
        total_count: int,
        files: list,
        user_id: int,
    ) -> PCBBatch:
        """创建PCB批次并导入图片"""
        existing = (
            db.query(PCBBatch)
            .filter(PCBBatch.batch_no == batch_no)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="批次号已存在")

        actual_count = total_count if total_count > 0 else len(files)
        if actual_count == 0:
            raise HTTPException(status_code=400, detail="总数量不能为0，请上传图片或指定总数量")

        batch = PCBBatch(
            batch_no=batch_no,
            pcb_type=pcb_type,
            production_line=production_line,
            total_count=actual_count,
            inspected_count=0,
            pass_count=0,
            fail_count=0,
            pass_rate=0,
            status="pending",
            created_by=user_id,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        if files:
            BatchService._upload_images_to_batch(db=db, batch=batch, files=files)

        return batch

    @staticmethod
    def _upload_images_to_batch(db: Session, batch: PCBBatch, files: list):
        """将图片上传到批次（内部方法）"""
        for file in files:
            try:
                content = file.file.read()
                file_ext = os.path.splitext(file.filename)[1] or ".jpg"
                object_name = f"batches/{batch.id}/{uuid.uuid4()}{file_ext}"

                image_url = minio_client.upload_bytes(
                    object_name=object_name,
                    data=content,
                    content_type=file.content_type or "image/jpeg",
                )

                img = Image.open(file.file)
                width, height = img.size
            except Exception:
                width = None
                height = None

            batch_image = BatchImage(
                batch_id=batch.id,
                image_path=object_name,
                image_url=image_url,
                filename=file.filename,
                file_size=len(content),
                image_width=width,
                image_height=height,
                status="pending",
            )
            db.add(batch_image)

        db.commit()

    @staticmethod
    def upload_batch_images(db: Session, batch_id: int, files: list, user_id: int) -> dict:
        """向批次导入图片"""
        batch = BatchService.get_batch_by_id(db=db, batch_id=batch_id)

        BatchService._upload_images_to_batch(db=db, batch=batch, files=files)

        image_count = db.query(BatchImage).filter(BatchImage.batch_id == batch_id).count()
        batch.total_count = image_count
        db.commit()
        db.refresh(batch)

        return {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "total_images": image_count,
        }

    @staticmethod
    def get_batch_images(db: Session, batch_id: int) -> list:
        """获取批次图片列表"""
        images = db.query(BatchImage).filter(BatchImage.batch_id == batch_id).all()
        return [
            {
                "id": img.id,
                "image_path": img.image_path,
                "image_url": img.image_url,
                "filename": img.filename,
                "file_size": img.file_size,
                "image_width": img.image_width,
                "image_height": img.image_height,
                "status": img.status,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
            for img in images
        ]

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

        images = db.query(BatchImage).filter(BatchImage.batch_id == batch_id).all()
        for img in images:
            minio_client.delete_file(img.image_path)

        db.delete(batch)
        db.commit()

    @staticmethod
    def get_batch_statistics(db: Session, batch: PCBBatch) -> dict:
        """获取批次良品率统计"""
        from app.entity.db_models import DetectionResult

        # 最新完成的检测任务
        latest_task = db.query(DetectionTask).filter(
            DetectionTask.batch_id == batch.id,
            DetectionTask.status == "completed",
        ).order_by(DetectionTask.id.desc()).first()

        inspected_tasks = 1 if latest_task else 0
        fail_count = (
            db.query(DetectionResult).filter(
                DetectionResult.task_id == latest_task.id
            ).count() if latest_task else 0
        )

        # pass_count = 无缺陷图片数（无法精确计算，设为0当有缺陷时）
        pass_count = 0 if fail_count > 0 else (batch.inspected_count or inspected_tasks)
        pass_rate = round(pass_count / max(batch.inspected_count or inspected_tasks, 1), 4)

        return {
            "total_count": batch.total_count,
            "inspected_count": inspected_tasks,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": pass_rate,
            "fail_rate": round(1 - pass_rate, 4) if inspected_tasks > 0 else 0,
            "remaining_count": batch.total_count - inspected_tasks,
        }

    @staticmethod
    def detect_batch(db: Session, batch_id: int, conf: float, scene_id: int, user_id: int) -> dict:
        """批次一键检测"""
        batch = BatchService.get_batch_by_id(db=db, batch_id=batch_id)

        images = db.query(BatchImage).filter(
            BatchImage.batch_id == batch_id,
            BatchImage.status == "pending",
        ).all()

        if not images:
            raise HTTPException(status_code=400, detail="批次中没有待检测的图片")

        image_paths = []
        for img in images:
            try:
                obj = minio_client.get_object_stream(img.image_path)
                if obj:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(img.filename)[1], delete=False) as tmp:
                        tmp.write(obj.read())
                        obj.close()
                        image_paths.append(tmp.name)
            except Exception:
                pass

        if not image_paths:
            raise HTTPException(status_code=400, detail="无法获取批次图片")

        result = detection_service.detect_batch(
            image_paths=image_paths,
            conf=conf,
            scene_id=scene_id,
            user_id=user_id,
        )

        for path in image_paths:
            try:
                os.unlink(path)
            except Exception:
                pass

        task_id = result.get("task_id")
        if task_id:
            task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
            if task:
                task.batch_id = batch_id
                db.commit()
                # 将检测结果的临时路径替换为批次图片文件名（按顺序匹配）
                from app.entity.db_models import DetectionResult
                det_results = db.query(DetectionResult).filter(
                    DetectionResult.task_id == task_id
                ).order_by(DetectionResult.id).all()
                # 按 image_path 分组，每组对应一张批次图片
                temp_paths_seen = []
                path_idx = 0
                for dr in det_results:
                    if dr.image_path not in temp_paths_seen:
                        temp_paths_seen.append(dr.image_path)
                        path_idx = len(temp_paths_seen) - 1
                    else:
                        path_idx = temp_paths_seen.index(dr.image_path)
                    if path_idx < len(images):
                        dr.image_path = images[path_idx].image_path  # 替换为 MinIO 路径
                db.commit()

        batch.status = "in_progress"
        db.commit()
        db.refresh(batch)

        # 检测完成后更新批次状态
        if result and not result.get("error"):
            batch.status = "completed"
            batch.inspected_count = result.get("total_images", len(images))
            db.commit()

        return {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "task_id": task_id,
            "total_images": len(images),
            "status": "detection_started",
            **result,
        }


batch_service = BatchService()