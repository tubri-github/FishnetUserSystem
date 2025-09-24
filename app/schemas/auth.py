# app/schemas/auth.py - 认证数据模式
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, EmailStr
from app.schemas.common import BaseResponse

# 在文件末尾添加model_rebuild调用来解决前向引用

class LoginRequest(BaseModel):
    username: str  # 可以是用户名或邮箱
    password: str
    remember_me: Optional[bool] = False

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    session_token: str
    user: "UserResponse"

class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    username: str
    email: str
    display_name: Optional[str]
    is_superuser: bool
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr


# 解决前向引用问题
TokenResponse.model_rebuild()
