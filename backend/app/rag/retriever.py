"""
RAG 检索器 — 混合检索（BM25 + 向量相似度）+ 重排序

职责：
  - 文档向量存储和相似度检索（向量检索）
  - BM25 关键词检索
  - 混合检索（加权融合 BM25 和向量相似度）
  - Reranker 重排序（可选）
  - 与文档加载器集成，支持增量更新

架构：
  query → BM25 检索 ─┐
        → 向量检索 ──┴→ 混合融合 → 重排序 → Top-K 结果

使用方式：
  from app.rag.retriever import rag_retriever
  results = rag_retriever.search("什么是YOLO?", top_k=5)
"""

import math
import re
from collections import Counter
from typing import List, Dict, Tuple
from dataclasses import dataclass

from app.core.logger import get_logger
from app.rag.embedding import embedding_client
from app.rag.document_loader import load_all_documents

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    content: str
    filename: str
    score: float
    bm25_score: float = 0.0
    vector_score: float = 0.0


class BM25Retriever:
    """
    BM25 关键词检索器
    
    BM25 (Best Match 25) 是一种基于词频-逆文档频率（TF-IDF）的概率检索模型，
    用于衡量文档与查询词的相关性。
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[str] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avgdl: float = 0.0
        self.df: Counter = Counter()
        self.idf: Dict[str, float] = {}
        self.filenames: List[str] = []

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """
        简单分词：中文按单字 + 2-gram，英文按单词
        适用于中英文混合文本
        """
        tokens = []
        
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        for i in range(len(chinese_chars)):
            tokens.append(chinese_chars[i])
            if i < len(chinese_chars) - 1:
                tokens.append(chinese_chars[i] + chinese_chars[i+1])
        
        english_words = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}', text.lower())
        tokens.extend(english_words)
        
        return tokens

    def add_documents(self, documents: List[Dict]):
        """添加文档到索引"""
        for doc in documents:
            content = doc.get("content", "")
            filename = doc.get("filename", "unknown")
            
            tokens = self.tokenize(content)
            self.documents.append(content)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            self.filenames.append(filename)
            
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.df[token] += 1
        
        self._calculate_idf()
        if self.doc_lengths:
            self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths)
        
        logger.info("BM25 索引构建完成: %d 篇文档, %d 个词", len(self.documents), len(self.df))

    def _calculate_idf(self):
        """计算逆文档频率 (IDF)"""
        N = len(self.documents)
        if N == 0:
            return
        for term, freq in self.df.items():
            self.idf[term] = math.log((N - freq + 0.5) / (freq + 0.5) + 1)

    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """计算查询与文档的 BM25 分数"""
        if doc_idx >= len(self.doc_tokens):
            return 0.0
        
        doc_tokens = self.doc_tokens[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        
        if not doc_tokens or self.avgdl == 0:
            return 0.0
        
        tf = Counter(doc_tokens)
        score = 0.0
        
        for term in query_tokens:
            if term not in self.idf:
                continue
            
            term_freq = tf.get(term, 0)
            if term_freq == 0:
                continue
            
            idf = self.idf[term]
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * numerator / denominator
        
        return score

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        BM25 搜索，返回 (文档索引, 分数) 的列表
        """
        query_tokens = self.tokenize(query)
        if not query_tokens or not self.documents:
            return []
        
        scores = []
        for i in range(len(self.documents)):
            score = self._score_document(query_tokens, i)
            if score > 0:
                scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class Reranker:
    """
    重排序器
    
    对初筛结果进行精细化排序，提升检索准确性。
    当前实现：基于关键词覆盖率和语义相似度的简单重排序。
    可扩展：接入 bge-reranker 等专业重排序模型。
    """
    
    def __init__(self):
        pass

    @staticmethod
    def _keyword_coverage(query: str, document: str) -> float:
        """计算查询关键词在文档中的覆盖率"""
        query_terms = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]{3,}', query.lower()))
        if not query_terms:
            return 0.0
        
        doc_lower = document.lower()
        matched = sum(1 for term in query_terms if term in doc_lower)
        return matched / len(query_terms)

    @staticmethod
    def _position_score(query: str, document: str) -> float:
        """
        位置分数：查询词出现在文档开头的分数更高
        """
        query_terms = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]{3,}', query.lower())
        if not query_terms or not document:
            return 0.0
        
        doc_lower = document.lower()
        positions = []
        for term in query_terms:
            pos = doc_lower.find(term)
            if pos >= 0:
                positions.append(pos)
        
        if not positions:
            return 0.0
        
        avg_position = sum(positions) / len(positions)
        doc_len = len(document)
        if doc_len == 0:
            return 0.0
        
        return max(0.0, 1.0 - avg_position / doc_len)

    def rerank(self, query: str, results: List[SearchResult], top_k: int = 5) -> List[SearchResult]:
        """
        对搜索结果进行重排序
        
        重排序分数 = 原始分数 * 0.6 + 关键词覆盖率 * 0.25 + 位置分数 * 0.15
        """
        if not results:
            return []
        
        max_score = max(r.score for r in results) if results else 1.0
        if max_score == 0:
            max_score = 1.0
        
        reranked = []
        for result in results:
            coverage = self._keyword_coverage(query, result.content)
            position = self._position_score(query, result.content)
            normalized_score = result.score / max_score
            
            rerank_score = (
                normalized_score * 0.6 +
                coverage * 0.25 +
                position * 0.15
            )
            
            reranked.append(SearchResult(
                content=result.content,
                filename=result.filename,
                score=rerank_score,
                bm25_score=result.bm25_score,
                vector_score=result.vector_score,
            ))
        
        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:top_k]


