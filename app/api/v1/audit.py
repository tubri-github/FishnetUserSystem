# app/api/v1/audit.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.common import BaseResponse
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/logs", response_model=BaseResponse[List[dict]])
async def get_audit_logs(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """获取审计日志"""
    return BaseResponse(
        success=True,
        message="Audit logs retrieved successfully",
        data=[]
    )