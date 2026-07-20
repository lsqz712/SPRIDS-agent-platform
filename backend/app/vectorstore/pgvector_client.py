"""
Pgvector 向量存储客户端

职责：
  - 连接 PostgreSQL + pgvector 扩展
  - 文档向量存储与相似度检索
  - 支持余弦相似度 / 欧氏距离

架构：
  document → embedding_client → pgvector.insert() → 向量表
  query → embedding_client → pgvector.search() → Top-K 文档
"""

import json
from typing import List, Optional

import psycopg2
import psycopg2.extras
import numpy as np

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 默认向量维度（通义千问 text-embedding-v3 = 1024，OpenAI ada-002 = 1536）
DEFAULT_VECTOR_DIM = 1024


class PgvectorClient:
    """Pgvector 向量存储客户端"""

    def __init__(self, table_name: str = "knowledge_embeddings", vector_dim: int = DEFAULT_VECTOR_DIM):
        self.table_name = table_name
        self.vector_dim = vector_dim
        self._conn = None

    def _get_conn(self):
        if self._conn and not self._conn.closed:
            return self._conn
        self._conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        self._conn.autocommit = True
        return self._conn

    def init_schema(self) -> bool:
        """初始化 pgvector 扩展和向量表"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    filename VARCHAR(255),
                    chunk_index INTEGER DEFAULT 0,
                    embedding vector({self.vector_dim}),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # 创建索引（IVFFlat 适合大批量数据）
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                ON {self.table_name} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            cur.close()
            logger.info("Pgvector schema initialized: %s (dim=%d)", self.table_name, self.vector_dim)
            return True
        except Exception as e:
            logger.error("Pgvector init failed: %s", e)
            return False

    def insert(self, content: str, embedding: List[float], filename: str = "",
               chunk_index: int = 0, metadata: dict = None) -> Optional[int]:
        """插入一条向量记录"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
            cur.execute(
                f"INSERT INTO {self.table_name} (content, filename, chunk_index, embedding, metadata) "
                "VALUES (%s, %s, %s, %s::vector, %s) RETURNING id",
                (content, filename, chunk_index, vector_str, json.dumps(metadata or {}, ensure_ascii=False))
            )
            row_id = cur.fetchone()[0]
            cur.close()
            return row_id
        except Exception as e:
            logger.error("Pgvector insert failed: %s", e)
            return None

    def insert_batch(self, items: List[dict]) -> int:
        """批量插入向量（每项包含 content, embedding, filename, chunk_index, metadata）"""
        count = 0
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            for item in items:
                vector_str = "[" + ",".join(str(v) for v in item["embedding"]) + "]"
                cur.execute(
                    f"INSERT INTO {self.table_name} (content, filename, chunk_index, embedding, metadata) "
                    "VALUES (%s, %s, %s, %s::vector, %s)",
                    (item["content"], item.get("filename", ""), item.get("chunk_index", 0),
                     vector_str, json.dumps(item.get("metadata", {}), ensure_ascii=False))
                )
                count += 1
            conn.commit()
            cur.close()
            logger.info("Pgvector batch insert: %d records", count)
        except Exception as e:
            logger.error("Pgvector batch insert failed: %s", e)
            try: conn.rollback()
            except: pass
        return count

    def search(self, query_embedding: List[float], top_k: int = 5,
               score_threshold: float = 0.0) -> List[dict]:
        """余弦相似度检索，返回 Top-K 最相似文档"""
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
            cur.execute(
                f"SELECT id, content, filename, chunk_index, metadata, "
                f"1 - (embedding <=> %s::vector) AS similarity "
                f"FROM {self.table_name} "
                f"WHERE 1 - (embedding <=> %s::vector) >= %s "
                f"ORDER BY embedding <=> %s::vector LIMIT %s",
                (vector_str, vector_str, score_threshold, vector_str, top_k)
            )
            rows = cur.fetchall()
            cur.close()
            return [
                {"id": r["id"], "content": r["content"], "filename": r["filename"],
                 "chunk_index": r["chunk_index"], "metadata": r["metadata"],
                 "score": float(r["similarity"])}
                for r in rows
            ]
        except Exception as e:
            logger.error("Pgvector search failed: %s", e)
            return []

    def delete_by_filename(self, filename: str) -> int:
        """按文件名删除向量"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {self.table_name} WHERE filename = %s", (filename,))
            deleted = cur.rowcount
            conn.commit()
            cur.close()
            logger.info("Pgvector deleted %d records for %s", deleted, filename)
            return deleted
        except Exception as e:
            logger.error("Pgvector delete failed: %s", e)
            return 0

    def clear(self) -> int:
        """清空向量表"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {self.table_name}")
            deleted = cur.rowcount
            conn.commit()
            cur.close()
            return deleted
        except Exception as e:
            logger.error("Pgvector clear failed: %s", e)
            return 0

    def count(self) -> int:
        """向量总数"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception:
            return 0

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


# 全局单例
pgvector_client = PgvectorClient()
