"""
知识智能体 — RAG 检索、领域知识问答

职责：
  - 搜索知识库，回答领域知识问题
  - 支持 BM25 + 向量混合检索
  - 重排序优化检索结果
"""

import json
from typing import AsyncGenerator, List, Dict

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger
from app.rag.retriever import rag_retriever

logger = get_logger(__name__)

MAX_TOOL_OUTPUT_CHARS = 2000
MAX_LIST_ITEMS = 5


def compress_tool_output(data: dict) -> str:
    PRIORITY_FIELDS = {"id", "name", "count", "total", "status", "confidence", "class_name", "result", "content", "source"}

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
def search_knowledge(query: str, top_k: int = 3) -> str:
    """
    搜索知识库，回答领域知识问题。

    Args:
        query: 用户查询问题
        top_k: 返回结果数量，默认 3

    返回检索到的知识内容，用于回答用户关于目标检测、YOLO、PCB检测等领域知识问题。
    """
    try:
        results = rag_retriever.search(query, top_k=top_k)
        
        knowledge_items = []
        for doc in results:
            knowledge_items.append({
                "content": doc.content[:500] if doc.content else "",
                "source": doc.filename if hasattr(doc, 'filename') else "",
                "score": doc.score if hasattr(doc, 'score') else 0,
            })

        return compress_tool_output({
            "query": query,
            "total": len(knowledge_items),
            "items": knowledge_items,
        })
    except Exception as e:
        logger.error("知识检索失败: %s", str(e))
        return json.dumps({
            "query": query,
            "error": str(e),
            "items": [],
        }, ensure_ascii=False)


KNOWLEDGE_TOOLS = [
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


class KnowledgeAgent:
    """知识智能体 — 封装 RAG 检索和领域知识问答"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("KnowledgeAgent 初始化完成（模拟模式），绑定 %d 个工具", len(KNOWLEDGE_TOOLS))
            return

        system_prompt = """你是一个专业的PCB检测领域知识助手，帮助用户解答关于目标检测、YOLO算法、PCB检测等专业知识问题。

工具调用规则：
1. 询问专业知识（IoU、YOLO、PCB检测原理等）→ 调用 search_knowledge
2. 询问概念定义、算法原理、技术参数 → 调用 search_knowledge
3. 无需工具时直接回答

回复要求：
- 知识问答：简洁定义+关键细节（≤200字）
- 基于检索结果回答，不要编造信息
- 如果知识库中没有相关内容，明确告知用户
- 风格：专业易懂，中文回复"""

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
            tools=KNOWLEDGE_TOOLS,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=KNOWLEDGE_TOOLS,
            verbose=True,
            max_iterations=3,
            return_intermediate_steps=True,
        )

        logger.info("KnowledgeAgent 初始化完成，绑定 %d 个工具", len(KNOWLEDGE_TOOLS))

    async def chat(self, message: str, session_id: str = None) -> dict:
        if self.use_simulated_mode:
            return {
                "output": "知识助手已就绪！我可以帮您解答关于目标检测、YOLO算法、PCB检测等领域知识问题。",
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
            logger.error("KnowledgeAgent 执行异常: %s", str(e), exc_info=True)
            return {"output": f"知识检索失败：{str(e)}", "intermediate_steps": []}


knowledge_agent = KnowledgeAgent()