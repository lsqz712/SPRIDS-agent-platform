"""
认证相关 API 路由
- POST /api/auth/register        用户注册
- POST /api/auth/login           用户登录
- GET  /api/auth/me              获取当前用户信息
- PATCH /api/auth/me             更新当前用户资料
- POST /api/auth/change-password 修改当前用户密码
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user, get_current_active_user
from app.entity.schemas import (
    TokenResponse, UserLogin, UserRegister, UserResponse,
    UserUpdate, ChangePassword,
)
from app.entity.db_models import User
from app.services.user_service import user_service

router = APIRouter(prefix="/api/auth", tags=["认证"])
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册
    - **username**: 用户名（3-50 字符）
    - **email**: 邮箱
    - **password**: 密码（至少 6 位）
    """
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
    )
    return user
    
@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    - 返回 JWT access_token
    - 后续请求在 Header 中携带：Authorization: Bearer <token>
    """
    user = user_service.login(
        db=db,
        username=request.username,
        password=request.password,
    )

    access_token = user_service.create_access_token_for_user(user)
    roles = user_service.get_user_roles(db, user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "roles": roles,
        },
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户信息（需要 Token 认证）"""
    roles = user_service.get_user_roles(db, current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
    }

@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    更新当前用户资料
    - **phone**: 手机号（可选）
    - **avatar**: 头像 URL（可选）
    - **email**: 邮箱（可选）
    """
    user = user_service.update_profile(
        db=db,
        user=current_user,
        **request.model_dump(exclude_unset=True),
    )
    roles = user_service.get_user_roles(db, user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": roles,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }

@router.post("/change-password")
async def change_password(
    request: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    修改当前用户密码
    - **old_password**: 旧密码
    - **new_password**: 新密码（至少 6 位）
    """
    user_service.change_password(
        db=db,
        user=current_user,
        old_password=request.old_password,
        new_password=request.new_password,
    )
    return {"message": "密码修改成功"}
