"""
认证相关 API 路由
- POST /api/auth/register  用户注册
- POST /api/auth/login     用户登录 
- GET  /api/auth/me        获取当前用户信息
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    return user_service.get_user_by_id(db, user_id)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
    )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": [],
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
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
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = user_service.get_user_roles(db, current_user)
    return serialize_user(current_user, roles)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_info(
    request: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = request.model_dump(exclude_unset=True)
    user = user_service.update_profile(db, current_user, payload)
    roles = user_service.get_user_roles(db, user)
    return serialize_user(user, roles)


@router.post("/change-password", status_code=204)
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


@router.post("/me/avatar", response_model=UserResponse)
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = await user_service.upload_avatar(db, current_user, file)
    roles = user_service.get_user_roles(db, user)
    return serialize_user(user, roles)