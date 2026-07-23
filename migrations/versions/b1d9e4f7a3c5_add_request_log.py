"""add request_log table for traffic and usage analytics

Revision ID: b1d9e4f7a3c5
Revises: c2a4f6b8d0e2
Create Date: 2026-07-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1d9e4f7a3c5"
down_revision: Union[str, None] = "c2a4f6b8d0e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("route_type", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_request_log_timestamp", "request_log", ["timestamp"])
    op.create_index("ix_request_log_route_type", "request_log", ["route_type"])


def downgrade() -> None:
    op.drop_index("ix_request_log_route_type", table_name="request_log")
    op.drop_index("ix_request_log_timestamp", table_name="request_log")
    op.drop_table("request_log")
