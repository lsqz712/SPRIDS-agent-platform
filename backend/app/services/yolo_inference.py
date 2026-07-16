"""
YOLO 推理服务
封装 ultralytics YOLO 模型加载和推理逻辑，支持模型缓存
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import cv2
from ultralytics import YOLO
from ultralytics.engine.results import Results
from app.config.settings import settings

_model_cache: Dict[str, YOLO] = {}

DEFAULT_CLASS_NAMES = {
    0: {"name": "short", "name_cn": "短路"},
    1: {"name": "open", "name_cn": "开路"},
    2: {"name": "missing", "name_cn": "缺件"},
    3: {"name": "offset", "name_cn": "偏移"},
    4: {"name": "solder", "name_cn": "焊点不良"},
}

def load_model(model_path: str) -> YOLO:
    """
    加载 YOLO 模型（带缓存）
    
    Args:
        model_path: 模型文件路径，可以是相对路径或绝对路径
    
    Returns:
        YOLO 模型实例
    """
    abs_path = os.path.abspath(model_path)
    
    if abs_path in _model_cache:
        return _model_cache[abs_path]
    
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"模型文件不存在: {abs_path}")
    
    try:
        model = YOLO(abs_path)
        _model_cache[abs_path] = model
        return model
    except Exception as e:
        raise RuntimeError(f"模型加载失败: {str(e)}")

def detect(
    model_path: str,
    image_path: str,
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    imgsz: int = 640,
    class_names: Optional[Dict[int, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    执行 YOLO 目标检测
    
    Args:
        model_path: 模型文件路径
        image_path: 图像文件路径
        conf_threshold: 置信度阈值
        iou_threshold: IoU 阈值
        imgsz: 输入图像尺寸
        class_names: 类别名称映射
    
    Returns:
        检测结果字典
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    model = load_model(model_path)
    
    try:
        results: Results = model.predict(
            source=image_path,
            conf=conf_threshold,
            iou=iou_threshold,
            imgsz=imgsz,
            verbose=False,
        )
        
        if len(results) == 0:
            return {
                "success": True,
                "defects": [],
                "inference_time": 0.0,
                "image_width": 0,
                "image_height": 0,
            }
        
        result = results[0]
        class_map = class_names or DEFAULT_CLASS_NAMES
        
        defects = []
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            bbox = box.xyxy[0].tolist()
            bbox = [round(x, 2) for x in bbox]
            
            class_info = class_map.get(class_id, {"name": f"class_{class_id}", "name_cn": f"类别{class_id}"})
            
            defects.append({
                "class_id": class_id,
                "class_name": class_info["name"],
                "class_name_cn": class_info["name_cn"],
                "confidence": confidence,
                "bbox": bbox,
                "inference_time": float(result.speed.get("inference", 0)),
            })
        
        image_shape = result.orig_shape
        inference_time = float(result.speed.get("inference", 0))
        
        return {
            "success": True,
            "defects": defects,
            "inference_time": inference_time,
            "image_width": image_shape[1],
            "image_height": image_shape[0],
        }
    
    except Exception as e:
        raise RuntimeError(f"检测失败: {str(e)}")

def batch_detect(
    model_path: str,
    image_paths: List[str],
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    imgsz: int = 640,
    class_names: Optional[Dict[int, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    批量执行 YOLO 目标检测
    
    Args:
        model_path: 模型文件路径
        image_paths: 图像文件路径列表
        conf_threshold: 置信度阈值
        iou_threshold: IoU 阈值
        imgsz: 输入图像尺寸
        class_names: 类别名称映射
    
    Returns:
        检测结果列表
    """
    results = []
    for img_path in image_paths:
        try:
            result = detect(
                model_path=model_path,
                image_path=img_path,
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                imgsz=imgsz,
                class_names=class_names,
            )
            result["image_path"] = img_path
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e),
                "image_path": img_path,
            })
    return results


