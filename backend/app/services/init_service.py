"""
系统初始化服务 - 初始化内置角色和权限
"""
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.entity.db_models import Role, Permission, UserRole, RolePermission, User
from app.services.role_service import role_service, permission_service


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@sprids.com"
DEFAULT_ADMIN_PASSWORD = "admin123"


PERMISSIONS = [
    {"code": "user:create", "name": "创建用户", "module": "用户管理", "description": "创建新用户账户"},
    {"code": "user:read", "name": "查看用户", "module": "用户管理", "description": "查看用户列表和详情"},
    {"code": "user:update", "name": "更新用户", "module": "用户管理", "description": "更新用户信息"},
    {"code": "user:delete", "name": "删除用户", "module": "用户管理", "description": "删除用户账户"},
    {"code": "user:disable", "name": "禁用用户", "module": "用户管理", "description": "禁用/启用用户账户"},

    {"code": "role:create", "name": "创建角色", "module": "角色管理", "description": "创建新角色"},
    {"code": "role:read", "name": "查看角色", "module": "角色管理", "description": "查看角色列表和详情"},
    {"code": "role:update", "name": "更新角色", "module": "角色管理", "description": "更新角色信息"},
    {"code": "role:delete", "name": "删除角色", "module": "角色管理", "description": "删除角色"},
    {"code": "role:assign", "name": "分配角色", "module": "角色管理", "description": "为用户分配/移除角色"},

    {"code": "permission:create", "name": "创建权限", "module": "权限管理", "description": "创建新权限"},
    {"code": "permission:read", "name": "查看权限", "module": "权限管理", "description": "查看权限列表"},
    {"code": "permission:update", "name": "更新权限", "module": "权限管理", "description": "更新权限信息"},
    {"code": "permission:delete", "name": "删除权限", "module": "权限管理", "description": "删除权限"},

    {"code": "detection:create", "name": "创建检测任务", "module": "检测业务", "description": "创建单图/批量检测任务"},
    {"code": "detection:read", "name": "查看检测结果", "module": "检测业务", "description": "查看检测任务和结果"},
    {"code": "detection:delete", "name": "删除检测任务", "module": "检测业务", "description": "删除检测任务"},
    {"code": "detection:review", "name": "人工复判", "module": "检测业务", "description": "对检测结果进行人工复判"},
    {"code": "detection:camera", "name": "摄像头检测", "module": "检测业务", "description": "使用摄像头进行实时检测"},
    {"code": "detection:video", "name": "视频检测", "module": "检测业务", "description": "对视频文件进行检测"},

    {"code": "scene:create", "name": "创建检测场景", "module": "场景管理", "description": "创建新的检测场景"},
    {"code": "scene:read", "name": "查看检测场景", "module": "场景管理", "description": "查看检测场景列表"},
    {"code": "scene:update", "name": "更新检测场景", "module": "场景管理", "description": "更新检测场景信息"},
    {"code": "scene:delete", "name": "删除检测场景", "module": "场景管理", "description": "删除检测场景"},

    {"code": "model:create", "name": "创建模型版本", "module": "模型管理", "description": "创建新的模型版本"},
    {"code": "model:read", "name": "查看模型版本", "module": "模型管理", "description": "查看模型版本列表"},
    {"code": "model:update", "name": "更新模型版本", "module": "模型管理", "description": "更新模型版本信息"},
    {"code": "model:delete", "name": "删除模型版本", "module": "模型管理", "description": "删除模型版本"},
    {"code": "model:train", "name": "训练模型", "module": "模型管理", "description": "发起模型训练任务"},

    {"code": "dataset:create", "name": "创建数据集", "module": "数据集管理", "description": "创建新的数据集版本"},
    {"code": "dataset:read", "name": "查看数据集", "module": "数据集管理", "description": "查看数据集列表"},
    {"code": "dataset:update", "name": "更新数据集", "module": "数据集管理", "description": "更新数据集信息"},
    {"code": "dataset:delete", "name": "删除数据集", "module": "数据集管理", "description": "删除数据集"},

    {"code": "statistics:read", "name": "查看统计信息", "module": "统计分析", "description": "查看检测统计和报告"},

    {"code": "system:config", "name": "系统配置", "module": "系统运维", "description": "修改系统配置"},
    {"code": "system:log", "name": "查看操作日志", "module": "系统运维", "description": "查看系统操作日志"},
]


