# app/services/project_service.py - 项目服务
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.crud.rbac import project_crud
from app.schemas.rbac import ProjectCreate, ProjectUpdate
from app.models.rbac import Project


class ProjectService:
    """项目服务"""

    async def get_project(self, db: AsyncSession, project_id: str) -> Optional[Project]:
        """获取项目"""
        try:
            project_uuid = uuid.UUID(project_id)
            return await project_crud.get(db, id=project_uuid)
        except ValueError:
            return None

    async def get_project_by_code(self, db: AsyncSession, code: str) -> Optional[Project]:
        """根据代码获取项目"""
        return await project_crud.get_by_code(db, code=code)

    async def create_project(self, db: AsyncSession, project_create: ProjectCreate) -> Project:
        """创建项目"""
        # 检查代码唯一性
        existing_project = await project_crud.get_by_code(db, code=project_create.code)
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project code already exists"
            )

        return await project_crud.create(db, obj_in=project_create)

    async def update_project(self, db: AsyncSession, project_id: str, project_update: ProjectUpdate) -> Project:
        """更新项目"""
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID format"
            )

        project = await project_crud.get(db, id=project_uuid)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        return await project_crud.update(db, db_obj=project, obj_in=project_update)

    async def delete_project(self, db: AsyncSession, project_id: str) -> bool:
        """删除项目"""
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            return False

        project = await project_crud.get(db, id=project_uuid)
        if not project:
            return False

        await project_crud.remove(db, id=project_uuid)
        return True

    async def get_projects(
            self,
            db: AsyncSession,
            skip: int = 0,
            limit: int = 50,
            is_active: bool = None
    ) -> Tuple[List[Project], int]:
        """获取项目列表"""
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active

        projects = await project_crud.get_multi(db, skip=skip, limit=limit, filters=filters)
        total = await project_crud.count(db, filters=filters)

        return projects, total