# app/api/v1/projects.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.common import BaseResponse
from app.schemas.rbac import ProjectCreate, ProjectUpdate, ProjectResponse
from app.dependencies import get_current_active_user, get_current_superuser
from app.crud.rbac import project_crud
from app.models.user import User
import uuid

router = APIRouter()


@router.get("", response_model=BaseResponse[List[ProjectResponse]])
async def get_projects(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        is_active: Optional[bool] = Query(None)
):
    """获取项目列表"""
    try:
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active

        projects = await project_crud.get_multi(db, skip=skip, limit=limit, filters=filters)
        total = await project_crud.count(db, filters=filters)

        project_responses = []
        for project in projects:
            project_responses.append(ProjectResponse(
                id=str(project.id),
                name=project.name,
                code=project.code,
                description=project.description,
                base_url=project.base_url,
                is_active=project.is_active,
                created_at=project.created_at
            ))

        return BaseResponse(
            success=True,
            message="Projects retrieved successfully",
            data=project_responses
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get projects: {str(e)}"
        )


@router.post("", response_model=BaseResponse[ProjectResponse])
async def create_project(
        project_data: ProjectCreate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """创建项目"""
    try:
        # 检查项目代码是否已存在
        existing_project = await project_crud.get_by_code(db, code=project_data.code)
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project code already exists"
            )

        # 创建项目
        project_create_data = project_data.model_dump()
        project_create_data["id"] = uuid.uuid4()

        project = await project_crud.create(db, obj_in=project_create_data)

        project_response = ProjectResponse(
            id=str(project.id),
            name=project.name,
            code=project.code,
            description=project.description,
            base_url=project.base_url,
            is_active=project.is_active,
            created_at=project.created_at
        )

        return BaseResponse(
            success=True,
            message="Project created successfully",
            data=project_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/{project_id}", response_model=BaseResponse[ProjectResponse])
async def get_project(
        project_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """获取项目详情"""
    try:
        project_uuid = uuid.UUID(project_id)
        project = await project_crud.get(db, id=project_uuid)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        project_response = ProjectResponse(
            id=str(project.id),
            name=project.name,
            code=project.code,
            description=project.description,
            base_url=project.base_url,
            is_active=project.is_active,
            created_at=project.created_at
        )

        return BaseResponse(
            success=True,
            message="Project retrieved successfully",
            data=project_response
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put("/{project_id}", response_model=BaseResponse[ProjectResponse])
async def update_project(
        project_id: str,
        project_data: ProjectUpdate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """更新项目"""
    try:
        project_uuid = uuid.UUID(project_id)
        project = await project_crud.get(db, id=project_uuid)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        updated_project = await project_crud.update(db, db_obj=project, obj_in=project_data)

        project_response = ProjectResponse(
            id=str(updated_project.id),
            name=updated_project.name,
            code=updated_project.code,
            description=updated_project.description,
            base_url=updated_project.base_url,
            is_active=updated_project.is_active,
            created_at=updated_project.created_at
        )

        return BaseResponse(
            success=True,
            message="Project updated successfully",
            data=project_response
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", response_model=BaseResponse[str])
async def delete_project(
        project_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_superuser)
):
    """删除项目"""
    try:
        project_uuid = uuid.UUID(project_id)
        project = await project_crud.get(db, id=project_uuid)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        await project_crud.remove(db, id=project_uuid)

        return BaseResponse(
            success=True,
            message="Project deleted successfully",
            data="success"
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )