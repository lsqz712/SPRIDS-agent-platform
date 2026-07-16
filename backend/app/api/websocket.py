"""
WebSocket API 路由 — 实时检测接口
支持摄像头实时检测、视频流检测等功能
"""
import json
import asyncio
import cv2
import base64
import io
import numpy as np
from PIL import Image
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from app.services.yolo_inference import load_model, detect_video_frame, DEFAULT_CLASS_NAMES
from app.services.detection_service import detection_service

router = APIRouter(prefix="/ws", tags=["实时检测"])

_active_camera_streams = {}


@router.websocket("/camera/detect")
async def websocket_camera_detect(
    websocket: WebSocket,
    device_id: int = Query(0, description="摄像头设备ID"),
    conf: float = Query(0.25, description="置信度阈值"),
    iou: float = Query(0.45, description="IoU阈值"),
):
    """
    摄像头实时检测 WebSocket 接口
    
    客户端发送:
    - JSON: {"type": "start"} - 开始检测
    - JSON: {"type": "stop"} - 停止检测
    - JSON: {"type": "config", "conf": 0.3, "iou": 0.5} - 更新检测参数
    
    服务端发送:
    - JSON: {"type": "detection", "defects": [...], "frame_index": N} - 检测结果
    - JSON: {"type": "error", "message": "..."} - 错误信息
    - JSON: {"type": "status", "message": "..."} - 状态信息
    """
    await websocket.accept()
    
    session_key = f"{id(websocket)}"
    camera_stream = None
    model = None
    model_path = None
    frame_interval = 1
    frame_count = 0
    
    try:
        await websocket.send_json({
            "type": "status",
            "message": "连接成功，准备启动摄像头",
        })
        
        model_path = detection_service._get_model_path(None)
        model = load_model(model_path)
        
        camera_stream = cv2.VideoCapture(device_id)
        if not camera_stream.isOpened():
            await websocket.send_json({
                "type": "error",
                "message": f"无法打开摄像头设备 {device_id}，请检查设备是否连接",
            })
            return
        
        _active_camera_streams[session_key] = {"stream": camera_stream, "running": True}
        
        await websocket.send_json({
            "type": "status",
            "message": f"摄像头 {device_id} 已启动，开始实时检测",
        })
        
        running = True
        while running and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await asyncio.sleep(0.05)
                
                ret, frame = camera_stream.read()
                if not ret:
                    await websocket.send_json({
                        "type": "error",
                        "message": "无法读取摄像头帧",
                    })
                    break
                
                frame_count += 1
                
                if frame_count % frame_interval == 0:
                    result = detect_video_frame(
                        model=model,
                        frame=frame,
                        conf_threshold=conf,
                        iou_threshold=iou,
                    )
                    
                    await websocket.send_json({
                        "type": "detection",
                        "frame_index": frame_count,
                        "defects": result.get("defects", []),
                        "image_width": result.get("image_width", 0),
                        "image_height": result.get("image_height", 0),
                        "inference_time": result.get("inference_time", 0),
                    })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except WebSocketDisconnect:
        pass
    finally:
        if camera_stream:
            camera_stream.release()
        if session_key in _active_camera_streams:
            del _active_camera_streams[session_key]


@router.websocket("/frame/detect")
async def websocket_frame_detect(
    websocket: WebSocket,
    conf: float = Query(0.25, description="置信度阈值"),
    iou: float = Query(0.45, description="IoU阈值"),
):
    """
    单帧图像检测 WebSocket 接口
    
    客户端发送:
    - Base64 编码的图像数据
    
    服务端发送:
    - JSON: {"type": "detection", "defects": [...]} - 检测结果
    - JSON: {"type": "error", "message": "..."} - 错误信息
    """
    await websocket.accept()
    
    model = None
    model_path = None
    
    try:
        model_path = detection_service._get_model_path(None)
        model = load_model(model_path)
        
        while websocket.client_state == WebSocketState.CONNECTED:
            data = await websocket.receive_text()
            
            try:
                if data.startswith("data:image"):
                    data = data.split(",")[1]
                
                image_data = base64.b64decode(data)
                np_array = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
                
                result = detect_video_frame(
                    model=model,
                    frame=frame,
                    conf_threshold=conf,
                    iou_threshold=iou,
                )
                
                await websocket.send_json({
                    "type": "detection",
                    "defects": result.get("defects", []),
                    "image_width": result.get("image_width", 0),
                    "image_height": result.get("image_height", 0),
                    "inference_time": result.get("inference_time", 0),
                })
            
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except WebSocketDisconnect:
        pass