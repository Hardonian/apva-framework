"""Initial APVA tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create APVA telemetry and evaluation tables."""
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("app_name", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("human_baseline_time", sa.Float(), nullable=False),
        sa.Column("ai_augmented_time", sa.Float(), nullable=False),
        sa.Column("guardrail_latency_tax", sa.Float(), nullable=False),
        sa.Column("session_iterations", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_telemetry_events_app_name",
        "telemetry_events",
        ["app_name"],
        unique=False,
    )
    op.create_index(
        "ix_telemetry_events_session_id",
        "telemetry_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_telemetry_events_run_id",
        "telemetry_events",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_telemetry_events_created_at",
        "telemetry_events",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "evaluation_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transcript_id", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("exact_span_recall", sa.Float(), nullable=True),
        sa.Column("llm_faithfulness_score", sa.Float(), nullable=True),
        sa.Column("precision_score", sa.Float(), nullable=True),
        sa.Column("rag_reliability_coefficient", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_evaluation_jobs_transcript_id",
        "evaluation_jobs",
        ["transcript_id"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_jobs_status",
        "evaluation_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_jobs_created_at",
        "evaluation_jobs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop APVA telemetry and evaluation tables."""
    op.drop_index("ix_evaluation_jobs_created_at", table_name="evaluation_jobs")
    op.drop_index("ix_evaluation_jobs_status", table_name="evaluation_jobs")
    op.drop_index("ix_evaluation_jobs_transcript_id", table_name="evaluation_jobs")
    op.drop_table("evaluation_jobs")
    op.drop_index("ix_telemetry_events_created_at", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_run_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_session_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_app_name", table_name="telemetry_events")
    op.drop_table("telemetry_events")
