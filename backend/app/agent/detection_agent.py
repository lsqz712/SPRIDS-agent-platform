"""
检测智能体 — ReAct Agent + 检测工具绑定 + RAG + 对话记忆

职责：
  - 创建 LangChain ReAct Agent
  - 绑定检测相关工具（单图/批量/ZIP/视频）
  - 绑定数据查询工具（统计、任务、缺陷类型、训练等）
  - 绑定 RAG 知识库工具（search_knowledge）
  - 集成对话记忆（Redis），支持跨轮次上下文理解
  - 处理 SSE 流式输出 Agent 的思考过程和结果

架构：
  用户消息 → 对话记忆加载 → Agent（LLM 决策）→ 调用工具 → 返回结果 → 对话记忆保存

使用方式：
  from app.agent.detection_agent import detection_agent

  agent = DetectionAgent()
  response = await agent.chat("检测这张图片", image_path="xxx.jpg", user_id=1, session_id="abc123")
"""

import json
from typing import AsyncGenerator, List, Dict

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.services.detection_service import detection_service
from app.services.statistics_service import statistics_service
from app.services.defect_type_service import defect_type_service
from app.entity.db_models import TrainingTask, DetectionScene, PCBBatch, ModelVersion, DetectionResult, DetectionTask, DefectType
from app.agent.memory import conversation_memory, estimate_tokens, estimate_message_tokens, trim_messages_to_token_limit

logger = get_logger(__name__)

MAX_TOOL_OUTPUT_CHARS = 2000
MAX_LIST_ITEMS = 5
MAX_CONTEXT_TOKENS = 8000


def compress_tool_output(data: dict) -> str:
    """
    压缩工具输出，减少 token 消耗。
    
    策略：
    1. 列表类数据：只保留前 MAX_LIST_ITEMS 条 + total 计数
    2. 移除 null/空字符串/空列表字段
    3. 深度清理嵌套结构
    4. 限制最终 JSON 长度不超过 MAX_TOOL_OUTPUT_CHARS
    5. 优先保留关键字段（id、name、count 等）
    """
    PRIORITY_FIELDS = {"id", "name", "count", "total", "status", "confidence", "class_name", "result"}
    
    def clean_item(item, depth=0):
        if depth > 3:
            return str(item) if item else None
        if isinstance(item, dict):
            cleaned = {}
            for k, v in item.items():
                if v is None or v == "" or v == [] or v == {}:
                    continue
                if k in PRIORITY_FIELDS:
                    cleaned[k] = clean_item(v, depth + 1)
                elif depth < 2:
                    cleaned[k] = clean_item(v, depth + 1)
            return cleaned if cleaned else None
        elif isinstance(item, list):
            if depth == 0:
                return [clean_item(i, depth + 1) for i in item[:MAX_LIST_ITEMS] if clean_item(i, depth + 1) is not None]
            return [clean_item(i, depth + 1) for i in item[:3] if clean_item(i, depth + 1) is not None]
        return item

    cleaned_data = clean_item(data)
    if cleaned_data is None:
        cleaned_data = {}
    
    if "items" in cleaned_data and isinstance(cleaned_data["items"], list) and "total" not in cleaned_data:
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            cleaned_data["total"] = len(data["items"])
    
    result = json.dumps(cleaned_data, ensure_ascii=False, default=str)
    
    if len(result) > MAX_TOOL_OUTPUT_CHARS:
        result = result[:MAX_TOOL_OUTPUT_CHARS - 3] + "..."
    
    return result


@tool
def detect_single_image(image_path: str, conf: float = 0.25, iou: float = 0.45) -> str:
    """
    检测单张图片中的目标物体。

    Args:
        image_path: 图片文件路径或 URL
        conf: 置信度阈值，默认 0.25
        iou: NMS IoU 阈值，默认 0.45

    Returns:
        JSON 字符串，包含检测结果（目标数量、类别统计、标注图路径）
    """
    result = detection_service.detect_single(image_path, conf=conf, iou=iou)
    return compress_tool_output(result)


