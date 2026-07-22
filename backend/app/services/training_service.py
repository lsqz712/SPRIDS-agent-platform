"""
训练服务 - YOLO 模型训练的后台执行、GPU 检测、进度追踪、结果管理
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional

import torch
from ultralytics import YOLO
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.entity.db_models import TrainingTask, TrainingMetric, ModelVersion, TaskStatus
from app.core.logger import get_logger

logger = get_logger(__name__)

_active_trainings: Dict[int, threading.Thread] = {}

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def detect_device(requested_device: str = "0") -> str:
    """检测可用设备，优先 GPU，不可用则回退 CPU。"""
    if requested_device == "cpu":
        return "cpu"

    if not torch.cuda.is_available():
        logger.info("CUDA 不可用，回退到 CPU")
        return "cpu"

    try:
        gpu_id = int(requested_device)
        if gpu_id < torch.cuda.device_count():
            return requested_device
        logger.warning(f"GPU {requested_device} 不存在，使用 GPU 0")
        return "0"
    except (ValueError, TypeError):
        return "0" if torch.cuda.is_available() else "cpu"


def get_gpu_info() -> Dict[str, Any]:
    """获取 GPU 信息，供前端展示。"""
    if not torch.cuda.is_available():
        return {
            "gpu_available": False,
            "gpu_count": 0,
            "gpu_names": [],
            "recommended_device": "cpu",
        }

    gpu_count = torch.cuda.device_count()
    gpu_names = [torch.cuda.get_device_name(i) for i in range(gpu_count)]

    return {
        "gpu_available": True,
        "gpu_count": gpu_count,
        "gpu_names": gpu_names,
        "recommended_device": "0",
    }


def _run_training(task_id: int, data_yaml: str):
    """在后台线程中执行 YOLO 训练。"""
    db: Session = SessionLocal()
    task = None
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            return

        actual_device = detect_device(task.device)
        task.device = actual_device
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        db.commit()

        scene_name = task.scene.name if task.scene else "default"
        run_id = task.task_uuid[:8]
        project_dir = os.path.join(MODELS_DIR, scene_name)
        run_name = f"{task.model_name}_{run_id}"

        model = YOLO(f"{task.model_name}.pt")

        def on_fit_epoch_end(trainer):
            """每个 epoch 结束时的回调：更新进度 + 记录指标。"""
            epoch = trainer.epoch + 1
            metrics_dict = trainer.metrics

            progress = int(epoch / task.epochs * 100)

            m = TrainingMetric(
                task_id=task.id,
                epoch=epoch,
                box_loss=_try_float(metrics_dict, "train/box_loss"),
                cls_loss=_try_float(metrics_dict, "train/cls_loss"),
                dfl_loss=_try_float(metrics_dict, "train/dfl_loss"),
                precision=_try_float(metrics_dict, "metrics/precision(B)"),
                recall=_try_float(metrics_dict, "metrics/recall(B)"),
                map50=_try_float(metrics_dict, "metrics/mAP50(B)"),
                map50_95=_try_float(metrics_dict, "metrics/mAP50-95(B)"),
                lr=_try_lr(trainer),
            )
            db.add(m)

            db.query(TrainingTask).filter(TrainingTask.id == task_id).update({
                "current_epoch": epoch,
                "progress": progress,
            })

            db.refresh(task)
            if task.status == TaskStatus.CANCELLED:
                trainer.model.stop_training = True

            db.commit()

        model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

        results = model.train(
            data=data_yaml,
            epochs=task.epochs,
            imgsz=task.img_size,
            batch=task.batch_size,
            device=actual_device,
            workers=0,  # 单进程，避免子进程加载 CUDA DLL 撑爆页面文件
            optimizer=task.optimizer or "SGD",
            lr0=task.lr0 or 0.01,
            project=project_dir,
            name=run_name,
            exist_ok=True,
            verbose=False,
        )

        # 检查是否被取消
        db.refresh(task)
        if task.status == TaskStatus.CANCELLED:
            return

        # 训练完成
        best_pt = os.path.join(project_dir, run_name, "weights", "best.pt")
        last_pt = os.path.join(project_dir, run_name, "weights", "last.pt")
        model_path = best_pt if os.path.exists(best_pt) else last_pt

        if not os.path.exists(model_path):
            raise RuntimeError(f"训练完成但模型文件未找到: {model_path}")

        # 提取最终指标（ultralytics 不同版本返回结构不同）
        if hasattr(results, "results_dict"):
            result_dict = results.results_dict
        elif isinstance(results, dict):
            result_dict = results
        else:
            result_dict = {}

        version_count = db.query(ModelVersion).filter(
            ModelVersion.scene_id == task.scene_id
        ).count()

        model_version = ModelVersion(
            scene_id=task.scene_id,
            training_task_id=task.id,
            version=f"v{version_count + 1}.0.0",
            model_name=f"{task.model_name}_{scene_name}",
            model_type=task.model_name,
            status="active",
            model_path=os.path.relpath(model_path),
            map50=_try_float(result_dict, "metrics/mAP50(B)"),
            map50_95=_try_float(result_dict, "metrics/mAP50-95(B)"),
            precision=_try_float(result_dict, "metrics/precision(B)"),
            recall=_try_float(result_dict, "metrics/recall(B)"),
            description=f"由训练任务 #{task.id} 自动生成",
        )
        db.add(model_version)

        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.current_epoch = task.epochs
        task.completed_at = datetime.now()
        db.commit()

        logger.info(f"训练任务 #{task_id} 完成，模型版本: {model_version.version}")

    except Exception as e:
        logger.error(f"训练任务 #{task_id} 失败: {e}")
        try:
            db.rollback()
            if task:
                db.query(TrainingTask).filter(TrainingTask.id == task_id).update({
                    "status": TaskStatus.FAILED,
                    "error_message": str(e),
                })
                db.commit()
        except Exception:
            pass
    finally:
        _active_trainings.pop(task_id, None)
        db.close()


def start_training(task: TrainingTask, data_yaml: str) -> None:
    """启动后台训练线程。"""
    thread = threading.Thread(
        target=_run_training,
        args=(task.id, data_yaml),
        daemon=True,
        name=f"training-{task.id}",
    )
    _active_trainings[task.id] = thread
    thread.start()
    logger.info(f"训练任务 #{task.id} 已启动，设备: {task.device}")


def cancel_training(task_id: int) -> bool:
    """取消正在进行的训练任务。"""
    if task_id not in _active_trainings:
        return False

    db = SessionLocal()
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if task and task.status == TaskStatus.PROCESSING:
            task.status = TaskStatus.CANCELLED
            db.commit()
            return True
        return False
    finally:
        db.close()


def _try_float(metrics_dict: dict, key: str) -> Optional[float]:
    """安全地从指标字典中提取 float 值。"""
    try:
        val = metrics_dict.get(key)
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _try_lr(trainer) -> Optional[float]:
    """安全地从 trainer 中提取当前学习率。"""
    try:
        if hasattr(trainer, "lr"):
            return float(trainer.lr)
        for pg in trainer.optimizer.param_groups:
            return float(pg["lr"])
    except Exception:
        pass
    return None
