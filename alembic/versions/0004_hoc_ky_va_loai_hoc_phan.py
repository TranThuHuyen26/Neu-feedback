"""Học kỳ (Thu/Xuân/Hè), loại học phần (15/10 buổi), lịch học kỳ Hè

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.String(length=9), nullable=False),
        sa.Column("term", sa.String(length=4), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "term", name="uq_semesters_year_term"),
    )
    with op.batch_alter_table("classes") as b:
        b.add_column(sa.Column("semester_id", sa.Integer(), nullable=True))
        b.add_column(
            sa.Column("course_type", sa.String(length=12), nullable=False, server_default="regular")
        )
        b.add_column(sa.Column("meeting_days", sa.JSON(), nullable=True))
        b.create_index("ix_classes_semester_id", ["semester_id"])
        b.create_foreign_key("fk_classes_semester", "semesters", ["semester_id"], ["id"])


def downgrade() -> None:
    raise NotImplementedError(
        "Không hỗ trợ quay lại — hãy tạo lại dữ liệu mẫu: python -m scripts.seed --reset"
    )
