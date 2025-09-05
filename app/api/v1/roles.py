# app/api/v1/roles.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.common import BaseResponse
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, UserRoleAssign
from app.dependencies import get_current_active_user, get_current_superuser
from app.services.rbac_service import RBACService
from app.crud.rbac import role_crud, user_role_crud
from app.models.user import User
import uuid

router = APIRouter()
rbac_service = RBACService()


@router.get("", response_model=BaseResponse[List[RoleResponse]])
async def get_roles(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        project_id: Optional[str] = Query(None)
):
    """获取角色列表"""
    try:
        project_uuid = None
        if project_id:
            project_uuid = uuid.UUID(project_id)

        if project_uuid:
            roles = await role_crud.get_project_roles(db, project_id=project_uuid)
        else:
            roles = await role_crud.get_global_roles(db)

        # 应用分页
        total = len(roles)
        roles = roles[skip:skip + limit]

        role_responses = []
        for role in roles:
            role_responses.append(RoleResponse(
                id=str(role.id),
                name=role.name,
                code=role.code,
                description=role.description,
                project_id=str(role.project_id) if role.project_id else None,
                is_system=role.is_system,
                created_at=role.created_at
            ))

        return BaseResponse(
            success=True,
            message="Roles retrieved successfully",
            data=role_responses
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get roles: {str(e)}"
        )


@router.post("", response_model=BaseResponse[RoleResponse])
async def create_role(
        role_data: RoleCreate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """创建角色"""
    try:
        # 检查角色代码是否已存在
        project_uuid = None
        if role_data.project_id:
            project_uuid = uuid.UUID(role_data.project_id)

        existing_role = await role_crud.get_by_code(
            db, code=role_data.code, project_id=project_uuid
        )
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role code already exists"
            )

        # 创建角色
        role_create_data = role_data.model_dump()
        role_create_data["id"] = uuid.uuid4()
        if project_uuid:
            role_create_data["project_id"] = project_uuid

        role = await role_crud.create(db, obj_in=role_create_data)

        role_response = RoleResponse(
            id=str(role.id),
            name=role.name,
            code=role.code,
            description=role.description,
            project_id=str(role.project_id) if role.project_id else None,
            is_system=role.is_system,
            created_at=role.created_at
        )

        return BaseResponse(
            success=True,
            message="Role created successfully",
            data=role_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}"
        )


@router.get("/{role_id}", response_model=BaseResponse[RoleResponse])
async def get_role(
        role_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """获取角色详情"""
    try:
        role_uuid = uuid.UUID(role_id)
        role = await role_crud.get(db, id=role_uuid)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        role_response = RoleResponse(
            id=str(role.id),
            name=role.name,
            code=role.code,
            description=role.description,
            project_id=str(role.project_id) if role.project_id else None,
            is_system=role.is_system,
            created_at=role.created_at
        )

        return BaseResponse(
            success=True,
            message="Role retrieved successfully",
            data=role_response
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role: {str(e)}"
        )


@router.put("/{role_id}", response_model=BaseResponse[RoleResponse])
async def update_role(
        role_id: str,
        role_data: RoleUpdate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """更新角色"""
    try:
        role_uuid = uuid.UUID(role_id)
        role = await role_crud.get(db, id=role_uuid)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        updated_role = await role_crud.update(db, db_obj=role, obj_in=role_data)

        role_response = RoleResponse(
            id=str(updated_role.id),
            name=updated_role.name,
            code=updated_role.code,
            description=updated_role.description,
            project_id=str(updated_role.project_id) if updated_role.project_id else None,
            is_system=updated_role.is_system,
            created_at=updated_role.created_at
        )

        return BaseResponse(
            success=True,
            message="Role updated successfully",
            data=role_response
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}"
        )


@router.delete("/{role_id}", response_model=BaseResponse[str])
async def delete_role(
        role_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """删除角色"""
    try:
        role_uuid = uuid.UUID(role_id)
        role = await role_crud.get(db, id=role_uuid)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system role"
            )

        await role_crud.remove(db, id=role_uuid)

        return BaseResponse(
            success=True,
            message="Role deleted successfully",
            data="success"
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role: {str(e)}"
        )


@router.post("/assign", response_model=BaseResponse[str])
async def assign_role_to_user(
        assign_data: UserRoleAssign,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """为用户分配角色"""
    try:
        user_uuid = uuid.UUID(assign_data.user_id)
        role_uuid = uuid.UUID(assign_data.role_id)
        project_uuid = None
        if assign_data.project_id:
            project_uuid = uuid.UUID(assign_data.project_id)

        await rbac_service.assign_role_to_user(
            db=db,
            user_id=user_uuid,
            role_id=role_uuid,
            project_id=project_uuid,
            granted_by=current_user.id,
            expires_at=assign_data.expires_at
        )

        return BaseResponse(
            success=True,
            message="Role assigned successfully",
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
            detail=f"Failed to assign role: {str(e)}"
        )