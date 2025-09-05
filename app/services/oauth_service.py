# app/services/oauth_service.py - OAuth服务
import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.crud.user import user_crud
from app.crud.auth import session_crud
from app.models.user import User
from app.services.auth_service import AuthService

settings = get_settings()


class OAuthService:
    """OAuth第三方登录服务"""

    def __init__(self):
        self.auth_service = AuthService()

    def get_google_auth_url(self, state: Optional[str] = None) -> str:
        """获取Google OAuth授权URL"""
        if not settings.GOOGLE_CLIENT_ID:
            raise ValueError("Google OAuth not configured")

        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }

        if state:
            params['state'] = state

        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    def get_orcid_auth_url(self, state: Optional[str] = None) -> str:
        """获取ORCID OAuth授权URL"""
        if not settings.ORCID_CLIENT_ID:
            raise ValueError("ORCID OAuth not configured")

        base_url = "https://sandbox.orcid.org" if settings.ORCID_ENVIRONMENT == "sandbox" else "https://orcid.org"

        params = {
            'client_id': settings.ORCID_CLIENT_ID,
            'response_type': 'code',
            'scope': '/authenticate',
            'redirect_uri': settings.ORCID_REDIRECT_URI
        }

        if state:
            params['state'] = state

        return f"{base_url}/oauth/authorize?{urlencode(params)}"

    async def handle_google_callback(
            self,
            db: AsyncSession,
            code: str,
            ip_address: str = None,
            user_agent: str = None
    ) -> Dict[str, Any]:
        """处理Google OAuth回调"""
        # 获取访问令牌
        token_data = await self._exchange_google_code(code)

        # 获取用户信息
        user_info = await self._get_google_user_info(token_data['access_token'])

        # 查找或创建用户
        user = await self._find_or_create_user_from_google(db, user_info, token_data)

        # 创建登录会话
        return await self.auth_service.create_login_session(
            db, user, ip_address, user_agent
        )

    async def handle_orcid_callback(
            self,
            db: AsyncSession,
            code: str,
            ip_address: str = None,
            user_agent: str = None
    ) -> Dict[str, Any]:
        """处理ORCID OAuth回调"""
        # 获取访问令牌
        token_data = await self._exchange_orcid_code(code)

        # 获取用户信息
        user_info = await self._get_orcid_user_info(token_data['access_token'])

        # 查找或创建用户
        user = await self._find_or_create_user_from_orcid(db, user_info, token_data)

        # 创建登录会话
        return await self.auth_service.create_login_session(
            db, user, ip_address, user_agent
        )

    async def _exchange_google_code(self, code: str) -> Dict[str, Any]:
        """交换Google授权码获取令牌"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': settings.GOOGLE_REDIRECT_URI
                }
            )
            response.raise_for_status()
            return response.json()

    async def _get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """获取Google用户信息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            return response.json()

    async def _exchange_orcid_code(self, code: str) -> Dict[str, Any]:
        """交换ORCID授权码获取令牌"""
        base_url = "https://sandbox.orcid.org" if settings.ORCID_ENVIRONMENT == "sandbox" else "https://orcid.org"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/oauth/token",
                data={
                    'client_id': settings.ORCID_CLIENT_ID,
                    'client_secret': settings.ORCID_CLIENT_SECRET,
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': settings.ORCID_REDIRECT_URI
                },
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            return response.json()

    async def _get_orcid_user_info(self, access_token: str) -> Dict[str, Any]:
        """获取ORCID用户信息"""
        # ORCID的用户信息获取相对复杂，这里简化处理
        return {
            'id': 'orcid_user_id',  # 从token中提取
            'name': 'ORCID User',
            'email': None  # ORCID可能不提供邮箱
        }

    async def _find_or_create_user_from_google(
            self,
            db: AsyncSession,
            user_info: Dict[str, Any],
            token_data: Dict[str, Any]
    ) -> User:
        """从Google信息查找或创建用户"""
        email = user_info.get('email')
        if not email:
            raise ValueError("Google account must have an email")

        # 查找现有用户
        user = await user_crud.get_by_email(db, email=email)

        if not user:
            # 创建新用户
            from app.schemas.user import UserCreate
            user_create = UserCreate(
                username=email.split('@')[0],  # 使用邮箱前缀作为用户名
                email=email,
                display_name=user_info.get('name', ''),
                password='',  # OAuth用户没有密码
                is_verified=True  # Google用户默认已验证
            )

            try:
                user = await user_crud.create(db, obj_in=user_create)
            except ValueError:
                # 如果用户名冲突，生成唯一用户名
                import random
                user_create.username = f"{user_create.username}_{random.randint(1000, 9999)}"
                user = await user_crud.create(db, obj_in=user_create)

        # TODO: 更新或创建OAuth账号记录

        return user

    async def _find_or_create_user_from_orcid(
            self,
            db: AsyncSession,
            user_info: Dict[str, Any],
            token_data: Dict[str, Any]
    ) -> User:
        """从ORCID信息查找或创建用户"""
        # ORCID处理逻辑类似Google，但可能需要不同的处理方式
        # 这里简化实现
        orcid_id = user_info.get('id')
        if not orcid_id:
            raise ValueError("Invalid ORCID response")

        # 简化：使用ORCID ID作为邮箱（实际应用中需要更复杂的逻辑）
        fake_email = f"{orcid_id}@orcid.temp"

        user = await user_crud.get_by_email(db, email=fake_email)
        if not user:
            from app.schemas.user import UserCreate
            user_create = UserCreate(
                username=f"orcid_{orcid_id}",
                email=fake_email,
                display_name=user_info.get('name', 'ORCID User'),
                password='',
                is_verified=True
            )
            user = await user_crud.create(db, obj_in=user_create)

        return user