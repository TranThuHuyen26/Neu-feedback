"""Quản trị viên quản lý Giảng viên và sinh viên theo lớp học phần: xem danh sách, thêm hoặc gỡ sinh viên,
đổi Giảng viên phụ trách. Mọi thay đổi đều ghi nhật ký.

Admin chỉ thấy ai thuộc lớp nào, không thấy ai đã hỏi câu nào.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Classroom, Enrollment, User
from app.routers.admin import admin_only, audit
from app.routers.classes import class_out
from app.schemas import AddStudentsIn, LecturerChangeIn, Msg
from app.services.core import notify
from app.utils import as_utc

router = APIRouter(prefix="/api/admin", tags=["Quản trị theo lớp"])


def _class(db: Session, class_id: int) -> Classroom:
    c = db.get(Classroom, class_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lớp học")
    return c


def _lecturer_brief(u: User | None) -> dict | None:
    if u is None:
        return None
    return {"id": u.id, "full_name": u.full_name, "email": u.email, "is_locked": u.is_locked}


def _summary(db: Session, c: Classroom, admin: User) -> dict:
    data = class_out(db, c, admin)
    data["lecturer"] = _lecturer_brief(c.lecturer)
    data.pop("join_code", None)  # mã tham gia là việc của giảng viên
    return data


@router.get("/classes", summary="Danh sách lớp học phần (lọc theo học kỳ, tìm theo mã lớp / môn)")
def list_classes(
    q: str | None = None,
    semester_id: int | None = None,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    stmt = select(Classroom)
    if semester_id:
        stmt = stmt.where(Classroom.semester_id == semester_id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Classroom.code).like(like) | func.lower(Classroom.subject).like(like)
        )
    classes = db.scalars(stmt.order_by(Classroom.semester_id.desc(), Classroom.code)).all()
    return [_summary(db, c, admin) for c in classes]


@router.get(
    "/classes/{class_id}", summary="Chi tiết lớp: giảng viên phụ trách + danh sách sinh viên"
)
def class_members(class_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    c = _class(db, class_id)
    rows = db.execute(
        select(User, Enrollment.joined_at)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.class_id == c.id)
        .order_by(User.full_name)
    ).all()
    data = _summary(db, c, admin)
    data["students"] = [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "faculty": u.faculty,
            "admin_class": u.admin_class,
            "is_locked": u.is_locked,
            "joined_at": as_utc(j),
        }
        for u, j in rows
    ]
    return data


@router.get("/lecturers", summary="Danh sách giảng viên (để chọn khi đổi giảng viên phụ trách)")
def lecturers(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(User)
        .where(User.role == "lecturer", User.is_locked.is_(False))
        .order_by(User.full_name)
    ).all()
    return [
        {"id": u.id, "full_name": u.full_name, "email": u.email, "faculty": u.faculty} for u in rows
    ]


@router.post("/classes/{class_id}/students", summary="Thêm sinh viên vào lớp bằng email")
def add_students(
    class_id: int,
    body: AddStudentsIn,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    c = _class(db, class_id)
    added, existed, not_found = [], [], []
    for email in sorted({e.lower() for e in body.emails}):
        st = db.scalar(select(User).where(func.lower(User.email) == email, User.role == "student"))
        if st is None:
            not_found.append(email)
        elif db.scalar(
            select(Enrollment.id).where(Enrollment.class_id == c.id, Enrollment.student_id == st.id)
        ):
            existed.append(email)
        else:
            db.add(Enrollment(class_id=c.id, student_id=st.id))
            notify(db, st.id, f"Bạn được thêm vào lớp {c.code}", c.subject, "student-classes.html")
            added.append(email)
    if added:
        audit(db, admin, "class.add_students", c.code, ", ".join(added))
    db.commit()
    return {"added": added, "already_in_class": existed, "not_found": not_found}


@router.delete(
    "/classes/{class_id}/students/{student_id}",
    response_model=Msg,
    summary="Gỡ sinh viên khỏi lớp (tài khoản và các lớp khác vẫn còn)",
)
def remove_student(
    class_id: int,
    student_id: int,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    c = _class(db, class_id)
    e = db.scalar(
        select(Enrollment).where(Enrollment.class_id == c.id, Enrollment.student_id == student_id)
    )
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sinh viên không thuộc lớp này")
    st = db.get(User, student_id)
    db.delete(e)  # câu hỏi đã gửi vẫn được giữ, vẫn ẩn danh
    audit(db, admin, "class.remove_student", c.code, st.email if st else str(student_id))
    db.commit()
    return Msg(message="Đã gỡ sinh viên khỏi lớp")


@router.patch(
    "/classes/{class_id}/lecturer",
    summary="Đổi giảng viên phụ trách lớp (câu hỏi và tài liệu giữ nguyên)",
)
def change_lecturer(
    class_id: int,
    body: LecturerChangeIn,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    c = _class(db, class_id)
    new = db.get(User, body.lecturer_id)
    if new is None or new.role != "lecturer":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy giảng viên")
    if new.is_locked:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tài khoản giảng viên này đang bị khóa")
    if c.lecturer_id == new.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Giảng viên này đang phụ trách lớp")
    old = c.lecturer
    c.lecturer_id = new.id
    audit(
        db,
        admin,
        "class.change_lecturer",
        c.code,
        f"{old.email if old else '—'} → {new.email}",
    )
    notify(
        db, new.id, f"Bạn được phân công phụ trách lớp {c.code}", c.subject, "lecturer-classes.html"
    )
    if old is not None:
        notify(
            db,
            old.id,
            f"Lớp {c.code} đã chuyển sang giảng viên khác",
            None,
            "lecturer-classes.html",
        )
    db.commit()
    db.refresh(c)
    return _summary(db, c, admin)
