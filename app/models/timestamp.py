from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, DateTime
from datetime import datetime, timezone
from typing import Optional

class AwareDateTime(TypeDecorator):
    impl = DateTime(timezone=True)

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

Base = declarative_base()

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(AwareDateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(AwareDateTime, onupdate=func.now())
