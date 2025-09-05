# app/auth/authenticators.py
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.auth import UserSession, APIKey, ServiceKey
from app.crud.user import user_crud
from app.crud.auth import session_crud, api_key_crud, service_key_crud
from app.core.security import SecurityUtils


class BaseAuthenticator(ABC):
    """认证器基类"""

    @abstractmethod
    async def authenticate(self, db: AsyncSession, credentials: Any) -> Optional[User]:
        pass


class SessionAuthenticator(BaseAuthenticator):
    """Session认证器"""

    async def authenticate(self, db: AsyncSession, session_token: str) -> Optional[User]:
        if not session_token:
            return None

        session = await session_crud.get_by_token(db, token=session_token)
        if not session or not session.is_active:
            return None

        # 使用UTC aware datetime进行比较
        from app.core.datetime_utils import utc_now, ensure_aware
        current_time = utc_now()
        session_expires = ensure_aware(session.expires_at)

        if session_expires and session_expires < current_time:
            await session_crud.deactivate(db, session_id=session.id)
            return None

        # 更新最后访问时间
        await session_crud.update_last_accessed(db, session_id=session.id)

        return await user_crud.get(db, id=session.user_id)


class APIKeyAuthenticator(BaseAuthenticator):
    """API Key认证器"""

    async def authenticate(self, db: AsyncSession, api_key: str) -> Optional[Tuple[User, APIKey]]:
        if not api_key:
            return None

        # 从API Key中提取哈希值进行查找
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_obj = await api_key_crud.get_by_hash(db, key_hash=key_hash)

        if not api_key_obj or not api_key_obj.is_active:
            return None

        # 检查是否过期
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            return None

        # 验证密钥
        if not SecurityUtils.verify_api_key(api_key, api_key_obj.key_hash):
            return None

        # 更新最后使用时间
        await api_key_crud.update_last_used(db, api_key_id=api_key_obj.id)

        user = await user_crud.get(db, id=api_key_obj.user_id)
        return user, api_key_obj


class ServiceKeyAuthenticator(BaseAuthenticator):
    """Service Key认证器"""

    async def authenticate(self, db: AsyncSession, service_key: str, project_id: str) -> Optional[ServiceKey]:
        if not service_key:
            return None

        key_hash = hashlib.sha256(service_key.encode()).hexdigest()
        service_key_obj = await service_key_crud.get_by_hash(db, key_hash=key_hash)

        if not service_key_obj or not service_key_obj.is_active:
            return None

        # 验证密钥
        if not SecurityUtils.verify_api_key(service_key, service_key_obj.key_hash):
            return None

        # 检查项目访问权限（这里简化处理）
        return service_key_obj


class JWTAuthenticator(BaseAuthenticator):
    """JWT认证器"""

    async def authenticate(self, db: AsyncSession, token: str) -> Optional[User]:
        if not token:
            return None

        payload = SecurityUtils.verify_jwt_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return await user_crud.get(db, id=user_id)