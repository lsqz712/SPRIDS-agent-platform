"""
缺陷类型字典 API 路由
- GET    /api/defect-types        缺陷类型列表（搜索、筛选）
- POST   /api/defect-types        创建缺陷类型（需认证）
- PUT    /api/defect-types/{id}   编辑缺陷类型（需认证）
- DELETE /api/defect-types/{id}   删除缺陷类型（需认证）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.entity.db_models import User
from app.entity.schemas import DefectTypeCreate, DefectTypeUpdate, DefectTypeResponse
from app.services.defect_type_service import defect_type_service

router = APIRouter(prefix="/api/defect-types", tags=["缺陷类型字典"])


@router.get("/seed")
@router.post("/seed")
async def seed_defect_types():
    """一键插入 6 种 PCB 缺陷类型（幂等）"""
    from app.database.session import SessionLocal
    from app.entity.db_models import DefectType

    DEFECTS = [
        {"code": "MH", "name": "missing_hole", "name_cn": "缺孔", "severity": "major", "description": "PCB 上缺少应有的孔位", "is_active": True},
        {"code": "MB", "name": "mouse_bite", "name_cn": "鼠咬", "severity": "major", "description": "PCB 边缘出现类似鼠咬的缺口", "is_active": True},
        {"code": "OC", "name": "open_circuit", "name_cn": "开路", "severity": "critical", "description": "电路导线断裂导致开路", "is_active": True},
        {"code": "SC", "name": "short", "name_cn": "短路", "severity": "critical", "description": "不应连接的导线发生短路", "is_active": True},
        {"code": "SP", "name": "spur", "name_cn": "毛刺", "severity": "minor", "description": "蚀刻残留导致的铜箔毛刺", "is_active": True},
        {"code": "SPC", "name": "spurious_copper", "name_cn": "残铜", "severity": "minor", "description": "PCB 表面残留的多余铜箔", "is_active": True},
    ]
    db = SessionLocal()
    count = 0
    try:
        for d in DEFECTS:
            existing = db.query(DefectType).filter(DefectType.code == d["code"]).first()
            if not existing:
                db.add(DefectType(**d))
                count += 1
        db.commit()
        return {"success": True, "inserted": count, "message": f"已插入 {count} 条新缺陷类型"}
    finally:
        db.close()


@router.get("", response_model=dict)
async def list_defect_types(
    keyword: str | None = Query(default=None, description="搜索编码/名称/中文名"),
    severity: str | None = Query(
        default=None, description="按严重等级筛选：minor/major/critical"
    ),
    is_active: bool | None = Query(default=None, description="按启用状态筛选"),
    db: Session = Depends(get_db),
):
    """
    获取缺陷类型列表（无需认证）
    - 支持按编码/名称/中文名搜索
    - 支持按严重等级和启用状态筛选
    """
    items = defect_type_service.list_defect_types(
        db=db,
        keyword=keyword,
        severity=severity,
        is_active=is_active,
    )

    return {
        "code": 200,
        "message": "success",
        "data": [DefectTypeResponse.model_validate(item).model_dump() for item in items],
    }


@router.post("", response_model=dict, status_code=201)
async def create_defect_type(
    data: DefectTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建缺陷类型（需要登录）

    预置缺陷类型参考：
    | 编码       | 名称          | 中文名   | 严重等级 |
    |-----------|---------------|---------|---------|
    | SHORT     | Short Circuit | 短路     | critical |
    | OPEN      | Open Circuit  | 开路     | critical |
    | SOLDER    | Solder Joint  | 焊点不良 | major    |
    | SCRATCH   | Scratch       | 划痕     | minor    |
    | SHIFT     | Component Shift | 元件偏移 | major  |
    | MISSING   | Missing Component | 缺件  | critical |
    | TOMBSTONE | Tombstone     | 立碑     | major    |
    | BRIDGE    | Solder Bridge | 锡桥     | critical |
    """
    dt = defect_type_service.create_defect_type(db=db, data=data)

    return {
        "code": 201,
        "message": "缺陷类型创建成功",
        "data": DefectTypeResponse.model_validate(dt).model_dump(),
    }


@router.put("/{defect_type_id}", response_model=dict)
async def update_defect_type(
    defect_type_id: int,
    data: DefectTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    编辑缺陷类型（需要登录）
    - 所有字段可选，只传需要修改的字段
    """
    dt = defect_type_service.update_defect_type(
        db=db, defect_type_id=defect_type_id, data=data
    )

    return {
        "code": 200,
        "message": "缺陷类型更新成功",
        "data": DefectTypeResponse.model_validate(dt).model_dump(),
    }


@router.delete("/{defect_type_id}", status_code=204)
async def delete_defect_type(
    defect_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除缺陷类型（需要登录）
    - 物理删除（关联的检测结果中 defect_type_id 会被置空）
    """
    defect_type_service.delete_defect_type(db=db, defect_type_id=defect_type_id)
    return None
