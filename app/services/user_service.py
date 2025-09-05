# app/services/user_service.py
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.crud.user import user_crud
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User
from app.core.security import SecurityUtils


class UserService:
    """用户服务"""

    async def get_user(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """获取用户"""
        try:
            user_uuid = uuid.UUID(user_id)
            return await user_crud.get(db, id=user_uuid)
        except ValueError:
            return None

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return await user_crud.get_by_email(db, email=email)

    async def create_user(self, db: AsyncSession, user_create: UserCreate) -> User:
        """创建用户"""
        try:
            return await user_crud.create(db, obj_in=user_create)
        except ValueError as e:
            if "Email already registered" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            elif "Username already taken" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

    async def update_user(self, db: AsyncSession, user_id: str, user_update: UserUpdate) -> User:
        """更新用户信息"""
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        user = await user_crud.get(db, id=user_uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return await user_crud.update(db, db_obj=user, obj_in=user_update)

    async def get_users(
            self,
            db: AsyncSession,
            skip: int = 0,
            limit: int = 50,
            search: str = None,
            is_active: bool = None
    ) -> Tuple[List[User], int]:
        """获取用户列表"""
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active

        users = await user_crud.get_multi(db, skip=skip, limit=limit, filters=filters)
        total = await user_crud.count(db, filters=filters)

        return users, total

    async def change_password(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            current_password: str,
            new_password: str
    ) -> User:
        """修改密码"""
        user = await user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if not SecurityUtils.verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )

        user.password_hash = SecurityUtils.get_password_hash(new_password)
        await db.commit()
        await db.refresh(user)
        return user