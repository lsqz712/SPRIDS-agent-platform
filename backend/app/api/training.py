"""
训练任务相关 API 路由
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.api.deps import get_current_user, check_permission
from app.entity.schemas import TrainingTaskCreate, TrainingTaskResponse, TrainingMetricResponse
from app.entity.db_models import TrainingTask, TrainingMetric, User, DetectionScene, DatasetVersion
from app.services.training_service import start_training, cancel_training, get_gpu_info, detect_device

router = APIRouter(prefix="/api/training", tags=["训练管理"])


def serialize_training_task(task: TrainingTask) -> dict:
    return {
        "id": task.id,
        "user_id": task.user_id,
        "scene_id": task.scene_id,
        "scene_name": task.scene.display_name if task.scene else None,
        "task_uuid": task.task_uuid,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "model_name": task.model_name,
        "epochs": task.epochs,
        "current_epoch": task.current_epoch,
        "progress": task.progress,
        "img_size": task.img_size,
        "batch_size": task.batch_size,
        "device": task.device,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("/gpu-info")
async def gpu_info():
    """获取 GPU 可用性信息"""
    return get_gpu_info()


@router.post("/tasks", status_code=201, dependencies=[Depends(check_permission("model:train"))])
async def create_training_task(
    request: TrainingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scene = db.query(DetectionScene).filter(DetectionScene.id == request.scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail=f"检测场景 ID {request.scene_id} 不存在")

    actual_device = detect_device(request.device)

    # 查找可用的 data_yaml
    data_yaml = request.data_yaml
    if not data_yaml:
        dataset = (
            db.query(DatasetVersion)
            .filter(
                DatasetVersion.scene_id == request.scene_id,
                DatasetVersion.is_active == True,
            )
            .order_by(DatasetVersion.created_at.desc())
            .first()
        )
        if dataset and dataset.data_yaml_path:
            data_yaml = dataset.data_yaml_path

    if not data_yaml:
        raise HTTPException(
            status_code=400,
            detail="未找到可用的数据集配置。请在场景中上传数据集后再启动训练。",
        )

    task = TrainingTask(
        user_id=current_user.id,
        scene_id=request.scene_id,
        task_uuid=str(uuid.uuid4()),
        model_name=request.model_name,
        epochs=request.epochs,
        img_size=request.img_size,
        batch_size=request.batch_size,
        device=actual_device,
        optimizer=request.optimizer,
        lr0=request.lr0,
        augment_config=request.augment_config,
        data_yaml=data_yaml,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    start_training(task, data_yaml)

    return serialize_training_task(task)


@router.get("/tasks", dependencies=[Depends(check_permission("model:read"))])
async def list_training_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = (
        db.query(TrainingTask)
        .options(joinedload(TrainingTask.scene))
        .order_by(TrainingTask.created_at.desc())
        .all()
    )
    return [serialize_training_task(task) for task in tasks]


@router.get("/status/{task_id}", dependencies=[Depends(check_permission("model:read"))])
async def get_training_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(TrainingTask)
        .options(joinedload(TrainingTask.scene))
        .filter(TrainingTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return serialize_training_task(task)


@router.get("/tasks/{task_id}/metrics", dependencies=[Depends(check_permission("model:read"))])
async def get_training_metrics(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    metrics = (
        db.query(TrainingMetric)
        .filter(TrainingMetric.task_id == task_id)
        .order_by(TrainingMetric.epoch)
        .all()
    )
    return [TrainingMetricResponse.model_validate(m).model_dump() for m in metrics]


@router.post("/tasks/{task_id}/cancel", dependencies=[Depends(check_permission("model:train"))])
async def cancel_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    if cancel_training(task_id):
        return {"code": 200, "message": "已发送取消信号"}
    raise HTTPException(status_code=400, detail="该任务不在训练中，无法取消")
