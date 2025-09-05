# app/api/v1/permissions.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.common import BaseResponse
from app.schemas.rbac import PermissionResponse, RolePermissionAssign
from app.dependencies import get_current_active_user, get_current_superuser
from app.crud.rbac import permission_crud, role_permission_crud
from app.models.user import User
import uuid

router = APIRouter()


@router.get("", response_model=BaseResponse[List[PermissionResponse]])
async def get_permissions(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user),
        project_id: Optional[str] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100)
):
    """获取权限列表"""
    try:
        if project_id:
            project_uuid = uuid.UUID(project_id)
            permissions = await permission_crud.get_project_permissions(db, project_id=project_uuid)
        else:
            permissions = await permission_crud.get_multi(db, skip=skip, limit=limit)

        # 应用分页
        total = len(permissions)
        permissions = permissions[skip:skip + limit]

        permission_responses = []
        for perm in permissions:
            permission_responses.append(PermissionResponse(
                id=str(perm.id),
                name=perm.name,
                code=perm.code,
                description=perm.description,
                resource_type=perm.resource_type,
                action=perm.action,
                project_id=str(perm.project_id),
                created_at=perm.created_at
            ))

        return BaseResponse(
            success=True,
            message="Permissions retrieved successfully",
            data=permission_responses
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get permissions: {str(e)}"
        )


@router.get("/role/{role_id}", response_model=BaseResponse[List[PermissionResponse]])
async def get_role_permissions(
        role_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """获取角色的权限"""
    try:
        role_uuid = uuid.UUID(role_id)
        permissions = await permission_crud.get_role_permissions(db, role_id=role_uuid)

        permission_responses = []
        for perm in permissions:
            permission_responses.append(PermissionResponse(
                id=str(perm.id),
                name=perm.name,
                code=perm.code,
                description=perm.description,
                resource_type=perm.resource_type,
                action=perm.action,
                project_id=str(perm.project_id),
                created_at=perm.created_at
            ))

        return BaseResponse(
            success=True,
            message="Role permissions retrieved successfully",
            data=permission_responses
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role permissions: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=BaseResponse[List[PermissionResponse]])
async def get_user_permissions(
        user_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user),
        project_id: Optional[str] = Query(None)
):
    """获取用户的权限"""
    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = None
        if project_id:
            project_uuid = uuid.UUID(project_id)

        # 检查权限：只能查看自己的权限，或者管理员可以查看所有人
        if str(current_user.id) != user_id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )

        permissions = await permission_crud.get_user_permissions(
            db, user_id=user_uuid, project_id=project_uuid
        )

        permission_responses = []
        for perm in permissions:
            permission_responses.append(PermissionResponse(
                id=str(perm.id),
                name=perm.name,
                code=perm.code,
                description=perm.description,
                resource_type=perm.resource_type,
                action=perm.action,
                project_id=str(perm.project_id),
                created_at=perm.created_at
            ))

        return BaseResponse(
            success=True,
            message="User permissions retrieved successfully",
            data=permission_responses
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user permissions: {str(e)}"
        )


@router.post("/assign", response_model=BaseResponse[str])
async def assign_permissions_to_role(
        assign_data: RolePermissionAssign,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """为角色分配权限"""
    try:
        role_uuid = uuid.UUID(assign_data.role_id)
        permission_uuids = [uuid.UUID(pid) for pid in assign_data.permission_ids]

        await role_permission_crud.assign_permissions_to_role(
            db, role_id=role_uuid, permission_ids=permission_uuids
        )

        return BaseResponse(
            success=True,
            message="Permissions assigned successfully",
            data="success"
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign permissions: {str(e)}"
        )