"""Sao lưu toàn bộ dữ liệu ra một file JSON trong thư mục backups/.

Chạy: python -m scripts.backup
(Gói miễn phí của Supabase không có sao lưu tự động — nên chạy lệnh này trước mỗi buổi demo.)
"""

import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app import models  # noqa: F401  (nạp các bảng)
from app.config import BASE_DIR
from app.database import Base, SessionLocal


def _default(o):
    return o.isoformat() if isinstance(o, (date, datetime)) else str(o)


def main():
    db = SessionLocal()
    data = {
        t.name: [dict(r._mapping) for r in db.execute(select(t)).all()]
        for t in Base.metadata.sorted_tables
    }
    folder = BASE_DIR / "backups"
    folder.mkdir(exist_ok=True)
    path = folder / f"neu_feedback_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, default=_default), encoding="utf-8")
    print(
        f"Đã sao lưu {sum(len(v) for v in data.values())} dòng dữ liệu vào {path.relative_to(BASE_DIR)}"
    )


if __name__ == "__main__":
    main()
