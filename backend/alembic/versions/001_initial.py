"""initial migration - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "operator", "viewer"), server_default="viewer"),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("group_name", sa.String(100), server_default="默认分组"),
        sa.Column("engine", sa.String(30), server_default="requests"),
        sa.Column("config_json", sa.JSON, server_default="{}"),
        sa.Column("status", sa.Enum("idle", "running", "paused", "error"), server_default="idle"),
        sa.Column("total_crawled", sa.Integer, server_default="0"),
        sa.Column("total_parsed", sa.Integer, server_default="0"),
        sa.Column("last_run_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.BigInteger, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Scripts table
    op.create_table(
        "scripts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.BigInteger, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_type", sa.Enum("crawl", "parse", "full"), server_default="full"),
        sa.Column("code", sa.Text, server_default=""),
        sa.Column("file_path", sa.String(500), server_default=""),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Task runs table
    op.create_table(
        "task_runs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.BigInteger, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger", sa.Enum("manual", "schedule", "api"), server_default="manual"),
        sa.Column("status", sa.Enum("pending", "running", "success", "failed", "timeout", "cancelled"), server_default="pending"),
        sa.Column("pid", sa.Integer, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("result_summary", sa.JSON, nullable=True),
    )

    # Run logs table
    op.create_table(
        "run_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.BigInteger, sa.ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.String(20), server_default="INFO"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
    )

    # Schedules table
    op.create_table(
        "schedules",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.BigInteger, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_type", sa.Enum("cron", "interval", "once"), server_default="interval"),
        sa.Column("cron_expr", sa.String(100), nullable=True),
        sa.Column("interval_seconds", sa.Integer, nullable=True),
        sa.Column("run_at", sa.DateTime, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("last_run_at", sa.DateTime, nullable=True),
        sa.Column("next_run_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("schedules")
    op.drop_table("run_logs")
    op.drop_table("task_runs")
    op.drop_table("scripts")
    op.drop_table("tasks")
    op.drop_table("users")
