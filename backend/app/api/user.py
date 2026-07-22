"""
用户管理 API 路由

接口列表：
  - GET  /api/user/list        用户列表（含角色筛选）
  - GET  /api/user/roles       系统角色列表
  - GET  /api/user/profile     当前用户信息
  - PATCH /api/user/password   修改密码
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.deps import check_permission
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.schemas import ChangePassword, UserUpdate
from app.services.user_service import user_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/user", tags=["用户管理"])


@router.get("/list", summary="用户列表", dependencies=[Depends(check_permission("user:read"))])
async def list_users(
    role: str = Query(None, description="角色筛选"),
    is_active: bool = Query(None, description="激活状态筛选"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取系统用户列表（支持按角色和状态筛选）"""
    from app.entity.db_models import User, UserRole
    query = db.query(User)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if role:
        query = query.join(UserRole).filter(UserRole.role.has(name=role))
    users = query.all()
    result = []
    for u in users:
        roles = user_service.get_user_roles(db, u)
        result.append({
            "id": u.id, "username": u.username, "email": u.email,
            "phone": u.phone, "avatar": u.avatar,
            "is_active": u.is_active, "is_superuser": u.is_superuser,
            "roles": roles,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return {"users": result, "total": len(result)}


@router.get("/roles", summary="系统角色列表", dependencies=[Depends(check_permission("role:read"))])
async def list_roles(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """获取系统所有角色"""
    from app.entity.db_models import Role
    roles = db.query(Role).all()
    return {"roles": [{"id": r.id, "name": r.name, "description": r.description} for r in roles]}


@router.get("/profile", summary="当前用户信息")
async def get_profile(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前登录用户的详细信息"""
    roles = user_service.get_user_roles(db, current_user)
    return {
        "id": current_user.id, "username": current_user.username,
        "email": current_user.email, "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.patch("/password", status_code=204)
async def change_password(
    request: ChangePassword,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户密码"""
    user_service.change_password(db, current_user, request.old_password, request.new_password)
