"""
文本向量化模块
负责将文本转换为向量表示
"""

import numpy as np
from typing import List, Optional

from app.core.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


class EmbeddingClient:
    def __init__(self):
        self._client = None
        self._model = None
        self._init_client()

    def _init_client(self):
        api_key = settings.effective_llm_api_key
        base_url = settings.effective_llm_base_url
        
        if api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )
                
                if settings.LLM_API_KEY:
                    self._model = "text-embedding-3-small"
                    provider = "LLM"
                elif settings.DEEPSEEK_API_KEY:
                    self._model = "BAAI/bge-large-zh-v1.5"
                    provider = "DEEPSEEK"
                elif settings.QWEN_API_KEY:
                    self._model = "text-embedding-v3"
                    provider = "QWEN"
                else:
                    self._model = "text-embedding-3-small"
                    provider = "OPENAI"
                
                logger.info("Embedding client initialized with API key from %s, model: %s", provider, self._model)
            except ImportError:
                logger.warning("OpenAI SDK not installed, will use mock embedding")
        else:
            logger.warning("LLM API key not configured, will use mock embedding")

    def embed(self, text: str) -> List[float]:
        if self._client and self._model:
            try:
                response = self._client.embeddings.create(
                    input=text,
                    model=self._model,
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning("Embedding API call failed: %s, using mock", str(e))

        return self._mock_embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]

    def _mock_embed(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        vector = np.zeros(1536, dtype=np.float32)
        for token in tokens:
            idx = hash(token) % 1536
            vector[idx] += 1.0
        if np.sum(vector) > 0:
            vector = vector / np.sum(vector)
        return vector.tolist()

    def _tokenize(self, text: str) -> List[str]:
        import re
        text = text.lower()
        tokens = re.findall(r'[a-zA-Z0-9\u4e00-\u9fa5]+', text)
        stop_words = {'the', 'and', 'or', 'is', 'are', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'a', 'an', 'this', 'that', 'these', 'those', 'it', 'its', 'from', 'as', 'by', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'need', 'must', 'shall', 'what', 'which', 'who', 'whom', 'whose', 'when', 'where', 'why', 'how', 'all', 'any', 'each', 'every', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'but', 'if', 'because', 'until', 'while', 'about', 'against', 'between', 'during', 'before', 'after', 'above', 'below', 'again', 'further', 'then', 'once', 'here', 'there', 'whence', 'wherever', 'whenever', 'however', 'whatever', 'whoever', 'whichever', 'he', 'she', 'they', 'we', 'you', 'i', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'our', 'their', 'am', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'need', 'must', 'shall', 'ought', 'used', 'dare', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'need', 'must', 'shall'}
        return [t for t in tokens if t not in stop_words and len(t) >= 2]

    def compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


embedding_client = EmbeddingClient()
