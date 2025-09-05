# app/services/audit_service.py - 审计服务
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.audit import audit_log_crud, login_log_crud
from app.models.audit import AuditLog, LoginLog


class AuditService:
    """审计服务"""

    async def log_user_action(
            self,
            db: AsyncSession,
            user_id: Optional[uuid.UUID],
            action: str,
            resource_type: str,
            resource_id: Optional[str] = None,
            project_id: Optional[uuid.UUID] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            request_data: Optional[Dict[str, Any]] = None,
            response_status: Optional[int] = None
    ) -> AuditLog:
        """记录用户操作"""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            response_status=response_status
        )

        db.add(audit_log)
        await db.commit()
        return audit_log

    async def log_login_attempt(
            self,
            db: AsyncSession,
            user_id: Optional[uuid.UUID],
            username: str,
            login_method: str,
            success: bool,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            failure_reason: Optional[str] = None,
            project_id: Optional[uuid.UUID] = None
    ) -> LoginLog:
        """记录登录尝试"""
        login_log = LoginLog(
            id=uuid.uuid4(),
            user_id=user_id,
            username=username,
            login_method=login_method,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=failure_reason,
            project_id=project_id
        )

        db.add(login_log)
        await db.commit()
        return login_log

    async def get_user_audit_logs(
            self,
            db: AsyncSession,
            user_id: uuid.UUID,
            skip: int = 0,
            limit: int = 50,
            action: Optional[str] = None,
            resource_type: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """获取用户审计日志"""
        filters = {"user_id": user_id}
        if action:
            filters["action"] = action
        if resource_type:
            filters["resource_type"] = resource_type

        # TODO: 实现日期范围过滤
        return await audit_log_crud.get_multi(db, skip=skip, limit=limit, filters=filters)

    async def get_login_history(
            self,
            db: AsyncSession,
            user_id: Optional[uuid.UUID] = None,
            username: Optional[str] = None,
            skip: int = 0,
            limit: int = 50,
            success_only: Optional[bool] = None
    ) -> List[LoginLog]:
        """获取登录历史"""
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if username:
            filters["username"] = username
        if success_only is not None:
            filters["success"] = success_only

        return await login_log_crud.get_multi(db, skip=skip, limit=limit, filters=filters)
