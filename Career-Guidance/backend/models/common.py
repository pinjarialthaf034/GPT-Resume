"""
CareerCompass AI — Common Pydantic models shared across the application.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standard API response envelope."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: Optional[str] = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
