"""
模型智能体 — 模型管理、训练任务、场景配置

职责：
  - 模型版本查询和管理
  - 检测场景配置
  - PCB批次管理
  - 训练任务查询
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
from app.entity.db_models import TrainingTask, DetectionScene, PCBBatch, ModelVersion

logger = get_logger(__name__)

MAX_TOOL_OUTPUT_CHARS = 2000
MAX_LIST_ITEMS = 5


def compress_tool_output(data: dict) -> str:
    PRIORITY_FIELDS = {"id", "name", "count", "total", "status", "confidence", "class_name", "result", "version", "progress"}

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


MODEL_TOOLS = [
    get_model_info,
    get_scenes,
    get_batches,
    get_training_tasks,
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


class ModelAgent:
    """模型智能体 — 封装模型管理、训练任务和场景配置"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("ModelAgent 初始化完成（模拟模式），绑定 %d 个工具", len(MODEL_TOOLS))
            return

        system_prompt = """你是一个专业的模型管理助手，帮助用户查询模型版本信息、检测场景配置、PCB批次和训练任务。

工具调用规则：
1. 查询模型信息 → 调用 get_model_info
2. 查询检测场景 → 调用 get_scenes
3. 查询PCB批次 → 调用 get_batches
4. 查询训练任务 → 调用 get_training_tasks
5. 无需工具时直接回答

回复要求：
- 模型信息：版本号+性能指标
- 场景列表：名称+状态
- 训练任务：状态+进度+关键参数
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
            tools=MODEL_TOOLS,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=MODEL_TOOLS,
            verbose=True,
            max_iterations=3,
            return_intermediate_steps=True,
        )

        logger.info("ModelAgent 初始化完成，绑定 %d 个工具", len(MODEL_TOOLS))

    async def chat(self, message: str, session_id: str = None) -> dict:
        if self.use_simulated_mode:
            return {
                "output": "模型管理助手已就绪！我可以帮您查询模型版本、检测场景、PCB批次和训练任务。",
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
            logger.error("ModelAgent 执行异常: %s", str(e), exc_info=True)
            return {"output": f"模型查询失败：{str(e)}", "intermediate_steps": []}


model_agent = ModelAgent()