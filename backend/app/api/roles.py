"""
角色与权限管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, check_permission
from app.api.utils import success_response
from app.entity.db_models import User
from app.entity.schemas import (
    RoleApplicationApprove,
    RoleApplicationResponse,
    RoleCreate,
    RoleResponse,
    PermissionResponse,
)
from app.services.role_service import (
    role_service,
    permission_service,
    user_role_service,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/api/roles", tags=["角色与权限"])


def serialize_role(role, permissions: list[str] = None) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "display_name": role.display_name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": permissions or [],
        "created_at": role.created_at,
    }


def serialize_permission(permission) -> dict:
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "module": permission.module,
        "description": permission.description,
    }


@router.get("/", dependencies=[Depends(check_permission("role:read"))])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    roles = role_service.get_all_roles(db)
    result = []
    for role in roles:
        permissions = role_service.get_role_permission_codes(db, role.id)
        result.append(serialize_role(role, permissions))
    return success_response(data=result)


@router.get("/applications/")
async def list_role_applications(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限查看角色申请")

    applications = user_service.get_role_applications(db, status)
    result = []
    for app in applications:
        result.append({
            "id": app.id,
            "user_id": app.user_id,
            "username": app.user.username,
            "email": app.user.email,
            "role_id": app.role_id,
            "role_name": app.role.name,
            "role_display_name": app.role.display_name,
            "status": app.status,
            "approver_id": app.approver_id,
            "approver_name": app.approver.username if app.approver else None,
            "approve_comment": app.approve_comment,
            "applied_at": app.applied_at,
            "approved_at": app.approved_at,
        })
    return success_response(data=result)


@router.get("/applications/{application_id}")
async def get_role_application_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from app.entity.db_models import RoleApplication
    
    application = db.query(RoleApplication).filter(RoleApplication.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")

    if not current_user.is_superuser and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此申请")

    return success_response(data={
        "id": application.id,
        "user_id": application.user_id,
        "username": application.user.username,
        "email": application.user.email,
        "role_id": application.role_id,
        "role_name": application.role.name,
        "role_display_name": application.role.display_name,
        "status": application.status,
        "approver_id": application.approver_id,
        "approver_name": application.approver.username if application.approver else None,
        "approve_comment": application.approve_comment,
        "applied_at": application.applied_at,
        "approved_at": application.approved_at,
    })


@router.post("/applications/{application_id}/approve")
async def approve_role_application(
    application_id: int,
    request: RoleApplicationApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限审批角色申请")

    application = user_service.approve_role_application(
        db=db,
        application_id=application_id,
        approver_id=current_user.id,
        status=request.status,
        comment=request.comment,
    )

    message = "审批通过" if request.status == "approved" else "已拒绝"
    return success_response(data={
        "id": application.id,
        "user_id": application.user_id,
        "role_id": application.role_id,
        "status": application.status,
        "approver_id": application.approver_id,
        "approve_comment": application.approve_comment,
        "approved_at": application.approved_at,
    }, message=message)


@router.get("/me/applications")
async def get_my_role_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    applications = user_service.get_user_role_applications(db, current_user.id)
    result = []
    for app in applications:
        result.append({
            "id": app.id,
            "user_id": app.user_id,
            "username": app.user.username,
            "email": app.user.email,
            "role_id": app.role_id,
            "role_name": app.role.name,
            "role_display_name": app.role.display_name,
            "status": app.status,
            "approver_id": app.approver_id,
            "approver_name": app.approver.username if app.approver else None,
            "approve_comment": app.approve_comment,
            "applied_at": app.applied_at,
            "approved_at": app.approved_at,
        })
    return success_response(data=result)


@router.get("/{role_id}", dependencies=[Depends(check_permission("role:read"))])
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    role = role_service.get_role_by_id(db, role_id)
    permissions = role_service.get_role_permission_codes(db, role_id)
    return success_response(data=serialize_role(role, permissions))


@router.post("/", status_code=201)
async def create_role(
    request: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限创建角色")

    role = role_service.create_role(
        db=db,
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        permission_codes=request.permission_codes,
    )
    permissions = role_service.get_role_permission_codes(db, role.id)
    return success_response(data=serialize_role(role, permissions), message="角色创建成功")


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    request: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限修改角色")

    updates = {
        "name": request.name,
        "display_name": request.display_name,
        "description": request.description,
    }
    role = role_service.update_role(db, role_id, updates)

    if request.permission_codes:
        role = role_service.assign_permissions(db, role_id, request.permission_codes)

    permissions = role_service.get_role_permission_codes(db, role.id)
    return success_response(data=serialize_role(role, permissions), message="角色更新成功")


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限删除角色")

    role_service.delete_role(db, role_id)
    return success_response(message="角色删除成功")


@router.post("/{role_id}/permissions")
async def assign_permissions_to_role(
    role_id: int,
    permission_codes: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限分配权限")

    role = role_service.assign_permissions(db, role_id, permission_codes)
    permissions = role_service.get_role_permission_codes(db, role_id)
    return success_response(data=serialize_role(role, permissions), message="权限分配成功")


@router.get("/{role_id}/permissions")
async def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    permissions = role_service.get_role_permissions(db, role_id)
    return success_response(data=[serialize_permission(p) for p in permissions])


@router.get("/permissions/")
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    permissions = permission_service.get_all_permissions(db)
    return success_response(data=[serialize_permission(p) for p in permissions])


@router.post("/permissions/", status_code=201)
async def create_permission(
    code: str,
    name: str,
    module: str,
    description: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限创建权限")

    permission = permission_service.create_permission(db, code, name, module, description)
    return success_response(data=serialize_permission(permission), message="权限创建成功")


@router.put("/permissions/{permission_id}")
async def update_permission(
    permission_id: int,
    code: str = None,
    name: str = None,
    module: str = None,
    description: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限修改权限")

    updates = {}
    if code is not None:
        updates["code"] = code
    if name is not None:
        updates["name"] = name
    if module is not None:
        updates["module"] = module
    if description is not None:
        updates["description"] = description

    permission = permission_service.update_permission(db, permission_id, updates)
    return success_response(data=serialize_permission(permission), message="权限更新成功")


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限删除权限")

    permission_service.delete_permission(db, permission_id)
    return success_response(message="权限删除成功")


@router.post("/users/{user_id}/assign")
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限分配角色")

    user_role_service.assign_role_to_user(db, user_id, role_id)
    return success_response(message="角色分配成功")


@router.post("/users/{user_id}/remove")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权限移除角色")

    user_role_service.remove_role_from_user(db, user_id, role_id)
    return success_response(message="角色移除成功")


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权限查看其他用户角色")

    roles = user_role_service.get_user_roles(db, user_id)
    result = []
    for role in roles:
        permissions = role_service.get_role_permission_codes(db, role.id)
        result.append(serialize_role(role, permissions))
    return success_response(data=result)


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权限查看其他用户权限")

    permissions = user_role_service.get_user_permissions(db, user_id)
    return success_response(data=[serialize_permission(p) for p in permissions])
