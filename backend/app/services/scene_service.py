"""
检测场景服务层
处理检测场景的 CRUD 及关联查询
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.entity.db_models import DetectionScene, ModelVersion, DetectionTask, DatasetVersion
from app.entity.schemas import SceneCreate, SceneUpdate

class SceneService:
    """检测场景服务"""

    @staticmethod
    def list_scenes(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[DetectionScene], int]:
        """
        获取检测场景分页列表
        返回: (场景列表, 总数)
        """
        query = db.query(DetectionScene).filter(DetectionScene.deleted_at.is_(None))

        # 筛选条件
        if keyword:
            query = query.filter(
                or_(
                    DetectionScene.name.ilike(f"%{keyword}%"),
                    DetectionScene.display_name.ilike(f"%{keyword}%"),
                )
            )
        if category:
            query = query.filter(DetectionScene.category == category)
        if is_active is not None:
            query = query.filter(DetectionScene.is_active == is_active)

        # 计算总数
        total = query.count()

        # 分页
        query = query.order_by(DetectionScene.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        scenes = query.all()
        return scenes, total

    @staticmethod
    def get_scene_by_id(db: Session, scene_id: int) -> DetectionScene:
        """根据 ID 获取场景（含默认模型信息）"""
        scene = (
            db.query(DetectionScene)
            .options(joinedload(DetectionScene.model_versions))
            .filter(DetectionScene.id == scene_id, DetectionScene.deleted_at.is_(None))
            .first()
        )
        if not scene:
            raise HTTPException(status_code=404, detail="检测场景不存在")
        return scene

    @staticmethod
    def create_scene(db: Session, data: SceneCreate, user_id: int) -> DetectionScene:
        """创建检测场景"""
        # 检查名称唯一性
        existing = (
            db.query(DetectionScene)
            .filter(DetectionScene.name == data.name, DetectionScene.deleted_at.is_(None))
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="场景标识已存在")

        scene = DetectionScene(
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            category=data.category,
            class_names=data.class_names,
            class_names_cn=data.class_names_cn,
            created_by=user_id,
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)
        return scene

    @staticmethod
    def update_scene(db: Session, scene_id: int, data: SceneUpdate) -> DetectionScene:
        """更新检测场景"""
        scene = SceneService.get_scene_by_id(db, scene_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(scene, field, value)

        db.commit()
        db.refresh(scene)
        return scene

    @staticmethod
    def delete_scene(db: Session, scene_id: int) -> None:
        """软删除检测场景"""
        scene = SceneService.get_scene_by_id(db, scene_id)
        from datetime import datetime
        scene.deleted_at = datetime.now()
        db.commit()

    @staticmethod
    def get_scene_statistics(db: Session, scene: DetectionScene) -> dict:
        """获取场景关联统计信息"""
        from app.entity.schemas import ModelVersionBrief

        model_count = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.scene_id == scene.id,
                ModelVersion.deleted_at.is_(None),
                ModelVersion.status == "active",
            )
            .count()
        )
        task_count = (
            db.query(DetectionTask)
            .filter(DetectionTask.scene_id == scene.id)
            .count()
        )
        dataset_count = (
            db.query(DatasetVersion)
            .filter(DatasetVersion.scene_id == scene.id)
            .count()
        )
        latest_model = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.scene_id == scene.id,
                ModelVersion.deleted_at.is_(None),
                ModelVersion.status == "active",
            )
            .order_by(ModelVersion.created_at.desc())
            .first()
        )
        default_model = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.scene_id == scene.id,
                ModelVersion.is_default == True,
                ModelVersion.deleted_at.is_(None),
            )
            .first()
        )

        return {
            "model_count": model_count,
            "task_count": task_count,
            "dataset_count": dataset_count,
            "default_model": ModelVersionBrief.model_validate(default_model).model_dump() if default_model else None,
            "latest_model": ModelVersionBrief.model_validate(latest_model).model_dump() if latest_model else None,
        }


# 全局单例
scene_service = SceneService()