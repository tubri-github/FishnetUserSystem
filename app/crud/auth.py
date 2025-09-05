# app/crud/auth.py
import uuid
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from app.crud.base import CRUDBase
from app.models.auth import UserSession, APIKey, ServiceKey, AuthCode
from app.core.security import SecurityUtils


class CRUDUserSession(CRUDBase[UserSession, dict, dict]):
    async def get_by_token(self, db: AsyncSession, *, token: str) -> Optional[UserSession]:
        """根据session token获取会话"""
        stmt = select(UserSession).where(
            and_(
                UserSession.session_token == token,
                UserSession.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_refresh_token(self, db: AsyncSession, *, refresh_token: str) -> Optional[UserSession]:
        """根据refresh token获取会话"""
        stmt = select(UserSession).where(
            and_(
                UserSession.refresh_token == refresh_token,
                UserSession.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_session(
            self,
            db: AsyncSession,
            *,
            user_id: uuid.UUID,
            session_token: str,
            refresh_token: str,
            expires_at: datetime,
            ip_address: str = None,
            user_agent: str = None,
            project_id: uuid.UUID = None
    ) -> UserSession:
        """创建新会话"""
        session = UserSession(
            id=uuid.uuid4(),
            user_id=user_id,
            session_token=session_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            project_id=project_id,
            is_active=True
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def deactivate(self, db: AsyncSession, *, session_id: uuid.UUID) -> None:
        """停用会话"""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_active=False)
        )
        await db.execute(stmt)
        await db.commit()

    async def update_last_accessed(self, db: AsyncSession, session_id: uuid.UUID) -> None:
        """更新最后访问时间"""
        from app.core.datetime_utils import utc_now

        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_accessed_at=utc_now())
        )
        await db.execute(stmt)
        await db.commit()


class CRUDAPIKey(CRUDBase[APIKey, dict, dict]):
    async def get_by_hash(self, db: AsyncSession, key_hash: str) -> Optional[APIKey]:
        """根据key hash获取API密钥"""
        stmt = select(APIKey).where(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_api_key(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            name: str,
            permissions: dict = None,
            ip_whitelist: List[str] = None,
            expires_days: int = 365
    ) -> tuple[APIKey, str]:
        """创建API密钥"""
        from app.core.datetime_utils import utc_now

        api_key, key_hash = SecurityUtils.generate_api_key()

        api_key_obj = APIKey(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            permissions=permissions,
            ip_whitelist=ip_whitelist,
            expires_at=utc_now() + timedelta(days=expires_days) if expires_days else None,
            is_active=True
        )

        db.add(api_key_obj)
        await db.commit()
        await db.refresh(api_key_obj)

        return api_key_obj, api_key

    async def update_last_used(self, db: AsyncSession, api_key_id: uuid.UUID) -> None:
        """更新最后使用时间"""
        from app.core.datetime_utils import utc_now

        stmt = (
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(last_used_at=utc_now())
        )
        await db.execute(stmt)
        await db.commit()


class CRUDServiceKey(CRUDBase[ServiceKey, dict, dict]):
    async def get_by_hash(self, db: AsyncSession, *, key_hash: str) -> Optional[ServiceKey]:
        """根据key hash获取服务密钥"""
        stmt = select(ServiceKey).where(
            and_(
                ServiceKey.key_hash == key_hash,
                ServiceKey.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class CRUDAuthCode(CRUDBase[AuthCode, dict, dict]):
    """授权码CRUD操作"""
    
    async def create_auth_code(
        self,
        db: AsyncSession,
        *,
        code: str,
        user_id: uuid.UUID,
        project: str,
        redirect_uri: str,
        expires_at: datetime
    ) -> AuthCode:
        """创建授权码"""
        auth_code = AuthCode(
            id=uuid.uuid4(),
            code=code,
            user_id=user_id,
            project=project,
            redirect_uri=redirect_uri,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(auth_code)
        await db.commit()
        await db.refresh(auth_code)
        
        return auth_code
    
    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[AuthCode]:
        """根据授权码获取记录"""
        stmt = select(AuthCode).where(AuthCode.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def mark_as_used(self, db: AsyncSession, *, auth_code_id: uuid.UUID) -> None:
        """标记授权码为已使用"""
        from app.core.datetime_utils import utc_now
        
        stmt = (
            update(AuthCode)
            .where(AuthCode.id == auth_code_id)
            .values(is_used=True, used_at=utc_now())
        )
        await db.execute(stmt)
        await db.commit()


# 创建实例
session_crud = CRUDUserSession(UserSession)
api_key_crud = CRUDAPIKey(APIKey)
service_key_crud = CRUDServiceKey(ServiceKey)
auth_code_crud = CRUDAuthCode(AuthCode)