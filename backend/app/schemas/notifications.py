"""In-app notification schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str
    channel: str
    status: str
    payload: dict | None = None
    read_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime
