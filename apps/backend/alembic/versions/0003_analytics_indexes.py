"""Add composite indexes for tenant analytics and usage queries.

Revision ID: 0003_analytics_indexes
Revises: 0002_multi_tenant_and_billing
Create Date: 2026-09-12
"""

from __future__ import annotations

from alembic import op

revision = "0003_analytics_indexes"
down_revision = "0002_multi_tenant_and_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes matching tenant-scoped dashboard and billing access paths."""
    op.create_index(
        "ix_telemetry_events_tenant_created",
        "telemetry_events",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_telemetry_events_tenant_app_created",
        "telemetry_events",
        ["tenant_id", "app_name", "created_at"],
    )
    op.create_index(
        "ix_evaluation_jobs_tenant_status",
        "evaluation_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_evaluation_jobs_tenant_created",
        "evaluation_jobs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_usage_records_tenant_created",
        "usage_records",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_usage_records_tenant_event",
        "usage_records",
        ["tenant_id", "event_type"],
    )


def downgrade() -> None:
    """Remove tenant analytics and usage indexes."""
    op.drop_index("ix_usage_records_tenant_event", table_name="usage_records")
    op.drop_index("ix_usage_records_tenant_created", table_name="usage_records")
    op.drop_index("ix_evaluation_jobs_tenant_created", table_name="evaluation_jobs")
    op.drop_index("ix_evaluation_jobs_tenant_status", table_name="evaluation_jobs")
    op.drop_index("ix_telemetry_events_tenant_app_created", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_tenant_created", table_name="telemetry_events")
