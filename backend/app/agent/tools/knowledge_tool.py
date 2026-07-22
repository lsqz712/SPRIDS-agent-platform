"""
知识库工具 — Agent 可调用的 RAG 检索 @tool 函数

工具列表：
  - search_knowledge: 语义检索知识库（BM25 + 向量混合检索 + 重排序）
"""

import json

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.rag.retriever import rag_retriever

logger = get_logger(__name__)


@tool
def search_knowledge(query: str, top_k: int = 3) -> str:
    """搜索知识库，回答目标检测、YOLO、PCB检测等领域知识问题。

    当用户询问专业知识问题时使用此工具，例如：
    - "什么是 IoU？"
    - "YOLOv11 有哪些改进？"
    - "mAP 是怎么计算的？"
    - "什么是 NMS 非极大值抑制？"

    Args:
        query: 用户的问题或搜索关键词
        top_k: 返回最相关的前 K 条知识片段，默认 3 条

    Returns:
        JSON 字符串，包含检索到的知识内容和来源信息
    """
    try:
        results = rag_retriever.search(query, top_k=top_k)

        if not results or not results.get("success"):
            return json.dumps({
                "answer": "知识库中暂无相关内容",
                "sources": [],
            }, ensure_ascii=False)

        return json.dumps({
            "query": query,
            "answer": results.get("answer", ""),
            "sources": results.get("sources", []),
            "total": len(results.get("sources", [])),
        }, ensure_ascii=False)
    except Exception as e:
        logger.error("知识检索失败: %s", str(e))
        return json.dumps({"error": f"检索失败: {str(e)}"}, ensure_ascii=False)


# 知识工具列表
KNOWLEDGE_TOOLS = [search_knowledge]
