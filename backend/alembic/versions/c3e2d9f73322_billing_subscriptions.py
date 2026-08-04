"""user_subscriptions billing

Revision ID: c3e2d9f73322
Revises: b2d1c8e62211
Create Date: 2026-08-04 23:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3e2d9f73322"
down_revision: Union[str, None] = "b2d1c8e62211"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    plan_code = postgresql.ENUM("free", "pro", "team", name="plan_code", create_type=False)
    sub_status = postgresql.ENUM(
        "active",
        "trialing",
        "past_due",
        "canceled",
        name="subscription_status",
        create_type=False,
    )
    plan_code.create(op.get_bind(), checkfirst=True)
    sub_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_subscriptions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan", plan_code, server_default="free", nullable=False),
        sa.Column("status", sub_status, server_default="active", nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default="false", nullable=False),
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
        sa.UniqueConstraint("user_id", name="uq_user_subscriptions_user_id"),
    )
    op.create_index(op.f("ix_user_subscriptions_plan"), "user_subscriptions", ["plan"], unique=False)
    op.create_index(
        op.f("ix_user_subscriptions_status"), "user_subscriptions", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_user_subscriptions_stripe_customer_id"),
        "user_subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_subscriptions_stripe_subscription_id"),
        "user_subscriptions",
        ["stripe_subscription_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_subscriptions_user_id"), "user_subscriptions", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_subscriptions_user_id"), table_name="user_subscriptions")
    op.drop_index(
        op.f("ix_user_subscriptions_stripe_subscription_id"), table_name="user_subscriptions"
    )
    op.drop_index(op.f("ix_user_subscriptions_stripe_customer_id"), table_name="user_subscriptions")
    op.drop_index(op.f("ix_user_subscriptions_status"), table_name="user_subscriptions")
    op.drop_index(op.f("ix_user_subscriptions_plan"), table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
    postgresql.ENUM(name="subscription_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="plan_code").drop(op.get_bind(), checkfirst=True)
