"""
PCB 缺陷类型常量 — 全局统一定义

使用方式：
    from app.entity.defect_types import DEFECT_TYPES, get_defect_by_code, get_defect_by_name

本模块定义 6 种 PCB SMT 缺陷类型，一处修改全局生效。
seed 脚本、Agent 工具、API 共享同一份数据。
"""

from typing import Optional

# ── 6 种 PCB 缺陷类型 ────────────────────────────────

DEFECT_TYPES = [
    {
        "code": "MH",
        "name": "missing_hole",
        "name_cn": "缺孔",
        "severity": "major",
        "description": "PCB 上缺少应有的孔位",
        "is_active": True,
    },
    {
        "code": "MB",
        "name": "mouse_bite",
        "name_cn": "鼠咬",
        "severity": "major",
        "description": "PCB 边缘出现类似鼠咬的缺口",
        "is_active": True,
    },
    {
        "code": "OC",
        "name": "open_circuit",
        "name_cn": "开路",
        "severity": "critical",
        "description": "电路导线断裂导致开路",
        "is_active": True,
    },
    {
        "code": "SC",
        "name": "short",
        "name_cn": "短路",
        "severity": "critical",
        "description": "不应连接的导线发生短路",
        "is_active": True,
    },
    {
        "code": "SP",
        "name": "spur",
        "name_cn": "毛刺",
        "severity": "minor",
        "description": "蚀刻残留导致的铜箔毛刺",
        "is_active": True,
    },
    {
        "code": "SPC",
        "name": "spurious_copper",
        "name_cn": "残铜",
        "severity": "minor",
        "description": "PCB 表面残留的多余铜箔",
        "is_active": True,
    },
]

# ── 查找函数 ──────────────────────────────────────────


def get_defect_by_code(code: str) -> Optional[dict]:
    """按 code 查缺陷（如 'MH' → 缺孔）"""
    for d in DEFECT_TYPES:
        if d["code"] == code.upper():
            return d
    return None


def get_defect_by_name(name: str) -> Optional[dict]:
    """按英文名查缺陷（如 'missing_hole' → 缺孔）"""
    for d in DEFECT_TYPES:
        if d["name"] == name.lower():
            return d
    return None


def get_name_cn_map() -> dict:
    """返回 {英文名: 中文名} 映射"""
    return {d["name"]: d["name_cn"] for d in DEFECT_TYPES}


def get_severity_map() -> dict:
    """返回 {英文名: 严重等级} 映射"""
    return {d["name"]: d["severity"] for d in DEFECT_TYPES}