def detect_video_frame(
    model: YOLO,
    frame,
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    imgsz: int = 640,
    class_names: Optional[Dict[int, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    对单帧图像执行 YOLO 目标检测
    
    Args:
        model: YOLO 模型实例
        frame: 视频帧（numpy array）
        conf_threshold: 置信度阈值
        iou_threshold: IoU 阈值
        imgsz: 输入图像尺寸
        class_names: 类别名称映射
    
    Returns:
        检测结果字典
    """
    try:
        results: Results = model.predict(
            source=frame,
            conf=conf_threshold,
            iou=iou_threshold,
            imgsz=imgsz,
            verbose=False,
        )
        
        if len(results) == 0:
            return {
                "success": True,
                "defects": [],
                "inference_time": 0.0,
                "image_width": frame.shape[1] if len(frame.shape) >= 2 else 0,
                "image_height": frame.shape[0] if len(frame.shape) >= 2 else 0,
            }
        
        result = results[0]
        class_map = class_names or DEFAULT_CLASS_NAMES
        
        defects = []
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            bbox = box.xyxy[0].tolist()
            bbox = [round(x, 2) for x in bbox]
            
            class_info = class_map.get(class_id, {"name": f"class_{class_id}", "name_cn": f"类别{class_id}"})
            
            defects.append({
                "class_id": class_id,
                "class_name": class_info["name"],
                "class_name_cn": class_info["name_cn"],
                "confidence": confidence,
                "bbox": bbox,
                "inference_time": float(result.speed.get("inference", 0)),
            })
        
        image_shape = result.orig_shape
        inference_time = float(result.speed.get("inference", 0))
        
        return {
            "success": True,
            "defects": defects,
            "inference_time": inference_time,
            "image_width": image_shape[1],
            "image_height": image_shape[0],
        }
    
    except Exception as e:
        raise RuntimeError(f"帧检测失败: {str(e)}")


def detect_video(
    model_path: str,
    video_path: str,
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    imgsz: int = 640,
    frame_interval: int = 10,
    class_names: Optional[Dict[int, Dict[str, str]]] = None,
    progress_callback=None,
) -> Dict[str, Any]:
    """
    执行视频检测（按帧间隔采样检测）
    
    Args:
        model_path: 模型文件路径
        video_path: 视频文件路径
        conf_threshold: 置信度阈值
        iou_threshold: IoU 阈值
        imgsz: 输入图像尺寸
        frame_interval: 检测帧间隔（每隔多少帧检测一次）
        class_names: 类别名称映射
        progress_callback: 进度回调函数，接收进度百分比
    
    Returns:
        检测结果字典
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    model = load_model(model_path)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("无法打开视频文件")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    all_defects = []
    frame_count = 0
    detected_frames = 0
    total_inference_time = 0.0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            if frame_count % frame_interval == 0:
                result = detect_video_frame(
                    model=model,
                    frame=frame,
                    conf_threshold=conf_threshold,
                    iou_threshold=iou_threshold,
                    imgsz=imgsz,
                    class_names=class_names,
                )
                
                if result["success"]:
                    for defect in result["defects"]:
                        defect["frame_index"] = frame_count
                        defect["timestamp"] = round(frame_count / fps, 2) if fps > 0 else 0
                    all_defects.extend(result["defects"])
                    detected_frames += 1
                    total_inference_time += result["inference_time"]
                
                if progress_callback:
                    progress = min(100, int(frame_count / total_frames * 100))
                    progress_callback(progress)
        
        return {
            "success": True,
            "task_type": "video",
            "total_frames": total_frames,
            "detected_frames": detected_frames,
            "frame_interval": frame_interval,
            "fps": round(fps, 2) if fps > 0 else 0,
            "duration": round(duration, 2),
            "total_objects": len(all_defects),
            "total_inference_time": round(total_inference_time, 2),
            "results": all_defects,
        }
    
    finally:
        cap.release()


def list_camera_devices(max_devices: int = 10) -> List[Dict[str, Any]]:
    """
    枚举可用的摄像头设备
    
    Args:
        max_devices: 最大枚举设备数
    
    Returns:
        设备列表，包含设备ID和名称
    """
    devices = []
    
    for i in range(max_devices):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # 获取设备信息
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            devices.append({
                "device_id": i,
                "name": f"摄像头 {i + 1}",
                "resolution": f"{width}x{height}",
                "fps": round(fps, 2) if fps > 0 else 0,
            })
            
            cap.release()
    
    return devices