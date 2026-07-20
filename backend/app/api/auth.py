"""
认证相关 API 路由
- POST /api/auth/register  用户注册
- POST /api/auth/login     用户登录 
- GET  /api/auth/me        获取当前用户信息
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.utils import success_response
from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.schemas import (
    ChangePassword,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/api/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def serialize_user(user, roles: list[str]) -> dict:
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


@router.post("/register", status_code=201)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
        role=request.role or "viewer",
    )
    
    approval_status = "pending" if not user.is_approved else "approved"
    message = "注册成功，请等待管理员审批" if not user.is_approved else "注册成功"
    
    return success_response(data={
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_approved": user.is_approved,
        "approval_status": approval_status,
        "applied_role": request.role,
        "roles": [],
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }, message=message)


@router.post("/login")
async def login(request: UserLogin, db: Session = Depends(get_db)):
    user = user_service.login(
        db=db,
        username=request.username,
        password=request.password,
    )
    access_token = user_service.create_access_token_for_user(user)
    roles = user_service.get_user_roles(db, user)
    return success_response(data={
        "access_token": access_token,
        "token_type": "bearer",
        "user": serialize_user(user, roles),
    }, message="登录成功")


@router.get("/me")
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = user_service.get_user_roles(db, current_user)
    return success_response(data=serialize_user(current_user, roles))


@router.patch("/me")
async def update_current_user_info(
    request: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = request.model_dump(exclude_unset=True)
    user = user_service.update_profile(db, current_user, payload)
    roles = user_service.get_user_roles(db, user)
    return success_response(data=serialize_user(user, roles), message="更新成功")


@router.post("/change-password")
async def change_current_user_password(
    request: ChangePassword,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.change_password(
        db,
        current_user,
        request.old_password,
        request.new_password,
    )
    return success_response(message="密码修改成功")


@router.post("/me/avatar")
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = await user_service.upload_avatar(db, current_user, file)
    roles = user_service.get_user_roles(db, user)
    return success_response(data=serialize_user(user, roles), message="头像上传成功")