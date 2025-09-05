# app/core/security.py - 安全工具
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Any, Union, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityUtils:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成随机令牌"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """生成API密钥和哈希值"""
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, key_hash

    @staticmethod
    def verify_api_key(api_key: str, key_hash: str) -> bool:
        """验证API密钥"""
        return hmac.compare_digest(
            hashlib.sha256(api_key.encode()).hexdigest(),
            key_hash
        )

    @staticmethod
    def generate_service_key() -> tuple[str, str]:
        """生成服务密钥和哈希值"""
        service_key = f"sk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(service_key.encode()).hexdigest()
        return service_key, key_hash

    @staticmethod
    def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建JWT令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def verify_jwt_token(token: str) -> Optional[dict]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None