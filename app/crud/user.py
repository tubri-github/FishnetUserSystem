# app/crud/user.py
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from app.crud.base import CRUDBase
from app.models.user import User, UserPreferences
from app.schemas.user import UserCreate, UserUpdate, UserPreferencesUpdate
from app.core.security import SecurityUtils


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """创建用户"""
        existing_user = await self.get_by_email(db, obj_in.email)
        if existing_user:
            raise ValueError("Email already registered")

        existing_user = await self.get_by_username(db, obj_in.username)
        if existing_user:
            raise ValueError("Username already taken")

        user_data = obj_in.model_dump()
        user_data["password_hash"] = SecurityUtils.get_password_hash(user_data.pop("password"))
        user_data["id"] = uuid.uuid4()

        db_user = User(**user_data)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """验证用户登录"""
        user = await self.get_by_email(db, email)
        if not user:
            return None
        if not SecurityUtils.verify_password(password, user.password_hash):
            return None
        return user

    async def update_login_info(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        """更新用户登录信息"""
        from app.core.datetime_utils import utc_now

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=utc_now(),
                login_count=User.login_count + 1
            )
        )
        await db.execute(stmt)
        await db.commit()


class CRUDUserPreferences(CRUDBase[UserPreferences, UserPreferencesUpdate, UserPreferencesUpdate]):
    async def get_by_user_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[UserPreferences]:
        """根据用户ID获取偏好设置"""
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# 创建实例
user_crud = CRUDUser(User)
user_preferences_crud = CRUDUserPreferences(UserPreferences)