@tool
def detect_batch_images(image_paths: list[str], conf: float = 0.25) -> str:
    """
    批量检测多张图片中的目标物体。

    Args:
        image_paths: 图片文件路径列表
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含每张图片的检测结果汇总
    """
    result = detection_service.detect_batch(image_paths, conf=conf)
    return compress_tool_output(result)


@tool
def detect_zip_images_file(zip_path: str, conf: float = 0.25) -> str:
    """
    解压 ZIP 文件并批量检测其中所有图片的目标物体。

    Args:
        zip_path: ZIP 文件路径
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含 ZIP 内所有图片的检测结果汇总
    """
    result = detection_service.detect_zip(zip_path, conf=conf)
    return json.dumps(result, ensure_ascii=False)


@tool
def get_statistics_overview() -> str:
    """
    获取数据看板总览统计信息。

    返回系统整体检测数据概览：
    - 总任务数、完成任务数、失败任务数
    - 总检测图像数、总检测目标数
    - 平均推理耗时
    - 各类别缺陷分布
    - 各复判状态分布
    - 各严重等级分布
    - 各场景分布
    """
    db = SessionLocal()
    try:
        data = statistics_service.get_overview(db=db)
        return compress_tool_output(data)
    finally:
        db.close()


@tool
def get_defect_types(keyword: str = None, severity: str = None, is_active: bool = None) -> str:
    """
    获取缺陷类型列表。

    Args:
        keyword: 搜索编码/名称/中文名（可选）
        severity: 按严重等级筛选：minor/major/critical（可选）
        is_active: 按启用状态筛选（可选）

    返回缺陷类型列表，包含编码、名称、中文名、严重等级等信息。
    """
    db = SessionLocal()
    try:
        items = defect_type_service.list_defect_types(
            db=db,
            keyword=keyword,
            severity=severity,
            is_active=is_active,
        )
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "name_cn": item.name_cn,
                "severity": item.severity,
                "description": item.description,
                "is_active": item.is_active,
                "created_at": str(item.created_at),
            })
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_task_list(page: int = 1, page_size: int = 20, status: str = None, task_type: str = None) -> str:
    """
    获取检测任务列表。

    Args:
        page: 页码，默认 1
        page_size: 每页数量，默认 20
        status: 按状态筛选：pending/processing/completed/failed/cancelled（可选）
        task_type: 按类型筛选：single/batch（可选）

    返回任务列表，包含任务 ID、状态、类型、检测图像数、目标数等信息。
    """
    db = SessionLocal()
    try:
        tasks, total = detection_service.list_tasks(
            db=db,
            page=page,
            page_size=page_size,
            status=status,
            task_type=task_type,
        )
        total_pages = (total + page_size - 1) // page_size
        return json.dumps({
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": tasks,
        }, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def get_task_detail(task_id: int) -> str:
    """
    获取检测任务详情。

    Args:
        task_id: 任务 ID

    返回任务详情，包含任务状态、检测结果、分析报告等信息。
    """
    db = SessionLocal()
    try:
        task = detection_service.get_task_by_id(db=db, task_id=task_id)
        task_data = {
            "id": task.id,
            "user_id": task.user_id,
            "scene_id": task.scene_id,
            "scene_name": task.scene.display_name if task.scene else None,
            "model_version_id": task.model_version_id,
            "task_type": task.task_type,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "total_inference_time": task.total_inference_time,
            "conf_threshold": task.conf_threshold,
            "iou_threshold": task.iou_threshold,
            "error_message": task.error_message,
            "batch_id": task.batch_id,
            "analysis_report": task.analysis_report,
            "analysis_suggestion": task.analysis_suggestion,
            "risk_level": task.risk_level,
            "source": task.source,
            "created_at": str(task.created_at),
            "completed_at": str(task.completed_at) if task.completed_at else None,
        }
        return compress_tool_output(task_data)
    finally:
        db.close()


@tool
def get_history_records(page: int = 1, page_size: int = 20) -> str:
    """
    获取历史检测记录。

    Args:
        page: 页码，默认 1
        page_size: 每页数量，默认 20

    返回历史记录列表，包含任务 ID、用户、场景、状态、检测统计等信息。
    """
    db = SessionLocal()
    try:
        offset = (page - 1) * page_size
        tasks = (
            db.query(detection_service.task_model)
            .order_by(detection_service.task_model.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        total = db.query(detection_service.task_model).count()
        items = []
        for task in tasks:
            items.append({
                "id": task.id,
                "user_id": task.user_id,
                "scene_id": task.scene_id,
                "scene_name": task.scene_name,
                "task_type": task.task_type,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "created_at": str(task.created_at),
            })
        return json.dumps({
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }, ensure_ascii=False)
    finally:
        db.close()


@tool
def get_training_tasks() -> str:
    """
    获取模型训练任务列表。

    返回所有训练任务，包含任务状态、模型名称、训练进度、epoch 等信息。
    """
    db = SessionLocal()
    try:
        tasks = db.query(TrainingTask).order_by(TrainingTask.created_at.desc()).all()
        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "user_id": task.user_id,
                "scene_id": task.scene_id,
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
                "created_at": str(task.created_at),
                "started_at": str(task.started_at) if task.started_at else None,
                "completed_at": str(task.completed_at) if task.completed_at else None,
            })
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_scenes() -> str:
    """
    获取检测场景列表。

    返回所有检测场景，包含场景 ID、名称、类别等信息。
    """
    db = SessionLocal()
    try:
        scenes = db.query(DetectionScene).order_by(DetectionScene.created_at.desc()).all()
        result = []
        for scene in scenes:
            result.append({
                "id": scene.id,
                "name": scene.name,
                "display_name": scene.display_name,
                "category": scene.category,
                "description": scene.description,
                "is_active": scene.is_active,
                "created_at": str(scene.created_at),
            })
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_batches() -> str:
    """
    获取PCB批次列表。

    返回所有PCB批次，包含批次ID、名称、描述、创建时间等信息。
    """
    db = SessionLocal()
    try:
        batches = db.query(PCBBatch).order_by(PCBBatch.created_at.desc()).all()
        result = []
        for batch in batches:
            result.append({
                "id": batch.id,
                "name": batch.name,
                "description": batch.description,
                "created_at": str(batch.created_at),
            })
        return compress_tool_output({"items": result, "total": len(result)})
    finally:
        db.close()


@tool
def get_model_info(model_id: int = None, scene_id: int = None) -> str:
    """
    查询模型版本信息，包括性能指标和适用场景。

    Args:
        model_id: 模型版本 ID（可选）
        scene_id: 场景 ID（可选，查询该场景的所有模型）

    Returns:
        模型信息列表或单个模型详情
    """
    from sqlalchemy import desc
    db = SessionLocal()
    try:
        if model_id:
            model = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
            if not model:
                return json.dumps({"error": f"模型版本 ID {model_id} 不存在"}, ensure_ascii=False)
            scene = db.query(DetectionScene).filter(DetectionScene.id == model.scene_id).first()
            result = {
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
                "description": model.description,
                "is_default": model.is_default,
                "created_at": str(model.created_at) if model.created_at else None,
            }
            return json.dumps(result, ensure_ascii=False)
        elif scene_id:
            models = db.query(ModelVersion).filter(
                ModelVersion.scene_id == scene_id
            ).order_by(desc(ModelVersion.created_at)).all()
            scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
            model_list = []
            for model in models:
                model_list.append({
                    "model_id": model.id,
                    "version": model.version,
                    "model_name": model.model_name,
                    "status": model.status,
                    "map50": model.map50,
                    "is_default": model.is_default,
                })
            result = {
                "scene_name": scene.display_name if scene else None,
                "total_models": len(model_list),
                "models": model_list,
            }
            return compress_tool_output(result)
        else:
            models = db.query(ModelVersion).order_by(desc(ModelVersion.created_at)).all()
            model_list = []
            for model in models:
                model_list.append({
                    "model_id": model.id,
                    "version": model.version,
                    "model_name": model.model_name,
                    "status": model.status,
                    "map50": model.map50,
                })
            return compress_tool_output({"items": model_list, "total": len(model_list)})
    finally:
        db.close()


@tool
def analyze_defects(task_id: int = None, batch_id: int = None, time_range: str = None) -> str:
    """
    分析缺陷数据，生成统计报告和维修建议。

    当用户需要分析缺陷分布、严重程度、风险等级或获取维修建议时使用此工具。

    Args:
        task_id: 检测任务 ID（可选）
        batch_id: PCB 批次 ID（可选）
        time_range: 时间范围，如 'today'/'week'/'month'（可选）

    Returns:
        缺陷分析报告，包含总数、类别分布、严重程度、风险分析和维修建议
    """
    from datetime import datetime, timedelta
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
            if time_range == "today":
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "week":
                start_time = end_time - timedelta(days=7)
            elif time_range == "month":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)
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
        if total_defects == 0:
            risk_level = "low"
        elif severity["critical"] > 0 or total_defects >= 20:
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
        
        repair_map = {
            "短路": {
                "description": "PCB 上相邻导体之间出现意外导通",
                "suggestion": "1. 检查焊锡量是否过多导致桥连\n2. 检查钢网开口是否过大\n3. 调整焊接温度曲线\n4. 检查 PCB 设计是否存在间距过小问题",
                "severity": "critical",
            },
            "开路": {
                "description": "预期导通的线路断开",
                "suggestion": "1. 检查元件引脚是否氧化\n2. 检查焊锡量是否不足\n3. 检查回流温度是否足够\n4. 检查元件是否虚焊",
                "severity": "critical",
            },
            "缺件": {
                "description": "元件未贴装到 PCB 上",
                "suggestion": "1. 检查贴片机吸嘴是否堵塞\n2. 检查供料器是否正常\n3. 检查元件是否用完\n4. 检查贴装坐标是否正确",
                "severity": "major",
            },
            "偏移": {
                "description": "元件贴装位置偏离",
                "suggestion": "1. 检查贴片机精度\n2. 检查 PCB 定位是否准确\n3. 调整贴装压力\n4. 检查钢网与 PCB 对齐情况",
                "severity": "major",
            },
            "焊点不良": {
                "description": "焊点形状、光泽或质量不符合要求",
                "suggestion": "1. 调整焊接温度曲线\n2. 检查助焊剂是否过期\n3. 检查焊锡品质\n4. 调整回流速度",
                "severity": "minor",
            },
        }
        
        repair_suggestions = []
        for defect_name, count in class_distribution.items():
            if defect_name in repair_map:
                repair_suggestions.append({
                    "defect_type": defect_name,
                    "count": count,
                    "description": repair_map[defect_name]["description"],
                    "suggestion": repair_map[defect_name]["suggestion"],
                    "severity": repair_map[defect_name]["severity"],
                })
        
        result = {
            "total_defects": total_defects,
            "total_images": total_images,
            "defects_per_image": round(total_defects / max(total_images, 1), 2),
            "class_distribution": class_distribution,
            "severity_distribution": severity_distribution,
            "risk_analysis": {
                "level": risk_level,
                "description": risk_map[risk_level],
                "critical_count": severity["critical"],
                "major_count": severity["major"],
                "minor_count": severity["minor"],
            },
            "repair_suggestions": repair_suggestions,
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def calculate_pass_rate(batch_id: int) -> str:
    """
    计算 PCB 批次的良品率。

    Args:
        batch_id: PCB 批次 ID

    Returns:
        批次良品率统计，包含总数、检测数、合格数、不合格数、良品率
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
        
        result = {
            "batch_id": batch.id,
            "batch_no": batch.batch_no if hasattr(batch, 'batch_no') else batch.name,
            "pcb_type": batch.pcb_type if hasattr(batch, 'pcb_type') else None,
            "total_count": batch.total_count if hasattr(batch, 'total_count') else None,
            "inspected_count": total_images,
            "pass_count": pass_count,
            "fail_count": total_defects,
            "pass_rate": pass_rate,
            "defect_distribution": defect_distribution,
            "status": batch.status,
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def search_knowledge(query: str) -> str:
    """
    搜索知识库，回答目标检测、YOLO、PCB检测等领域知识问题。

    当用户询问专业知识（如"什么是 IoU"、"YOLO 如何工作"、"PCB 缺陷类型"）时使用此工具。
    使用混合检索（BM25 + 向量相似度）+ 重排序提升检索质量。

    Args:
        query: 用户的问题或搜索关键词

    Returns:
        JSON 字符串，包含回答内容和来源信息
    """
    try:
        from app.rag.retriever import rag_retriever

        result = rag_retriever.search(query, top_k=5, use_hybrid=True, use_rerank=True)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("知识库检索失败: %s", str(e))
        return json.dumps({"error": f"知识库检索失败: {str(e)}"}, ensure_ascii=False)


DETECTION_TOOLS = [
    detect_single_image,
    detect_batch_images,
    detect_zip_images_file,
    get_statistics_overview,
    get_defect_types,
    get_task_list,
    get_task_detail,
    get_history_records,
    get_training_tasks,
    get_model_info,
    get_scenes,
    get_batches,
    analyze_defects,
    calculate_pass_rate,
    search_knowledge,
]


def create_llm():
    api_key = settings.effective_llm_api_key
    if not api_key:
        logger.warning("未配置 LLM API Key，将使用模拟模式")
        return None

    base_url = settings.effective_llm_base_url
    model_name = settings.effective_llm_model

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
    )


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 创建和对话逻辑"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("DetectionAgent 初始化完成（模拟模式），绑定 %d 个工具", len(DETECTION_TOOLS))
            return

        system_prompt = """你是一个专业的PCB检测智能助手，帮助用户检测PCB缺陷、查询检测数据和回答领域知识问题。

工具调用规则：
1. 消息含 [附件图片路径: xxx] → 调用检测工具
2. 询问专业知识（IoU、YOLO等）→ 调用 search_knowledge
3. 询问统计信息、任务记录、缺陷类型等 → 调用对应数据查询工具
4. 无需工具时直接回答

回复要求：
- 检测结果：总数→类别数量→推理耗时
- 知识问答：简洁定义+关键细节（≤200字）
- 统计数据：数字+趋势判断
- 风格：简洁专业，中文回复"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=DETECTION_TOOLS,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=DETECTION_TOOLS,
            verbose=True,
            max_iterations=5,
            return_intermediate_steps=True,
        )

        logger.info("DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS))

    async def chat(self, message: str, image_path: str = None, user_id: int = 1, session_id: str = None) -> dict:
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        chat_history = []
        if session_id:
            chat_history = conversation_memory.load_context_with_summary(user_id, session_id, MAX_CONTEXT_TOKENS)
            logger.debug("加载对话历史(含摘要): user=%d, session=%s, 消息数=%d, tokens=%d", 
                        user_id, session_id, len(chat_history), estimate_message_tokens(chat_history))

        if self.use_simulated_mode:
            result = self._simulate_chat(message, image_path)
            if session_id:
                conversation_memory.save_message(user_id, session_id, "user", message)
                conversation_memory.save_message(user_id, session_id, "ai", result["output"])
            return result

        try:
            result = await self.executor.ainvoke({
                "input": message,
                "chat_history": chat_history,
            })

            if session_id:
                conversation_memory.save_message(user_id, session_id, "user", message)
                conversation_memory.save_message(user_id, session_id, "ai", result["output"])

            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", str(e), exc_info=True)
            return {
                "output": f"抱歉，处理过程中出现错误：{str(e)}",
                "intermediate_steps": [],
            }

    async def chat_stream(self, message: str, image_path: str = None, user_id: int = 1, session_id: str = None) -> AsyncGenerator:
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        chat_history = []
        if session_id:
            chat_history = conversation_memory.load_context_with_summary(user_id, session_id, MAX_CONTEXT_TOKENS)

        if self.use_simulated_mode:
            async for event in self._simulate_chat_stream(message, image_path):
                yield event
            if session_id:
                conversation_memory.save_message(user_id, session_id, "user", message)
            return

        full_output = ""
        try:
            async for event in self.executor.astream_events(
                {"input": message, "chat_history": chat_history},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_start":
                    yield {"type": "thinking", "content": "思考中…"}

                elif event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        full_output += chunk.content
                        yield {
                            "type": "text_chunk",
                            "content": chunk.content,
                        }

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("工具调用: %s, 输入: %s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info(
                        "工具完成: %s, output类型=%s, output长度=%d",
                        tool_name,
                        type(tool_output).__name__,
                        len(str(tool_output)) if tool_output else 0,
                    )
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_output) if tool_output else "",
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", str(e), exc_info=True)
            yield {
                "type": "error",
                "content": f"处理出错：{str(e)}",
            }

        finally:
            if session_id and full_output:
                conversation_memory.save_message(user_id, session_id, "user", message)
                conversation_memory.save_message(user_id, session_id, "ai", full_output)

    def _simulate_chat(self, message: str, image_path: str = None) -> dict:
        import re
        zip_pattern = r'\.(zip|rar|7z)$'
        if image_path:
            if re.search(zip_pattern, image_path, re.IGNORECASE):
                result = detect_zip_images_file.invoke({"zip_path": image_path})
                tool_name = "detect_zip_images_file"
            else:
                result = detect_single_image.invoke({"image_path": image_path})
                tool_name = "detect_single_image"
            result_data = json.loads(result)
            if "error" in result_data:
                output = f"检测失败：{result_data['error']}"
            else:
                total = result_data.get("total_objects", 0)
                counts = result_data.get("class_counts", {})
                count_str = ", ".join([f"{k}: {v}" for k, v in counts.items()]) if counts else "无"
                output = f"检测完成！共检测到 {total} 个目标。类别统计：{count_str}。"
            return {
                "output": output,
                "intermediate_steps": [{"tool": tool_name, "result": result}],
            }
        return {
            "output": "请提供图片路径进行检测。支持单图检测、批量检测和 ZIP 文件检测。",
            "intermediate_steps": [],
        }

    async def _simulate_chat_stream(self, message: str, image_path: str = None):
        import re
        zip_pattern = r'\.(zip|rar|7z)$'
        if image_path:
            if re.search(zip_pattern, image_path, re.IGNORECASE):
                tool_name = "detect_zip_images_file"
                yield {"type": "tool_call", "tool": tool_name, "input": {"zip_path": image_path}}
                result = detect_zip_images_file.invoke({"zip_path": image_path})
            else:
                tool_name = "detect_single_image"
                yield {"type": "tool_call", "tool": tool_name, "input": {"image_path": image_path}}
                result = detect_single_image.invoke({"image_path": image_path})
            
            yield {"type": "tool_result", "tool": tool_name, "result": result}
            
            result_data = json.loads(result)
            if "error" in result_data:
                yield {"type": "text_chunk", "content": "检测失败："}
                yield {"type": "text_chunk", "content": result_data["error"]}
            else:
                total = result_data.get("total_objects", 0)
                counts = result_data.get("class_counts", {})
                yield {"type": "text_chunk", "content": f"检测完成！共检测到 {total} 个目标。"}
                if counts:
                    count_str = ", ".join([f"{k}: {v}" for k, v in counts.items()])
                    yield {"type": "text_chunk", "content": f"类别统计：{count_str}。"}
                else:
                    yield {"type": "text_chunk", "content": "未检测到任何目标。"}
        else:
            yield {"type": "text_chunk", "content": "请提供图片路径进行检测。"}
            yield {"type": "text_chunk", "content": "支持单图检测、批量检测和 ZIP 文件检测。"}


detection_agent = DetectionAgent()