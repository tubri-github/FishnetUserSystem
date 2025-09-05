# app/schemas/rbac.py - RBAC数据模式
import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class ProjectBase(BaseModel):
    """项目基础模式"""
    name: str
    code: str
    description: Optional[str] = None
    base_url: Optional[str] = None

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Project code can only contain lowercase letters, numbers and hyphens')
        return v


class ProjectCreate(ProjectBase):
    """创建项目模式"""
    is_active: bool = True


class ProjectUpdate(BaseModel):
    """更新项目模式"""
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """项目响应模式"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime


class RoleBase(BaseModel):
    """角色基础模式"""
    name: str
    code: str
    description: Optional[str] = None

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError('Role code can only contain lowercase letters, numbers and underscores')
        return v


class RoleCreate(RoleBase):
    """创建角色模式"""
    project_id: Optional[str] = None
    is_system: bool = False


class RoleUpdate(BaseModel):
    """更新角色模式"""
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    """角色响应模式"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: Optional[str] = None
    is_system: bool
    created_at: datetime


class PermissionBase(BaseModel):
    """权限基础模式"""
    name: str
    code: str
    description: Optional[str] = None
    resource_type: str
    action: str


class PermissionCreate(PermissionBase):
    """创建权限模式"""
    project_id: str


class PermissionResponse(PermissionBase):
    """权限响应模式"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    created_at: datetime


class UserRoleAssign(BaseModel):
    """用户角色分配模式"""
    user_id: str
    role_id: str
    project_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class RolePermissionAssign(BaseModel):
    """角色权限分配模式"""
    role_id: str
    permission_ids: List[str]


class UserRoleResponse(BaseModel):
    """用户角色响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    role_id: str
    project_id: Optional[str] = None
    granted_by: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool