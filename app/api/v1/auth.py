# app/api/v1/auth.py - 认证API
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse,
    PasswordChangeRequest, PasswordResetRequest, UserResponse
)
from app.schemas.common import BaseResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.dependencies import get_current_active_user
from app.models.user import User
from app.config import get_settings

router = APIRouter()
auth_service = AuthService()
user_service = UserService()
settings = get_settings()


@router.post("/login", response_model=BaseResponse[TokenResponse])
async def login(
        request: Request,
        response: Response,
        login_data: LoginRequest,
        db: AsyncSession = Depends(get_async_session)
):
    """用户登录"""
    try:
        # 获取客户端信息
        ip_address = request.client.host
        user_agent = request.headers.get("User-Agent")

        # 执行登录
        token_response = await auth_service.login(
            db, login_data, ip_address, user_agent
        )

        # 设置Session Cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token_response.session_token,
            max_age=settings.SESSION_EXPIRE_HOURS * 3600,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )

        return BaseResponse(
            success=True,
            message="登录成功",
            data=token_response
        )

    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.post("/logout", response_model=BaseResponse[str])
async def logout(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """用户登出"""
    try:
        # 获取会话令牌
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_token:
            await auth_service.logout(db, session_token)

        # 清除Cookie
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )

        return BaseResponse(
            success=True,
            message="登出成功",
            data="success"
        )

    except Exception as e:
        return BaseResponse(
            success=False,
            message="登出失败"
        )


@router.post("/register", response_model=BaseResponse[UserResponse])
async def register(
        register_data: RegisterRequest,
        db: AsyncSession = Depends(get_async_session)
):
    """用户注册"""
    try:
        user = await user_service.create_user(db, register_data)
        return BaseResponse(
            success=True,
            message="注册成功",
            data=UserResponse.from_orm(user)
        )
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.post("/refresh", response_model=BaseResponse[TokenResponse])
async def refresh_token(
        request: Request,
        db: AsyncSession = Depends(get_async_session)
):
    """刷新令牌"""
    try:
        # 从请求体或Cookie中获取refresh_token
        refresh_token = request.headers.get("X-Refresh-Token")
        if not refresh_token:
            body = await request.json()
            refresh_token = body.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少刷新令牌"
            )

        token_response = await auth_service.refresh_token(db, refresh_token)

        return BaseResponse(
            success=True,
            message="令牌刷新成功",
            data=token_response
        )

    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.get("/me", response_model=BaseResponse[UserResponse])
async def get_current_user_info(
        current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    # 手动构造用户数据，避免from_orm问题
    user_data = UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at.isoformat(),
        login_count=current_user.login_count
    )

    """获取当前用户信息"""
    return BaseResponse(
        success=True,
        message="获取用户信息成功",
        data=user_data
    )


@router.put("/password", response_model=BaseResponse[str])
async def change_password(
        password_data: PasswordChangeRequest,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(get_current_active_user)
):
    """修改密码"""
    try:
        await user_service.change_password(
            db, current_user.id,
            password_data.current_password,
            password_data.new_password
        )

        return BaseResponse(
            success=True,
            message="密码修改成功",
            data="success"
        )

    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.post("/forgot-password", response_model=BaseResponse[str])
async def forgot_password(
        password_reset_data: PasswordResetRequest,
        db: AsyncSession = Depends(get_async_session)
):
    """忘记密码"""
    try:
        await user_service.request_password_reset(db, password_reset_data.email)

        return BaseResponse(
            success=True,
            message="密码重置邮件已发送",
            data="success"
        )

    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )