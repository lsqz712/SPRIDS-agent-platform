"""
分析统计工具集 — Agent 可调用的数据查询 @tool 函数

工具列表：
  - get_statistics_overview: 数据看板总览
  - query_detection_stats: 按天数统计检测数据
  - get_defect_types: 缺陷类型列表
  - get_task_list: 检测任务列表
  - get_task_detail: 任务详情
  - get_history_records: 历史记录
  - analyze_defects: 缺陷分析报告
  - calculate_pass_rate: 良品率计算
  - query_user_list: 用户列表查询
"""

import json
from datetime import datetime, timedelta

from langchain_core.tools import tool
from sqlalchemy import desc, func

from app.agent.shared import compress_tool_output
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import (
    DetectionResult, DetectionTask, DetectionScene, PCBBatch,
    DefectType, ModelVersion, TrainingTask, User,
)
from app.services.statistics_service import statistics_service
from app.services.defect_type_service import defect_type_service
from app.services.detection_service import detection_service

logger = get_logger(__name__)


@tool
def get_statistics_overview() -> str:
    """获取数据看板总览统计信息。

    返回系统整体检测数据概览：总任务数、完成任务数、失败任务数、总检测图像数、
    总检测目标数、平均推理耗时、各类别缺陷分布、各复判状态分布、各严重等级分布、各场景分布。
    """
    db = SessionLocal()
    try:
        data = statistics_service.get_overview(db=db)
        return compress_tool_output(data)
    finally:
        db.close()


