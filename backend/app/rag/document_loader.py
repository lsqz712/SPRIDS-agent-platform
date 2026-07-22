"""
文档加载与分块模块
负责读取领域知识文档并进行文本分块

支持的分块策略：
1. 固定大小分块（简单快速）
2. Markdown 结构感知分块（基于标题层级，推荐）
3. 语义分块（需要 embedding，可选）
"""

import os
import re
from typing import List, Dict, Any

from app.core.logger import get_logger

logger = get_logger(__name__)

KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "knowledge_base")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
MAX_CHUNK_SIZE = 800
MIN_CHUNK_SIZE = 100


def load_markdown_file(file_path: str) -> str:
    """读取 Markdown 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error("读取文档失败: %s, 错误: %s", file_path, str(e))
        return ""


def extract_markdown_headings(text: str) -> List[Dict[str, Any]]:
    """
    提取 Markdown 标题结构
    
    返回:
    [
        {"level": 1, "title": "标题", "start": 0, "end": 100, "content": "..."},
        ...
    ]
    """
    headings = []
    lines = text.split('\n')
    current_pos = 0
    
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    
    for i, line in enumerate(lines):
        match = heading_pattern.match(line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append({
                "level": level,
                "title": title,
                "line_index": i,
                "char_pos": current_pos,
            })
        current_pos += len(line) + 1
    
    for i, heading in enumerate(headings):
        if i < len(headings) - 1:
            heading["end_char_pos"] = headings[i + 1]["char_pos"]
        else:
            heading["end_char_pos"] = len(text)
    
    return headings


def split_by_markdown_structure(text: str, max_chunk_size: int = MAX_CHUNK_SIZE) -> List[str]:
    """
    基于 Markdown 标题结构的语义感知分块
    
    策略：
    1. 优先按 ## (h2) 标题分块
    2. 如果 h2 块太大，按 ### (h3) 细分
    3. 如果 h3 块仍然太大，使用固定大小分块
    4. 太小的相邻块会被合并
    """
    headings = extract_markdown_headings(text)
    
    if not headings:
        return split_text_fixed(text)
    
    h2_sections = []
    current_h2 = None
    
    for heading in headings:
        if heading["level"] == 2:
            if current_h2:
                h2_sections.append(current_h2)
            current_h2 = {
                "title": heading["title"],
                "start": heading["char_pos"],
                "end": heading["end_char_pos"],
            }
        elif heading["level"] == 1 and current_h2 is None:
            current_h2 = {
                "title": heading["title"],
                "start": heading["char_pos"],
                "end": heading["end_char_pos"],
            }
    
    if current_h2:
        h2_sections.append(current_h2)
    
    if not h2_sections:
        first_heading = headings[0]
        h2_sections.append({
            "title": first_heading["title"],
            "start": first_heading["char_pos"],
            "end": len(text),
        })
    
    chunks = []
    for section in h2_sections:
        section_content = text[section["start"]:section["end"]].strip()
        
        if len(section_content) <= max_chunk_size:
            if section_content:
                chunks.append(section_content)
        else:
            sub_chunks = split_text_fixed(section_content, max_chunk_size, CHUNK_OVERLAP)
            chunks.extend(sub_chunks)
    
    return merge_small_chunks(chunks, MIN_CHUNK_SIZE, max_chunk_size)


def merge_small_chunks(chunks: List[str], min_size: int, max_size: int) -> List[str]:
    """合并太小的相邻块"""
    if not chunks:
        return []
    
    merged = []
    current = chunks[0]
    
    for chunk in chunks[1:]:
        if len(current) + len(chunk) < max_size and len(current) < min_size:
            current = current + "\n\n" + chunk
        else:
            merged.append(current)
            current = chunk
    
    if current:
        merged.append(current)
    
    return merged


def split_text_fixed(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """固定大小分块（带边界检测）"""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        if end < text_length:
            last_period = text.rfind('。', start, end)
            last_period_en = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            split_pos = max(last_period, last_period_en, last_newline)
            if split_pos > start + chunk_overlap:
                end = split_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - chunk_overlap
        if start >= text_length:
            break

    return chunks


def split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    智能分块：优先使用 Markdown 结构分块，失败则使用固定大小分块
    """
    markdown_chunks = split_by_markdown_structure(text)
    if len(markdown_chunks) > 1:
        return markdown_chunks
    
    return split_text_fixed(text, chunk_size, chunk_overlap)


def load_all_documents() -> List[Dict[str, Any]]:
    """加载所有知识库文档"""
    documents = []
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        logger.warning("知识库目录不存在: %s", KNOWLEDGE_BASE_DIR)
        return documents

    for filename in sorted(os.listdir(KNOWLEDGE_BASE_DIR)):
        if filename.endswith('.md'):
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
            content = load_markdown_file(file_path)
            if content:
                chunks = split_text(content)
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "content": chunk,
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "metadata": {
                            "filename": filename,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                        }
                    })
            logger.info("加载文档: %s, 分块数: %d", filename, len(chunks))

    return documents


def get_document_by_filename(filename: str) -> List[Dict[str, Any]]:
    """按文件名获取文档"""
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
            "filename": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "metadata": {
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
        })

    return documents
