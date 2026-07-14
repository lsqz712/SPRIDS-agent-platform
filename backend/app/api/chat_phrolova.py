"""
智能体对话 API — 弗洛洛风格流式聊天
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.schemas import ChatStreamRequest
from app.services.chat_service import stream_chat
from app.services.user_service import user_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["智能对话"])


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


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user: ChatUser = Depends(get_chat_user),
):
    history = [{"role": m.role, "content": m.content} for m in body.history]

    async def event_generator():
        try:
            async for chunk in stream_chat(
                user_message=body.message,
                history=history,
                username=user.username,
            ):
                payload = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("chat stream failed")
            message = str(exc)
            if "Connection error" in message or "ConnectError" in message:
                message = (
                    "无法连接 LLM 服务。请检查 backend/.env 中的 API Key 与 Base URL，"
                    "或改用 LLM_PROVIDER=qwen / USE_LOCAL_LLM=true"
                )
            payload = json.dumps({"error": message}, ensure_ascii=False)
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
