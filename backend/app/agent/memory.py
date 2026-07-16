"""
对话记忆管理 — 基于 Redis 的对话历史存储

职责：
  - 保存用户对话消息到 Redis（支持 TTL 过期）
  - 加载历史消息作为 Agent 上下文
  - 管理会话（创建、获取、删除）
  - 限制历史消息数量，防止上下文超长

架构：
  ConversationMemory 使用 Redis List 存储每个会话的消息列表。
  key 格式: chat:session:{user_id}:{session_id}
  value: JSON 序列化的消息列表

Redis key 设计：
  chat:session:user1:abc123  → [msg1, msg2, ...]  TTL=3600s
  chat:sessions:user1        → [session_id1, session_id2, ...]
"""

import json
import time
from typing import Optional, List, Dict

from app.core.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

MAX_HISTORY_MESSAGES = 20
SESSION_TTL = 3600
SESSION_INDEX_TTL = 86400


class ConversationMemory:
    def __init__(self, max_messages: int = MAX_HISTORY_MESSAGES, ttl: int = SESSION_TTL):
        self.max_messages = max_messages
        self.ttl = ttl
        self.redis = self._get_redis()

    def _get_redis(self):
        try:
            from app.storage.redis_client import redis_client
            return redis_client
        except ImportError:
            logger.warning("Redis client not available, using in-memory fallback")
            return None

    def _session_key(self, user_id: int, session_id: str) -> str:
        return f"chat:session:{user_id}:{session_id}"

    def _index_key(self, user_id: int) -> str:
        return f"chat:sessions:{user_id}"

    def save_message(self, user_id: int, session_id: str, role: str, content: str):
        key = self._session_key(user_id, session_id)
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }

        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                client.lpush(key, json.dumps(message, ensure_ascii=False))
                client.expire(key, self.ttl)

                index_key = self._index_key(user_id)
                existing = client.get(f"chat:exists:{user_id}:{session_id}")
                if not existing:
                    client.lpush(index_key, session_id)
                    client.set(f"chat:exists:{user_id}:{session_id}", "1", ex=SESSION_INDEX_TTL)
                    client.expire(index_key, SESSION_INDEX_TTL)
            except Exception as e:
                logger.warning("Redis save failed: %s", str(e))

        logger.debug("保存消息: user=%d, session=%s, role=%s, len=%d", user_id, session_id, role, len(content))

    def load_history(self, user_id: int, session_id: str) -> List[Dict]:
        key = self._session_key(user_id, session_id)
        messages = []

        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                raw_messages = client.lrange(key, 0, -1)
                if raw_messages:
                    for raw in raw_messages[-self.max_messages:]:
                        try:
                            msg = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
                            messages.append({
                                "role": msg.get("role", "user"),
                                "content": msg.get("content", ""),
                            })
                        except (json.JSONDecodeError, AttributeError):
                            continue
            except Exception as e:
                logger.warning("Redis load failed: %s", str(e))

        messages.reverse()
        logger.debug("加载历史: user=%d, session=%s, 消息数=%d", user_id, session_id, len(messages))
        return messages

    def get_sessions(self, user_id: int) -> List[str]:
        index_key = self._index_key(user_id)
        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                sessions = client.lrange(index_key, 0, -1)
                return [s.decode('utf-8') if isinstance(s, bytes) else s for s in sessions]
            except Exception as e:
                logger.warning("Redis get sessions failed: %s", str(e))
        return []

    def clear_session(self, user_id: int, session_id: str):
        key = self._session_key(user_id, session_id)
        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                client.delete(key)
            except Exception as e:
                logger.warning("Redis clear failed: %s", str(e))
        logger.info("清空会话: user=%d, session=%s", user_id, session_id)


conversation_memory = ConversationMemory()
