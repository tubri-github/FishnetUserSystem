# app/schemas/audit.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """审计日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    project_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_data: Optional[dict] = None
    response_status: Optional[int] = None
    created_at: datetime


class LoginLogResponse(BaseModel):
    """登录日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    username: str
    login_method: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    failure_reason: Optional[str] = None
    project_id: Optional[str] = None
    created_at: datetime


class AuditLogFilter(BaseModel):
    """审计日志过滤器"""
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    project_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    success_only: Optional[bool] = None