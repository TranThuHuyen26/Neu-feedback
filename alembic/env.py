"""Alembic: quản lý thay đổi cấu trúc bảng. Lệnh thường dùng:
alembic upgrade head                          # tạo/cập nhật bảng
alembic revision --autogenerate -m "mô tả"    # sau khi sửa app/models.py
"""

from alembic import context

from app import models  # noqa: F401  (nạp các bảng)
from app.database import Base, engine

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=str(engine.url), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
