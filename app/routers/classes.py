"""Lớp học: tạo/sửa lớp, lịch 15 tuần liền mạch, tham gia bằng mã, danh sách sinh viên, thống kê theo tuần."""

from pathlib import Path
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Answer,
    ClassSession,
    Classroom,
    Enrollment,
    Material,
    Question,
    Semester,
    User,
)
from app.schemas import AddStudentsIn, ClassCreate, ClassUpdate, JoinIn, Msg
from app.security import get_current_user, require_role
from app.services.core import (
    semester_for_date,
    term_of,
    semester_label,
    unit_count,
    unit_label,
    class_timeline,
    get_class_for_user,
    get_owned_class,
    layout_weeks,
    monday_of,
    question_out,
    week_out,
    week_status,
)
from app.utils import today_vn, as_utc, new_join_code
from app.services.files import resolve_stored

router = APIRouter(prefix="/api", tags=["Lớp học"])
settings = get_settings()


def class_out(db: Session, c: Classroom, user: User) -> dict:
    tl = class_timeline(db, c)
    q_counts = dict(
        db.execute(
            select(Question.status, func.count())
            .where(Question.class_id == c.id)
            .group_by(Question.status)
        ).all()
    )
    cur = db.get(ClassSession, tl["current_week_id"]) if tl["current_week_id"] else None
    data = {
        "id": c.id,
        "code": c.code,
        "subject": c.subject,
        "semester": c.semester,
        "faculty": c.faculty,
        "semester_id": c.semester_id,
        "course_type": c.course_type,
        "unit_label": unit_label(c),
        "unit_count": unit_count(c),
        "meeting_days": c.meeting_days,
        "lecturer_name": c.lecturer.full_name if c.lecturer else None,
        "timeline": tl,
        "current_week": {"id": cur.id, "number": cur.number, "title": cur.title} if cur else None,
        "material_count": db.scalar(
            select(func.count()).select_from(Material).where(Material.class_id == c.id)
        ),
        "student_count": db.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.class_id == c.id)
        ),
        "question_count": sum(v for k, v in q_counts.items() if k != "deleted"),
    }
    if user.role in ("lecturer", "admin"):
        data["join_code"] = c.join_code
        data["answered_count"] = q_counts.get("answered", 0)
        data["waiting_count"] = q_counts.get("waiting", 0)
    return data


# ---------------------------------------------------------------- danh sách & chi tiết
@router.get("/classes", summary="Lớp học của tôi (sinh viên: đã tham gia · Giảng viên: đang dạy)")
def my_classes(
    q: str | None = None,
    semester_id: int | None = None,
    user: User = Depends(require_role("student", "lecturer")),
    db: Session = Depends(get_db),
):
    if user.role == "lecturer":
        stmt = select(Classroom).where(Classroom.lecturer_id == user.id)
    else:
        stmt = (
            select(Classroom)
            .join(Enrollment, Enrollment.class_id == Classroom.id)
            .where(Enrollment.student_id == user.id)
        )
    if semester_id:
        stmt = stmt.where(Classroom.semester_id == semester_id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Classroom.code).like(like) | func.lower(Classroom.subject).like(like)
        )
    return [class_out(db, c, user) for c in db.scalars(stmt.order_by(Classroom.code)).all()]


