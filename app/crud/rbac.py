# app/crud/rbac.py
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from app.crud.base import CRUDBase
from app.models.rbac import Project, Role, Permission, RolePermission, UserRole
from app.schemas.rbac import ProjectCreate, ProjectUpdate, RoleCreate, RoleUpdate, PermissionCreate


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Project]:
        """根据代码获取项目"""
        stmt = select(Project).where(Project.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    async def get_by_code(self, db: AsyncSession, *, code: str, project_id: Optional[uuid.UUID] = None) -> Optional[
        Role]:
        """根据代码获取角色"""
        conditions = [Role.code == code]
        if project_id:
            conditions.append(Role.project_id == project_id)
        else:
            conditions.append(Role.project_id.is_(None))

        stmt = select(Role).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_global_roles(self, db: AsyncSession) -> List[Role]:
        """获取全局角色"""
        stmt = select(Role).where(Role.project_id.is_(None))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_project_roles(self, db: AsyncSession, *, project_id: uuid.UUID) -> List[Role]:
        """获取项目角色"""
        stmt = select(Role).where(Role.project_id == project_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_roles(self, db: AsyncSession, *, user_id: uuid.UUID, project_id: Optional[uuid.UUID] = None) -> \
    List[Role]:
        """获取用户角色"""
        stmt = select(Role).join(UserRole).where(UserRole.user_id == user_id)

        if project_id:
            stmt = stmt.where(UserRole.project_id == project_id)

        stmt = stmt.where(UserRole.is_active == True)

        result = await db.execute(stmt)
        return result.scalars().all()


class CRUDPermission(CRUDBase[Permission, PermissionCreate, dict]):
    async def get_role_permissions(self, db: AsyncSession, *, role_id: uuid.UUID) -> List[Permission]:
        """获取角色权限"""
        stmt = select(Permission).join(RolePermission).where(RolePermission.role_id == role_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_project_permissions(self, db: AsyncSession, *, project_id: uuid.UUID) -> List[Permission]:
        """获取项目权限"""
        stmt = select(Permission).where(Permission.project_id == project_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_permissions(self, db: AsyncSession, *, user_id: uuid.UUID,
                                   project_id: Optional[uuid.UUID] = None) -> List[Permission]:
        """获取用户权限"""
        stmt = (
            select(Permission)
            .join(RolePermission)
            .join(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
            .where(UserRole.is_active == True)
        )

        if project_id:
            stmt = stmt.where(
                or_(
                    UserRole.project_id == project_id,
                    UserRole.project_id.is_(None)  # 全局角色
                )
            )

        result = await db.execute(stmt)
        return result.scalars().all()


class CRUDRolePermission(CRUDBase[RolePermission, dict, dict]):
    async def assign_permissions_to_role(
            self,
            db: AsyncSession,
            *,
            role_id: uuid.UUID,
            permission_ids: List[uuid.UUID]
    ) -> List[RolePermission]:
        """为角色分配权限"""
        # 先删除现有权限
        await self.remove_all_role_permissions(db, role_id=role_id)

        # 添加新权限
        role_permissions = []
        for permission_id in permission_ids:
            role_permission = RolePermission(
                id=uuid.uuid4(),
                role_id=role_id,
                permission_id=permission_id
            )
            db.add(role_permission)
            role_permissions.append(role_permission)

        await db.commit()
        return role_permissions

    async def remove_all_role_permissions(self, db: AsyncSession, *, role_id: uuid.UUID) -> int:
        """删除角色的所有权限"""
        stmt = delete(RolePermission).where(RolePermission.role_id == role_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


class CRUDUserRole(CRUDBase[UserRole, dict, dict]):
    async def get_user_roles(
            self,
            db: AsyncSession,
            *,
            user_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None,
            active_only: bool = True
    ) -> List[UserRole]:
        """获取用户的所有角色关系"""
        conditions = [UserRole.user_id == user_id]

        if project_id:
            conditions.append(UserRole.project_id == project_id)

        if active_only:
            conditions.append(UserRole.is_active == True)

        stmt = select(UserRole).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def assign_role_to_user(
            self,
            db: AsyncSession,
            *,
            user_id: uuid.UUID,
            role_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None,
            granted_by: Optional[uuid.UUID] = None,
            expires_at: Optional[datetime] = None
    ) -> UserRole:
        """为用户分配角色"""
        # 检查是否已存在相同的角色分配
        existing = await self.get_user_role_assignment(
            db, user_id=user_id, role_id=role_id, project_id=project_id
        )

        if existing:
            # 如果存在但不活跃，重新激活
            if not existing.is_active:
                existing.is_active = True
                existing.granted_by = granted_by
                existing.granted_at = datetime.utcnow()
                existing.expires_at = expires_at
                await db.commit()
                return existing
            else:
                raise ValueError("User already has this role")

        # 创建新的角色分配
        user_role = UserRole(
            id=uuid.uuid4(),
            user_id=user_id,
            role_id=role_id,
            project_id=project_id,
            granted_by=granted_by,
            expires_at=expires_at
        )
        db.add(user_role)
        await db.commit()
        await db.refresh(user_role)
        return user_role

    async def get_user_role_assignment(
            self,
            db: AsyncSession,
            *,
            user_id: uuid.UUID,
            role_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None
    ) -> Optional[UserRole]:
        """获取特定的用户角色分配"""
        conditions = [
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ]

        if project_id:
            conditions.append(UserRole.project_id == project_id)
        else:
            conditions.append(UserRole.project_id.is_(None))

        stmt = select(UserRole).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# 创建实例
project_crud = CRUDProject(Project)
role_crud = CRUDRole(Role)
permission_crud = CRUDPermission(Permission)
role_permission_crud = CRUDRolePermission(RolePermission)
user_role_crud = CRUDUserRole(UserRole)