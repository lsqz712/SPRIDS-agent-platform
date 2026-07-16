"""
语义检索模块
负责根据查询向量检索最相关的文档片段
"""

from typing import List, Dict, Any, Tuple

from app.core.logger import get_logger
from app.rag.document_loader import load_all_documents
from app.rag.embedding import embedding_client

logger = get_logger(__name__)

TOP_K = 3


class KnowledgeRetriever:
    def __init__(self):
        self._documents = []
        self._embeddings = []
        self._metadata = []
        self._is_initialized = False

    def initialize(self):
        if self._is_initialized:
            return

        self._documents = []
        self._embeddings = []
        self._metadata = []

        documents = load_all_documents()
        for doc in documents:
            self._documents.append(doc["content"])
            self._metadata.append(doc["metadata"])
            try:
                embedding = embedding_client.embed(doc["content"])
                self._embeddings.append(embedding)
            except Exception as e:
                logger.warning("向量化失败: %s", str(e))
                self._embeddings.append([])

        self._is_initialized = True
        logger.info("知识库初始化完成: %d 个文档片段", len(self._documents))

    def retrieve(self, query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
        if not self._is_initialized:
            self.initialize()

        if not self._documents:
            return []

        query_embedding = embedding_client.embed(query)

        similarities = []
        for i, doc_embedding in enumerate(self._embeddings):
            if doc_embedding:
                similarity = embedding_client.compute_similarity(query_embedding, doc_embedding)
                similarities.append((i, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, similarity in similarities[:top_k]:
            if similarity > 0.05:
                results.append({
                    "content": self._documents[i],
                    "metadata": self._metadata[i],
                    "similarity": round(similarity, 4),
                })

        logger.debug("检索完成: 查询='%s', 返回 %d 条结果", query[:50], len(results))
        return results

    def get_document_count(self) -> int:
        if not self._is_initialized:
            self.initialize()
        return len(self._documents)


knowledge_retriever = KnowledgeRetriever()