ROLES = [
    {
        "name": "admin",
        "display_name": "管理员",
        "description": "系统全部权限，包括用户管理、角色分配、系统配置",
        "is_system": True,
    },
    {
        "name": "operator",
        "display_name": "质检操作员",
        "description": "执行PCB检测任务、查看检测结果、进行人工复判",
        "is_system": True,
    },
    {
        "name": "engineer",
        "display_name": "数据工程师",
        "description": "管理数据集、发起模型训练、管理模型版本",
        "is_system": True,
    },
    {
        "name": "viewer",
        "display_name": "普通访客",
        "description": "仅可查看检测报告与统计信息，无操作权限",
        "is_system": True,
    },
]


ROLE_PERMISSIONS = {
    "admin": [
        "user:create", "user:read", "user:update", "user:delete", "user:disable",
        "role:create", "role:read", "role:update", "role:delete", "role:assign",
        "permission:create", "permission:read", "permission:update", "permission:delete",
        "detection:create", "detection:read", "detection:delete", "detection:review", "detection:camera", "detection:video",
        "scene:create", "scene:read", "scene:update", "scene:delete",
        "model:create", "model:read", "model:update", "model:delete", "model:train",
        "dataset:create", "dataset:read", "dataset:update", "dataset:delete",
        "statistics:read",
        "system:config", "system:log",
    ],
    "operator": [
        "detection:create", "detection:read", "detection:review", "detection:camera", "detection:video",
        "scene:read",
        "model:read",
        "statistics:read",
    ],
    "engineer": [
        "detection:read",
        "scene:create", "scene:read", "scene:update", "scene:delete",
        "model:create", "model:read", "model:update", "model:delete", "model:train",
        "dataset:create", "dataset:read", "dataset:update", "dataset:delete",
        "statistics:read",
    ],
    "viewer": [
        "detection:read",
        "scene:read",
        "model:read",
        "statistics:read",
    ],
}


class InitService:
    @staticmethod
    def init_permissions(db: Session) -> int:
        created = permission_service.create_permissions(db, PERMISSIONS)
        return len(created)

    @staticmethod
    def init_roles(db: Session) -> int:
        created_count = 0
        for role_data in ROLES:
            existing = role_service.get_role_by_name(db, role_data["name"])
            if not existing:
                role = Role(**role_data)
                db.add(role)
                created_count += 1
        db.commit()
        return created_count

    @staticmethod
    def init_role_permissions(db: Session) -> int:
        created_count = 0
        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            role = role_service.get_role_by_name(db, role_name)
            if not role:
                continue

            existing_codes = role_service.get_role_permission_codes(db, role.id)
            missing_codes = [code for code in permission_codes if code not in existing_codes]

            if missing_codes:
                for code in missing_codes:
                    permission = permission_service.get_permission_by_code(db, code)
                    if permission:
                        rp = RolePermission(role_id=role.id, permission_id=permission.id)
                        db.add(rp)
                        created_count += 1

        if created_count > 0:
            db.commit()
        return created_count

    @staticmethod
    def init_all(db: Session) -> dict:
        result = {}

        # 一键修复：存量用户自动审批 + 分配 viewer 角色
        from sqlalchemy import update
        users_to_fix = db.query(User).filter(
            (User.is_approved == False) | (User.is_approved == None)
        ).all()
        for user in users_to_fix:
            user.is_approved = True
        if users_to_fix:
            db.commit()
            result["existing_users_approved"] = len(users_to_fix)

        # 存量用户：没有角色的自动分配 viewer
        viewer_role = role_service.get_role_by_name(db, "viewer")
        if viewer_role:
            unassigned = db.query(User).filter(
                ~User.user_roles.any()
            ).all()
            for user in unassigned:
                db.add(UserRole(user_id=user.id, role_id=viewer_role.id))
            if unassigned:
                db.commit()
                result["viewer_assigned"] = len(unassigned)

        perm_count = InitService.init_permissions(db)
        result["permissions_created"] = perm_count

        role_count = InitService.init_roles(db)
        result["roles_created"] = role_count

        rp_count = InitService.init_role_permissions(db)
        result["role_permissions_created"] = rp_count

        admin_created = InitService.init_default_admin(db)
        result["admin_created"] = admin_created

        return result

    @staticmethod
    def init_default_admin(db: Session) -> bool:
        existing = db.query(User).filter(
            (User.username == DEFAULT_ADMIN_USERNAME) | (User.email == DEFAULT_ADMIN_EMAIL)
        ).first()
        
        if existing:
            return False
        
        admin_role = role_service.get_role_by_name(db, "admin")
        if not admin_role:
            return False
        
        admin_user = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True,
            is_approved=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        ur = UserRole(user_id=admin_user.id, role_id=admin_role.id)
        db.add(ur)
        db.commit()
        
        return True


init_service = InitService()
