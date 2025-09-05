# app/crud/audit.py
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.crud.base import CRUDBase
from app.models.audit import AuditLog, LoginLog


class CRUDAuditLog(CRUDBase[AuditLog, dict, dict]):
    async def get_user_logs(
            self,
            db: AsyncSession,
            *,
            user_id: uuid.UUID,
            skip: int = 0,
            limit: int = 50,
            action: Optional[str] = None,
            resource_type: Optional[str] = None
    ) -> List[AuditLog]:
        """获取用户审计日志"""
        filters = {"user_id": user_id}
        if action:
            filters["action"] = action
        if resource_type:
            filters["resource_type"] = resource_type

        return await self.get_multi(db, skip=skip, limit=limit, filters=filters)


class CRUDLoginLog(CRUDBase[LoginLog, dict, dict]):
    async def get_user_login_history(
            self,
            db: AsyncSession,
            *,
            user_id: uuid.UUID,
            skip: int = 0,
            limit: int = 50,
            success_only: Optional[bool] = None
    ) -> List[LoginLog]:
        """获取用户登录历史"""
        filters = {"user_id": user_id}
        if success_only is not None:
            filters["success"] = success_only

        return await self.get_multi(db, skip=skip, limit=limit, filters=filters)


# 创建实例
audit_log_crud = CRUDAuditLog(AuditLog)
login_log_crud = CRUDLoginLog(LoginLog)