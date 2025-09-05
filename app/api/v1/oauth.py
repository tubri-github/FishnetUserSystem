# app/api/v1/oauth.py - 第三方登录API
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services.oauth_service import OAuthService
from app.schemas.common import BaseResponse
from app.config import get_settings

router = APIRouter()
oauth_service = OAuthService()
settings = get_settings()


@router.get("/google/login")
async def google_login(request: Request):
    """Google登录重定向"""
    authorization_url = oauth_service.get_google_auth_url()
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(
        request: Request,
        response: Response,
        code: str,
        db: AsyncSession = Depends(get_async_session)
):
    """Google登录回调"""
    try:
        # 获取客户端信息
        ip_address = request.client.host
        user_agent = request.headers.get("User-Agent")

        # 处理Google回调
        token_response = await oauth_service.handle_google_callback(
            db, code, ip_address, user_agent
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

        # 重定向到前端成功页面
        frontend_url = settings.PROJECT_URLS.get("frontend", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth/success")

    except HTTPException as e:
        # 重定向到前端错误页面
        frontend_url = settings.PROJECT_URLS.get("frontend", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth/error?message={e.detail}")


@router.get("/orcid/login")
async def orcid_login(request: Request):
    """ORCID登录重定向"""
    authorization_url = oauth_service.get_orcid_auth_url()
    return RedirectResponse(url=authorization_url)


@router.get("/orcid/callback")
async def orcid_callback(
        request: Request,
        response: Response,
        code: str,
        db: AsyncSession = Depends(get_async_session)
):
    """ORCID登录回调"""
    try:
        ip_address = request.client.host
        user_agent = request.headers.get("User-Agent")

        token_response = await oauth_service.handle_orcid_callback(
            db, code, ip_address, user_agent
        )

        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token_response.session_token,
            max_age=settings.SESSION_EXPIRE_HOURS * 3600,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )

        frontend_url = settings.PROJECT_URLS.get("frontend", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth/success")

    except HTTPException as e:
        frontend_url = settings.PROJECT_URLS.get("frontend", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth/error?message={e.detail}")
