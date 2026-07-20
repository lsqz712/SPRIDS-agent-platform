"""
⽤户服务层
处理⽤户注册、登录、鉴权等业务逻辑
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.security import create_access_token, hash_password, verify_password
from app.entity.db_models import User


class UserService:
    """⽤户服务"""

    @staticmethod
    def register(db: Session, username: str, email: str, password: str) -> User:
        """
        ⽤户注册
        Args:
            db: 数据库会话
            username: ⽤户名
            email: 邮箱
            password: 明⽂密码
        Returns:
            新创建的⽤户对象
        Raises:
            HTTPException: ⽤户名或邮箱已存在
        """
        # 检查⽤户名是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="⽤户名已存在")
        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被注册")
        # 创建新⽤户
        new_user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(db: Session, username: str, password: str) -> User:
        """
        ⽤户登录
        Args:
            db: 数据库会话
            username: ⽤户名
            password: 明⽂密码
        Returns:
            登录成功的⽤户对象
        Raises:
            HTTPException: ⽤户名或密码错误
        """
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="⽤户名或密码错误")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="⽤户名或密码错误")
        return user

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """为⽤户⽣成 JWT Token"""
        return create_access_token(data={"sub": str(user.id)})

    @staticmethod
    def get_user_roles(db: Session, user: User) -> list[str]:
        """获取⽤户的⻆⾊标识列表"""
        return [ur.role.name for ur in user.user_roles]

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """根据 ID 获取⽤户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="⽤户不存在")
        return user

    @staticmethod
    def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
        """
        修改用户密码
        Args:
            db: 数据库会话
            user: 当前登录用户
            old_password: 旧密码（明文）
            new_password: 新密码（明文）
        Raises:
            HTTPException: 旧密码不正确
        """
        # 校验旧密码
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="旧密码不正确")

        # 新密码不能与旧密码相同
        if old_password == new_password:
            raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

        # 更新密码
        user.hashed_password = hash_password(new_password)
        db.commit()
        db.refresh(user)

    @staticmethod
    def update_profile(db: Session, user: User, **kwargs) -> User:
        """
        更新用户资料
        Args:
            db: 数据库会话
            user: 当前登录用户
            kwargs: 可更新字段（username, email, phone, avatar 等）
        Returns:
            更新后的用户对象
        """
        allowed_fields = {"username", "email", "phone", "avatar"}
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                # 检查用户名唯一性
                if field == "username":
                    existing = db.query(User).filter(
                        User.username == value,
                        User.id != user.id,
                    ).first()
                    if existing:
                        raise HTTPException(status_code=400, detail="用户名已存在")
                # 检查邮箱唯一性
                if field == "email":
                    existing = db.query(User).filter(
                        User.email == value,
                        User.id != user.id,
                    ).first()
                    if existing:
                        raise HTTPException(status_code=400, detail="邮箱已被注册")
                setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return user


# 全局单例
user_service = UserService()