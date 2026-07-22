"""
缺陷类型字典服务层
标准化管理 PCB 缺陷类型（短路、开路、焊点不良等）
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.entity.db_models import DefectType
from app.entity.schemas import DefectTypeCreate, DefectTypeUpdate


class DefectTypeService:
    """缺陷类型字典服务"""

    @staticmethod
    def list_defect_types(
        db: Session,
        keyword: str | None = None,
        severity: str | None = None,
        is_active: bool | None = None,
    ) -> list[DefectType]:
        """
        获取缺陷类型列表（支持搜索和筛选）
        """
        query = db.query(DefectType)

        if keyword:
            query = query.filter(
                or_(
                    DefectType.code.ilike(f"%{keyword}%"),
                    DefectType.name.ilike(f"%{keyword}%"),
                    DefectType.name_cn.ilike(f"%{keyword}%"),
                )
            )
        if severity:
            query = query.filter(DefectType.severity == severity)
        if is_active is not None:
            query = query.filter(DefectType.is_active == is_active)

        query = query.order_by(DefectType.code)
        return query.all()

    @staticmethod
    def get_defect_type_by_id(db: Session, defect_type_id: int) -> DefectType:
        """根据 ID 获取缺陷类型"""
        dt = db.query(DefectType).filter(DefectType.id == defect_type_id).first()
        if not dt:
            raise HTTPException(status_code=404, detail="缺陷类型不存在")
        return dt

    @staticmethod
    def create_defect_type(db: Session, data: DefectTypeCreate) -> DefectType:
        """创建缺陷类型"""
        # 检查编码唯一性
        existing = (
            db.query(DefectType)
            .filter(DefectType.code == data.code)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"缺陷编码 '{data.code}' 已存在")

        dt = DefectType(
            code=data.code,
            name=data.name,
            name_cn=data.name_cn,
            severity=data.severity,
            description=data.description,
        )
        db.add(dt)
        db.commit()
        db.refresh(dt)
        return dt

    @staticmethod
    def update_defect_type(db: Session, defect_type_id: int, data: DefectTypeUpdate) -> DefectType:
        """更新缺陷类型"""
        dt = DefectTypeService.get_defect_type_by_id(db, defect_type_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dt, field, value)

        db.commit()
        db.refresh(dt)
        return dt

    @staticmethod
    def delete_defect_type(db: Session, defect_type_id: int) -> None:
        """删除缺陷类型（物理删除）"""
        dt = DefectTypeService.get_defect_type_by_id(db, defect_type_id)
        db.delete(dt)
        db.commit()


# 全局单例
defect_type_service = DefectTypeService()
