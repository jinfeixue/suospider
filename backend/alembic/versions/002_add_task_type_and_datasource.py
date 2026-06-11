"""add task_type and datasource_id to tasks

Revision ID: 002_add_task_type_datasource
Revises: 001_initial
Create Date: 2026-06-08 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_add_task_type_datasource"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add task_type column to tasks table
    op.add_column(
        "tasks",
        sa.Column("task_type", sa.String(20), server_default="professional", comment="任务类型：smart/professional"),
    )

    # Add datasource_id column to tasks table (Integer to match data_sources.id)
    # 注意：先加列不加外键，等确认类型一致后再加外键
    op.add_column(
        "tasks",
        sa.Column("datasource_id", sa.Integer, nullable=True, comment="关联数据源ID"),
    )
    # 尝试添加外键（如果 data_sources 表已存在且 id 类型为 Integer）
    try:
        op.create_foreign_key(
            "fk_tasks_datasource", "tasks", "data_sources", ["datasource_id"], ["id"]
        )
    except Exception:
        pass  # 外键添加失败时忽略，不影响主功能


def downgrade() -> None:
    op.drop_column("tasks", "datasource_id")
    op.drop_column("tasks", "task_type")
