"""Lưu thời gian NEU AI trả lời mỗi tin nhắn (phục vụ trang Thống kê)."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("latency_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "latency_ms")
