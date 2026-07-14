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