@router.get("/classes/{class_id}", summary="Chi tiết lớp")
def class_detail(
    class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return class_out(db, get_class_for_user(db, class_id, user), user)


# ---------------------------------------------------------------- giảng viên quản lý lớp
@router.post(
    "/classes",
    status_code=201,
    summary="Tạo lớp theo học kỳ — tự tạo lịch 15 (hoặc 10) buổi, mã tham gia tự sinh",
)
def create_class(
    body: ClassCreate, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    from app.routers.semesters import current_semester

    start = body.start_date
    if start is None:  # không gửi ngày: theo học kỳ chỉ định / đang diễn ra / thứ Hai tuần này
        base = db.get(Semester, body.semester_id) if body.semester_id else current_semester(db)
        start = base.start_date if base else monday_of(today_vn())
    sem = semester_for_date(db, start)
    days = sorted(set(body.meeting_days or []))
    if sem.term == "he" and (len(days) != 3 or any(d < 0 or d > 5 for d in days)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Lớp kỳ Hè cần chọn đúng 3 thứ học trong tuần (thứ Hai → thứ Bảy)",
        )
    code = body.code.strip().upper()
    clash = code_conflict(db, code, sem.id)
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, conflict_message(clash))
    c = Classroom(
        code=code,
        subject=body.subject.strip(),
        semester=semester_label(sem),
        semester_id=sem.id,
        course_type=body.course_type,
        meeting_days=days if sem.term == "he" else None,
        faculty=user.faculty,
        lecturer_id=user.id,
        join_code=new_join_code(body.code),
        start_date=start if sem.term == "he" else monday_of(start),
    )
    db.add(c)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Tên lớp đã tồn tại")
    db.refresh(c)
    layout_weeks(db, c)
    db.commit()
    return class_out(db, c, user)


@router.patch("/classes/{class_id}", summary="Sửa tên lớp / môn học")
def update_class(
    class_id: int,
    body: ClassUpdate,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    c = get_owned_class(db, class_id, user)
    if body.code:
        code = body.code.strip().upper()
        clash = code_conflict(db, code, c.semester_id, exclude_id=c.id)
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, conflict_message(clash))
        c.code = code
    if body.subject:
        c.subject = body.subject.strip()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Tên lớp đã tồn tại")
    return class_out(db, c, user)


@router.post("/classes/{class_id}/join-code", summary="Tạo mã tham gia mới (mã cũ hết hiệu lực)")
def regenerate_code(
    class_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    c = get_owned_class(db, class_id, user)
    c.join_code = new_join_code(c.code)
    db.commit()
    return {"join_code": c.join_code}


@router.delete(
    "/classes/{class_id}",
    response_model=Msg,
    summary="Xóa hẳn lớp — chỉ khi lớp còn trống (chưa có sinh viên và chưa có câu hỏi)",
)
def delete_class(
    class_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    from app.models import ChatMessage, Material, MaterialChunk, SimilarGroup

    c = db.get(Classroom, class_id)
    if c is None or c.lecturer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lớp học")
    if db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.class_id == c.id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Lớp đã có sinh viên tham gia nên không xóa được"
        )
    if db.scalar(select(func.count()).select_from(Question).where(Question.class_id == c.id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Lớp đã có câu hỏi của sinh viên nên không xóa được"
        )
    for m in db.scalars(select(Material).where(Material.class_id == c.id)).all():
        try:
            resolve_stored(m.stored_path).unlink(missing_ok=True)
        except Exception:
            pass
    for model in (MaterialChunk, Material, ChatMessage, SimilarGroup, Enrollment, ClassSession):
        db.execute(sa_delete(model).where(model.class_id == c.id))
    db.delete(c)
    db.commit()
    return Msg(message="Đã xóa lớp học")


@router.get("/classes-check-code", summary="Kiểm tra tên lớp đã dùng trong học kỳ chưa")
def check_code(
    code: str,
    semester_id: int | None = None,
    start_date: date | None = None,
    exclude_id: int | None = None,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    from app.routers.semesters import current_semester

    if start_date:  # tên lớp chỉ cần không trùng trong cùng học kỳ
        year, term = term_of(start_date)
        sem = db.scalar(select(Semester).where(Semester.year == year, Semester.term == term))
        sid = sem.id if sem else -1
    else:
        sid = semester_id or (current_semester(db).id if current_semester(db) else None)
    clash = code_conflict(db, code.strip().upper(), sid, exclude_id=exclude_id)
    return {
        "available": clash is None,
        "code": code.strip().upper(),
        "message": conflict_message(clash) if clash else "",
    }


def code_conflict(
    db: Session, code: str, semester_id: int | None, exclude_id: int | None = None
) -> Classroom | None:
    stmt = select(Classroom).where(
        func.upper(Classroom.code) == code.upper(), Classroom.semester_id == semester_id
    )
    if exclude_id:
        stmt = stmt.where(Classroom.id != exclude_id)
    return db.scalar(stmt)


def conflict_message(c: Classroom) -> str:
    return f"Lớp {c.code} đã tồn tại trong {c.semester}"


# ---------------------------------------------------------------- 15 tuần học
@router.get(
    "/classes/{class_id}/weeks", summary="15 tuần học của lớp (Đã học / Đang học / Chưa học)"
)
def list_weeks(
    class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    c = get_class_for_user(db, class_id, user)
    tl = class_timeline(db, c)
    weeks = db.scalars(
        select(ClassSession).where(ClassSession.class_id == c.id).order_by(ClassSession.number)
    ).all()
    return {"timeline": tl, "weeks": [week_out(db, w, tl) for w in weeks]}


@router.post("/classes/join", summary="Sinh viên tham gia lớp bằng mã")
def join_class(
    body: JoinIn, user: User = Depends(require_role("student")), db: Session = Depends(get_db)
):
    c = db.scalar(
        select(Classroom).where(
            func.upper(Classroom.join_code) == body.join_code.strip().upper(),
            Classroom.is_archived.is_(False),
        )
    )
    if c is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Mã tham gia không đúng hoặc lớp không còn hoạt động"
        )
    if db.scalar(
        select(Enrollment.id).where(Enrollment.class_id == c.id, Enrollment.student_id == user.id)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bạn đã ở trong lớp này")
    db.add(Enrollment(class_id=c.id, student_id=user.id))
    db.commit()
    return class_out(db, c, user)


# ---------------------------------------------------------------- danh sách sinh viên
@router.get("/classes/{class_id}/students", summary="Danh sách sinh viên của lớp (Giảng viên)")
def list_students(
    class_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    get_owned_class(db, class_id, user)
    rows = db.execute(
        select(User, Enrollment.joined_at)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.class_id == class_id)
        .order_by(User.full_name)
    ).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "admin_class": u.admin_class,
            "joined_at": as_utc(j),
        }
        for u, j in rows
    ]


@router.post("/classes/{class_id}/students", summary="Thêm sinh viên vào lớp bằng email")
def add_students(
    class_id: int,
    body: AddStudentsIn,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    get_owned_class(db, class_id, user)
    added, not_found, existed = [], [], []
    for email in {e.lower() for e in body.emails}:
        st = db.scalar(select(User).where(func.lower(User.email) == email, User.role == "student"))
        if st is None:
            not_found.append(email)
        elif db.scalar(
            select(Enrollment.id).where(
                Enrollment.class_id == class_id, Enrollment.student_id == st.id
            )
        ):
            existed.append(email)
        else:
            db.add(Enrollment(class_id=class_id, student_id=st.id))
            added.append(email)
    db.commit()
    return {"added": added, "already_in_class": existed, "not_found": not_found}


@router.delete(
    "/classes/{class_id}/students/{student_id}",
    response_model=Msg,
    summary="Xóa sinh viên khỏi lớp",
)
def remove_student(
    class_id: int,
    student_id: int,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    get_owned_class(db, class_id, user)
    e = db.scalar(
        select(Enrollment).where(
            Enrollment.class_id == class_id, Enrollment.student_id == student_id
        )
    )
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sinh viên không thuộc lớp này")
    db.delete(e)  # câu hỏi đã gửi vẫn được giữ, vẫn ẩn danh
    db.commit()
    return Msg(message="Đã xóa sinh viên khỏi lớp")


# ---------------------------------------------------------------- thống kê
def _avg_response_seconds(db: Session, stmt_filter) -> int | None:
    rows = db.execute(
        select(Question.created_at, func.min(Answer.created_at))
        .join(Answer, Answer.question_id == Question.id)
        .where(stmt_filter, Answer.source_answer_id.is_(None))
        .group_by(Question.id, Question.created_at)
    ).all()
    if not rows:
        return None
    return int(sum((as_utc(a) - as_utc(q)).total_seconds() for q, a in rows) / len(rows))


@router.get("/classes/{class_id}/stats", summary="Thống kê của lớp theo từng tuần (Giảng viên)")
def class_stats(
    class_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    c = get_owned_class(db, class_id, user)
    tl = class_timeline(db, c)
    weeks = db.scalars(
        select(ClassSession).where(ClassSession.class_id == class_id).order_by(ClassSession.number)
    ).all()
    per = []
    for w in weeks:
        o = week_out(db, w, tl)
        o["avg_response_seconds"] = _avg_response_seconds(db, Question.session_id == w.id)
        o["group_count"] = db.scalar(
            select(func.count(func.distinct(Question.group_id))).where(
                Question.session_id == w.id, Question.group_id.is_not(None)
            )
        )
        per.append(o)
    total = sum(p["question_count"] for p in per)
    answered = sum(p["answered_count"] for p in per)
    return {
        "timeline": tl,
        "question_count": total,
        "answered_count": answered,
        "waiting_count": sum(p["waiting_count"] for p in per),
        "flagged_count": sum(p["flagged_count"] for p in per),
        "review_count": sum(p["review_count"] for p in per),
        "answer_rate": round(answered * 100 / total) if total else 0,
        "avg_response_seconds": _avg_response_seconds(db, Question.class_id == class_id),
        "group_count": sum(p["group_count"] for p in per),
        "weeks": per,
    }


@router.get("/lecturer/stats", summary="Thống kê tổng hợp các lớp của Giảng viên")
def lecturer_stats(
    semester_id: str | None = None,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    """semester_id: bỏ trống = các lớp chưa lưu trữ (như cũ) · "all" = mọi lớp mọi học kỳ (cả lớp đã lưu trữ) · số = một học kỳ (cả lớp đã lưu trữ)."""
    from app.routers.semesters import current_semester

    all_cls = db.scalars(select(Classroom).where(Classroom.lecturer_id == user.id)).all()
    sem_ids = {c.semester_id for c in all_cls if c.semester_id}
    sems = (
        db.scalars(
            select(Semester).where(Semester.id.in_(sem_ids)).order_by(Semester.start_date.desc())
        ).all()
        if sem_ids
        else []
    )
    cur_sem = current_semester(db)
    cur_sem_id = cur_sem.id if cur_sem and cur_sem.id in sem_ids else (sems[0].id if sems else None)
    if semester_id is None:
        classes = [c for c in all_cls if not c.is_archived]
    elif semester_id == "all":
        classes = list(all_cls)
    else:
        try:
            sid = int(semester_id)
        except ValueError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, 'semester_id phải là số hoặc "all"'
            )
        classes = [c for c in all_cls if c.semester_id == sid]
    rows = [class_out(db, c, user) for c in classes]
    total = sum(r["question_count"] for r in rows)
    answered = sum(r["answered_count"] for r in rows)
    ids = [c.id for c in classes]
    cur = [r for r in rows if r.get("current_week")]
    nums = sorted({r["current_week"]["number"] for r in cur})
    unit = (cur[0]["timeline"].get("unit_label") if cur else None) or "Tuần"
    if nums:  # tuần hiện tại (không cộng dồn); các lớp lệch tuần → "Tuần 4–10"
        week_label = f"{unit} {nums[0]}" if len(nums) == 1 else f"{unit} {nums[0]}–{nums[-1]}"
    else:
        phases = {r["timeline"]["phase"] for r in rows}
        week_label = (
            "Chưa vào học"
            if "not_started" in phases
            else ("Đã kết thúc" if phases == {"ended"} else "Không có lớp đang học")
        )
    week_ids = [r["current_week"]["id"] for r in cur]
    this_week = (
        db.scalar(
            select(func.count()).select_from(Question).where(Question.session_id.in_(week_ids))
        )
        if week_ids
        else 0
    )
    return {
        "class_count": len(rows),
        "student_count": sum(r["student_count"] for r in rows),
        "semesters": [
            {
                "id": x.id,
                "year": x.year,
                "label": semester_label(x),
                "is_default": x.id == cur_sem_id,
            }
            for x in sems
        ],
        "current_semester_id": cur_sem_id,
        "current_week_label": week_label,
        "semester": (cur[0] if cur else (rows[0] if rows else {})).get("semester"),
        "questions_this_week": this_week,
        "week_count": sum(
            r["timeline"]["weeks_done"] + (1 if r["timeline"]["current_week"] else 0) for r in rows
        ),
        "question_count": total,
        "answered_count": answered,
        "answer_rate": round(answered * 100 / total) if total else 0,
        "avg_response_seconds": (
            _avg_response_seconds(db, Question.class_id.in_(ids)) if ids else None
        ),
        "classes": [
            {
                "id": r["id"],
                "code": r["code"],
                "subject": r["subject"],
                "student_count": r["student_count"],
                "weeks_learned": r["timeline"]["weeks_done"]
                + (1 if r["timeline"]["current_week"] else 0),
                "current_week": r["current_week"]["number"] if r.get("current_week") else None,
                "question_count": r["question_count"],
                "answered_count": r["answered_count"],
            }
            for r in rows
        ],
    }


@router.get(
    "/lecturer/pending",
    summary="Câu hỏi đang chờ trả lời ở mọi lớp của Giảng viên (mới nhất trước)",
)
def lecturer_pending(
    limit: int = 8, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    rows = db.execute(
        select(Question, Classroom, ClassSession)
        .join(Classroom, Classroom.id == Question.class_id)
        .join(ClassSession, ClassSession.id == Question.session_id)
        .where(
            Classroom.lecturer_id == user.id,
            Classroom.is_archived.is_(False),
            Question.status == "waiting",
        )
        .order_by(Question.created_at.desc())
        .limit(min(limit, 50))
    ).all()
    total = db.scalar(
        select(func.count())
        .select_from(Question)
        .join(Classroom, Classroom.id == Question.class_id)
        .where(
            Classroom.lecturer_id == user.id,
            Classroom.is_archived.is_(False),
            Question.status == "waiting",
        )
    )
    return {
        "total": total,
        "items": [
            {
                **question_out(db, q, with_answers=False),
                "class_id": c.id,
                "class_code": c.code,
                "week_number": w.number,
            }
            for q, c, w in rows
        ],
    }
