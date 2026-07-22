"""
弗洛洛风格对话服务
"""
import re
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger
from app.personas.persona_retriever import format_examples_block

logger = get_logger(__name__)

PERSONAS_DIR = Path(__file__).resolve().parent.parent / "personas"


def load_persona_prompt(name: str = "phrolova") -> str:
    path = PERSONAS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"未找到人设文件: {path}")
    return path.read_text(encoding="utf-8")


def create_chat_model() -> ChatOpenAI:
    if settings.USE_LOCAL_LLM or settings.LLM_PROVIDER == "ollama":
        return ChatOpenAI(
            model=settings.OLLAMA_MODEL,
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL.rstrip('/')}/v1",
            streaming=True,
            temperature=0.85,
        )

    if settings.LLM_PROVIDER == "qwen":
        if not settings.QWEN_API_KEY or settings.QWEN_API_KEY.startswith("sk-your-"):
            raise RuntimeError(
                "未配置有效的 QWEN_API_KEY，请在 backend/.env 中填写通义千问 API Key"
            )
        return ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            streaming=True,
            temperature=0.78,
        )

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("未配置 OPENAI_API_KEY，请在 backend/.env 中设置")

    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
        streaming=True,
        temperature=0.85,
    )


PREVIEW_USERNAMES = frozenset({"预览用户", "旅人", ""})


def resolve_player_name(username: str) -> str:
    """将登录名映射为游戏内称呼；预览账号统一视为「漂泊者」"""
    name = (username or "").strip()
    if not name or name in PREVIEW_USERNAMES:
        return "漂泊者"
    return name


def apply_player_placeholders(text: str, player_name: str) -> str:
    return text.replace("{PlayerName}", player_name).replace("{TA}", player_name)


def build_scene_anchor(player_name: str) -> str:
    return (
        "\n\n## 当前场景（始终成立，不可推翻）\n"
        f"- 正在与你对话的人：**漂泊者 {player_name}**\n"
        "- 你们是老相识，不是第一次见面，不是陌生访客\n"
        "- 你完全知道对方身份，**禁止**追问「你是谁」「你从哪来」「介绍一下自己」\n"
        "- 禁止使用「访客」「用户」「网友」等称呼对方\n"
    )


def build_identity_reinforcement(user_message: str, player_name: str) -> str:
    """轻量提示，约束角色边界，但不强制固定措辞"""
    text = user_message.strip()

    if re.search(r"我是谁|你知道我是谁|你认识我吗|我是谁啊", text):
        return (
            "\n\n【本回合提示】对方在问自己的身份。"
            f"请思考后自然回答：TA 就是漂泊者 {player_name}。"
            "可联想旧识、承诺、失约；禁止反问、禁止要求自我介绍；"
            "禁止照搬示范台词或使用固定开头。"
        )

    if re.search(r"你是谁|你叫什么", text):
        return (
            "\n\n【本回合提示】对方在问你的身份。"
            "请思考后以弗洛洛/指挥家身份作答（指挥家是你自己的外号，不是对方）。"
        )

    if re.search(r"我们见过|见过面|认识吗", text):
        return (
            "\n\n【本回合提示】对方在问是否见过。"
            "请思考后肯定见过，用旧友重逢语气；可提狂欢节、七丘、今州。"
        )

    if re.fullmatch(r"(你好|您好|hi|hello|嗨|在吗|在不在)[\?？!！。…~\s]*", text, re.I):
        return (
            "\n\n【本回合提示】这是寒暄。"
            f"请用旧识重逢语气回应 {player_name}，但换用新的意象与开场，"
            "禁止照搬示范台词，禁止以「我们又见面了」「就这里吧」开头。"
        )

    if re.search(r"你会.*等我|你肯等我|你会等吗|等我吗|会不会等我", text):
        return (
            "\n\n【本回合提示】对方在问：你会不会等 TA（漂泊者）。"
            "必须从你的视角回答你曾等过/还会不会继续等；"
            "禁止反过来教训对方「你若真要等」「别把自己耗成间奏」——那是弄反了角色。"
        )

    if re.search(r"你怎么想我|你如何看待我|你怎么看我", text):
        return (
            "\n\n【本回合提示】对方在问你对 TA 的看法。"
            "以弗洛洛的疏离、文学感作答；可用乐章/音符隐喻；不要客服式夸奖。"
        )

    return ""


def build_messages(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    username: str = "漂泊者",
) -> list:
    player_name = resolve_player_name(username)
    system = apply_player_placeholders(
        load_persona_prompt(settings.CHAT_PERSONA), player_name
    )
    system += build_scene_anchor(player_name)
    system += format_examples_block(user_message, player_name)
    system += build_identity_reinforcement(user_message, player_name)

    messages: list = [SystemMessage(content=system)]

    for item in history or []:
        role = item.get("role")
        content = item.get("content", "")
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))
    return messages


async def stream_chat(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    username: str = "漂泊者",
):
    llm = create_chat_model()
    messages = build_messages(user_message, history, username)

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
