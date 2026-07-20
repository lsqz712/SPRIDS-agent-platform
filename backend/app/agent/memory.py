"""
对话记忆管理 — 基于 Redis 的对话历史存储 + 摘要记忆 + Token 优化

职责：
  - 保存用户对话消息到 Redis（支持 TTL 过期）
  - 加载历史消息作为 Agent 上下文
  - 对话摘要记忆（Conversation Summary Memory）：长对话自动生成摘要
  - Token 计数和上下文窗口管理
  - 管理会话（创建、获取、删除）

架构：
  ConversationMemory 使用 Redis List 存储每个会话的消息列表。
  key 格式: chat:session:{user_id}:{session_id}
  value: JSON 序列化的消息列表

Redis key 设计：
  chat:session:user1:abc123  → [msg1, msg2, ...]  TTL=3600s
  chat:sessions:user1        → [session_id1, session_id2, ...]
  chat:summary:user1:abc123  → 对话摘要文本
  chat:msg_count:user1:abc123 → 消息计数（用于触发摘要生成）
"""

import json
import time
import re
from typing import Optional, List, Dict

from app.core.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

MAX_HISTORY_MESSAGES = 20
SESSION_TTL = 3600
SESSION_INDEX_TTL = 86400

SUMMARY_TRIGGER_INTERVAL = 8
MAX_SUMMARY_TOKENS = 500
MAX_CONTEXT_TOKENS = 8000


def estimate_tokens(text: str) -> int:
    """
    粗略估算文本的 token 数量。
    
    对于中英文混合文本：
    - 英文：约 4 个字符 = 1 token
    - 中文：约 1.5 个字符 = 1 token
    """
    if not text:
        return 0
    
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    
    return int(chinese_chars / 1.5 + other_chars / 4 + 0.5)


def estimate_message_tokens(messages: List[Dict]) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
        total += 4
    return total


def trim_messages_to_token_limit(messages: List[Dict], max_tokens: int) -> List[Dict]:
    """
    将消息列表裁剪到指定 token 限制内。
    保留最新的消息，删除最早的消息。
    """
    if not messages:
        return []
    
    result = []
    current_tokens = 0
    
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg.get("content", "")) + 4
        if current_tokens + msg_tokens > max_tokens and result:
            break
        result.insert(0, msg)
        current_tokens += msg_tokens
    
    return result


