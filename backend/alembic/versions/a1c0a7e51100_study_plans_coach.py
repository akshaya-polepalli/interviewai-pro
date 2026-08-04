"""study_plans and coach_messages

Revision ID: a1c0a7e51100
Revises: 32f0f7b28943
Create Date: 2026-08-04 22:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1c0a7e51100"
down_revision: Union[str, None] = "32f0f7b28943"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    study_plan_status = postgresql.ENUM(
        "active",
        "completed",
        "archived",
        name="study_plan_status",
        create_type=False,
    )
    coach_message_role = postgresql.ENUM(
        "user",
        "assistant",
        name="coach_message_role",
        create_type=False,
    )
    study_plan_status.create(op.get_bind(), checkfirst=True)
    coach_message_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "study_plans",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            study_plan_status,
            server_default="active",
            nullable=False,
        ),
        sa.Column("weeks", sa.Integer(), server_default="2", nullable=False),
        sa.Column("focus_areas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_provider", sa.String(length=64), nullable=True),
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
    )
    op.create_index(op.f("ix_study_plans_status"), "study_plans", ["status"], unique=False)
    op.create_index(op.f("ix_study_plans_user_id"), "study_plans", ["user_id"], unique=False)

    op.create_table(
        "study_plan_tasks",
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("day_offset", sa.Integer(), server_default="0", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("resource_path", sa.String(length=255), nullable=True),
        sa.Column("is_done", sa.Boolean(), server_default="false", nullable=False),
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
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_study_plan_tasks_plan_id"), "study_plan_tasks", ["plan_id"], unique=False
    )

    op.create_table(
        "coach_messages",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", coach_message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
    )
    op.create_index(
        op.f("ix_coach_messages_user_id"), "coach_messages", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_coach_messages_user_id"), table_name="coach_messages")
    op.drop_table("coach_messages")
    op.drop_index(op.f("ix_study_plan_tasks_plan_id"), table_name="study_plan_tasks")
    op.drop_table("study_plan_tasks")
    op.drop_index(op.f("ix_study_plans_user_id"), table_name="study_plans")
    op.drop_index(op.f("ix_study_plans_status"), table_name="study_plans")
    op.drop_table("study_plans")
    postgresql.ENUM(name="coach_message_role").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="study_plan_status").drop(op.get_bind(), checkfirst=True)
