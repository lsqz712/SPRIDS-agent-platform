"""
Pgvector 客户端 — 基于 PostgreSQL pgvector 扩展的向量存储
"""

from typing import Optional

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 1024


class PgvectorClient:
    """Pgvector 向量存储客户端"""

    def __init__(self):
        self._initialized = False

    def _get_connection(self):
        import psycopg2
        import pgvector.psycopg2
        conn = psycopg2.connect(settings.DATABASE_URL)
        pgvector.psycopg2.register_vector(conn)
        return conn

    def init_table(self):
        if self._initialized:
            return

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    embedding vector({EMBEDDING_DIM}),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_vector
                ON knowledge_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            conn.commit()
            cur.close()
            self._initialized = True
            logger.info("Pgvector 表和索引初始化完成")
        except Exception as e:
            conn.rollback()
            logger.error("Pgvector 初始化失败: %s", str(e))
        finally:
            conn.close()

    def insert_embeddings(self, contents, embeddings, metadatas=None):
        if not contents or not embeddings:
            return

        conn = self._get_connection()
        try:
            import json
            cur = conn.cursor()

            for i in range(len(contents)):
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                embedding_str = "[" + ",".join(str(v) for v in embeddings[i]) + "]"

                cur.execute(
                    """
                    INSERT INTO knowledge_embeddings (content, metadata, embedding)
                    VALUES (%s, %s::jsonb, %s::vector)
                    """,
                    (contents[i], json.dumps(metadata, ensure_ascii=False), embedding_str),
                )

            conn.commit()
            cur.close()
            logger.info("插入 %d 条向量数据", len(contents))
        except Exception as e:
            conn.rollback()
            logger.error("插入向量数据失败: %s", str(e))
        finally:
            conn.close()

    def search(self, query_embedding, top_k=3):
        conn = self._get_connection()
        try:
            import numpy as np
            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding, dtype=np.float32)
            cur = conn.cursor()

            cur.execute("SET ivfflat.probes = 10;")
            
            cur.execute(
                """
                SELECT content, metadata, 1 - (embedding <=> %s) as similarity
                FROM knowledge_embeddings
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (query_embedding, query_embedding, top_k),
            )

            search_results = []
            for row in cur.fetchall():
                search_results.append({
                    "content": row[0],
                    "metadata": row[1] if isinstance(row[1], dict) else {},
                    "similarity": round(float(row[2]), 4),
                })

            cur.close()

            logger.info(
                "向量检索完成: top_k=%d, 最高相似度=%.4f",
                top_k,
                search_results[0]["similarity"] if search_results else 0,
            )
            return search_results

        except Exception as e:
            logger.error("向量检索失败: %s", str(e))
            return []
        finally:
            conn.close()

    def count(self):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM knowledge_embeddings")
            result = cur.fetchone()[0]
            cur.close()
            return result or 0
        except Exception:
            return 0
        finally:
            conn.close()

    def clear(self):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_embeddings")
            conn.commit()
            cur.close()
            logger.info("向量表已清空")
        except Exception as e:
            conn.rollback()
            logger.error("清空向量表失败: %s", str(e))
        finally:
            conn.close()


pgvector_client = PgvectorClient()