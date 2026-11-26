"""Học kỳ: hệ thống TỰ tạo khi Giảng viên tạo lớp (theo ngày bắt đầu học: tháng 7–11 Thu, 12–4 Xuân, 5–6 Hè).
Admin không phải khai báo; mọi người xem danh sách để lọc lớp và thống kê."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Classroom, Semester, User
from app.security import get_current_user
from app.services.core import semester_end, semester_label
from app.utils import today_vn

router = APIRouter(prefix="/api", tags=["Học kỳ"])
TERM_ORDER = {"thu": 0, "xuan": 1, "he": 2}


def semester_out(db: Session, s: Semester) -> dict:
    end, today = semester_end(s), today_vn()
    return {
        "id": s.id,
        "year": s.year,
        "term": s.term,
        "label": semester_label(s),
        "start_date": s.start_date,
        "end_date": end,
        "is_current": s.start_date <= today <= end,
        "class_count": db.scalar(
            select(func.count()).select_from(Classroom).where(Classroom.semester_id == s.id)
        ),
    }


def all_semesters(db: Session) -> list[Semester]:
    return sorted(db.scalars(select(Semester)).all(), key=lambda s: (s.year, TERM_ORDER[s.term]))


def current_semester(db: Session) -> Semester | None:
    """Học kỳ đang diễn ra; nếu đang nghỉ giữa các kỳ thì lấy kỳ gần nhất đã bắt đầu."""
    sems, today = all_semesters(db), today_vn()
    now = [s for s in sems if s.start_date <= today <= semester_end(s)]
    if now:
        return now[0]
    started = [s for s in sems if s.start_date <= today]
    return started[-1] if started else (sems[0] if sems else None)


@router.get("/semesters", summary="Danh sách học kỳ (mới nhất trước)")
def list_semesters(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cur = current_semester(db)
    return [
        {**semester_out(db, s), "is_default": cur is not None and s.id == cur.id}
        for s in reversed(all_semesters(db))
    ]
