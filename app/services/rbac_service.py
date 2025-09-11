# app/services/rbac_service.py - RBAC权限服务
from datetime import datetime
import uuid
from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_
from app.models.rbac import Role, Permission, UserRole, RolePermission
from app.crud.rbac import role_crud, permission_crud, user_role_crud
from app.core.cache import cache_manager, settings


class RBACService:
    """RBAC权限服务"""

    async def get_user_permissions(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None
    ) -> Set[str]:
        """获取用户权限"""
        cache_key = f"user_permissions:{user_id}:{project_id or 'global'}"

        # 尝试从缓存获取
        cached_permissions = await cache_manager.get(cache_key)
        if cached_permissions:
            return set(cached_permissions)

        # 从数据库查询
        permissions = set()

        # 查询用户角色
        user_roles = await user_role_crud.get_user_roles(db, user_id=user_id, project_id=project_id)

        for user_role in user_roles:
            # 检查角色是否激活且未过期
            if not user_role.is_active:
                continue
            if user_role.expires_at and user_role.expires_at < datetime.utcnow():
                continue

            # 获取角色权限
            role_permissions = await permission_crud.get_role_permissions(db, role_id=user_role.role_id)
            for perm in role_permissions:
                permissions.add(perm.code)

        # 缓存权限信息
        await cache_manager.set(
            cache_key,
            list(permissions),
            ttl=settings.CACHE_PERMISSION_TTL
        )

        return permissions

    async def check_permission(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            permission_code: str,
            project_id: Optional[uuid.UUID] = None
    ) -> bool:
        """检查用户权限"""
        user_permissions = await self.get_user_permissions(db, user_id, project_id)
        return permission_code in user_permissions

    async def assign_role_to_user(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            role_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None,
            granted_by: Optional[uuid.UUID] = None,
            expires_at: Optional[datetime] = None
    ) -> UserRole:
        """为用户分配角色"""
        user_role_data = {
            "user_id": user_id,
            "role_id": role_id,
            "project_id": project_id,
            "granted_by": granted_by,
            "expires_at": expires_at
        }

        user_role = await user_role_crud.create(db, user_role_data)

        # 清除用户权限缓存
        cache_key = f"user_permissions:{user_id}:{project_id or 'global'}"
        await cache_manager.delete(cache_key)

        return user_role

    async def revoke_role_from_user(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            role_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None
    ) -> bool:
        """撤销用户角色"""
        result = await user_role_crud.revoke_user_role(db, user_id, role_id, project_id)

        if result:
            # 清除用户权限缓存
            cache_key = f"user_permissions:{user_id}:{project_id or 'global'}"
            await cache_manager.delete(cache_key)

        return result

    async def get_user_roles(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            project_id: Optional[uuid.UUID] = None
    ) -> List[Role]:
        """获取用户角色"""
        return await role_crud.get_user_roles(db, user_id=user_id, project_id=project_id)

    async def check_user_project_access(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            project_code: str
    ) -> bool:
        """检查用户是否有项目访问权限"""
        # 首先检查是否为超级用户
        from app.crud.user import user_crud
        user = await user_crud.get(db, id=user_id)
        if user and user.is_superuser:
            return True
        
        # 检查用户是否有该项目的任何角色
        from app.models.rbac import Project
        from sqlalchemy import select
        
        # 获取项目ID
        stmt = select(Project).where(Project.code == project_code)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            return False
        
        # 检查用户是否有该项目的有效角色
        user_roles = await user_role_crud.get_user_roles(db, user_id=user_id, project_id=project.id)
        active_roles = [
            role for role in user_roles
            if role.is_active and (not role.expires_at or role.expires_at > datetime.utcnow())
        ]
        
        return len(active_roles) > 0

    async def get_user_project_permissions(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            project_code: str
    ) -> List[str]:
        """获取用户在特定项目中的权限列表"""
        # 获取项目ID
        from app.models.rbac import Project
        from sqlalchemy import select
        
        stmt = select(Project).where(Project.code == project_code)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            return []
        
        # 获取权限
        permissions = await self.get_user_permissions(db, user_id, project.id)
        return list(permissions)

    async def create_default_project_permissions(
            self,
            db: AsyncSession,
            project_id: uuid.UUID,
            project_code: str
    ) -> List[Permission]:
        """为项目创建默认权限"""
        default_permissions = [
            {
                "name": f"{project_code.upper()} - 查看仪表板",
                "code": f"{project_code}.dashboard.view",
                "description": f"查看{project_code}项目仪表板",
                "resource_type": "dashboard",
                "action": "view",
                "project_id": project_id
            },
            {
                "name": f"{project_code.upper()} - 查看数据",
                "code": f"{project_code}.data.view",
                "description": f"查看{project_code}项目数据",
                "resource_type": "data",
                "action": "view",
                "project_id": project_id
            },
            {
                "name": f"{project_code.upper()} - 编辑数据",
                "code": f"{project_code}.data.edit",
                "description": f"编辑{project_code}项目数据",
                "resource_type": "data",
                "action": "edit",
                "project_id": project_id
            },
            {
                "name": f"{project_code.upper()} - 删除数据",
                "code": f"{project_code}.data.delete",
                "description": f"删除{project_code}项目数据",
                "resource_type": "data",
                "action": "delete",
                "project_id": project_id
            },
            {
                "name": f"{project_code.upper()} - 管理用户",
                "code": f"{project_code}.users.manage",
                "description": f"管理{project_code}项目用户",
                "resource_type": "users",
                "action": "manage",
                "project_id": project_id
            },
            {
                "name": f"{project_code.upper()} - 系统管理",
                "code": f"{project_code}.admin.access",
                "description": f"访问{project_code}项目管理功能",
                "resource_type": "admin",
                "action": "access",
                "project_id": project_id
            }
        ]
        
        created_permissions = []
        for perm_data in default_permissions:
            # 检查权限是否已存在
            existing_perm = await permission_crud.get_by_code(db, perm_data["code"])
            if not existing_perm:
                permission = await permission_crud.create(db, perm_data)
                created_permissions.append(permission)
            else:
                created_permissions.append(existing_perm)
        
        return created_permissions

    async def create_default_project_roles(
            self,
            db: AsyncSession,
            project_id: uuid.UUID,
            project_code: str
    ) -> List[Role]:
        """为项目创建默认角色"""
        # 首先创建默认权限
        permissions = await self.create_default_project_permissions(db, project_id, project_code)
        
        # 创建角色权限映射
        permission_map = {perm.code: perm for perm in permissions}
        
        default_roles = [
            {
                "name": f"{project_code.upper()} - 查看者",
                "code": f"{project_code}.viewer",
                "description": f"{project_code}项目查看者角色",
                "project_id": project_id,
                "permissions": [
                    f"{project_code}.dashboard.view",
                    f"{project_code}.data.view"
                ]
            },
            {
                "name": f"{project_code.upper()} - 编辑者",
                "code": f"{project_code}.editor",
                "description": f"{project_code}项目编辑者角色",
                "project_id": project_id,
                "permissions": [
                    f"{project_code}.dashboard.view",
                    f"{project_code}.data.view",
                    f"{project_code}.data.edit"
                ]
            },
            {
                "name": f"{project_code.upper()} - 管理员",
                "code": f"{project_code}.admin",
                "description": f"{project_code}项目管理员角色",
                "project_id": project_id,
                "permissions": [
                    f"{project_code}.dashboard.view",
                    f"{project_code}.data.view",
                    f"{project_code}.data.edit",
                    f"{project_code}.data.delete",
                    f"{project_code}.users.manage",
                    f"{project_code}.admin.access"
                ]
            }
        ]
        
        created_roles = []
        for role_data in default_roles:
            # 分离权限信息
            role_permissions = role_data.pop("permissions")
            
            # 检查角色是否已存在
            existing_role = await role_crud.get_by_code(db, role_data["code"])
            if not existing_role:
                role = await role_crud.create(db, role_data)
                
                # 为角色分配权限
                for perm_code in role_permissions:
                    if perm_code in permission_map:
                        await permission_crud.assign_permission_to_role(
                            db, role.id, permission_map[perm_code].id
                        )
                
                created_roles.append(role)
            else:
                created_roles.append(existing_role)
        
        return created_roles

    async def setup_project_rbac(
            self,
            db: AsyncSession,
            project_id: uuid.UUID,
            project_code: str
    ) -> dict:
        """为项目设置RBAC权限系统"""
        # 创建默认权限
        permissions = await self.create_default_project_permissions(db, project_id, project_code)
        
        # 创建默认角色
        roles = await self.create_default_project_roles(db, project_id, project_code)
        
        return {
            "project_id": str(project_id),
            "project_code": project_code,
            "permissions_created": len(permissions),
            "roles_created": len(roles),
            "permissions": [{"id": str(p.id), "code": p.code, "name": p.name} for p in permissions],
            "roles": [{"id": str(r.id), "code": r.code, "name": r.name} for r in roles]
        }
