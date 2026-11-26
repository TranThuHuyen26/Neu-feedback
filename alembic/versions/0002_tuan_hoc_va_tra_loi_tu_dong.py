"""Tuần học (15 tuần, tuần nghỉ), tài liệu theo tuần, trả lời tự động cho câu hỏi tương đồng

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_breaks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"], name="fk_class_breaks_class", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "week_start", name="uq_class_breaks_week"),
    )
    op.create_index("ix_class_breaks_class_id", "class_breaks", ["class_id"])

    with op.batch_alter_table("classes") as b:
        b.add_column(
            sa.Column("start_date", sa.Date(), nullable=False, server_default="2026-08-03")
        )

    with op.batch_alter_table("sessions") as b:
        b.add_column(sa.Column("description", sa.Text(), nullable=True))
        b.drop_index("uq_one_open_session_per_class")  # không còn khái niệm "một phiên đang mở"

    with op.batch_alter_table("questions") as b:
        b.add_column(
            sa.Column("auto_answered", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        b.add_column(sa.Column("no_auto", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("answers") as b:
        b.add_column(sa.Column("auto", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("source_question_id", sa.Integer(), nullable=True))
        b.create_foreign_key(
            "fk_answers_source_question",
            "questions",
            ["source_question_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("materials") as b:
        b.add_column(sa.Column("week_id", sa.Integer(), nullable=True))
        b.create_index("ix_materials_week_id", ["week_id"])
        b.create_foreign_key(
            "fk_materials_week", "sessions", ["week_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("similar_groups") as b:
        b.add_column(sa.Column("class_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("answer_text", sa.Text(), nullable=True))
        b.add_column(sa.Column("answered_by", sa.Integer(), nullable=True))
        b.add_column(sa.Column("source_question_id", sa.Integer(), nullable=True))
        b.create_index("ix_similar_groups_class_id", ["class_id"])
        b.create_foreign_key("fk_groups_class", "classes", ["class_id"], ["id"], ondelete="CASCADE")
        b.create_foreign_key("fk_groups_answered_by", "users", ["answered_by"], ["id"])
        b.create_foreign_key(
            "fk_groups_source_question",
            "questions",
            ["source_question_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # nhóm cũ: gán lớp theo phiên/tuần tạo nhóm
    op.execute(
        "UPDATE similar_groups SET class_id = (SELECT class_id FROM sessions WHERE sessions.id = similar_groups.session_id)"
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Không hỗ trợ quay lại phiên bản 0001 — hãy tạo lại dữ liệu mẫu bằng: python -m scripts.seed --reset"
    )
