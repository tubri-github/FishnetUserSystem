# app/schemas/common.py - 通用数据模式
from typing import Generic, TypeVar, Optional, Any, List
from datetime import datetime
from pydantic import BaseModel

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """统一响应格式"""
    success: bool = True
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None
    timestamp: Optional[datetime] = None
    trace_id: Optional[str] = None


class PaginationParams(BaseModel):
    """分页参数"""
    skip: int = 0
    limit: int = 50


class PaginationResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: List[T], total: int, skip: int, limit: int):
        """创建分页响应"""
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
