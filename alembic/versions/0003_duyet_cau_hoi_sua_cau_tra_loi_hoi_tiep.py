"""Bỏ tuần nghỉ; duyệt câu hỏi tương đồng; sửa câu trả lời; hỏi tiếp; thông báo gộp; tệp đính kèm cho NEU AI

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_class_breaks_class_id", table_name="class_breaks")
    op.drop_table("class_breaks")  # lịch 15 tuần luôn liền mạch

    with op.batch_alter_table("questions") as b:
        b.add_column(sa.Column("reuse_from_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("reuse_score", sa.Float(), nullable=True))
        b.add_column(
            sa.Column("followup_pending", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        b.create_foreign_key(
            "fk_questions_reuse_from", "questions", ["reuse_from_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("answers") as b:
        b.add_column(sa.Column("source_answer_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True))
        b.create_index("ix_answers_source_answer_id", ["source_answer_id"])
        b.create_foreign_key(
            "fk_answers_source_answer", "answers", ["source_answer_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("notifications") as b:
        b.add_column(sa.Column("key", sa.String(length=120), nullable=True))
        b.add_column(sa.Column("count", sa.Integer(), nullable=False, server_default="1"))
        b.create_index("ix_notifications_key", ["key"])

    with op.batch_alter_table("chat_messages") as b:
        b.add_column(sa.Column("attachments", sa.JSON(), nullable=True))

    op.create_table(
        "followups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reply", sa.Text(), nullable=True),
        sa.Column("replied_by", sa.Integer(), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], name="fk_followups_question", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["replied_by"], ["users.id"], name="fk_followups_replied_by"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_followups_question_id", "followups", ["question_id"])

    # bản 2.0 có trả lời tự động: chuyển các câu đó thành câu trả lời đã gửi bình thường
    op.execute("UPDATE answers SET auto = false")
    op.execute("UPDATE questions SET auto_answered = false")


def downgrade() -> None:
    raise NotImplementedError(
        "Không hỗ trợ quay lại — hãy tạo lại dữ liệu mẫu bằng: python -m scripts.seed --reset"
    )
