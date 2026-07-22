"""
检测工具集 — Agent 可调用的检测相关 @tool 函数

工具列表：
  - detect_single_image: 单张图片检测
  - detect_batch_images: 批量图片检测
  - detect_zip_images_file: ZIP 文件解压检测
  - detect_video_file: 视频文件检测
"""

import json

from langchain_core.tools import tool

from app.agent.shared import compress_tool_output
from app.core.logger import get_logger
from app.services.detection_service import detection_service

logger = get_logger(__name__)


@tool
def detect_single_image(image_path: str, conf: float = 0.25, iou: float = 0.45) -> str:
    """检测单张图片中的目标物体。

    当用户上传了一张图片并要求检测、识别、分析图中的目标时使用此工具。

    Args:
        image_path: 图片文件的服务器路径（绝对路径），如 /tmp/rsod_uploads/xxx.jpg
        conf: 置信度阈值，0~1 之间，默认 0.25
        iou: NMS IoU 阈值，0~1 之间，默认 0.45

    Returns:
        JSON 字符串，包含检测结果（目标数量、类别统计、标注图路径、推理耗时）
    """
    try:
        result = detection_service.detect_single(image_path, conf=conf, iou=iou)
        logger.info("单图检测完成: %s, 目标数: %d", image_path, result.get("total_objects", 0))
        return compress_tool_output(result)
    except Exception as e:
        logger.error("单图检测失败: %s", str(e))
        return json.dumps({"error": f"检测失败: {str(e)}"}, ensure_ascii=False)


@tool
def detect_batch_images(image_paths: list[str], conf: float = 0.25) -> str:
    """批量检测多张图片中的目标物体。

    当用户一次上传了多张图片，或者要求"检测所有图片"时使用此工具。

    Args:
        image_paths: 图片文件路径列表
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含每张图片的检测结果汇总
    """
    try:
        result = detection_service.detect_batch(image_paths, conf=conf)
        logger.info("批量检测完成: %d 张图片", len(image_paths))
        return compress_tool_output(result)
    except Exception as e:
        logger.error("批量检测失败: %s", str(e))
        return json.dumps({"error": f"批量检测失败: {str(e)}"}, ensure_ascii=False)


@tool
def detect_zip_images_file(zip_path: str, conf: float = 0.25) -> str:
    """解压 ZIP 文件并批量检测其中所有图片的目标物体。

    当用户上传了 ZIP 压缩包进行批量检测时使用此工具。

    Args:
        zip_path: ZIP 文件的服务器路径
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含 ZIP 内所有图片的检测结果汇总
    """
    try:
        result = detection_service.detect_zip(zip_path, conf=conf)
        logger.info("ZIP 检测完成: %s", zip_path)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("ZIP 检测失败: %s", str(e))
        return json.dumps({"error": f"ZIP 检测失败: {str(e)}"}, ensure_ascii=False)


@tool
def detect_video_file(video_path: str, conf: float = 0.25, frame_sample_rate: int = 5) -> str:
    """检测视频文件中的目标物体。对视频进行帧采样后逐帧检测。

    当用户上传了视频文件并要求检测视频中的目标时使用此工具。

    Args:
        video_path: 视频文件的服务器路径（mp4/avi/mov 等格式）
        conf: 置信度阈值，默认 0.25
        frame_sample_rate: 帧采样间隔，每 N 帧取 1 帧进行检测，默认 5

    Returns:
        JSON 字符串，包含视频检测结果（关键帧目标统计、视频时长、处理帧数）
    """
    result = detection_service.detect_video(
        video_path, conf=conf, frame_sample_rate=frame_sample_rate
    )
    if "key_frames" in result:
        for frame in result["key_frames"]:
            frame.pop("annotated_image_base64", None)
    result.pop("annotated_video_url", None)
    logger.info("视频检测完成: %s", video_path)
    return json.dumps(result, ensure_ascii=False)


# 工具列表
DETECTION_TOOLS = [
    detect_single_image,
    detect_batch_images,
    detect_zip_images_file,
    detect_video_file,
]
