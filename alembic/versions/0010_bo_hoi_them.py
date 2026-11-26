"""Bỏ tính năng hỏi thêm Giảng viên: xóa bảng followups và cột questions.followup_pending

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("followups")
    op.drop_column("questions", "followup_pending")


def downgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("followup_pending", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "followups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("reply", sa.Text()),
        sa.Column("replied_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
    )