@tool
def query_detection_stats(days: int = 30) -> str:
    """查询用户的检测统计数据。

    当用户询问"今天检测了多少次"、"最近检测了多少目标"、"检测统计"等统计类问题时使用此工具。

    Args:
        days: 统计最近 N 天的数据，默认 30 天

    Returns:
        JSON 字符串，包含总任务数、总目标数、各类型任务数等统计信息
    """
    db = SessionLocal()
    try:
        start_date = datetime.now() - timedelta(days=days)
        stats = (
            db.query(
                func.count(DetectionTask.id).label("total_tasks"),
                func.coalesce(func.sum(DetectionTask.total_objects), 0).label("total_objects"),
                func.coalesce(func.sum(DetectionTask.total_images), 0).label("total_images"),
                func.coalesce(func.avg(DetectionTask.total_inference_time), 0).label("avg_time"),
            )
            .filter(DetectionTask.created_at >= start_date)
            .first()
        )
        result = {
            "period": f"最近 {days} 天",
            "total_tasks": stats.total_tasks,
            "total_objects": int(stats.total_objects),
            "total_images": int(stats.total_images),
            "avg_inference_time_ms": round(float(stats.avg_time), 2),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("查询统计失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)
    finally:
        db.close()


@tool
def get_defect_types(keyword: str = None, severity: str = None, is_active: bool = None) -> str:
    """获取缺陷类型列表。

    Args:
        keyword: 搜索编码/名称/中文名（可选）
        severity: 按严重等级筛选：minor/major/critical（可选）
        is_active: 按启用状态筛选（可选）

    返回缺陷类型列表，包含编码、名称、中文名、严重等级等信息。
    """
    db = SessionLocal()
    try:
        items = defect_type_service.list_defect_types(
            db=db, keyword=keyword, severity=severity, is_active=is_active,
        )
        result = []
        for item in items:
            result.append({
                "id": item.id, "code": item.code, "name": item.name,
                "name_cn": item.name_cn, "severity": item.severity,
                "description": item.description, "is_active": item.is_active,
                "created_at": str(item.created_at),
            })
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_task_list(page: int = 1, page_size: int = 20, status: str = None, task_type: str = None) -> str:
    """获取检测任务列表。

    Args:
        page: 页码，默认 1
        page_size: 每页数量，默认 20
        status: 按状态筛选：pending/processing/completed/failed/cancelled（可选）
        task_type: 按类型筛选：single/batch/video/camera（可选）

    返回任务列表，包含任务 ID、状态、类型、检测图像数、目标数等信息。
    """
    db = SessionLocal()
    try:
        tasks, total = detection_service.list_tasks(
            db=db, page=page, page_size=page_size, status=status, task_type=task_type,
        )
        total_pages = (total + page_size - 1) // page_size
        return json.dumps({
            "total": total, "page": page, "page_size": page_size,
            "total_pages": total_pages, "items": tasks,
        }, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def get_task_detail(task_id: int) -> str:
    """获取检测任务详情。

    Args:
        task_id: 任务 ID

    返回任务详情，包含任务状态、检测结果、分析报告等信息。
    """
    db = SessionLocal()
    try:
        task = detection_service.get_task_by_id(db=db, task_id=task_id)
        task_data = {
            "id": task.id, "user_id": task.user_id, "scene_id": task.scene_id,
            "scene_name": task.scene.display_name if task.scene else None,
            "model_version_id": task.model_version_id, "task_type": task.task_type,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "total_images": task.total_images, "total_objects": task.total_objects,
            "total_inference_time": task.total_inference_time,
            "conf_threshold": task.conf_threshold, "iou_threshold": task.iou_threshold,
            "error_message": task.error_message, "batch_id": task.batch_id,
            "analysis_report": task.analysis_report, "analysis_suggestion": task.analysis_suggestion,
            "risk_level": task.risk_level, "source": task.source,
            "created_at": str(task.created_at),
            "completed_at": str(task.completed_at) if task.completed_at else None,
        }
        return compress_tool_output(task_data)
    finally:
        db.close()


@tool
def get_history_records(page: int = 1, page_size: int = 20) -> str:
    """获取历史检测记录。

    当用户询问"最近的检测结果"、"上次检测了什么"、"检测历史"等问题时使用此工具。

    Args:
        page: 页码，默认 1
        page_size: 每页数量，默认 20

    返回历史记录列表，包含任务 ID、用户、场景、状态、检测统计等信息。
    """
    db = SessionLocal()
    try:
        offset = (page - 1) * page_size
        tasks = (
            db.query(DetectionTask)
            .order_by(DetectionTask.created_at.desc())
            .offset(offset).limit(page_size).all()
        )
        items = []
        for task in tasks:
            items.append({
                "id": task.id, "user_id": task.user_id,
                "scene_id": task.scene_id, "scene_name": task.scene_name,
                "task_type": task.task_type,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "total_images": task.total_images, "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "created_at": str(task.created_at),
            })
        return json.dumps({"total": db.query(DetectionTask).count(), "page": page,
                           "page_size": page_size, "items": items}, ensure_ascii=False)
    finally:
        db.close()


@tool
def analyze_defects(task_id: int = None, batch_id: int = None, time_range: str = None) -> str:
    """分析缺陷数据，生成统计报告和维修建议。

    当用户需要分析缺陷分布、严重程度、风险等级或获取维修建议时使用此工具。

    Args:
        task_id: 检测任务 ID（可选）
        batch_id: PCB 批次 ID（可选）
        time_range: 时间范围，如 'today'/'week'/'month'（可选）

    Returns:
        缺陷分析报告，包含总数、类别分布、严重程度、风险分析和维修建议
    """
    db = SessionLocal()
    try:
        query = db.query(DetectionResult)
        if task_id:
            query = query.filter(DetectionResult.task_id == task_id)
        elif batch_id:
            tasks = db.query(DetectionTask.id).filter(DetectionTask.batch_id == batch_id).subquery()
            query = query.filter(DetectionResult.task_id.in_(tasks))
        elif time_range:
            end_time = datetime.now()
            delta_map = {"today": 1, "week": 7, "month": 30}
            days = delta_map.get(time_range, 7)
            start_time = end_time - timedelta(days=days)
            tasks = db.query(DetectionTask.id).filter(
                DetectionTask.created_at >= start_time
            ).subquery()
            query = query.filter(DetectionResult.task_id.in_(tasks))

        results = query.all()
        if not results:
            return json.dumps({"error": "未找到检测结果数据"}, ensure_ascii=False)

        class_distribution = {}
        severity_distribution = {"minor": 0, "major": 0, "critical": 0}
        image_set = set()
        for result in results:
            class_name = result.class_name_cn or result.class_name
            class_distribution[class_name] = class_distribution.get(class_name, 0) + 1
            if result.severity:
                severity_distribution[result.severity.value] += 1
            else:
                severity_distribution["major"] += 1
            image_set.add(result.image_path)

        total_defects = len(results)
        total_images = len(image_set)
        severity = severity_distribution

        risk_level = "low"
        if severity["critical"] > 0 or total_defects >= 20:
            risk_level = "critical"
        elif severity["major"] >= 5 or total_defects >= 10:
            risk_level = "high"
        elif severity["major"] > 0 or total_defects >= 5:
            risk_level = "medium"

        risk_map = {
            "critical": "高风险：存在致命缺陷，需立即停机排查",
            "high": "较高风险：缺陷数量较多，建议加强抽检",
            "medium": "中等风险：存在少量缺陷，需关注趋势",
            "low": "低风险：质量状况良好",
        }

        repair_suggestions = _build_repair_suggestions(class_distribution)

        return json.dumps({
            "total_defects": total_defects, "total_images": total_images,
            "defects_per_image": round(total_defects / max(total_images, 1), 2),
            "class_distribution": class_distribution,
            "severity_distribution": severity_distribution,
            "risk_analysis": {
                "level": risk_level, "description": risk_map[risk_level],
                "critical_count": severity["critical"],
                "major_count": severity["major"],
                "minor_count": severity["minor"],
            },
            "repair_suggestions": repair_suggestions,
        }, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def calculate_pass_rate(batch_id: int) -> str:
    """计算 PCB 批次的良品率。

    Args:
        batch_id: PCB 批次 ID

    返回批次良品率统计，包含总数、检测数、合格数、不合格数、良品率。
    """
    db = SessionLocal()
    try:
        batch = db.query(PCBBatch).filter(PCBBatch.id == batch_id).first()
        if not batch:
            return json.dumps({"error": f"PCB 批次 ID {batch_id} 不存在"}, ensure_ascii=False)

        tasks = db.query(DetectionTask).filter(DetectionTask.batch_id == batch_id).all()
        total_images = sum(task.total_images for task in tasks) if tasks else 0
        total_defects = 0
        defect_distribution = {}
        for task in tasks:
            results = db.query(DetectionResult).filter(DetectionResult.task_id == task.id).all()
            total_defects += len(results)
            for result in results:
                class_name = result.class_name_cn or result.class_name
                defect_distribution[class_name] = defect_distribution.get(class_name, 0) + 1

        pass_count = max(total_images - total_defects, 0)
        pass_rate = round((pass_count / max(total_images, 1)) * 100, 2)

        return json.dumps({
            "batch_id": batch.id,
            "batch_no": batch.batch_no if hasattr(batch, 'batch_no') else batch.name,
            "pcb_type": batch.pcb_type if hasattr(batch, 'pcb_type') else None,
            "total_count": batch.total_count if hasattr(batch, 'total_count') else None,
            "inspected_count": total_images, "pass_count": pass_count,
            "fail_count": total_defects, "pass_rate": pass_rate,
            "defect_distribution": defect_distribution, "status": batch.status,
        }, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def query_user_list(limit: int = 20) -> str:
    """查询系统中的用户列表。

    当用户询问"系统有哪些用户"、"有哪些管理员"、"用户列表"等问题时使用此工具。

    Args:
        limit: 返回最多 N 个用户，默认 20 个

    Returns:
        JSON 字符串，包含用户列表（用户名、邮箱、角色、注册时间）
    """
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
        items = []
        for u in users:
            items.append({
                "id": u.id, "username": u.username, "email": u.email,
                "roles": u.roles or [], "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "created_at": str(u.created_at) if u.created_at else None,
            })
        return json.dumps({"users": items, "count": len(items)}, ensure_ascii=False)
    except Exception as e:
        logger.error("查询用户列表失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)
    finally:
        db.close()


def _build_repair_suggestions(class_distribution: dict) -> list:
    """根据缺陷分布生成维修建议"""
    repair_map = {
        "短路": {"description": "PCB 上相邻导体之间出现意外导通",
                 "suggestion": "1. 检查焊锡量是否过多\n2. 检查钢网开口\n3. 调整焊接温度曲线\n4. 检查 PCB 间距",
                 "severity": "critical"},
        "开路": {"description": "预期导通的线路断开",
                 "suggestion": "1. 检查元件引脚是否氧化\n2. 检查焊锡量\n3. 检查回流温度\n4. 检查虚焊",
                 "severity": "critical"},
        "缺件": {"description": "元件未贴装到 PCB 上",
                 "suggestion": "1. 检查贴片机吸嘴\n2. 检查供料器\n3. 检查元件库存\n4. 检查贴装坐标",
                 "severity": "major"},
        "偏移": {"description": "元件贴装位置偏离",
                 "suggestion": "1. 检查贴片机精度\n2. 检查 PCB 定位\n3. 调整贴装压力\n4. 检查钢网对齐",
                 "severity": "major"},
        "焊点不良": {"description": "焊点形状或质量不符合要求",
                     "suggestion": "1. 调整焊接温度曲线\n2. 检查助焊剂\n3. 检查焊锡品质\n4. 调整回流速度",
                     "severity": "minor"},
    }
    suggestions = []
    for defect_name, count in class_distribution.items():
        if defect_name in repair_map:
            suggestions.append({
                "defect_type": defect_name, "count": count,
                "description": repair_map[defect_name]["description"],
                "suggestion": repair_map[defect_name]["suggestion"],
                "severity": repair_map[defect_name]["severity"],
            })
    return sorted(suggestions, key=lambda x: ["critical", "major", "minor"].index(x["severity"]))


# 分析工具列表
ANALYSIS_TOOLS = [
    get_statistics_overview,
    query_detection_stats,
    get_defect_types,
    get_task_list,
    get_task_detail,
    get_history_records,
    analyze_defects,
    calculate_pass_rate,
    query_user_list,
]