class ConversationMemory:
    def __init__(self, max_messages: int = MAX_HISTORY_MESSAGES, ttl: int = SESSION_TTL):
        self.max_messages = max_messages
        self.ttl = ttl
        self.redis = self._get_redis()
        self.summary_trigger_interval = SUMMARY_TRIGGER_INTERVAL

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

    def _summary_key(self, user_id: int, session_id: str) -> str:
        return f"chat:summary:{user_id}:{session_id}"

    def _msg_count_key(self, user_id: int, session_id: str) -> str:
        return f"chat:msg_count:{user_id}:{session_id}"

    def _generate_summary(self, messages: List[Dict], existing_summary: str = "") -> str:
        """
        生成对话摘要。
        使用 LLM 生成摘要，如果 LLM 不可用则使用简单的关键词提取。
        """
        try:
            from app.agent.llm_client import llm_client
            
            conversation_text = ""
            for msg in messages:
                role = "用户" if msg["role"] == "user" else "助手"
                conversation_text += f"{role}: {msg['content']}\n"
            
            system_prompt = """你是一个对话摘要专家。请根据提供的对话历史，生成简洁的对话摘要。

要求：
1. 摘要控制在 300 字以内
2. 保留关键信息：用户的主要问题、检测任务、重要数据点
3. 如果已有历史摘要，请基于历史摘要更新，而不是完全重写
4. 用中文输出

输出格式：
直接输出摘要内容，不要有其他解释。"""

            user_prompt = f"""历史摘要（如果有）：
{existing_summary if existing_summary else '无'}

对话历史：
{conversation_text}

请生成对话摘要："""

            summary = llm_client.generate([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], max_tokens=MAX_SUMMARY_TOKENS)
            
            return summary.strip()
        except Exception as e:
            logger.warning("LLM summary generation failed, using simple summary: %s", str(e))
            return self._simple_summary(messages, existing_summary)

    def _simple_summary(self, messages: List[Dict], existing_summary: str = "") -> str:
        """简单的摘要生成（fallback）"""
        keywords = set()
        user_messages = [m for m in messages if m["role"] == "user"]
        
        for msg in user_messages:
            content = msg["content"]
            words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
            keywords.update(words[:10])
        
        new_summary = f"对话包含 {len(messages)} 条消息，涉及关键词：{', '.join(list(keywords)[:15])}"
        
        if existing_summary:
            return f"{existing_summary}\n更新：{new_summary}"
        return new_summary

    def _check_and_update_summary(self, user_id: int, session_id: str, messages: List[Dict]):
        """
        检查是否需要更新摘要。
        每 N 条消息更新一次摘要。
        """
        if len(messages) < self.summary_trigger_interval:
            return
        
        count_key = self._msg_count_key(user_id, session_id)
        summary_key = self._summary_key(user_id, session_id)
        
        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                current_count = client.get(count_key)
                current_count = int(current_count) if current_count else 0
                new_count = len(messages)
                
                if new_count - current_count >= self.summary_trigger_interval:
                    logger.info("Generating conversation summary: user=%d, session=%s, msgs=%d", 
                                user_id, session_id, new_count)
                    
                    existing_summary = client.get(summary_key)
                    if existing_summary:
                        existing_summary = existing_summary.decode('utf-8') if isinstance(existing_summary, bytes) else existing_summary
                    
                    recent_messages = messages[-self.summary_trigger_interval * 2:]
                    summary = self._generate_summary(recent_messages, existing_summary)
                    
                    client.set(summary_key, summary, ex=self.ttl)
                    client.set(count_key, str(new_count), ex=self.ttl)
            except Exception as e:
                logger.warning("Summary update failed: %s", str(e))

    def get_summary(self, user_id: int, session_id: str) -> str:
        """获取对话摘要"""
        summary_key = self._summary_key(user_id, session_id)
        
        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                summary = client.get(summary_key)
                if summary:
                    return summary.decode('utf-8') if isinstance(summary, bytes) else summary
            except Exception as e:
                logger.warning("Get summary failed: %s", str(e))
        
        return ""

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
                
                all_messages = self.load_history(user_id, session_id)
                self._check_and_update_summary(user_id, session_id, all_messages)
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
                    for raw in raw_messages:
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

    def load_context_with_summary(self, user_id: int, session_id: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> List[Dict]:
        """
        加载带摘要的上下文消息。
        
        策略：
        1. 获取对话摘要
        2. 获取最近的消息
        3. 组合成带摘要的上下文，确保不超过 token 限制
        """
        messages = self.load_history(user_id, session_id)
        summary = self.get_summary(user_id, session_id)
        
        if not summary:
            recent_messages = messages[-self.max_messages:]
            return trim_messages_to_token_limit(recent_messages, max_tokens)
        
        system_summary_msg = {
            "role": "system",
            "content": f"【对话历史摘要】\n{summary}\n\n（以上是之前对话的摘要，用于帮助你理解对话背景）"
        }
        
        summary_tokens = estimate_tokens(system_summary_msg["content"]) + 4
        remaining_tokens = max_tokens - summary_tokens
        
        if remaining_tokens < 500:
            return [system_summary_msg]
        
        recent_messages = messages[-self.max_messages:]
        trimmed_recent = trim_messages_to_token_limit(recent_messages, remaining_tokens)
        
        return [system_summary_msg] + trimmed_recent

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
        summary_key = self._summary_key(user_id, session_id)
        msg_count_key = self._msg_count_key(user_id, session_id)
        
        if self.redis:
            try:
                client = getattr(self.redis, '_client', self.redis)
                client.delete(key)
                client.delete(summary_key)
                client.delete(msg_count_key)
            except Exception as e:
                logger.warning("Redis clear failed: %s", str(e))
        logger.info("清空会话: user=%d, session=%s", user_id, session_id)


conversation_memory = ConversationMemory()
