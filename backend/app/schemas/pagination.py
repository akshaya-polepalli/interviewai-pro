"""Pagination helpers used across list endpoints."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def of(cls, *, items: list[T], total: int, page: int, page_size: int) -> Page[T]:
        pages = max(1, (total + page_size - 1) // page_size) if total else 1
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)
