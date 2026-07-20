"""
检测工具
提供检测任务的创建和查询功能
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.agent.tools import BaseTool, ToolRegistry
from app.entity.db_models import DetectionTask, DetectionResult, DetectionScene, PCBBatch, ModelVersion
from app.services.yolo_inference import detect, batch_detect
from sqlalchemy.orm import Session
from sqlalchemy import desc
class DetectionTool(BaseTool):
    """检测工具实现"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "run_detection"
    def get_description(self) -> str:
        return "执行 PCB 缺陷检测任务，支持单图检测和批量检测"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "图像文件路径或 URL"
                },
                "scene_id": {
                    "type": "integer",
                    "description": "检测场景 ID"
                },
                "batch_id": {
                    "type": "integer",
                    "description": "PCB 批次 ID（可选）"
                },
                "conf_threshold": {
                    "type": "number",
                    "description": "置信度阈值，默认 0.25"
                },
                "iou_threshold": {
                    "type": "number",
                    "description": "IoU 阈值，默认 0.45"
                }
            },
            "required": ["image_path"]
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        image_path = kwargs.get("image_path")
        scene_id = kwargs.get("scene_id", 1)
        batch_id = kwargs.get("batch_id")
        conf_threshold = kwargs.get("conf_threshold", 0.25)
        iou_threshold = kwargs.get("iou_threshold", 0.45)
        
        scene = self.db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
        if not scene:
            return {"error": f"检测场景 ID {scene_id} 不存在"}
        
        default_model = self.db.query(ModelVersion).filter(
            ModelVersion.scene_id == scene_id,
            ModelVersion.is_default == True,
            ModelVersion.status == "active"
        ).first()
        
        if not default_model:
            default_model = self.db.query(ModelVersion).filter(
                ModelVersion.scene_id == scene_id,
                ModelVersion.status == "active"
            ).order_by(desc(ModelVersion.created_at)).first()
        
        if not default_model:
            return {"error": f"场景 {scene_id} 没有可用的模型版本"}
        
        model_path = default_model.model_path
        
        new_task = DetectionTask(
            user_id=1,
            scene_id=scene_id,
            task_type="single",
            status="processing",
            total_images=1,
            total_objects=0,
            total_inference_time=0.0,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=640,
            batch_id=batch_id,
            model_version_id=default_model.id,
        )
        self.db.add(new_task)
        self.db.commit()
        self.db.refresh(new_task)
        
        try:
            detect_result = detect(
                model_path=model_path,
                image_path=image_path,
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
            )
            
            defects = detect_result.get("defects", [])
            inference_time = detect_result.get("inference_time", 0.0)
            image_width = detect_result.get("image_width", 640)
            image_height = detect_result.get("image_height", 640)
            
            for defect in defects:
                result = DetectionResult(
                    task_id=new_task.id,
                    image_path=image_path,
                    class_name=defect["class_name"],
                    class_name_cn=defect["class_name_cn"],
                    class_id=defect["class_id"],
                    confidence=defect["confidence"],
                    bbox=defect["bbox"],
                    inference_time=defect.get("inference_time", inference_time),
                    image_width=image_width,
                    image_height=image_height,
                )
                self.db.add(result)
                new_task.total_objects += 1
            
            new_task.status = "completed"
            new_task.total_inference_time = inference_time
            new_task.completed_at = datetime.now()
            self.db.commit()
            
            return {
                "task_id": new_task.id,
                "task_type": new_task.task_type,
                "status": new_task.status,
                "scene_name": scene.display_name,
                "model_version": default_model.version,
                "model_name": default_model.model_name,
                "total_images": new_task.total_images,
                "total_objects": new_task.total_objects,
                "inference_time": new_task.total_inference_time,
                "defects": defects,
            }
        
        except Exception as e:
            new_task.status = "failed"
            new_task.completed_at = datetime.now()
            self.db.commit()
            return {"error": f"检测失败: {str(e)}"}