class RAGRetriever:
    """
    RAG 检索器 - 混合检索 + 重排序
    
    支持：
    1. 纯向量检索（默认）
    2. 纯 BM25 检索
    3. 混合检索（BM25 + 向量，加权融合）
    4. 结果重排序
    """
    
    def __init__(self):
        self.documents: List[Dict] = []
        self.embeddings: List[List[float]] = []
        self.bm25 = BM25Retriever()
        self.reranker = Reranker()
        self.vector_weight = 0.6
        self.bm25_weight = 0.4
        self._initialized = False

    def initialize(self):
        """初始化检索器，加载所有文档"""
        if self._initialized:
            return
        
        logger.info("初始化 RAG 检索器...")
        
        all_chunks = load_all_documents()
        if not all_chunks:
            logger.warning("没有找到文档片段")
            self._initialized = True
            return
        
        self.documents = all_chunks
        
        self.embeddings = embedding_client.embed_batch([chunk["content"] for chunk in all_chunks])
        
        self.bm25.add_documents(all_chunks)
        
        self._initialized = True
        logger.info("RAG 检索器初始化完成: %d 个文档片段", len(self.documents))

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

    def vector_search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """纯向量相似度检索"""
        self.initialize()
        
        if not self.documents or not self.embeddings:
            return []
        
        query_embedding = embedding_client.embed(query)
        
        scores = []
        for i, doc_embedding in enumerate(self.embeddings):
            sim = self._cosine_similarity(query_embedding, doc_embedding)
            if sim > 0:
                scores.append((i, sim))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in scores[:top_k]:
            doc = self.documents[idx]
            results.append(SearchResult(
                content=doc["content"],
                filename=doc.get("filename", "unknown"),
                score=score,
                vector_score=score,
                bm25_score=0.0,
            ))
        
        return results

    def bm25_search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """纯 BM25 关键词检索"""
        self.initialize()
        
        bm25_results = self.bm25.search(query, top_k)
        
        results = []
        for idx, score in bm25_results:
            if idx < len(self.documents):
                doc = self.documents[idx]
                results.append(SearchResult(
                    content=doc["content"],
                    filename=doc.get("filename", "unknown"),
                    score=score,
                    bm25_score=score,
                    vector_score=0.0,
                ))
        
        return results

    def hybrid_search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        混合检索：融合 BM25 和向量相似度
        
        使用 Reciprocal Rank Fusion (RRF) 算法融合两种检索结果
        """
        self.initialize()
        
        if not self.documents:
            return []
        
        vector_results = self.vector_search(query, top_k * 2)
        bm25_results = self.bm25_search(query, top_k * 2)
        
        rrf_scores: Dict[int, float] = {}
        vector_idx_map: Dict[int, float] = {}
        bm25_idx_map: Dict[int, float] = {}
        
        for rank, result in enumerate(vector_results):
            for i, doc in enumerate(self.documents):
                if doc["content"] == result.content:
                    vector_idx_map[i] = result.vector_score
                    rrf_scores[i] = rrf_scores.get(i, 0) + self.vector_weight / (rank + 60)
                    break
        
        for rank, result in enumerate(bm25_results):
            for i, doc in enumerate(self.documents):
                if doc["content"] == result.content:
                    bm25_idx_map[i] = result.bm25_score
                    rrf_scores[i] = rrf_scores.get(i, 0) + self.bm25_weight / (rank + 60)
                    break
        
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in sorted_docs[:top_k]:
            doc = self.documents[idx]
            results.append(SearchResult(
                content=doc["content"],
                filename=doc.get("filename", "unknown"),
                score=score,
                bm25_score=bm25_idx_map.get(idx, 0.0),
                vector_score=vector_idx_map.get(idx, 0.0),
            ))
        
        return results

    def search(self, query: str, top_k: int = 5, use_hybrid: bool = True, use_rerank: bool = True) -> Dict:
        """
        统一搜索接口
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_hybrid: 是否使用混合检索
            use_rerank: 是否使用重排序
        
        Returns:
            包含答案和来源的字典
        """
        self.initialize()
        
        if not self.documents:
            return {
                "success": True,
                "answer": "知识库中暂无相关内容",
                "sources": [],
            }
        
        if use_hybrid:
            candidates = self.hybrid_search(query, top_k * 2)
        else:
            candidates = self.vector_search(query, top_k * 2)
        
        if use_rerank and candidates:
            results = self.reranker.rerank(query, candidates, top_k)
        else:
            results = candidates[:top_k]
        
        if not results:
            return {
                "success": True,
                "answer": "知识库中暂无相关内容",
                "sources": [],
            }
        
        context_parts = []
        sources = []
        for i, result in enumerate(results):
            context_parts.append(f"[{i+1}] {result.content}")
            sources.append({
                "filename": result.filename,
                "similarity": round(result.score, 4),
                "bm25_score": round(result.bm25_score, 4),
                "vector_score": round(result.vector_score, 4),
            })
        
        context = "\n\n".join(context_parts)
        
        answer = self._generate_answer(query, context)
        
        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "context": context,
        }

    def _generate_answer(self, query: str, context: str) -> str:
        """基于检索结果生成答案"""
        try:
            from app.agent.llm_client import llm_client
            
            system_prompt = """你是一个专业的知识问答助手。请根据提供的参考资料回答用户的问题。

要求：
1. 只能使用参考资料中的信息，不要编造
2. 如果参考资料中没有答案，直接说"知识库中暂无相关内容"
3. 回答要简洁准确，控制在 200 字以内
4. 用中文回答"""

            user_prompt = f"""参考资料：
{context}

问题：{query}

请回答："""
            
            answer = llm_client.generate([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ], max_tokens=500)
            
            return answer.strip()
        except Exception as e:
            logger.warning("生成答案失败: %s", str(e))
            return f"知识库中找到相关内容，建议参考以下信息：\n{context[:500]}"

    def reload_documents(self):
        """重新加载所有文档（用于知识库更新后）"""
        self._initialized = False
        self.documents = []
        self.embeddings = []
        self.bm25 = BM25Retriever()
        self.initialize()
        logger.info("知识库已重新加载")


rag_retriever = RAGRetriever()
