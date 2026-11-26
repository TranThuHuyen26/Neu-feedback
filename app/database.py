"""Kết nối cơ sở dữ liệu PostgreSQL (hệ thống không còn hỗ trợ SQLite)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

url = settings.database_url.strip()
if not url:
    raise RuntimeError(
        "Chưa cấu hình DATABASE_URL. Mở file .env và đặt, ví dụ:\n"
        "    DATABASE_URL=postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/neu_feedback"
    )
# Chấp nhận cả dạng postgresql:// và postgres:// (ví dụ chuỗi sao chép từ Supabase) — tự đổi sang trình điều khiển psycopg.
for prefix in ("postgresql://", "postgres://"):
    if url.startswith(prefix):
        url = "postgresql+psycopg://" + url[len(prefix) :]
if not url.startswith("postgresql+psycopg://"):
    raise RuntimeError(
        "DATABASE_URL phải là PostgreSQL (bắt đầu bằng postgresql+psycopg://). Hệ thống không còn hỗ trợ SQLite."
    )

settings.upload_dir.parent.mkdir(parents=True, exist_ok=True)
# pool_pre_ping giúp tự kết nối lại khi kết nối nhàn rỗi bị máy chủ đóng
engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
