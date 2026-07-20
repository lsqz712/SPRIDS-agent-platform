"""
角色与权限服务层
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.entity.db_models import Role, Permission, UserRole, RolePermission


class RoleService:
    @staticmethod
    def get_all_roles(db: Session):
        return db.query(Role).filter(Role.deleted_at.is_(None)).all()

    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> Role:
        role = db.query(Role).filter(Role.id == role_id, Role.deleted_at.is_(None)).first()
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role

    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Role:
        return db.query(Role).filter(Role.name == name, Role.deleted_at.is_(None)).first()

    @staticmethod
    def create_role(db: Session, name: str, display_name: str, description: str = None, permission_codes: list = None) -> Role:
        if RoleService.get_role_by_name(db, name):
            raise HTTPException(status_code=400, detail="角色标识已存在")

        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            is_system=False,
        )
        db.add(role)
        db.commit()
        db.refresh(role)

        if permission_codes:
            RoleService.assign_permissions(db, role.id, permission_codes)

        return role

    @staticmethod
    def update_role(db: Session, role_id: int, updates: dict) -> Role:
        role = RoleService.get_role_by_id(db, role_id)

        if role.is_system:
            raise HTTPException(status_code=403, detail="系统内置角色不允许修改")

        if "name" in updates:
            existing = RoleService.get_role_by_name(db, updates["name"])
            if existing and existing.id != role_id:
                raise HTTPException(status_code=400, detail="角色标识已存在")
            role.name = updates["name"]

        if "display_name" in updates:
            role.display_name = updates["display_name"]

        if "description" in updates:
            role.description = updates["description"]

        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete_role(db: Session, role_id: int) -> None:
        role = RoleService.get_role_by_id(db, role_id)

        if role.is_system:
            raise HTTPException(status_code=403, detail="系统内置角色不允许删除")

        role.deleted_at = __import__('datetime').datetime.now()
        db.commit()

    @staticmethod
    def assign_permissions(db: Session, role_id: int, permission_codes: list) -> Role:
        role = RoleService.get_role_by_id(db, role_id)

        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

        for code in permission_codes:
            permission = PermissionService.get_permission_by_code(db, code)
            if permission:
                rp = RolePermission(role_id=role_id, permission_id=permission.id)
                db.add(rp)

        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def get_role_permissions(db: Session, role_id: int) -> list[Permission]:
        role = RoleService.get_role_by_id(db, role_id)
        return [rp.permission for rp in role.role_permissions]

    @staticmethod
    def get_role_permission_codes(db: Session, role_id: int) -> list[str]:
        return [p.code for p in RoleService.get_role_permissions(db, role_id)]


class PermissionService:
    @staticmethod
    def get_all_permissions(db: Session):
        return db.query(Permission).all()

    @staticmethod
    def get_permission_by_id(db: Session, permission_id: int) -> Permission:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise HTTPException(status_code=404, detail="权限不存在")
        return permission

    @staticmethod
    def get_permission_by_code(db: Session, code: str) -> Permission:
        return db.query(Permission).filter(Permission.code == code).first()

    @staticmethod
    def create_permission(db: Session, code: str, name: str, module: str, description: str = None) -> Permission:
        if PermissionService.get_permission_by_code(db, code):
            raise HTTPException(status_code=400, detail="权限编码已存在")

        permission = Permission(
            code=code,
            name=name,
            module=module,
            description=description,
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission

    @staticmethod
    def create_permissions(db: Session, permissions: list[dict]) -> list[Permission]:
        created = []
        for p in permissions:
            existing = PermissionService.get_permission_by_code(db, p["code"])
            if not existing:
                permission = Permission(**p)
                db.add(permission)
                created.append(permission)
        db.commit()
        for p in created:
            db.refresh(p)
        return created

    @staticmethod
    def update_permission(db: Session, permission_id: int, updates: dict) -> Permission:
        permission = PermissionService.get_permission_by_id(db, permission_id)

        if "code" in updates:
            existing = PermissionService.get_permission_by_code(db, updates["code"])
            if existing and existing.id != permission_id:
                raise HTTPException(status_code=400, detail="权限编码已存在")
            permission.code = updates["code"]

        if "name" in updates:
            permission.name = updates["name"]

        if "module" in updates:
            permission.module = updates["module"]

        if "description" in updates:
            permission.description = updates["description"]

        db.commit()
        db.refresh(permission)
        return permission

    @staticmethod
    def delete_permission(db: Session, permission_id: int) -> None:
        permission = PermissionService.get_permission_by_id(db, permission_id)
        db.delete(permission)
        db.commit()


class UserRoleService:
    @staticmethod
    def assign_role_to_user(db: Session, user_id: int, role_id: int) -> None:
        existing = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).first()
        if not existing:
            ur = UserRole(user_id=user_id, role_id=role_id)
            db.add(ur)
            db.commit()

    @staticmethod
    def remove_role_from_user(db: Session, user_id: int, role_id: int) -> None:
        ur = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).first()
        if ur:
            db.delete(ur)
            db.commit()

    @staticmethod
    def get_user_roles(db: Session, user_id: int) -> list[Role]:
        user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
        role_ids = [ur.role_id for ur in user_roles]
        return db.query(Role).filter(
            Role.id.in_(role_ids),
            Role.deleted_at.is_(None)
        ).all()

    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> list[Permission]:
        user_roles = UserRoleService.get_user_roles(db, user_id)
        role_ids = [r.id for r in user_roles]

        role_permissions = db.query(RolePermission).filter(
            RolePermission.role_id.in_(role_ids)
        ).all()
        permission_ids = [rp.permission_id for rp in role_permissions]

        return db.query(Permission).filter(Permission.id.in_(permission_ids)).all()

    @staticmethod
    def get_user_permission_codes(db: Session, user_id: int) -> list[str]:
        permissions = UserRoleService.get_user_permissions(db, user_id)
        return [p.code for p in permissions]

    @staticmethod
    def has_permission(db: Session, user_id: int, permission_code: str) -> bool:
        if permission_code is None:
            return True

        permissions = UserRoleService.get_user_permission_codes(db, user_id)
        return permission_code in permissions


role_service = RoleService()
permission_service = PermissionService()
user_role_service = UserRoleService()
