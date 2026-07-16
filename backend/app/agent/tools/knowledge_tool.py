"""
知识库工具
提供RAG语义检索和问答功能
"""

from typing import Dict, Any, List
from app.agent.tools import BaseTool, ToolRegistry
from app.rag.retriever import knowledge_retriever
from app.agent.prompts import RAG_QA_PROMPT
from app.agent.llm_client import llm_client


class KnowledgeSearchTool(BaseTool):
    def get_name(self) -> str:
        return "search_knowledge"

    def get_description(self) -> str:
        return "搜索知识库，回答目标检测、YOLO、PCB检测等领域知识问题"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户的问题或搜索关键词，如'什么是IoU'、'YOLOv11有哪些改进'"
                }
            },
            "required": ["query"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query")
        if not query:
            return {"error": "请提供查询关键词"}

        try:
            results = knowledge_retriever.retrieve(query)
            if not results:
                return {
                    "success": True,
                    "answer": "知识库中暂无相关内容",
                    "sources": [],
                }

            context = "\n\n".join([f"【来源{idx+1}】{r['content']}" for idx, r in enumerate(results)])
            prompt = RAG_QA_PROMPT.format(context=context, question=query)

            answer = llm_client.generate([{"role": "user", "content": prompt}])

            sources = []
            for r in results:
                sources.append({
                    "filename": r["metadata"].get("filename", "unknown"),
                    "chunk_index": r["metadata"].get("chunk_index", 0),
                    "similarity": r["similarity"],
                })

            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "context_length": len(context),
            }

        except Exception as e:
            return {"error": f"知识库检索失败: {str(e)}"}


def register_knowledge_tools(registry: ToolRegistry, db=None):
    registry.register(KnowledgeSearchTool())
