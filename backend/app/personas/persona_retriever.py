"""
弗洛洛台词检索 — 根据用户输入选取相关原作台词作 few-shot 参考
"""
import json
import re
from functools import lru_cache
from pathlib import Path

PERSONAS_DIR = Path(__file__).resolve().parent
LINES_FILE = PERSONAS_DIR / "phrolova_lines.json"

# 主题关键词 → 优先匹配的台词特征词
TOPIC_HINTS = {
    "喜欢": ["喜欢", "爱", "心", "等", "记忆", "重逢", "承诺", "等待", "忘记"],
    "爱": ["喜欢", "爱", "等", "记忆", "承诺", "陌路", "等待", "忘记"],
    "等待": ["等", "承诺", "遗忘", "不会再", "忘记", "十字路口"],
    "想你": ["等", "记忆", "承诺", "重逢", "忘记"],
    "音乐": ["乐章", "指挥", "音符", "旋律", "演奏", "频率"],
    "指挥": ["指挥", "乐章", "音符", "频率"],
    "漂泊": ["漂泊者", "记忆", "承诺", "见面"],
    "残星": ["残星", "彼岸", "失亡"],
    "你好": ["见面", "荣幸", "紧张", "指挥家", "又见面", "重逢"],
    "我是谁": ["漂泊者", "记忆", "承诺", "见面", "重逢", "约定"],
    "你是谁": ["指挥家", "弗洛洛", "荣幸", "见面"],
    "见过": ["见面", "重逢", "记忆", "狂欢节", "约定"],
    "谢谢": ["荣幸", "不必", "呵呵"],
    "为什么": ["不必", "好奇", "看来"],
    "等我": ["等", "承诺", "不会再", "十字路口", "忘记"],
    "怎么想": ["记忆", "承诺", "乐章", "音符", "等"],
    "难过": ["记忆", "承诺", "等待", "可惜"],
    "孤独": ["记忆", "乐章", "等待", "可惜"],
}

# 无论检索结果如何，始终混入的标志性台词（语气锚点）
STYLE_ANCHORS = [
    "能在你繁多的记忆里留下一帧画面，是我的荣幸。",
    "别紧张，我只是以一名「指挥家」的身份，受邀前来参与这场对话而已。",
    "世间任何事物，追求时候的兴致总要比享用时候的兴致浓烈。",
    "毕竟，即便你真诚地相信、热切地盼望、耐心地站在十字路口旁等待……",
    "你所等待的那个人也有可能早就忘记了这里的存在，忘记了自己还要回来实现曾许下的承诺。",
    "我们之间的乐章……",
    "……序曲，才刚刚奏响。",
    "呵呵……不要担心，我不会打破这场白日梦。",
    "我不会再等了。",
]


def _tokenize(text: str) -> set[str]:
    text = text.lower()
    tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}", text))
    tokens.update(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    return tokens


@lru_cache
def load_lines() -> tuple[str, ...]:
    if not LINES_FILE.exists():
        return ()
    data = json.loads(LINES_FILE.read_text(encoding="utf-8"))
    return tuple(line for line in data if isinstance(line, str) and line.strip())


def retrieve_examples(user_message: str, limit: int = 6) -> list[str]:
    """按关键词重叠为用户消息选取最相关的弗洛洛台词"""
    lines = load_lines()
    if not lines:
        return []

    query_tokens = _tokenize(user_message)
    boost_words: set[str] = set()
    for keyword, hints in TOPIC_HINTS.items():
        if keyword in user_message:
            boost_words.update(hints)

    scored: list[tuple[int, str]] = []
    for line in lines:
        line_tokens = _tokenize(line)
        score = len(query_tokens & line_tokens)
        for w in boost_words:
            if w in line:
                score += 3
        if "……" in line or "——" in line:
            score += 1
        if len(line) >= 20:
            score += 1
        if score > 0:
            scored.append((score, line))

    if not scored:
        # 无匹配时返回几条代表性台词
        fallbacks = [
            "能在你繁多的记忆里留下一帧画面，是我的荣幸。",
            "别紧张，我只是以一名「指挥家」的身份，受邀前来参与这场对话而已。",
            "世间任何事物，追求时候的兴致总要比享用时候的兴致浓烈。",
            "我不会再等了。",
            "你问的问题……像是不经意拨动的一根弦。",
        ]
        return [l for l in fallbacks if l in lines][:limit] or list(lines[:limit])

    scored.sort(key=lambda x: (-x[0], len(x[1])))
    result: list[str] = []
    seen: set[str] = set()
    for _, line in scored:
        if line in seen:
            continue
        seen.add(line)
        result.append(line)
        if len(result) >= limit:
            break

    # 补充语气锚点，避免检索偏短或偏剧情向
    lines_set = set(lines)
    for anchor in STYLE_ANCHORS:
        if anchor in lines_set and anchor not in seen and len(result) < limit:
            result.append(anchor)
            seen.add(anchor)

    return result[:limit]


def format_examples_block(user_message: str, player_name: str = "漂泊者") -> str:
    examples = retrieve_examples(user_message)
    if not examples:
        return ""
    quoted = "\n".join(
        f"- 「{line.replace('{PlayerName}', player_name).replace('{TA}', player_name)}」"
        for line in examples
    )
    return (
        "\n\n## 本轮台词参考（来自原作，请模仿语气与节奏，勿整段照搬）\n"
        f"{quoted}\n"
        "回答时融合上述风格：冷静、文学感、偶有「呵呵……」；"
        "涉及情感时可有克制锋芒，但不要歇斯底里。"
        "**禁止照搬以上台词原文，须用自己的话重新组织。**"
    )
