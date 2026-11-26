"""Nhiều tệp đính kèm cho một câu hỏi (bảng question_attachments) — chuyển tệp cũ sang bảng mới, bỏ 2 cột cũ

Revision ID: 0007
Revises: 0006
"""

import os
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TYPES = {
    ".png": "IMG",
    ".jpg": "IMG",
    ".jpeg": "IMG",
    ".gif": "IMG",
    ".webp": "IMG",
    ".pdf": "PDF",
    ".docx": "DOC",
    ".pptx": "PPT",
    ".xlsx": "XLS",
}


def upgrade() -> None:
    op.create_table(
        "question_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_question_attachments_question_id", "question_attachments", ["question_id"])
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, attachment_name, attachment_path, created_at FROM questions "
            "WHERE attachment_path IS NOT NULL"
        )
    ).fetchall()
    for qid, name, path, created in rows:  # chuyển tệp đính kèm cũ (1 tệp/câu) sang bảng mới
        ext = os.path.splitext(name or path)[1].lower()
        size = os.path.getsize(path) if path and os.path.exists(path) else 0
        conn.execute(
            sa.text(
                "INSERT INTO question_attachments (question_id, filename, stored_path, file_type, size_bytes, created_at) "
                "VALUES (:q, :n, :p, :t, :s, :c)"
            ),
            {
                "q": qid,
                "n": name or os.path.basename(path),
                "p": path,
                "t": TYPES.get(ext, "FILE"),
                "s": size,
                "c": created or datetime.now(timezone.utc),
            },
        )
    with op.batch_alter_table("questions") as b:
        b.drop_column("attachment_path")
        b.drop_column("attachment_name")


def downgrade() -> None:
    with op.batch_alter_table("questions") as b:
        b.add_column(sa.Column("attachment_name", sa.String(length=255), nullable=True))
        b.add_column(sa.Column("attachment_path", sa.String(length=500), nullable=True))
    conn = op.get_bind()
    for qid, name, path in conn.execute(
        sa.text(
            "SELECT question_id, filename, stored_path FROM question_attachments " "ORDER BY id"
        )
    ).fetchall():
        conn.execute(
            sa.text(
                "UPDATE questions SET attachment_name = :n, attachment_path = :p "
                "WHERE id = :q AND attachment_path IS NULL"
            ),
            {"n": name, "p": path, "q": qid},
        )
    op.drop_index("ix_question_attachments_question_id", "question_attachments")
    op.drop_table("question_attachments")
