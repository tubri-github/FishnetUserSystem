# app/dependencies.py - 依赖注入
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.user import User
from app.auth.authenticators import (
    SessionAuthenticator,
    APIKeyAuthenticator,
    ServiceKeyAuthenticator,
    JWTAuthenticator
)

# 认证器实例
session_auth = SessionAuthenticator()
api_key_auth = APIKeyAuthenticator()
service_key_auth = ServiceKeyAuthenticator()
jwt_auth = JWTAuthenticator()


async def authenticate_request(
        request: Request,
        db: AsyncSession = Depends(get_async_session)
) -> tuple[Optional[User], Optional[dict]]:
    """统一认证处理"""

    # 1. Cookie Session认证 (最高优先级)
    session_token = request.cookies.get("auth_session")
    if session_token:
        user = await session_auth.authenticate(db, session_token)
        if user:
            return user, {"auth_type": "session", "session_token": session_token}

    # 2. API Key认证
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if api_key:
        result = await api_key_auth.authenticate(db, api_key)
        if result:
            user, api_key_obj = result
            return user, {
                "auth_type": "api_key",
                "api_key_id": str(api_key_obj.id),
                "permissions": api_key_obj.permissions
            }

    # 3. Service Key认证
    service_key = request.headers.get("X-Service-Key")
    project_id = request.headers.get("X-Project-ID")
    if service_key and project_id:
        service_key_obj = await service_key_auth.authenticate(db, service_key, project_id)
        if service_key_obj:
            return None, {
                "auth_type": "service_key",
                "service_key_id": str(service_key_obj.id),
                "project_id": project_id,
                "permissions": service_key_obj.permissions
            }

    # 4. JWT Bearer认证
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]
        user = await jwt_auth.authenticate(db, jwt_token)
        if user:
            return user, {"auth_type": "jwt", "token": jwt_token}

    return None, None


async def get_current_user_optional(
        request: Request,
        db: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """获取当前用户（可选）"""
    user, auth_info = await authenticate_request(request, db)
    if auth_info:
        # 将认证信息存储到request state中
        request.state.auth_info = auth_info
    return user


async def get_current_user(
        request: Request,
        db: AsyncSession = Depends(get_async_session)
) -> User:
    """获取当前用户（必需）"""
    user, auth_info = await authenticate_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 将认证信息存储到request state中
    request.state.auth_info = auth_info
    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


async def get_current_superuser(
        current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges"
        )
    return current_user


async def get_current_verified_user(
        current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前已验证用户"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


# 服务认证相关依赖
async def get_service_auth_info(
        request: Request,
        db: AsyncSession = Depends(get_async_session)
) -> dict:
    """获取服务认证信息"""
    _, auth_info = await authenticate_request(request, db)
    if not auth_info or auth_info.get("auth_type") != "service_key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required"
        )
    return auth_info


async def require_service_permission(
        required_permission: str,
        auth_info: dict = Depends(get_service_auth_info)
) -> bool:
    """检查服务权限"""
    permissions = auth_info.get("permissions", {})
    if required_permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service permission required: {required_permission}"
        )
    return True


# 项目相关依赖
async def get_project_id_from_request(request: Request) -> Optional[str]:
    """从请求中获取项目ID"""
    # 从Header中获取
    project_id = request.headers.get("X-Project-ID")
    if project_id:
        return project_id

    # 从查询参数中获取
    project_id = request.query_params.get("project_id")
    if project_id:
        return project_id

    # 从认证信息中获取
    auth_info = getattr(request.state, 'auth_info', None)
    if auth_info:
        return auth_info.get("project_id")

    return None


async def require_project_id(
        project_id: Optional[str] = Depends(get_project_id_from_request)
) -> str:
    """要求提供项目ID"""
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID is required"
        )
    return project_id


# 分页依赖
def get_pagination_params(
        skip: int = 0,
        limit: int = 50
) -> tuple[int, int]:
    """获取分页参数"""
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 50
    elif limit > 100:
        limit = 100

    return skip, limit


# 搜索依赖
def get_search_params(
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
) -> dict:
    """获取搜索参数"""
    return {
        "search": search.strip() if search else None,
        "sort_by": sort_by,
        "sort_desc": sort_desc
    }


# 审计日志依赖
async def log_user_action(
        request: Request,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        current_user: Optional[User] = Depends(get_current_user_optional),
        db: AsyncSession = Depends(get_async_session)
):
    """记录用户操作审计日志"""
    from app.services.audit_service import AuditService

    audit_service = AuditService()

    # 获取请求信息
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    project_id = getattr(request.state, 'project_id', None)

    # 记录审计日志
    await audit_service.log_user_action(
        db=db,
        user_id=current_user.id if current_user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


# 速率限制依赖（简单实现）
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # 简单的内存存储，生产环境应使用Redis

    async def check_rate_limit(self, key: str) -> bool:
        """检查速率限制"""
        import time

        current_time = time.time()
        window_start = current_time - self.window_seconds

        # 清理过期记录
        if key in self.requests:
            self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        else:
            self.requests[key] = []

        # 检查是否超限
        if len(self.requests[key]) >= self.max_requests:
            return False

        # 记录当前请求
        self.requests[key].append(current_time)
        return True


rate_limiter = RateLimiter()


async def check_rate_limit(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional)
):
    """检查速率限制"""
    # 使用用户ID或IP作为限制键
    if current_user:
        rate_key = f"user:{current_user.id}"
    else:
        rate_key = f"ip:{request.client.host if request.client else 'unknown'}"

    if not await rate_limiter.check_rate_limit(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )

    return True