"""
知识库管理 API

接口列表：
  - POST /api/knowledge/build    构建/重建知识库索引
  - GET  /api/knowledge/search   语义检索知识库
  - GET  /api/knowledge/stats    知识库统计信息
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.rag.embedding import embedding_client
from app.rag.document_loader import load_all_documents
from app.vectorstore.pgvector_client import pgvector_client

logger = get_logger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.post("/build")
async def build_knowledge_base(current_user=Depends(get_current_user)):
    """构建/重建知识库索引：加载文档 → 分块 → 向量化 → 存入 Pgvector"""
    try:
        from app.rag.retriever import rag_retriever
        # 用 retriever 的 initialize 方法完整重建索引
        pgvector_client.clear()
        rag_retriever._initialized = False
        rag_retriever.initialize()
        # 统计分块数
        total = len(rag_retriever.documents)
        logger.info("Knowledge base built: %d chunks indexed", total)
        return {
            "success": True,
            "message": f"知识库构建完成",
            "total_documents": len(rag_retriever.documents),
            "total_chunks": total,
        }
    except Exception as e:
        logger.error("Knowledge base build failed: %s", str(e))
        return {"success": False, "message": str(e)}


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., description="查询文本"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数"),
    current_user=Depends(get_current_user),
):
    """语义检索知识库"""
    try:
        embedding = embedding_client.embed_text(q)
        if not embedding:
            return {"results": [], "message": "向量化失败"}

        results = pgvector_client.search(query_embedding=embedding, top_k=top_k, score_threshold=0.3)
        return {
            "query": q,
            "results": [
                {"content": r["content"], "filename": r["filename"],
                 "score": round(r["score"], 4), "chunk_index": r["chunk_index"]}
                for r in results
            ],
            "total": len(results),
        }
    except Exception as e:
        logger.error("Knowledge search failed: %s", str(e))
        return {"results": [], "message": str(e)}


@router.get("/stats")
async def knowledge_stats(current_user=Depends(get_current_user)):
    """知识库统计信息"""
    from app.rag.retriever import rag_retriever
    return {
        "total_chunks": len(rag_retriever.documents) if rag_retriever._initialized else 0,
        "documents_loaded": len(rag_retriever.documents),
    }
