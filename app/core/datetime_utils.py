# app/core/datetime_utils.py
from datetime import datetime, timezone
from typing import Optional

def utc_now() -> datetime:
    """获取当前UTC时间，带时区信息"""
    return datetime.now(timezone.utc)

def make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """将naive datetime转换为UTC aware datetime"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def make_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """将aware datetime转换为naive datetime (UTC)"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """确保datetime是aware的，如果是naive则假设为UTC"""
    return make_aware(dt)