# app/auth/permissions.py - 权限装饰器
from functools import wraps
from typing import Optional, List, Union
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services.rbac_service import RBACService
from app.dependencies import get_current_user


def require_permission(
        permission: Union[str, List[str]],
        project_id: Optional[str] = None
):
    """权限验证装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户和数据库会话
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')

            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )

            # 超级用户跳过权限检查
            if current_user.is_superuser:
                return await func(*args, **kwargs)

            rbac_service = RBACService()

            # 检查权限
            permissions_to_check = [permission] if isinstance(permission, str) else permission

            for perm in permissions_to_check:
                has_permission = await rbac_service.check_permission(
                    db, current_user.id, perm, project_id
                )
                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"缺少权限: {perm}"
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_roles(roles: Union[str, List[str]], project_id: Optional[str] = None):
    """角色验证装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')

            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )

            if current_user.is_superuser:
                return await func(*args, **kwargs)

            rbac_service = RBACService()
            user_roles = await rbac_service.get_user_roles(db, current_user.id, project_id)

            roles_to_check = [roles] if isinstance(roles, str) else roles
            user_role_codes = [role.code for role in user_roles]

            has_required_role = any(role in user_role_codes for role in roles_to_check)

            if not has_required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"缺少角色: {', '.join(roles_to_check)}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator