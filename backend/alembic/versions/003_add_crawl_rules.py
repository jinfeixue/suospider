"""add crawl_rules table

Revision ID: 003_add_crawl_rules
Revises: 002_add_task_type_datasource
Create Date: 2026-06-09 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_add_crawl_rules"
down_revision: Union[str, None] = "002_add_task_type_datasource"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crawl_rules",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("domain", sa.String(200), nullable=False, index=True, comment="域名"),
        sa.Column("url_pattern", sa.String(500), comment="URL匹配规则"),
        sa.Column("detail_link_xpath", sa.Text, comment="详情页链接XPath"),
        sa.Column("pagination_type", sa.String(50), comment="翻页类型"),
        sa.Column("pagination_xpath", sa.Text, comment="翻页XPath"),
        sa.Column("pagination_pattern", sa.String(200), comment="URL翻页规律"),
        sa.Column("field_xpaths", sa.JSON, comment="字段XPath映射"),
        sa.Column("recommended_engine", sa.String(50), server_default="requests", comment="推荐引擎"),
        sa.Column("use_count", sa.Integer, server_default="0", comment="使用次数"),
        sa.Column("success_count", sa.Integer, server_default="0", comment="成功次数"),
        sa.Column("last_used_at", sa.DateTime, comment="最后使用时间"),
        sa.Column("last_success_at", sa.DateTime, comment="最后成功时间"),
        sa.Column("is_active", sa.Boolean, server_default="1", comment="是否启用"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("crawl_rules")
