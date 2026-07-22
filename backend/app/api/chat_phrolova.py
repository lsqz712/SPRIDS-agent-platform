"""
智能体对话 API — 弗洛洛风格流式聊天
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.logger import get_logger
from app.entity.schemas import ChatStreamRequest
from app.services.chat_service import stream_chat
from app.api.deps import get_chat_user

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["智能对话"])


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user=Depends(get_chat_user),
):
    """SSE 流式对话（弗洛洛风格）"""
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