# app/middleware.py - 认证中间件
import json
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.auth.authenticators import (
    SessionAuthenticator,
    APIKeyAuthenticator,
    ServiceKeyAuthenticator,
    JWTAuthenticator
)
from app.models.user import User
from app.models.auth import APIKey, ServiceKey
from app.core.cache import cache_manager


class AuthenticationMiddleware:
    """统一认证中间件"""

    def __init__(self):
        self.session_auth = SessionAuthenticator()
        self.api_key_auth = APIKeyAuthenticator()
        self.service_key_auth = ServiceKeyAuthenticator()
        self.jwt_auth = JWTAuthenticator()

    async def authenticate_request(
            self,
            request: Request
    ) -> Tuple[Optional[User], Optional[dict]]:
        """认证请求 - 按优先级尝试不同认证方式"""

        db = None
        try:
            # 获取数据库会话
            async for session in get_async_session():
                db = session
                break

            # 认证策略按优先级执行

            # 1. Cookie Session认证 (最高优先级 - Web用户)
            session_token = request.cookies.get("auth_session")
            if session_token:
                user = await self.session_auth.authenticate(db, session_token)
                if user:
                    return user, {"auth_type": "session", "session_token": session_token}

            # 2. API Key认证 (用户API调用)
            api_key = self._extract_api_key(request)
            if api_key:
                result = await self.api_key_auth.authenticate(db, api_key)
                if result:
                    user, api_key_obj = result
                    return user, {
                        "auth_type": "api_key",
                        "api_key_id": str(api_key_obj.id),
                        "permissions": api_key_obj.permissions
                    }

            # 3. Service Key认证 (服务间调用)
            service_key, project_id = self._extract_service_key(request)
            if service_key and project_id:
                service_key_obj = await self.service_key_auth.authenticate(
                    db, service_key, project_id
                )
                if service_key_obj:
                    return None, {
                        "auth_type": "service_key",
                        "service_key_id": str(service_key_obj.id),
                        "project_id": project_id,
                        "permissions": service_key_obj.permissions
                    }

            # 4. JWT Bearer认证 (临时令牌)
            jwt_token = self._extract_jwt_token(request)
            if jwt_token:
                user = await self.jwt_auth.authenticate(db, jwt_token)
                if user:
                    return user, {"auth_type": "jwt", "token": jwt_token}

            return None, None

        finally:
            if db:
                await db.close()

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """提取API Key"""
        # 从Header中提取
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # 从查询参数中提取
        api_key = request.query_params.get("api_key")
        return api_key

    def _extract_service_key(self, request: Request) -> Tuple[Optional[str], Optional[str]]:
        """提取Service Key和项目ID"""
        service_key = request.headers.get("X-Service-Key")
        project_id = request.headers.get("X-Project-ID")
        return service_key, project_id

    def _extract_jwt_token(self, request: Request) -> Optional[str]:
        """提取JWT令牌"""
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]  # 去掉 "Bearer " 前缀
        return None
