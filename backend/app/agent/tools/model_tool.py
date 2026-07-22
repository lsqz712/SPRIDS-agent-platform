"""
模型管理工具集 — Agent 可调用的模型/场景/批次/训练查询 @tool 函数

工具列表：
  - get_model_info: 模型版本查询
  - get_scenes: 检测场景列表
  - get_batches: PCB 批次列表
  - get_training_tasks: 训练任务列表
"""

import json

from langchain_core.tools import tool
from sqlalchemy import desc

from app.agent.shared import compress_tool_output
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import TrainingTask, DetectionScene, PCBBatch, ModelVersion

logger = get_logger(__name__)


@tool
def get_model_info(model_id: int = None, scene_id: int = None) -> str:
    """查询模型版本信息，包括性能指标和适用场景。

    Args:
        model_id: 模型版本 ID（可选）
        scene_id: 场景 ID（可选，查询该场景的所有模型）

    Returns:
        模型信息列表或单个模型详情
    """
    db = SessionLocal()
    try:
        if model_id:
            model = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
            if not model:
                return json.dumps({"error": f"模型版本 ID {model_id} 不存在"}, ensure_ascii=False)
            scene = db.query(DetectionScene).filter(DetectionScene.id == model.scene_id).first()
            result = {
                "model_id": model.id, "version": model.version,
                "model_name": model.model_name, "model_type": model.model_type,
                "status": model.status,
                "scene_name": scene.display_name if scene else None,
                "map50": model.map50, "map50_95": model.map50_95,
                "precision": model.precision, "recall": model.recall,
                "description": model.description, "is_default": model.is_default,
                "created_at": str(model.created_at) if model.created_at else None,
            }
            return json.dumps(result, ensure_ascii=False)
        elif scene_id:
            models = db.query(ModelVersion).filter(
                ModelVersion.scene_id == scene_id
            ).order_by(desc(ModelVersion.created_at)).all()
            scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
            model_list = [{
                "model_id": m.id, "version": m.version,
                "model_name": m.model_name, "status": m.status,
                "map50": m.map50, "is_default": m.is_default,
            } for m in models]
            return compress_tool_output({
                "scene_name": scene.display_name if scene else None,
                "total_models": len(model_list), "models": model_list,
            })
        else:
            models = db.query(ModelVersion).order_by(desc(ModelVersion.created_at)).all()
            model_list = [{
                "model_id": m.id, "version": m.version,
                "model_name": m.model_name, "status": m.status, "map50": m.map50,
            } for m in models]
            return compress_tool_output({"items": model_list, "total": len(model_list)})
    finally:
        db.close()


@tool
def get_scenes() -> str:
    """获取检测场景列表。

    返回所有检测场景，包含场景 ID、名称、类别等信息。
    """
    db = SessionLocal()
    try:
        scenes = db.query(DetectionScene).order_by(DetectionScene.created_at.desc()).all()
        result = [{
            "id": s.id, "name": s.name, "display_name": s.display_name,
            "category": s.category, "description": s.description,
            "is_active": s.is_active, "created_at": str(s.created_at),
        } for s in scenes]
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_batches() -> str:
    """获取PCB批次列表。

    返回所有PCB批次，包含批次ID、名称、描述、创建时间等信息。
    """
    db = SessionLocal()
    try:
        batches = db.query(PCBBatch).order_by(PCBBatch.created_at.desc()).all()
        result = [{
            "id": b.id, "name": b.name, "description": b.description,
            "created_at": str(b.created_at),
        } for b in batches]
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_training_tasks() -> str:
    """获取模型训练任务列表。

    返回所有训练任务，包含任务状态、模型名称、训练进度、epoch 等信息。
    """
    db = SessionLocal()
    try:
        tasks = db.query(TrainingTask).order_by(TrainingTask.created_at.desc()).all()
        result = [{
            "id": t.id, "user_id": t.user_id, "scene_id": t.scene_id,
            "task_uuid": t.task_uuid, "status": t.status,
            "model_name": t.model_name, "epochs": t.epochs,
            "current_epoch": t.current_epoch, "progress": t.progress,
            "img_size": t.img_size, "batch_size": t.batch_size,
            "device": t.device, "dataset_size": t.dataset_size,
            "error_message": t.error_message,
            "created_at": str(t.created_at),
            "started_at": str(t.started_at) if t.started_at else None,
            "completed_at": str(t.completed_at) if t.completed_at else None,
        } for t in tasks]
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


# 模型工具列表
MODEL_TOOLS = [get_model_info, get_scenes, get_batches, get_training_tasks]
