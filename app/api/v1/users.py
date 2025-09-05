# app/api/v1/users.py - 用户管理API
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.schemas.common import BaseResponse, PaginationParams
from app.services.user_service import UserService
from app.dependencies import get_current_active_user, get_current_superuser
from app.auth.permissions import require_permission
from app.models.user import User

router = APIRouter()
user_service = UserService()


@router.get("", response_model=BaseResponse[UserListResponse])
@require_permission("user.read")
async def get_users(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        search: Optional[str] = Query(None),
        is_active: Optional[bool] = Query(None)
):
    """获取用户列表"""
    try:
        users, total = await user_service.get_users(
            db, skip=skip, limit=limit, search=search, is_active=is_active
        )

        return BaseResponse(
            success=True,
            message="获取用户列表成功",
            data=UserListResponse(
                users=[UserResponse.from_orm(user) for user in users],
                total=total,
                skip=skip,
                limit=limit
            )
        )

    except Exception as e:
        return BaseResponse(
            success=False,
            message="获取用户列表失败"
        )


@router.post("", response_model=BaseResponse[UserResponse])
@require_permission("user.create")
async def create_user(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """创建用户"""
    try:
        user = await user_service.create_user(db, user_data)
        return BaseResponse(
            success=True,
            message="用户创建成功",
            data=UserResponse.from_orm(user)
        )
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.get("/{user_id}", response_model=BaseResponse[UserResponse])
@require_permission("user.read")
async def get_user(
        user_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """获取用户详情"""
    try:
        user = await user_service.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return BaseResponse(
            success=True,
            message="获取用户信息成功",
            data=UserResponse.from_orm(user)
        )
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.put("/{user_id}", response_model=BaseResponse[UserResponse])
@require_permission("user.update")
async def update_user(
        user_id: str,
        user_data: UserUpdate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """更新用户信息"""
    try:
        user = await user_service.update_user(db, user_id, user_data)
        return BaseResponse(
            success=True,
            message="用户信息更新成功",
            data=UserResponse.from_orm(user)
        )
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.delete("/{user_id}", response_model=BaseResponse[str])
@require_permission("user.delete")
async def delete_user(
        user_id: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """删除用户"""
    try:
        # 不能删除自己
        if str(current_user.id) == user_id:
            raise HTTPException(status_code=400, detail="不能删除自己")

        success = await user_service.delete_user(db, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="用户不存在")

        return BaseResponse(
            success=True,
            message="用户删除成功",
            data="success"
        )
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )