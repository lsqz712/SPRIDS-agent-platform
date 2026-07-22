"""
Agent 共享模块 — create_llm() + compress_tool_output()

所有 Agent 统一从这里导入，消除代码重复。
"""

import json

from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

MAX_TOOL_OUTPUT_CHARS = 2000
MAX_LIST_ITEMS = 5


def create_llm():
    """根据配置创建 LLM 实例（所有 Agent 共用）"""
    api_key = settings.effective_llm_api_key
    if not api_key:
        logger.warning("未配置 LLM API Key，将使用模拟模式")
        return None

    base_url = settings.effective_llm_base_url
    model_name = settings.effective_llm_model

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
    )


def compress_tool_output(data: dict) -> str:
    """
    压缩工具输出，减少 token 消耗。

    策略：
    1. 列表类数据：只保留前 MAX_LIST_ITEMS 条 + total 计数
    2. 移除 null/空字符串/空列表字段
    3. 深度清理嵌套结构
    4. 限制最终 JSON 长度不超过 MAX_TOOL_OUTPUT_CHARS
    """
    PRIORITY_FIELDS = {"id", "name", "count", "total", "status", "confidence",
                       "class_name", "result", "version", "progress", "content", "source"}

    def clean_item(item, depth=0):
        if depth > 3:
            return str(item) if item else None
        if isinstance(item, dict):
            cleaned = {}
            for k, v in item.items():
                if v is None or v == "" or v == [] or v == {}:
                    continue
                if k in PRIORITY_FIELDS:
                    cleaned[k] = clean_item(v, depth + 1)
                elif depth < 2:
                    cleaned[k] = clean_item(v, depth + 1)
            return cleaned if cleaned else None
        elif isinstance(item, list):
            if depth == 0:
                return [clean_item(i, depth + 1) for i in item[:MAX_LIST_ITEMS]
                        if clean_item(i, depth + 1) is not None]
            return [clean_item(i, depth + 1) for i in item[:3]
                    if clean_item(i, depth + 1) is not None]
        return item

    cleaned_data = clean_item(data)
    if cleaned_data is None:
        cleaned_data = {}

    if "items" in cleaned_data and isinstance(cleaned_data["items"], list) and "total" not in cleaned_data:
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            cleaned_data["total"] = len(data["items"])

    result = json.dumps(cleaned_data, ensure_ascii=False, default=str)

    if len(result) > MAX_TOOL_OUTPUT_CHARS:
        result = result[:MAX_TOOL_OUTPUT_CHARS - 3] + "..."

    return result
