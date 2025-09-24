# app/services/auth_service.py
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.auth import UserSession
from app.schemas.auth import LoginRequest, TokenResponse, SessionInfo
from app.crud.user import user_crud
from app.crud.auth import session_crud
from app.core.security import SecurityUtils
from app.core.datetime_utils import utc_now
from app.config import get_settings

settings = get_settings()


class AuthService:
    """认证服务"""

    async def login(
            self,
            db: AsyncSession,
            login_data: LoginRequest,
            ip_address: str = None,
            user_agent: str = None
    ) -> TokenResponse:
        """用户登录"""

        # 验证用户名密码 - 支持用户名或邮箱登录
        user = await user_crud.get_by_email(db, login_data.username)
        if not user:
            user = await user_crud.get_by_username(db, login_data.username)

        if not user or not SecurityUtils.verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )

        # 创建会话 - 使用UTC aware datetime
        session_token = SecurityUtils.generate_token()
        refresh_token = SecurityUtils.generate_token()
        expires_at = utc_now() + timedelta(hours=settings.SESSION_EXPIRE_HOURS)

        session = await session_crud.create_session(
            db,
            user_id=user.id,
            session_token=session_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # 更新用户登录信息
        await user_crud.update_login_info(db, user.id)

        # 创建JWT访问令牌
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = SecurityUtils.create_jwt_token(
            data={"sub": str(user.id), "session": str(session.id)},
            expires_delta=access_token_expires
        )

        # 构造用户响应数据
        user_data = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat(),
            "login_count": user.login_count
        }

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            session_token=session_token,
            user=user_data
        )

    async def logout(self, db: AsyncSession, session_token: str) -> bool:
        """用户登出"""
        session = await session_crud.get_by_token(db, token=session_token)
        if session:
            await session_crud.deactivate(db, session_id=session.id)
            return True
        return False

    async def refresh_token(self, db: AsyncSession, refresh_token: str) -> TokenResponse:
        """刷新令牌"""
        session = await session_crud.get_by_refresh_token(db, refresh_token=refresh_token)
        if not session or not session.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # 使用UTC aware datetime进行比较
        current_time = utc_now()
        if session.expires_at < current_time:
            await session_crud.deactivate(db, session_id=session.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )

        user = await user_crud.get(db, id=session.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )

        # 生成新的访问令牌
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = SecurityUtils.create_jwt_token(
            data={"sub": str(user.id), "session": str(session.id)},
            expires_delta=access_token_expires
        )

        user_data = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat(),
            "login_count": user.login_count
        }

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            session_token=session.session_token,
            user=user_data
        )

    async def get_user_by_session(self, db: AsyncSession, session_token: str) -> Optional[User]:
        """通过会话令牌获取用户"""
        session = await session_crud.get_by_token(db, token=session_token)
        if not session or not session.is_active:
            return None
            
        # 检查会话是否过期
        current_time = utc_now()
        if session.expires_at < current_time:
            await session_crud.deactivate(db, session_id=session.id)
            return None
            
        user = await user_crud.get(db, id=session.user_id)
        if not user or not user.is_active:
            return None
            
        return user

    async def generate_auth_code(
        self, 
        db: AsyncSession, 
        user_id: uuid.UUID, 
        project: str, 
        redirect_uri: str
    ) -> str:
        """生成临时授权码（用于SSO）"""
        from app.models.auth import AuthCode
        from app.crud.auth import auth_code_crud
        
        # 生成授权码
        code = SecurityUtils.generate_token(length=32)
        expires_at = utc_now() + timedelta(minutes=5)  # 5分钟有效
        
        # 保存授权码
        auth_code = await auth_code_crud.create_auth_code(
            db,
            code=code,
            user_id=user_id,
            project=project,
            redirect_uri=redirect_uri,
            expires_at=expires_at
        )
        
        return code

    async def exchange_auth_code(
        self, 
        db: AsyncSession, 
        code: str, 
        project: str, 
        redirect_uri: str
    ) -> Dict[str, Any]:
        """交换授权码获取访问令牌"""
        from app.crud.auth import auth_code_crud
        
        # 获取并验证授权码
        auth_code = await auth_code_crud.get_by_code(db, code=code)
        if not auth_code or auth_code.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的授权码"
            )
        
        # 检查是否过期
        current_time = utc_now()
        if auth_code.expires_at < current_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="授权码已过期"
            )
        
        # 验证项目和重定向URI
        if auth_code.project != project or auth_code.redirect_uri != redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="授权码参数不匹配"
            )
        
        # 标记授权码为已使用
        await auth_code_crud.mark_as_used(db, auth_code_id=auth_code.id)
        
        # 获取用户信息
        user = await user_crud.get(db, id=auth_code.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账号已禁用"
            )
        
        # 生成访问令牌（针对特定项目）
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = SecurityUtils.create_jwt_token(
            data={
                "sub": str(user.id), 
                "project": project,
                "type": "sso_access"
            },
            expires_delta=access_token_expires
        )
        
        # 获取用户权限
        from app.services.rbac_service import RBACService
        from app.crud.rbac import project_crud
        rbac_service = RBACService()
        
        # 通过项目代码获取项目UUID
        project_obj = await project_crud.get_by_code(db, code=project)
        project_id = project_obj.id if project_obj else None
        
        # 获取用户在该项目中的权限
        user_permissions = await rbac_service.get_user_permissions(db, user.id, project_id)
        permission_codes = list(user_permissions) if isinstance(user_permissions, set) else []
        
        # 获取用户在该项目中的角色
        user_roles = await rbac_service.get_user_roles(db, user.id, project_id)
        role_data = []
        for role in user_roles:
            role_data.append({
                "id": str(role.id),
                "name": role.name,
                "code": role.code,
                "description": role.description,
                "is_system": role.is_system
            })
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "is_superuser": user.is_superuser,
            "permissions": permission_codes,
            "roles": role_data,
            "project": project
        }

    async def get_user_by_access_token(
        self, 
        db: AsyncSession, 
        access_token: str, 
        project: str
    ) -> Dict[str, Any]:
        """通过访问令牌获取用户信息（用于项目间调用）"""
        try:
            # 验证JWT令牌
            payload = SecurityUtils.verify_jwt_token(access_token)
            user_id = payload.get("sub")
            token_project = payload.get("project")
            token_type = payload.get("type")
            
            if not user_id or token_project != project or token_type != "sso_access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的访问令牌"
                )
            
            # 获取用户信息
            user = await user_crud.get(db, id=uuid.UUID(user_id))
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户账号已禁用"
                )
            
            return {
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_superuser": user.is_superuser,
                "project": project
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"令牌验证失败: {str(e)}"
            )