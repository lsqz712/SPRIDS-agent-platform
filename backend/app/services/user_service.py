"""
用户服务层
"""
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.entity.db_models import User
from app.storage.minio_client import minio_client

AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class UserService:
    @staticmethod
    def register(db: Session, username: str, email: str, password: str) -> User:
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="邮箱已被注册")

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
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        return user

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        return create_access_token(data={"sub": str(user.id)})

    @staticmethod
    def get_user_roles(db: Session, user: User) -> list[str]:
        return [ur.role.name for ur in user.user_roles]

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    @staticmethod
    def update_profile(db: Session, user: User, updates: dict) -> User:
        if "username" in updates:
            username = updates["username"]
            if username != user.username:
                existing = (
                    db.query(User)
                    .filter(User.username == username, User.id != user.id)
                    .first()
                )
                if existing:
                    raise HTTPException(status_code=400, detail="用户名已存在")
                user.username = username

        if "email" in updates:
            email = updates["email"]
            if email != user.email:
                existing = (
                    db.query(User)
                    .filter(User.email == email, User.id != user.id)
                    .first()
                )
                if existing:
                    raise HTTPException(status_code=400, detail="邮箱已被注册")
                user.email = email

        if "phone" in updates:
            user.phone = updates["phone"] or None

        if "avatar" in updates:
            user.avatar = updates["avatar"] or None

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def change_password(
        db: Session,
        user: User,
        old_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="当前密码不正确")
        user.hashed_password = hash_password(new_password)
        db.commit()

    @staticmethod
    def _avatar_object_name_from_url(avatar_url: str | None) -> str | None:
        if not avatar_url:
            return None
        prefix = "/api/storage/"
        if avatar_url.startswith(prefix):
            return avatar_url[len(prefix) :]
        return None

    @staticmethod
    async def upload_avatar(db: Session, user: User, file: UploadFile) -> User:
        content_type = file.content_type or ""
        extension = AVATAR_ALLOWED_TYPES.get(content_type)
        if not extension:
            raise HTTPException(status_code=400, detail="仅支持 JPG、PNG、WEBP、GIF 格式")

        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="上传文件为空")
        if len(data) > AVATAR_MAX_BYTES:
            raise HTTPException(status_code=400, detail="头像大小不能超过 2MB")

        object_name = f"avatars/{user.id}/{uuid.uuid4().hex}{extension}"
        minio_client.upload_bytes(object_name, data, content_type=content_type)
        avatar_url = minio_client.build_public_url(object_name)

        old_object = UserService._avatar_object_name_from_url(user.avatar)
        user.avatar = avatar_url
        db.commit()
        db.refresh(user)

        if old_object and old_object != object_name:
            try:
                minio_client.delete_file(old_object)
            except Exception:
                pass

        return user

    @staticmethod
    def get_role_applications(db: Session, status: str = None) -> list:
        """获取角色申请列表"""
        from app.entity.db_models import RoleApplication
        query = db.query(RoleApplication)
        if status:
            query = query.filter(RoleApplication.status == status)
        return query.order_by(RoleApplication.applied_at.desc()).all()

    @staticmethod
    def get_user_role_applications(db: Session, user_id: int) -> list:
        """获取用户的角色申请历史"""
        from app.entity.db_models import RoleApplication
        return db.query(RoleApplication).filter(
            RoleApplication.user_id == user_id
        ).order_by(RoleApplication.applied_at.desc()).all()

    @staticmethod
    def approve_role_application(db: Session, application_id: int, approver_id: int, status: str, comment: str = None):
        """审批角色申请"""
        from datetime import datetime
        from fastapi import HTTPException
        from app.entity.db_models import RoleApplication, UserRole
        app = db.query(RoleApplication).filter(RoleApplication.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="申请不存在")
        if app.status != "pending":
            raise HTTPException(status_code=400, detail="该申请已处理")
        app.status = status
        app.approver_id = approver_id
        app.approve_comment = comment
        app.approved_at = datetime.now()
        if status == "approved":
            existing = db.query(UserRole).filter(
                UserRole.user_id == app.user_id, UserRole.role_id == app.role_id
            ).first()
            if not existing:
                db.add(UserRole(user_id=app.user_id, role_id=app.role_id))
        db.commit()
        db.refresh(app)
        return app


user_service = UserService()