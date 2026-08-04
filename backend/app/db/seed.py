"""
Seed RBAC roles/permissions, achievements, and optional bootstrap admin.

Idempotent: safe to run multiple times.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.db.coding_seed import upsert_coding_problems
from app.models import Achievement, Analytics, Permission, Role, User
from app.models.enums import UserStatus

logger = structlog.get_logger(__name__)

PERMISSIONS: list[tuple[str, str]] = [
    ("users:read", "View user profiles"),
    ("users:write", "Update user profiles"),
    ("users:delete", "Delete user accounts"),
    ("admin:access", "Access admin dashboard"),
    ("admin:users", "Manage all users"),
    ("admin:analytics", "View platform analytics"),
    ("resumes:read", "View own resumes"),
    ("resumes:write", "Upload and manage resumes"),
    ("interviews:read", "View own interviews"),
    ("interviews:write", "Create and take interviews"),
    ("coding:read", "View coding problems"),
    ("coding:submit", "Submit coding solutions"),
    ("reports:read", "Download reports"),
    ("coach:read", "View AI coach insights and study plans"),
    ("coach:write", "Generate study plans and chat with the coach"),
    ("roadmaps:read", "View company prep roadmaps"),
    ("roadmaps:write", "Enroll in company tracks and check milestones"),
    ("billing:read", "View subscription and entitlements"),
    ("billing:write", "Change subscription plan"),
]

ROLES: dict[str, list[str]] = {
    "candidate": [
        "users:read",
        "users:write",
        "users:delete",
        "resumes:read",
        "resumes:write",
        "interviews:read",
        "interviews:write",
        "coding:read",
        "coding:submit",
        "reports:read",
        "coach:read",
        "coach:write",
        "roadmaps:read",
        "roadmaps:write",
        "billing:read",
        "billing:write",
    ],
    "recruiter": [
        "users:read",
        "resumes:read",
        "interviews:read",
        "reports:read",
        "admin:analytics",
    ],
    "admin": [code for code, _ in PERMISSIONS],
}

ACHIEVEMENTS: list[tuple[str, str, str, int]] = [
    ("first_login", "Welcome Aboard", "Completed first successful login", 10),
    ("first_interview", "Ice Breaker", "Finished your first mock interview", 25),
    ("first_accepted", "Green Check", "Got your first accepted coding submission", 25),
    ("week_streak_7", "Consistency", "Practiced 7 days in a row", 50),
    ("ats_80", "ATS Ready", "Scored 80+ on a resume ATS analysis", 40),
]


def _get_or_create_permission(db: Session, code: str, description: str) -> Permission:
    existing = db.scalar(select(Permission).where(Permission.code == code))
    if existing:
        return existing
    perm = Permission(code=code, description=description)
    db.add(perm)
    db.flush()
    return perm


def _get_or_create_role(db: Session, name: str, permission_codes: list[str]) -> Role:
    existing = db.scalar(select(Role).where(Role.name == name))
    perms = [
        _get_or_create_permission(db, code, desc)
        for code, desc in PERMISSIONS
        if code in permission_codes
    ]
    if existing:
        existing.permissions = perms
        existing.is_system = True
        return existing
    role = Role(
        name=name,
        description=f"System role: {name}",
        is_system=True,
        permissions=perms,
    )
    db.add(role)
    db.flush()
    return role


def _get_or_create_achievement(
    db: Session, code: str, title: str, description: str, points: int
) -> Achievement:
    existing = db.scalar(select(Achievement).where(Achievement.code == code))
    if existing:
        return existing
    row = Achievement(code=code, title=title, description=description, points=points)
    db.add(row)
    db.flush()
    return row


def _ensure_admin_user(db: Session) -> None:
    settings = get_settings()
    email = (settings.seed_admin_email or "").strip().lower()
    password = settings.seed_admin_password or ""
    if not email or not password:
        logger.info("seed_admin_skipped", reason="SEED_ADMIN_EMAIL/PASSWORD not set")
        return

    admin_role = db.scalar(select(Role).where(Role.name == "admin"))
    if admin_role is None:
        logger.warning("seed_admin_skipped", reason="admin role missing")
        return

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        if admin_role not in (existing.roles or []):
            existing.roles = list({*existing.roles, admin_role})
            db.add(existing)
            db.flush()
        logger.info("seed_admin_exists", email=email)
        return

    user = User(
        email=email,
        full_name=settings.seed_admin_name,
        hashed_password=hash_password(password),
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        email_verified_at=datetime.now(UTC),
        roles=[admin_role],
    )
    db.add(user)
    db.flush()
    db.add(Analytics(user_id=user.id))
    logger.info("seed_admin_created", email=email)


def seed(db: Session) -> None:
    for code, description in PERMISSIONS:
        _get_or_create_permission(db, code, description)

    for role_name, codes in ROLES.items():
        _get_or_create_role(db, role_name, codes)

    for code, title, description, points in ACHIEVEMENTS:
        _get_or_create_achievement(db, code, title, description, points)

    _ensure_admin_user(db)

    created_problems = upsert_coding_problems(db)

    db.commit()
    logger.info(
        "seed_complete",
        permissions=len(PERMISSIONS),
        roles=len(ROLES),
        achievements=len(ACHIEVEMENTS),
        coding_problems_created=created_problems,
    )


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
