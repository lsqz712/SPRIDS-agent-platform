"""
文档加载与分块模块
负责读取领域知识文档并进行文本分块
"""

import os
import re
from typing import List, Dict, Any

from app.core.logger import get_logger

logger = get_logger(__name__)

KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "knowledge_base")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def load_markdown_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error("读取文档失败: %s, 错误: %s", file_path, str(e))
        return ""


def split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        if end < text_length:
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            split_pos = max(last_period, last_newline)
            if split_pos > start + chunk_overlap:
                end = split_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - chunk_overlap

    return chunks


def load_all_documents() -> List[Dict[str, Any]]:
    documents = []
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        logger.warning("知识库目录不存在: %s", KNOWLEDGE_BASE_DIR)
        return documents

    for filename in os.listdir(KNOWLEDGE_BASE_DIR):
        if filename.endswith('.md'):
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
            content = load_markdown_file(file_path)
            if content:
                chunks = split_text(content)
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "content": chunk,
                        "metadata": {
                            "filename": filename,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                        }
                    })
            logger.info("加载文档: %s, 分块数: %d", filename, len(chunks))

    return documents


def get_document_by_filename(filename: str) -> List[Dict[str, Any]]:
    file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
    if not os.path.exists(file_path):
        logger.warning("文档不存在: %s", file_path)
        return []

    content = load_markdown_file(file_path)
    if not content:
        return []

    chunks = split_text(content)
    documents = []
    for i, chunk in enumerate(chunks):
        documents.append({
            "content": chunk,
            "metadata": {
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
        })

    return documents
