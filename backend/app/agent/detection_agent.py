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
from app.entity.db_models import TrainingTask, DetectionScene, PCBBatch
from app.agent.memory import conversation_memory

logger = get_logger(__name__)


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
    return json.dumps(result, ensure_ascii=False)


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
    return json.dumps(result, ensure_ascii=False)


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
        return json.dumps(data, ensure_ascii=False, default=str)
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
        return json.dumps({"items": result, "total": len(result)}, ensure_ascii=False)
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
        return json.dumps(task_data, ensure_ascii=False)
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
        return json.dumps({"items": result, "total": len(result)}, ensure_ascii=False)
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
        return json.dumps({"items": result, "total": len(result)}, ensure_ascii=False)
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
        return json.dumps({"items": result, "total": len(result)}, ensure_ascii=False)
    finally:
        db.close()


@tool
def search_knowledge(query: str) -> str:
    """
    搜索知识库，回答目标检测、YOLO、PCB检测等领域知识问题。

    当用户询问专业知识（如"什么是 IoU"、"YOLO 如何工作"、"PCB 缺陷类型"）时使用此工具。

    Args:
        query: 用户的问题或搜索关键词

    Returns:
        JSON 字符串，包含回答内容和来源信息
    """
    try:
        from app.rag.retriever import knowledge_retriever
        from app.rag.embedding import embedding_client
        from app.agent.prompts import RAG_QA_PROMPT
        from app.agent.llm_client import llm_client

        results = knowledge_retriever.retrieve(query)
        if not results:
            return json.dumps({
                "success": True,
                "answer": "知识库中暂无相关内容",
                "sources": [],
            }, ensure_ascii=False)

        context = "\n\n".join([f"【来源{idx+1}】{r['content']}" for idx, r in enumerate(results)])
        prompt = RAG_QA_PROMPT.format(context=context, question=query)
        answer = llm_client.generate([{"role": "user", "content": prompt}])

        sources = []
        for r in results:
            sources.append({
                "filename": r["metadata"].get("filename", "unknown"),
                "similarity": r["similarity"],
            })

        return json.dumps({
            "success": True,
            "answer": answer,
            "sources": sources,
        }, ensure_ascii=False)
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
    get_scenes,
    get_batches,
    search_knowledge,
]


def create_llm():
    qwen_api_key = getattr(settings, "QWEN_API_KEY", "")
    if qwen_api_key and qwen_api_key != "sk-your-qwen-api-key":
        api_key = qwen_api_key
        base_url = getattr(
            settings, "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        model_name = getattr(settings, "QWEN_MODEL", "qwen-plus")
    else:
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("未配置 LLM API Key，将使用模拟模式")
            return None
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

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

        system_prompt = """你是一个专业的PCB检测智能助手。你可以帮用户检测图片中的PCB缺陷，也可以查询系统中的各类数据，还能回答目标检测领域的专业知识问题。

可用工具：
1. 检测工具：
   - detect_single_image：检测单张图片中的PCB缺陷
   - detect_batch_images：批量检测多张图片
   - detect_zip_images_file：检测ZIP文件中的所有图片

2. 数据查询工具：
   - get_statistics_overview：获取数据看板总览统计（任务数、图像数、目标数、缺陷分布等）
   - get_defect_types：获取缺陷类型列表（支持按关键词、严重等级筛选）
   - get_task_list：获取检测任务列表（支持按状态、类型筛选）
   - get_task_detail：获取单个任务的详细信息
   - get_history_records：获取历史检测记录
   - get_training_tasks：获取模型训练任务列表
   - get_scenes：获取检测场景列表
   - get_batches：获取PCB批次列表

3. 知识问答工具：
   - search_knowledge：搜索知识库，回答目标检测、YOLO、PCB检测等领域知识问题

工具调用优先级：
1. 如果消息中包含 [附件图片路径: xxx]，直接使用路径调用对应的检测工具
2. 如果用户询问专业知识（如"什么是 IoU"、"YOLO 如何工作"），调用 search_knowledge
3. 如果用户询问统计信息、任务记录、缺陷类型、训练状态等，调用相应的数据查询工具
4. 如果不需要工具，直接用自身知识回答

回复格式要求：
- 检测结果：先报告总数 → 列出各类别数量 → 提及推理耗时
- 知识问答：先给简洁定义 → 再补充关键细节 → 控制在 200 字以内
- 统计数据：用数字说话 → 适当给出趋势判断
- 语言风格：简洁专业，中文回复，不要过度解释"""

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
            chat_history = conversation_memory.load_history(user_id, session_id)
            logger.debug("加载对话历史: user=%d, session=%s, 消息数=%d", user_id, session_id, len(chat_history))

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
            chat_history = conversation_memory.load_history(user_id, session_id)

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

                if event_kind == "on_chat_model_stream":
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