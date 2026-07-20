"""
Agent 会话管理工具类
负责对话状态管理、会话 CRUD 和消息存储
"""
from typing import Dict, Any, List
from datetime import datetime
from app.entity.db_models import ChatSession, ChatMessage
from sqlalchemy.orm import Session
from sqlalchemy import desc


class AgentCore:
    def __init__(self, db: Session, user_id: int = None):
        self.db = db
        self.user_id = user_id

    def create_session(self, title: str = None) -> ChatSession:
        import uuid
        session = ChatSession(
            user_id=self.user_id,
            session_uuid=str(uuid.uuid4()),
            title=title or "新对话",
            status="active",
            message_count=0,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: int) -> ChatSession:
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"会话 ID {session_id} 不存在")
        return session

    def get_message_history(self, session_id: int, limit: int = None) -> List[ChatMessage]:
        query = self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        query = query.order_by(ChatMessage.created_at)
        if limit:
            query = query.limit(limit)
        return query.all()

    def save_message(self, session_id: int, role: str, content: str,
                     tool_calls: List[Dict] = None, tool_result: str = None) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_result=tool_result,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.message_count += 1
            session.last_message_at = datetime.now()
            self.db.commit()
        return message

    def get_session_list(self, user_id: int = None) -> List[ChatSession]:
        query = self.db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
        elif self.user_id:
            query = query.filter(ChatSession.user_id == self.user_id)
        query = query.filter(ChatSession.status == "active")
        query = query.order_by(desc(ChatSession.last_message_at))
        return query.all()

    def delete_session(self, session_id: int):
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.status = "archived"
            self.db.commit()