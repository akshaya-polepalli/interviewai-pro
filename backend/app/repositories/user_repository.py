"""User data-access repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Role, User
from app.models.enums import UserStatus
from app.models.rbac import user_roles


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self, *, include_deleted: bool = False):
        stmt = select(User).options(selectinload(User.roles).selectinload(Role.permissions))
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        return stmt

    def get_by_id(self, user_id: UUID, *, include_deleted: bool = False) -> User | None:
        return self.db.scalar(self._base_query(include_deleted=include_deleted).where(User.id == user_id))

    def get_by_email(self, email: str, *, include_deleted: bool = False) -> User | None:
        return self.db.scalar(
            self._base_query(include_deleted=include_deleted).where(User.email == email.lower())
        )

    def get_by_google_sub(self, google_sub: str) -> User | None:
        return self.db.scalar(
            self._base_query().where(User.google_sub == google_sub)
        )

    def get_by_github_id(self, github_id: str) -> User | None:
        return self.db.scalar(
            self._base_query().where(User.github_id == github_id)
        )

    def get_role_by_name(self, name: str) -> Role | None:
        return self.db.scalar(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )

    def list_roles(self) -> list[Role]:
        return list(
            self.db.scalars(select(Role).options(selectinload(Role.permissions)).order_by(Role.name)).all()
        )

    def list_permissions(self):
        from app.models import Permission

        return list(self.db.scalars(select(Permission).order_by(Permission.code)).all())

    def create(
        self,
        *,
        email: str,
        full_name: str,
        hashed_password: str | None,
        status: UserStatus = UserStatus.PENDING_VERIFICATION,
        roles: list[Role] | None = None,
        google_sub: str | None = None,
        github_id: str | None = None,
        is_email_verified: bool = False,
        avatar_url: str | None = None,
    ) -> User:
        user = User(
            email=email.lower().strip(),
            full_name=full_name.strip(),
            hashed_password=hashed_password,
            status=status,
            google_sub=google_sub,
            github_id=github_id,
            is_email_verified=is_email_verified,
            avatar_url=avatar_url,
        )
        if roles:
            user.roles = roles
        self.db.add(user)
        self.db.flush()
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def soft_delete(self, user: User) -> User:
        user.is_deleted = True
        user.deleted_at = datetime.now(UTC)
        user.status = UserStatus.INACTIVE
        return self.save(user)

    def list_users(
        self,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
        status: UserStatus | None = None,
        role: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[User], int]:
        filters = []
        if not include_deleted:
            filters.append(User.is_deleted.is_(False))
        if status is not None:
            filters.append(User.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            filters.append(or_(func.lower(User.email).like(term), func.lower(User.full_name).like(term)))

        count_stmt = select(func.count(func.distinct(User.id))).select_from(User)
        list_stmt = self._base_query(include_deleted=include_deleted)

        if role:
            count_stmt = count_stmt.join(user_roles, user_roles.c.user_id == User.id).join(
                Role, Role.id == user_roles.c.role_id
            ).where(Role.name == role)
            list_stmt = list_stmt.join(user_roles, user_roles.c.user_id == User.id).join(
                Role, Role.id == user_roles.c.role_id
            ).where(Role.name == role)

        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = int(self.db.scalar(count_stmt) or 0)
        rows = list(
            self.db.scalars(
                list_stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
            ).unique().all()
        )
        return rows, total

    def count_by_status(self, status: UserStatus, *, include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(User).where(User.status == status)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        return int(self.db.scalar(stmt) or 0)

    def count_users(self, *, include_deleted: bool = False, verified_only: bool = False) -> int:
        stmt = select(func.count()).select_from(User)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        if verified_only:
            stmt = stmt.where(User.is_email_verified.is_(True))
        return int(self.db.scalar(stmt) or 0)

    def count_deleted(self) -> int:
        return int(
            self.db.scalar(select(func.count()).select_from(User).where(User.is_deleted.is_(True))) or 0
        )

    def count_registered_since(self, since: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.is_deleted.is_(False), User.created_at >= since)
            )
            or 0
        )

    def count_by_role(self) -> dict[str, int]:
        stmt = (
            select(Role.name, func.count(User.id))
            .select_from(Role)
            .outerjoin(user_roles, user_roles.c.role_id == Role.id)
            .outerjoin(User, (User.id == user_roles.c.user_id) & (User.is_deleted.is_(False)))
            .group_by(Role.name)
            .order_by(Role.name)
        )
        return {name: int(count or 0) for name, count in self.db.execute(stmt).all()}
