"""Persona retriever tests"""
from app.personas.persona_retriever import format_examples_block, retrieve_examples


def test_retrieve_examples_returns_lines():
    examples = retrieve_examples("你好", limit=4)
    assert len(examples) >= 1
    assert all(isinstance(line, str) for line in examples)


def test_retrieve_love_topic_includes_emotional_lines():
    examples = retrieve_examples("我喜欢你", limit=8)
    joined = "".join(examples)
    assert any(k in joined for k in ("记忆", "等", "承诺", "喜欢"))


def test_format_examples_block_has_header():
    block = format_examples_block("指挥家")
    assert "本轮台词参考" in block
    assert "「" in block
