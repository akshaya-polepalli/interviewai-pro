"""In-app notifications API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.dependencies import DbSession, require_permissions
from app.models import Notification, User
from app.models.enums import NotificationStatus
from app.schemas.auth import MessageResponse
from app.schemas.notifications import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

NotifReader = Annotated[User, Depends(require_permissions("users:read"))]


@router.get("", response_model=list[NotificationResponse], summary="List my notifications")
def list_notifications(user: NotifReader, db: DbSession) -> list[NotificationResponse]:
    rows = list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        ).all()
    )
    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            body=n.body,
            channel=n.channel.value if hasattr(n.channel, "value") else str(n.channel),
            status=n.status.value if hasattr(n.status, "value") else str(n.status),
            payload=n.payload,
            read_at=n.read_at,
            sent_at=n.sent_at,
            created_at=n.created_at,
        )
        for n in rows
    ]


@router.post("/{notification_id}/read", response_model=MessageResponse, summary="Mark as read")
def mark_read(notification_id: UUID, user: NotifReader, db: DbSession) -> MessageResponse:
    row = db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if row is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Notification not found")
    row.status = NotificationStatus.READ
    row.read_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    return MessageResponse(message="Marked as read")
