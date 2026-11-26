"""Đọc lại toàn bộ tài liệu đã tải lên theo cách chia đoạn mới (bỏ trang bìa/mục lục, gộp slide…).

Chạy sau khi cập nhật phiên bản hoặc sau khi bật Gemini API key:
    python -m scripts.reindex
"""

from pathlib import Path

from sqlalchemy import select

from app import models  # noqa: F401
from app.database import SessionLocal
from app.models import Material
from app.routers.materials import _index_material
from app.services.files import resolve_stored


def main():
    db = SessionLocal()
    mats = db.scalars(select(Material)).all()
    if not mats:
        print("Chưa có tài liệu nào để đọc lại.")
        return
    for m in mats:
        path = resolve_stored(m.stored_path)
        if not path.exists():
            print(f"  Lỗi: {m.filename}: không tìm thấy tệp trên máy")
            continue
        _index_material(db, m, path)
        db.commit()
        print(
            f"  {m.filename}: {m.chunk_count} đoạn"
            + (" (không đọc được nội dung)" if m.status == "failed" else "")
        )
    print(f"Đã đọc lại {len(mats)} tài liệu.")


if __name__ == "__main__":
    main()
