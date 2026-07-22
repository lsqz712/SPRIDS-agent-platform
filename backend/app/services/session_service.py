"""
会话管理服务层
处理聊天会话的创建、查询、删除等操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.entity.db_models import ChatSession, ChatMessage
from app.entity.schemas import ChatSessionResponse, ChatHistoryResponse


class SessionService:
    """会话管理服务"""

    @staticmethod
    def create_session(db: Session, user_id: int, title: str = None) -> ChatSession:
        """创建新会话"""
        import uuid
        session = ChatSession(
            user_id=user_id,
            session_uuid=str(uuid.uuid4()),
            title=title or "新对话",
            status="active",
            message_count=0,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session(db: Session, session_id: int, user_id: int = None) -> ChatSession:
        """获取会话详情（可校验归属）"""
        query = db.query(ChatSession).filter(ChatSession.id == session_id)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
        session = query.first()
        if not session:
            raise ValueError(f"会话 ID {session_id} 不存在")
        return session

    @staticmethod
    def get_session_list(db: Session, user_id: int = None) -> list[ChatSession]:
        """获取会话列表"""
        query = db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
        query = query.filter(ChatSession.status == "active")
        query = query.order_by(desc(ChatSession.last_message_at))
        return query.all()

    @staticmethod
    def delete_session(db: Session, session_id: int):
        """删除会话（软删除）"""
        session = SessionService.get_session(db, session_id)
        session.status = "archived"
        db.commit()

    @staticmethod
    def get_message_history(db: Session, session_id: int, limit: int = None) -> list[ChatMessage]:
        """获取会话消息历史"""
        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        query = query.order_by(ChatMessage.created_at)
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def save_message(
        db: Session,
        session_id: int,
        role: str,
        content: str,
        tool_calls: list = None,
        tool_result: str = None,
    ) -> ChatMessage:
        """保存消息"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_result=tool_result,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.message_count += 1
            from datetime import datetime
            session.last_message_at = datetime.now()
            db.commit()
        
        return message

    @staticmethod
    def format_messages_response(messages: list[ChatMessage]) -> list[dict]:
        """格式化消息响应数据"""
        return [
            {
                "id": msg.id,
                "session_id": msg.session_id,
                "role": msg.role,
                "content": msg.content,
                "agent_used": msg.agent_used,
                "tool_calls": msg.tool_calls,
                "tool_result": msg.tool_result,
                "tokens_used": msg.tokens_used,
                "latency_ms": msg.latency_ms,
                "created_at": msg.created_at,
            }
            for msg in messages
        ]


session_service = SessionService()