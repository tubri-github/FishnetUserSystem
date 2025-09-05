# app/schemas/user.py - 用户数据模式
import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
import re


class UserBase(BaseModel):
    """用户基础模式"""
    username: str
    email: EmailStr
    display_name: Optional[str] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be at most 50 characters long')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores and hyphens')
        return v


class UserCreate(UserBase):
    """创建用户模式"""
    password: str
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        return v


class UserUpdate(BaseModel):
    """更新用户模式"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters long')
            if len(v) > 50:
                raise ValueError('Username must be at most 50 characters long')
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, underscores and hyphens')
        return v


class UserResponse(UserBase):
    """用户响应模式"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    login_count: int

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class UserListResponse(BaseModel):
    """用户列表响应"""
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


class UserPreferencesResponse(BaseModel):
    """用户偏好设置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    language: str
    timezone: str
    theme: str
    notifications: Optional[dict] = None
    privacy_settings: Optional[dict] = None


class UserPreferencesUpdate(BaseModel):
    """用户偏好设置更新"""
    language: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    notifications: Optional[dict] = None
    privacy_settings: Optional[dict] = None