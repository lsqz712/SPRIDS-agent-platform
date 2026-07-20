"""Identity reinforcement in chat messages"""
from app.services.chat_service import (
    build_identity_reinforcement,
    build_messages,
    resolve_player_name,
)


def test_who_am_i_gets_soft_hint_not_template():
    block = build_identity_reinforcement("我是谁", "漂泊者")
    assert "漂泊者" in block
    assert "提示" in block
    assert "固定开头" in block or "固定套话" in block


def test_wait_question_prevents_role_swap():
    block = build_identity_reinforcement("你会等我吗", "漂泊者")
    assert "你会不会等" in block
    assert "间奏" in block  # mentioned as forbidden pattern


def test_build_messages_no_fake_history():
    msgs = build_messages("今天天气怎么样", username="漂泊者")
    roles = [type(m).__name__ for m in msgs]
    assert roles == ["SystemMessage", "HumanMessage"]


def test_preview_user_resolves_to_rover():
    assert resolve_player_name("预览用户") == "漂泊者"
