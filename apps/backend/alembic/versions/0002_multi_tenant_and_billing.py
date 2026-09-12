"""Multi-tenant organization and usage metering tables.

Revision ID: 0002_multi_tenant_and_billing
Revises: 0001_initial
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_multi_tenant_and_billing"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tenants and usage_records tables, and alter telemetry and eval tables."""
    # 1. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("tier", sa.String(length=50), nullable=False, server_default="community"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_tenants_api_key_hash",
        "tenants",
        ["api_key_hash"],
        unique=True,
    )

    # 2. Create usage_records table
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_usage_records_tenant_id",
        "usage_records",
        ["tenant_id"],
        unique=False,
    )

    # 3. Add tenant_id, hourly_rate_usd, is_shadow to telemetry_events
    with op.batch_alter_table("telemetry_events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id"),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column("hourly_rate_usd", sa.Float(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("is_shadow", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index("ix_telemetry_events_tenant_id", ["tenant_id"])

    # 4. Add tenant_id to evaluation_jobs
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id"),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_index("ix_evaluation_jobs_tenant_id", ["tenant_id"])


def downgrade() -> None:
    """Drop multi-tenant structures and columns."""
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.drop_index("ix_evaluation_jobs_tenant_id")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("telemetry_events") as batch_op:
        batch_op.drop_index("ix_telemetry_events_tenant_id")
        batch_op.drop_column("is_shadow")
        batch_op.drop_column("hourly_rate_usd")
        batch_op.drop_column("tenant_id")

    op.drop_index("ix_usage_records_tenant_id", table_name="usage_records")
    op.drop_table("usage_records")

    op.drop_index("ix_tenants_api_key_hash", table_name="tenants")
    op.drop_table("tenants")
