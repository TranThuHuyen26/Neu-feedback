"""Tên lớp duy nhất trong cùng học kỳ; bỏ 4 cột cũ không dùng

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None
NC = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("classes", naming_convention=NC, recreate="always") as b:
            b.drop_constraint("uq_classes_code", type_="unique")
            b.create_unique_constraint("uq_classes_code_semester", ["code", "semester_id"])
            b.create_index("ix_classes_code", ["code"])
    else:
        insp = sa.inspect(bind)
        for uc in insp.get_unique_constraints("classes"):
            if uc["column_names"] == ["code"]:
                op.drop_constraint(uc["name"], "classes", type_="unique")
        op.create_unique_constraint("uq_classes_code_semester", "classes", ["code", "semester_id"])
        op.create_index("ix_classes_code", "classes", ["code"])
    with op.batch_alter_table("sessions") as b:
        b.drop_column("status")
        b.drop_column("closed_at")
    with op.batch_alter_table("questions") as b:
        b.drop_column("auto_answered")
    with op.batch_alter_table("answers") as b:
        b.drop_column("auto")


def downgrade() -> None:
    raise NotImplementedError(
        "Không hỗ trợ quay lại — hãy tạo lại dữ liệu mẫu: python -m scripts.seed --reset"
    )
