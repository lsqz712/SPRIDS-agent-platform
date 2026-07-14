"""
对话相关 API 路由

接口列表：
  - POST /api/chat/upload    上传图片文件，返回服务端路径
  - POST /api/chat/stream    SSE 流式对话（检测模式）
  - POST /api/chat/stream/phrolova    SSE 流式对话（弗洛洛风格）
  - POST /api/chat/sessions    创建新会话
  - GET  /api/chat/sessions    获取会话列表
  - GET  /api/chat/sessions/{id}/messages  获取会话消息历史
  - DELETE /api/chat/sessions/{id}  删除会话
"""

import json
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.agent.detection_agent import detection_agent
from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    ChatMessageRequest, ChatSessionResponse,
    ChatSessionCreate, ChatHistoryResponse,
)
from app.agent.core import AgentCore
from app.services.chat_service import stream_chat
from app.services.user_service import user_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["智能对话"])

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "rsod_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatUser:
    def __init__(self, user_id: int, username: str):
        self.id = user_id
        self.username = username


async def get_chat_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> ChatUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录，请先登录或使用预览模式")

    token = authorization.removeprefix("Bearer ").strip()

    if token == "dev-preview" and settings.DEBUG:
        return ChatUser(user_id=0, username="漂泊者")

    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        user = user_service.get_user_by_id(db, int(user_id_str))
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        return ChatUser(user_id=user.id, username=user.username)
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="无效的认证凭据") from exc


@router.post("/upload", summary="上传图片文件")
async def upload_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{os.getpid()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("图片上传成功: %s → %s", file.filename, file_path)
    return {"image_path": file_path}


@router.post("/stream")
async def chat_stream(
    request: Request,
    current_user=Depends(get_current_user),
):
    body = await request.json()
    message = body.get("message", "")
    image_path = body.get("image_path")
    session_id = body.get("session_id")

    if not message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    logger.info(
        "用户 %s 发起对话: message=%s, image=%s",
        current_user.username,
        message[:50],
        "有" if image_path else "无",
    )

    async def event_generator():
        try:
            async for event in detection_agent.chat_stream(
                message=message,
                image_path=image_path,
            ):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("SSE 流异常: %s", str(e), exc_info=True)
            error_data = json.dumps(
                {"type": "error", "content": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream/phrolova")
async def chat_stream_phrolova(
    request: Request,
    user: ChatUser = Depends(get_chat_user),
):
    body = await request.json()
    message = body.get("message", "")
    history = body.get("history", [])

    if not message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    logger.info("用户 %s 发起弗洛洛对话: message=%s", user.username, message[:50])

    async def event_generator():
        try:
            async for chunk in stream_chat(
                user_message=message,
                history=history,
                username=user.username,
            ):
                payload = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("phrolova chat stream failed")
            error_message = str(exc)
            if "Connection error" in error_message or "ConnectError" in error_message:
                error_message = (
                    "无法连接 LLM 服务。请检查 backend/.env 中的 API Key 与 Base URL，"
                    "或改用 LLM_PROVIDER=qwen / USE_LOCAL_LLM=true"
                )
            payload = json.dumps({"error": error_message}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Chat-Persona": "phrolova-v2",
        },
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    request: ChatSessionCreate = ChatSessionCreate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = AgentCore(db, current_user.id)
    session = agent.create_session(title=request.title)
    return session


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = AgentCore(db, current_user.id)
    sessions = agent.get_session_list()
    return sessions


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = AgentCore(db, current_user.id)
    try:
        session = agent.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    messages = agent.get_message_history(session_id)
    message_responses = []
    for msg in messages:
        message_responses.append({
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
        })
    return {
        "session": session,
        "messages": message_responses,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = AgentCore(db, current_user.id)
    agent.delete_session(session_id)
    return {"code": 200, "message": "会话已删除"}


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = AgentCore(db, current_user.id)
    session_id = request.session_id
    if not session_id:
        session = agent.create_session()
        session_id = session.id
    else:
        try:
            agent.get_session(session_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    agent.save_message(session_id, role="user", content=request.content)
    response = agent.generate_response(session_id, request.content)
    agent.save_message(session_id, role="assistant", content=response)
    return {
        "session_id": session_id,
        "content": response,
    }


@router.get("/welcome")
async def get_welcome(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = AgentCore(db, current_user.id)
    return {"message": agent.get_welcome_message()}