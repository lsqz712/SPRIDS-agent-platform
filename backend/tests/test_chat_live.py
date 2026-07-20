"""Live LLM chat variation tests — requires QWEN_API_KEY"""
import os
import asyncio

import pytest

from app.config.settings import settings
from app.services.chat_service import stream_chat

pytestmark = pytest.mark.skipif(
    not settings.QWEN_API_KEY or settings.QWEN_API_KEY.startswith("sk-your-"),
    reason="需要配置 QWEN_API_KEY（在 backend/.env 中设置）才能运行",
)

BANNED_OPENERS = (
    "就这里吧",
    "我们又见面了",
    "你好呀",
    "很高兴",
)


async def _collect(message: str) -> str:
    parts = []
    async for chunk in stream_chat(message, username="漂泊者"):
        parts.append(chunk)
    return "".join(parts).strip()


def _first_line(text: str) -> str:
    return text.split("\n", 1)[0].strip()


@pytest.mark.asyncio
async def test_hello_replies_are_not_identical():
    replies = [await _collect("你好") for _ in range(3)]
    assert len(set(replies)) >= 2, f"三次回复完全相同: {replies[0][:80]}"
    for reply in replies:
        assert any(k in reply for k in ("漂泊者", "你")), reply[:120]


@pytest.mark.asyncio
async def test_hello_avoids_canned_openers():
    reply = await _collect("你好")
    first = _first_line(reply)
    for opener in BANNED_OPENERS:
        assert not first.startswith(opener), f"使用了固定开场「{opener}」: {first}"


@pytest.mark.asyncio
async def test_who_am_i_is_rover_not_stranger():
    reply = await _collect("我是谁")
    assert "漂泊者" in reply
    assert "好奇者" not in reply
    assert "寻求帮助" not in reply


@pytest.mark.asyncio
async def test_wait_for_me_not_role_reversed():
    reply = await _collect("你会等我吗")
    assert "你若真要等" not in reply
    assert "别把自己耗成" not in reply