class DetectionResultTool(BaseTool):
    """检测结果查询工具"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "get_detection_result"
    def get_description(self) -> str:
        return "查询检测结果详情，包括缺陷标注和统计信息"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "检测任务 ID"
                }
            },
            "required": ["task_id"]
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        task_id = kwargs.get("task_id")
        task = self.db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return {"error": f"检测任务 ID {task_id} 不存在"}
        scene = self.db.query(DetectionScene).filter(DetectionScene.id == task.scene_id).first()
        batch = None
        if task.batch_id:
            batch = self.db.query(PCBBatch).filter(PCBBatch.id == task.batch_id).first()
        results = self.db.query(DetectionResult).filter(DetectionResult.task_id == task_id).all()
        defect_list = []
        class_distribution = {}
        for result in results:
            defect_list.append({
                "id": result.id,
                "class_name": result.class_name,
                "class_name_cn": result.class_name_cn,
                "confidence": result.confidence,
                "bbox": result.bbox,
                "review_status": result.review_status.value if result.review_status else "pending",
                "severity": result.severity.value if result.severity else None,
            })
            class_distribution[result.class_name_cn or result.class_name] = (
                class_distribution.get(result.class_name_cn or result.class_name, 0) + 1
            )
        return {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "scene_name": scene.display_name if scene else None,
            "batch_no": batch.batch_no if batch else None,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "inference_time": task.total_inference_time,
            "conf_threshold": task.conf_threshold,
            "iou_threshold": task.iou_threshold,
            "class_distribution": class_distribution,
            "defects": defect_list,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
class TaskListTool(BaseTool):
    """任务列表查询工具"""
    def __init__(self, db: Session):
        self.db = db
    def get_name(self) -> str:
        return "get_task_list"
    def get_description(self) -> str:
        return "获取检测任务列表，支持按状态、时间筛选"
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "任务状态：pending/processing/completed/failed"
                },
                "page": {
                    "type": "integer",
                    "description": "页码，默认 1"
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页数量，默认 20"
                }
            }
        }
    def execute(self, **kwargs) -> Dict[str, Any]:
        status = kwargs.get("status")
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        query = self.db.query(DetectionTask)
        if status:
            query = query.filter(DetectionTask.status == status)
        query = query.order_by(desc(DetectionTask.created_at))
        total = query.count()
        offset = (page - 1) * page_size
        tasks = query.offset(offset).limit(page_size).all()
        task_list = []
        for task in tasks:
            scene = self.db.query(DetectionScene).filter(DetectionScene.id == task.scene_id).first()
            task_list.append({
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "scene_name": scene.display_name if scene else None,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "inference_time": task.total_inference_time,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            })
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "tasks": task_list,
        }

class DetectVideoFileTool(BaseTool):
    """视频文件检测工具"""
    def __init__(self, db: Session):
        self.db = db

    def get_name(self) -> str:
        return "detect_video_file"

    def get_description(self) -> str:
        return "对视频文件执行 PCB 缺陷检测，异步处理并返回进度"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "视频文件路径"},
                "scene_id": {"type": "integer", "description": "检测场景 ID，默认 1"},
                "conf_threshold": {"type": "number", "description": "置信度阈值，默认 0.25"},
                "frame_sample_rate": {"type": "integer", "description": "帧采样间隔，默认 5"},
                "max_frames": {"type": "integer", "description": "最多关键帧数，默认 50"},
            },
            "required": ["video_path"],
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        video_path = kwargs.get("video_path")
        scene_id = kwargs.get("scene_id", 1)
        conf_threshold = kwargs.get("conf_threshold", 0.25)
        frame_sample_rate = kwargs.get("frame_sample_rate", 5)
        max_frames = kwargs.get("max_frames", 50)

        from app.services.detection_service import detection_service
        result = detection_service.detect_video(
            video_path=video_path, conf=conf_threshold,
            frame_sample_rate=frame_sample_rate, max_frames=max_frames,
            scene_id=scene_id, user_id=1,
        )
        if "error" in result:
            return {"error": result["error"]}
        return {
            "task_id": result["task_id"], "total_frames": result["total_frames"],
            "processed_frames": result["processed_frames"], "fps": result["fps"],
            "duration_seconds": result["duration_seconds"],
            "total_objects": result["total_objects"],
            "class_counts": result["class_counts"],
            "total_inference_time": result["total_inference_time"],
            "success": True,
        }


def register_detection_tools(registry: ToolRegistry, db: Session):
    registry.register(DetectionTool(db))
    registry.register(DetectionResultTool(db))
    registry.register(TaskListTool(db))
    registry.register(DetectVideoFileTool(db))
