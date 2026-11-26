"""Điền chủ đề + mô tả cho các tuần còn TRỐNG của các lớp mẫu trong CSDL đang chạy. KHÔNG xóa hay sửa dữ liệu khác.

Chạy (từ thư mục gốc dự án):
    python -m scripts.fill_weeks
"""

from sqlalchemy import select

from app.database import SessionLocal
from app.models import ClassSession, Classroom
from scripts.seed import HQT_TOPICS, KTPM_TOPICS, LTUD_TOPICS, QLDA_TOPICS

TOPICS = {
    "HQTCSDL_01": HQT_TOPICS,
    "KTPM_01": KTPM_TOPICS,
    "LTUD_01": LTUD_TOPICS,
    "QLDA_01": QLDA_TOPICS,
}


def main():
    db = SessionLocal()
    filled = 0
    for c in db.scalars(select(Classroom)):
        topics = TOPICS.get(c.code)
        if not topics:
            continue
        for w in db.scalars(select(ClassSession).where(ClassSession.class_id == c.id)):
            if (w.title or "").strip():
                continue  # tuần đã có nội dung: giữ nguyên
            w.title = topics[min(w.number - 1, len(topics) - 1)]
            w.description = (
                f"Mục tiêu: nắm được nội dung \u201c{w.title}\u201d. Sinh viên đọc trước tài liệu tuần, "
                "làm bài tập nhỏ trên lớp và gửi câu hỏi ẩn danh nếu chưa rõ."
            )
            filled += 1
    db.commit()
    print(f"Đã điền nội dung cho {filled} tuần còn trống.")


if __name__ == "__main__":
    main()
