"""
分析智能体 — 统计分析、缺陷分析、任务查询

职责：
  - 数据看板总览统计
  - 缺陷类型管理和分析
  - 检测任务列表和详情查询
  - 缺陷分析报告生成
  - 批次良品率计算
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
from app.services.statistics_service import statistics_service
from app.services.defect_type_service import defect_type_service
from app.services.detection_service import detection_service
from app.entity.db_models import DetectionTask, DetectionResult

logger = get_logger(__name__)

MAX_TOOL_OUTPUT_CHARS = 2000
MAX_LIST_ITEMS = 5


def compress_tool_output(data: dict) -> str:
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
        task_type: 按类型筛选：single/batch/video/camera（可选）

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
            db.query(DetectionTask)
            .order_by(DetectionTask.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "created_at": str(task.created_at),
                "completed_at": str(task.completed_at) if task.completed_at else None,
            })
        return compress_tool_output({"items": result, "total": len(tasks)})
    finally:
        db.close()


@tool
def analyze_defects(task_id: int = None, batch_id: int = None, time_range: str = None) -> str:
    """
    分析缺陷数据，生成统计报告和维修建议。

    Args:
        task_id: 检测任务 ID（可选）
        batch_id: PCB 批次 ID（可选）
        time_range: 时间范围，如 'today'/'week'/'month'（可选）

    返回缺陷分析报告，包含缺陷分布、趋势分析和维修建议。
    """
    db = SessionLocal()
    try:
        result = {
            "analysis_type": "defect_analysis",
            "task_id": task_id,
            "batch_id": batch_id,
            "time_range": time_range,
            "defect_distribution": {},
            "severity_distribution": {},
            "suggestions": [],
        }

        if task_id:
            results = db.query(DetectionResult).filter(DetectionResult.task_id == task_id).all()
            for r in results:
                class_name = r.class_name_cn or r.class_name
                result["defect_distribution"][class_name] = (
                    result["defect_distribution"].get(class_name, 0) + 1
                )

        if batch_id:
            tasks = db.query(DetectionTask).filter(DetectionTask.batch_id == batch_id).all()
            for task in tasks:
                results = db.query(DetectionResult).filter(DetectionResult.task_id == task.id).all()
                for r in results:
                    class_name = r.class_name_cn or r.class_name
                    result["defect_distribution"][class_name] = (
                        result["defect_distribution"].get(class_name, 0) + 1
                    )

        result["suggestions"] = [
            "建议重点关注高频缺陷类型的生产环节",
            "建议定期校准检测设备",
            "建议对严重缺陷及时进行复判确认",
        ]

        return compress_tool_output(result)
    finally:
        db.close()


@tool
def calculate_pass_rate(batch_id: int) -> str:
    """
    计算 PCB 批次的良品率。

    Args:
        batch_id: PCB 批次 ID

    返回批次良品率统计，包含总数量、良品数、不良品数和良品率。
    """
    db = SessionLocal()
    try:
        total = 0
        passed = 0
        failed = 0

        tasks = db.query(DetectionTask).filter(DetectionTask.batch_id == batch_id).all()
        for task in tasks:
            total += task.total_images or 0
            failed += task.total_objects or 0

        passed = total - failed if total > 0 else 0
        pass_rate = (passed / total * 100) if total > 0 else 0

        return compress_tool_output({
            "batch_id": batch_id,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
        })
    finally:
        db.close()


ANALYSIS_TOOLS = [
    get_statistics_overview,
    get_defect_types,
    get_task_list,
    get_task_detail,
    get_history_records,
    analyze_defects,
    calculate_pass_rate,
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


class AnalysisAgent:
    """分析智能体 — 封装统计分析、缺陷分析和任务查询"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("AnalysisAgent 初始化完成（模拟模式），绑定 %d 个工具", len(ANALYSIS_TOOLS))
            return

        system_prompt = """你是一个专业的数据分析助手，帮助用户分析PCB检测数据、查询统计信息和生成分析报告。

工具调用规则：
1. 查询数据概览 → 调用 get_statistics_overview
2. 查询缺陷类型 → 调用 get_defect_types
3. 查询任务列表 → 调用 get_task_list
4. 查询任务详情 → 调用 get_task_detail
5. 查询历史记录 → 调用 get_history_records
6. 分析缺陷分布 → 调用 analyze_defects
7. 计算良品率 → 调用 calculate_pass_rate
8. 无需工具时直接回答

回复要求：
- 统计数据：数字+趋势判断
- 分析报告：清晰的分布图表描述
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
            tools=ANALYSIS_TOOLS,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=ANALYSIS_TOOLS,
            verbose=True,
            max_iterations=5,
            return_intermediate_steps=True,
        )

        logger.info("AnalysisAgent 初始化完成，绑定 %d 个工具", len(ANALYSIS_TOOLS))

    async def chat(self, message: str, session_id: str = None) -> dict:
        if self.use_simulated_mode:
            return {
                "output": "数据分析助手已就绪！我可以帮您查询统计信息、分析缺陷分布、计算良品率等。",
                "intermediate_steps": [],
            }

        try:
            result = await self.executor.ainvoke({
                "input": message,
                "chat_history": [],
            })
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("AnalysisAgent 执行异常: %s", str(e), exc_info=True)
            return {"output": f"分析失败：{str(e)}", "intermediate_steps": []}


analysis_agent = AnalysisAgent()