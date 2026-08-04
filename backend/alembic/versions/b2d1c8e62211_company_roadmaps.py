"""user_company_roadmaps

Revision ID: b2d1c8e62211
Revises: a1c0a7e51100
Create Date: 2026-08-04 23:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2d1c8e62211"
down_revision: Union[str, None] = "a1c0a7e51100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    roadmap_company = postgresql.ENUM(
        "google",
        "amazon",
        "microsoft",
        "meta",
        "apple",
        "netflix",
        "stripe",
        "openai",
        "general",
        name="roadmap_target_company",
        create_type=False,
    )
    enrollment_status = postgresql.ENUM(
        "active",
        "completed",
        "archived",
        name="roadmap_enrollment_status",
        create_type=False,
    )
    roadmap_company.create(op.get_bind(), checkfirst=True)
    enrollment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_company_roadmaps",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company", roadmap_company, nullable=False),
        sa.Column(
            "status",
            enrollment_status,
            server_default="active",
            nullable=False,
        ),
        sa.Column("manual_done", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "company", name="uq_user_company_roadmap"),
    )
    op.create_index(
        op.f("ix_user_company_roadmaps_company"),
        "user_company_roadmaps",
        ["company"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_company_roadmaps_status"),
        "user_company_roadmaps",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_company_roadmaps_user_id"),
        "user_company_roadmaps",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_company_roadmaps_user_id"), table_name="user_company_roadmaps")
    op.drop_index(op.f("ix_user_company_roadmaps_status"), table_name="user_company_roadmaps")
    op.drop_index(op.f("ix_user_company_roadmaps_company"), table_name="user_company_roadmaps")
    op.drop_table("user_company_roadmaps")
    postgresql.ENUM(name="roadmap_enrollment_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="roadmap_target_company").drop(op.get_bind(), checkfirst=True)
