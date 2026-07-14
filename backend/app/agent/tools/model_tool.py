"""
模型查询工具
提供模型版本信息查询和训练任务状态查询功能
"""
from typing import Dict, Any, List
from app.agent.tools import BaseTool, ToolRegistry
from app.entity.db_models import ModelVersion, DetectionScene, TrainingTask
from sqlalchemy.orm import Session
from sqlalchemy import desc
class ModelInfoTool(BaseTool):
    """模型版本信息查询工具"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "get_model_info"
    def get_description(self) -> str:
        return "查询模型版本信息，包括性能指标和适用场景"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "integer",
                    "description": "模型版本 ID"
                },
                "scene_id": {
                    "type": "integer",
                    "description": "场景 ID（可选，查询该场景的所有模型）"
                }
            }
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        model_id = kwargs.get("model_id")
        scene_id = kwargs.get("scene_id")
        if model_id:
            model = self.db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
            if not model:
                return {"error": f"模型版本 ID {model_id} 不存在"}
            scene = self.db.query(DetectionScene).filter(DetectionScene.id == model.scene_id).first()
            return {
                "model_id": model.id,
                "version": model.version,
                "model_name": model.model_name,
                "model_type": model.model_type,
                "status": model.status,
                "scene_name": scene.display_name if scene else None,
                "map50": model.map50,
                "map50_95": model.map50_95,
                "precision": model.precision,
                "recall": model.recall,
                "per_class_ap": model.per_class_ap,
                "description": model.description,
                "file_size": model.file_size,
                "is_default": model.is_default,
                "export_format": model.export_format,
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }
        elif scene_id:
            models = self.db.query(ModelVersion).filter(
                ModelVersion.scene_id == scene_id
            ).order_by(desc(ModelVersion.created_at)).all()
            scene = self.db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
            model_list = []
            for model in models:
                model_list.append({
                    "model_id": model.id,
                    "version": model.version,
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "status": model.status,
                    "map50": model.map50,
                    "map50_95": model.map50_95,
                    "is_default": model.is_default,
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                })
            return {
                "scene_name": scene.display_name if scene else None,
                "total_models": len(model_list),
                "models": model_list,
            }
        else:
            return {"error": "请提供 model_id 或 scene_id 参数"}
class TrainingTaskTool(BaseTool):
    """训练任务查询工具"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "get_training_tasks"
    def get_description(self) -> str:
        return "查询训练任务列表和状态"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "训练任务 ID"
                },
                "scene_id": {
                    "type": "integer",
                    "description": "场景 ID（可选）"
                },
                "status": {
                    "type": "string",
                    "description": "任务状态"
                }
            }
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        task_id = kwargs.get("task_id")
        scene_id = kwargs.get("scene_id")
        status = kwargs.get("status")
        if task_id:
            task = self.db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
            if not task:
                return {"error": f"训练任务 ID {task_id} 不存在"}
            scene = self.db.query(DetectionScene).filter(DetectionScene.id == task.scene_id).first()
            return {
                "task_id": task.id,
                "task_uuid": task.task_uuid,
                "status": task.status,
                "scene_name": scene.display_name if scene else None,
                "model_name": task.model_name,
                "epochs": task.epochs,
                "current_epoch": task.current_epoch,
                "progress": task.progress,
                "img_size": task.img_size,
                "batch_size": task.batch_size,
                "device": task.device,
                "optimizer": task.optimizer,
                "lr0": task.lr0,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
        else:
            query = self.db.query(TrainingTask)
            if scene_id:
                query = query.filter(TrainingTask.scene_id == scene_id)
            if status:
                query = query.filter(TrainingTask.status == status)
            query = query.order_by(desc(TrainingTask.created_at))
            tasks = query.all()
            task_list = []
            for task in tasks:
                scene = self.db.query(DetectionScene).filter(DetectionScene.id == task.scene_id).first()
                task_list.append({
                    "task_id": task.id,
                    "task_uuid": task.task_uuid,
                    "status": task.status,
                    "scene_name": scene.display_name if scene else None,
                    "model_name": task.model_name,
                    "epochs": task.epochs,
                    "current_epoch": task.current_epoch,
                    "progress": task.progress,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                })
            return {
                "total_tasks": len(task_list),
                "tasks": task_list,
            }
def register_model_tools(registry: ToolRegistry, db: Session):
    registry.register(ModelInfoTool(db))
    registry.register(TrainingTaskTool(db))