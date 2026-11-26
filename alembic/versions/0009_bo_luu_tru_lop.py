"""Bỏ chức năng lưu trữ lớp: đưa mọi lớp đã lưu trữ trở lại danh sách (cột is_archived giữ nguyên, không dùng nữa)

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE classes SET is_archived = FALSE WHERE is_archived = TRUE")


def downgrade() -> None:
    pass
