import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # 基础配置
    PROJECT_NAME: str = "统一认证授权系统"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # 数据库配置
    DATABASE_URL: str
    # DATABASE_POOL_SIZE: int = 20
    # DATABASE_POOL_OVERFLOW: int = 30
    DATABASE_ECHO: bool = False

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # JWT配置
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    # Session配置
    SESSION_SECRET_KEY: str
    SESSION_EXPIRE_HOURS: int = 24
    SESSION_COOKIE_NAME: str = "auth_session"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"

    # API Key配置
    API_KEY_EXPIRE_DAYS: int = 365
    API_KEY_RATE_LIMIT: int = 1000  # 每小时请求数

    # Service Key配置
    SERVICE_KEY_EXPIRE_DAYS: int = 90
    SERVICE_KEY_ROTATION_DAYS: int = 30

    # Google OAuth配置
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # ORCID OAuth配置
    ORCID_CLIENT_ID: Optional[str] = None
    ORCID_CLIENT_SECRET: Optional[str] = None
    ORCID_REDIRECT_URI: str = "http://localhost:8000/auth/orcid/callback"
    ORCID_ENVIRONMENT: str = "sandbox"  # sandbox or production

    # 安全配置
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    # 登录安全
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30
    LOGIN_RATE_LIMIT: int = 10  # 每分钟尝试次数

    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_CREDENTIALS: bool = True
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # 项目配置
    ALLOWED_PROJECTS: List[str] = ["project-a", "project-b", "project-c"]
    PROJECT_URLS: dict = {
        "project-a": "http://localhost:8001",
        "project-b": "http://localhost:8002",
        "project-c": "http://localhost:8003"
    }

    # 审计配置
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_LOG_BATCH_SIZE: int = 1000

    # 缓存配置
    CACHE_DEFAULT_TTL: int = 300  # 5分钟
    CACHE_USER_TTL: int = 3600  # 1小时
    CACHE_PERMISSION_TTL: int = 1800  # 30分钟

    @field_validator("DATABASE_URL", mode='before')
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

    @field_validator("JWT_SECRET_KEY", mode='before')
    @classmethod
    def validate_jwt_secret(cls, v):
        if not v or len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()