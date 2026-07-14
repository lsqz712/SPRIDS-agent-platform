"""
训练任务相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.entity.schemas import TrainingTaskCreate, TrainingTaskResponse, TrainingMetricResponse
from app.entity.db_models import TrainingTask, TrainingMetric

router = APIRouter(prefix="/api/training", tags=["训练管理"])


def serialize_training_task(task: TrainingTask) -> dict:
    return {
        "id": task.id,
        "user_id": task.user_id,
        "scene_id": task.scene_id,
        "scene_name": None,
        "task_uuid": task.task_uuid,
        "status": task.status,
        "model_name": task.model_name,
        "epochs": task.epochs,
        "current_epoch": task.current_epoch,
        "progress": task.progress,
        "img_size": task.img_size,
        "batch_size": task.batch_size,
        "device": task.device,
        "dataset_size": task.dataset_size,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


@router.post("/tasks", response_model=TrainingTaskResponse, status_code=201)
async def create_training_task(
    request: TrainingTaskCreate,
    db: Session = Depends(get_db),
):
    task = TrainingTask(
        scene_id=request.scene_id,
        model_name=request.model_name,
        epochs=request.epochs,
        img_size=request.img_size,
        batch_size=request.batch_size,
        device=request.device,
        optimizer=request.optimizer,
        lr0=request.lr0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return serialize_training_task(task)


@router.get("/tasks", response_model=list[TrainingTaskResponse])
async def list_training_tasks(db: Session = Depends(get_db)):
    tasks = db.query(TrainingTask).order_by(TrainingTask.created_at.desc()).all()
    return [serialize_training_task(task) for task in tasks]


@router.get("/status/{task_id}")
async def get_training_status(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return serialize_training_task(task)


@router.get("/tasks/{task_id}/metrics", response_model=list[TrainingMetricResponse])
async def get_training_metrics(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    metrics = db.query(TrainingMetric).filter(TrainingMetric.task_id == task_id).order_by(TrainingMetric.epoch).all()
    return metrics