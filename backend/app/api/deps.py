"""
公共依赖注入模块
  - 提供 get_current_user（从 JWT Token 解析当前用户）
  - 提供 get_current_active_user（验证用户是否被禁用）
  - 后续可扩展：RBAC 权限校验的工厂函数（check_permission）
"""
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.db_models import User
from app.services.user_service import user_service

# OAuth2 密码模式，用于从请求 Header 中提取 Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从 JWT Token 中解析当前用户
    在需要认证的路由中通过 Depends(get_current_user) 使用
    如果 token 不存在或无效，返回 None（用于可选认证场景）
    """
    if token is None:
        return None
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
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """验证当前用户是否已被禁用"""
    if current_user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    return current_user


class ChatUser:
    def __init__(self, user_id: int, username: str):
        self.id = user_id
        self.username = username


async def get_chat_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> ChatUser:
    """
    获取聊天用户信息（支持预览模式）
    用于弗洛洛风格对话等需要用户标识但允许预览的场景
    """
    from app.config.settings import settings
    
    if token is None:
        raise HTTPException(status_code=401, detail="未登录，请先登录或使用预览模式")

    if token == "dev-preview" and settings.DEBUG:
        return ChatUser(user_id=0, username="漂泊者")

    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user = user_service.get_user_by_id(db, int(user_id_str))
        if not user:
            raise credentials_exception
        return ChatUser(user_id=user.id, username=user.username)
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc
