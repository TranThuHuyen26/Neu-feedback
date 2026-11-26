"""Quản trị: tổng quan, thống kê, quản lý tài khoản (SV & GV), kiểm duyệt nội dung gắn cờ."""

import csv
import io
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Answer,
    AuditLog,
    ChatMessage,
    ClassSession,
    Classroom,
    Enrollment,
    Flag,
    Question,
    User,
)
from app.schemas import AccountIn, AccountUpdate, DecisionIn, Msg, TraceIn, UserOut
from app.security import check_email_domain, hash_password, require_role
from app.services import analytics
from app.services.core import author_of, notify, question_out
from app.utils import as_utc, plain_text, temp_password, today_vn, utcnow, vn_date

router = APIRouter(prefix="/api/admin", tags=["Quản trị"])
admin_only = require_role("admin")
MANAGED_ROLES = ("student", "lecturer")  # admin không quản lý tài khoản quản trị viên


def audit(db: Session, actor: User, action: str, target: str, detail: str | None = None) -> None:
    db.add(AuditLog(actor_id=actor.id, action=action, target=target, detail=detail))


def _semester_scope(
    db: Session, year: str | None, semester_id: int | None, term: str | None
) -> dict:
    """Chọn học kỳ theo bộ lọc năm học / học kỳ. Dùng chung cho trang Tổng quan và Thống kê để hai trang luôn khớp nhau."""
    from app.routers.semesters import all_semesters, current_semester, semester_out
    from app.services.core import TERM_NAME, semester_end

    sems = all_semesters(db)
    cur = current_semester(db)

    def prev_year(y):
        a, b = (int(x) for x in y.split("-"))
        return f"{a - 1}-{b - 1}"

    years = {s.year for s in sems}
    if cur:
        years |= {cur.year, prev_year(cur.year)}
    years = sorted(years, reverse=True)
    if semester_id:
        chosen = [s for s in sems if s.id == semester_id]
        sel_year = chosen[0].year if chosen else (year or (cur.year if cur else None))
        sel_term = chosen[0].term if chosen else (term or "")
    elif year or term:
        sel_year = year or (cur.year if cur else (years[0] if years else None))
        sel_term = term or ""
        chosen = [s for s in sems if s.year == sel_year and (not sel_term or s.term == sel_term)]
    else:
        chosen = [cur] if cur else []
        sel_year = cur.year if cur else (years[0] if years else None)
        sel_term = cur.term if cur else ""
    rng = None
    if chosen:
        rng = {
            "from": min(s.start_date for s in chosen),
            "to": max(semester_end(s) for s in chosen),
            "label": chosen[0].year if len(chosen) > 1 else semester_out(db, chosen[0])["label"],
        }
    term_list = []
    for t in ("thu", "xuan", "he"):
        decl = next((x for x in sems if x.year == sel_year and x.term == t), None)
        if decl:
            term_list.append({**semester_out(db, decl), "declared": True})
        elif sel_year:
            y1, y2 = sel_year.split("-")
            term_list.append(
                {
                    "id": None,
                    "term": t,
                    "year": sel_year,
                    "declared": False,
                    "label": f"Học kỳ {TERM_NAME[t]} {y1 if t == 'thu' else y2}",
                }
            )
    if rng is None and sel_year:
        lab = (
            next((x["label"] for x in term_list if x["term"] == sel_term), None)
            if sel_term
            else f"Năm học {sel_year}"
        )
        rng = {"from": None, "to": None, "label": lab}
    return {
        "chosen": chosen,
        "years": years,
        "sel_year": sel_year,
        "sel_term": sel_term,
        "term_list": term_list,
        "rng": rng,
    }


# ================================================================ TỔNG QUAN
@router.get("/overview", summary="Tổng quan: việc cần xử lý hôm nay (cùng cách đếm với Thống kê)")
def overview(
    year: str | None = None,
    semester_id: int | None = None,
    term: str | None = None,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    sc = _semester_scope(db, year, semester_id, term)
    chosen = sc["chosen"]
    classes = (
        db.scalars(
            select(Classroom).where(
                Classroom.semester_id.in_([s.id for s in chosen]), Classroom.is_archived.is_(False)
            )
        ).all()
        if chosen
        else []
    )
    cids = [c.id for c in classes]
    items = [q for q, _ in analytics.question_rows(db, cids)]
    counts = analytics.tally(items)
    roles = dict(
        db.execute(
            select(User.role, func.count()).where(User.role.in_(MANAGED_ROLES)).group_by(User.role)
        ).all()
    )
    today = today_vn()
    waiting = [q for q in items if q.status == "waiting"]
    waiting_by_class = {}
    for q in waiting:
        waiting_by_class[q.class_id] = waiting_by_class.get(q.class_id, 0) + 1
    attention = sorted(classes, key=lambda c: -waiting_by_class.get(c.id, 0))[:3]
    pending = db.scalars(
        select(Flag).where(Flag.status == "pending").order_by(Flag.ai_score.desc()).limit(3)
    ).all()
    logs = db.execute(
        select(AuditLog, User.full_name)
        .join(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    ).all()
    rng = sc["rng"]
    return {
        "years": sc["years"],
        "year": sc["sel_year"],
        "term": sc["sel_term"],
        "semester_id": chosen[0].id if len(chosen) == 1 else None,
        "semesters": sc["term_list"],
        "range": {
            "from": min((s.start_date for s in chosen), default=None),
            "to": None,
            "label": rng["label"] if rng else None,
        },
        "accounts": {
            "total": roles.get("student", 0) + roles.get("lecturer", 0),
            "students": roles.get("student", 0),
            "lecturers": roles.get("lecturer", 0),
        },
        "classes": len(classes),
        "questions": counts,
        "today": {
            "date": today.isoformat(),
            "new_waiting": sum(1 for q in waiting if vn_date(q.created_at) == today),
            "waiting": counts["waiting"],
            "over_48h": sum(1 for q in waiting if (analytics.hours_since(q.created_at) or 0) > 48),
        },
        "grouping_week": analytics.grouping_stats(db, cids, analytics.week_start(today)),
        "trend": analytics.trend_7_days(items),
        "pending_flags": db.scalar(
            select(func.count()).select_from(Flag).where(Flag.status == "pending")
        ),
        "top_flags": [_flag_out(db, f, short=True) for f in pending],
        "attention_classes": [
            {
                "id": c.id,
                "code": c.code,
                "subject": c.subject,
                "lecturer": c.lecturer.full_name if c.lecturer else "",
                "waiting": waiting_by_class.get(c.id, 0),
            }
            for c in attention
            if waiting_by_class.get(c.id, 0)
        ],
        "recent_activity": [
            {"action": a.action, "target": a.target, "actor": n, "created_at": as_utc(a.created_at)}
            for a, n in logs
        ],
    }


@router.get(
    "/stats", summary="Thống kê theo năm học / học kỳ: theo tuần, theo lớp, theo Giảng viên"
)
def stats(
    year: str | None = None,
    semester_id: int | None = None,
    term: str | None = None,
    faculty: str | None = None,
    lecturer_id: int | None = None,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    from app.models import ClassSession
    from app.services.core import unit_count

    sc = _semester_scope(db, year, semester_id, term)
    chosen, years, sel_year, sel_term = sc["chosen"], sc["years"], sc["sel_year"], sc["sel_term"]
    ids = [s.id for s in chosen]
    classes = (
        db.scalars(
            select(Classroom)
            .where(Classroom.semester_id.in_(ids), Classroom.is_archived.is_(False))
            .order_by(Classroom.code)
        ).all()
        if ids
        else []
    )
    filter_options = {
        "faculties": sorted({c.faculty for c in classes if c.faculty}),
        "lecturers": sorted(
            {(c.lecturer_id, c.lecturer.full_name) for c in classes if c.lecturer},
            key=lambda x: x[1],
        ),
    }
    if faculty:
        classes = [c for c in classes if c.faculty == faculty]
    if lecturer_id:
        classes = [c for c in classes if c.lecturer_id == lecturer_id]
    cids = [c.id for c in classes]
    qs = analytics.question_rows(db, cids)
    first_ans = (
        dict(
            db.execute(
                select(Answer.question_id, func.min(Answer.created_at))
                .where(
                    Answer.question_id.in_([q.id for q, _ in qs]), Answer.source_answer_id.is_(None)
                )
                .group_by(Answer.question_id)
            ).all()
        )
        if qs
        else {}
    )

    def resp(items):
        secs = [
            (as_utc(first_ans[q.id]) - as_utc(q.created_at)).total_seconds()
            for q in items
            if q.id in first_ans
        ]
        return int(sum(secs) / len(secs)) if secs else None

    def pack(items):
        return {**analytics.tally(items), "avg_response_seconds": resp(items)}

    all_q = [q for q, _ in qs]
    max_units = max([unit_count(c) for c in classes] or [15])
    today = today_vn()
    learned = set()
    for c in classes:
        for w in db.scalars(select(ClassSession).where(ClassSession.class_id == c.id)).all():
            if vn_date(w.starts_at) <= today:
                learned.add(w.number)
    by_week = [
        {"number": n, "learned": n in learned, **pack([q for q, num in qs if num == n])}
        for n in range(1, max_units + 1)
    ]
    by_class = []
    for c in classes:
        items = [q for q in all_q if q.class_id == c.id]
        by_class.append(
            {
                "id": c.id,
                "code": c.code,
                "subject": c.subject,
                "lecturer": c.lecturer.full_name if c.lecturer else "",
                "semester": c.semester,
                "students": db.scalar(
                    select(func.count()).select_from(Enrollment).where(Enrollment.class_id == c.id)
                ),
                **pack(items),
            }
        )
    lect = {}
    for c in classes:
        lect.setdefault(
            c.lecturer_id, {"name": c.lecturer.full_name if c.lecturer else "", "classes": []}
        )["classes"].append(c)
    by_lecturer = [
        {
            "name": v["name"],
            "class_count": len(v["classes"]),
            "class_codes": [c.code for c in v["classes"]],
            **pack([q for q in all_q if q.class_id in {c.id for c in v["classes"]}]),
        }
        for v in lect.values()
    ]
    flags = dict(db.execute(select(Flag.status, func.count()).group_by(Flag.status)).all())
    flag_total = sum(flags.values())
    students = (
        db.scalar(
            select(func.count(func.distinct(Enrollment.student_id))).where(
                Enrollment.class_id.in_(cids)
            )
        )
        if cids
        else 0
    )
    rng, term_list = sc["rng"], sc["term_list"]
    by_faculty = []
    for fac in sorted({c.faculty or "Chưa rõ khoa" for c in classes}):
        fcids = {c.id for c in classes if (c.faculty or "Chưa rõ khoa") == fac}
        by_faculty.append(
            {
                "faculty": fac,
                "class_count": len(fcids),
                **pack([q for q in all_q if q.class_id in fcids]),
            }
        )
    per_day = Counter(vn_date(q.created_at) for q in all_q)
    by_day, d0 = [], min((s.start_date for s in chosen), default=None)
    if d0:
        d = d0
        while d <= max(d0, today_vn()):
            by_day.append({"date": d.isoformat(), "questions": per_day.get(d, 0)})
            d += timedelta(days=1)
    ai_msgs = (
        db.scalars(
            select(ChatMessage).where(ChatMessage.class_id.in_(cids), ChatMessage.role == "ai")
        ).all()
        if cids
        else []
    )
    timed = [m.latency_ms for m in ai_msgs if m.latency_ms]
    reused = (
        db.scalar(
            select(func.count())
            .select_from(Answer)
            .where(
                Answer.question_id.in_([q.id for q in all_q]),
                or_(Answer.source_answer_id.is_not(None), Answer.via_group.is_(True)),
            )
        )
        if all_q
        else 0
    )
    return {
        "years": years,
        "year": sel_year,
        "term": sel_term,
        "semester_id": chosen[0].id if len(chosen) == 1 else None,
        "semesters": term_list,
        "range": rng,
        "empty": not classes,
        "total": {
            **pack(all_q),
            "classes": len(classes),
            "students": students,
            "lecturers": len(lect),
        },
        "by_week": by_week,
        "by_class": by_class,
        "by_lecturer": by_lecturer,
        "by_faculty": by_faculty,
        "filters": {
            "faculties": filter_options["faculties"],
            "lecturers": [{"id": i, "name": n} for i, n in filter_options["lecturers"]],
            "faculty": faculty,
            "lecturer_id": lecturer_id,
        },
        "by_day": by_day,
        "heatmap": analytics.hour_heatmap(all_q),
        "keywords": analytics.keywords_by_week(qs, plain_text),
        "ai": {
            "grouping": analytics.grouping_stats(db, cids),
            "reused_answers": reused,
            "chat_answers": len(ai_msgs),
            "chat_avg_seconds": round(sum(timed) / len(timed) / 1000, 1) if timed else None,
        },
        "flags": {
            "total": flag_total,
            "pending": flags.get("pending", 0),
            "processed": flag_total - flags.get("pending", 0),
        },
    }


@router.get("/faculties", summary="Danh sách khoa (lọc tài khoản)")
def faculties(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return sorted({f for f in db.scalars(select(User.faculty)).all() if f})


# ================================================================ TÀI KHOẢN
def _managed_user(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None or u.role not in MANAGED_ROLES:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Không tìm thấy tài khoản sinh viên/Giảng viên"
        )
    return u


@router.get("/users", summary="Danh sách tài khoản sinh viên & Giảng viên")
def list_users(
    q: str | None = None,
    role: str | None = None,
    faculty: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    size: int = 20,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    stmt = select(User).where(User.role.in_(MANAGED_ROLES))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(User.full_name).like(like), func.lower(User.email).like(like))
        )
    if role:
        stmt = stmt.where(User.role == role)
    if faculty:
        stmt = stmt.where(User.faculty == faculty)
    if status_filter == "locked":
        stmt = stmt.where(User.is_locked.is_(True))
    elif status_filter == "active":
        stmt = stmt.where(User.is_locked.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    size = max(1, min(size, 100))
    users = db.scalars(
        stmt.order_by(User.full_name).offset((max(page, 1) - 1) * size).limit(size)
    ).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                **UserOut.model_validate(u).model_dump(),
                "last_active_at": as_utc(u.last_active_at),
                "locked_at": as_utc(u.locked_at),
            }
            for u in users
        ],
    }


def _create(db: Session, body: AccountIn) -> tuple[User, str]:
    check_email_domain(body.email)
    if db.scalar(select(User.id).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email {body.email} đã tồn tại")
    pw = temp_password()
    u = User(
        email=body.email.lower(),
        full_name=body.full_name.strip(),
        role=body.role,
        faculty=body.faculty,
        admin_class=body.admin_class,
        password_hash=hash_password(pw),
        must_change_password=True,
    )
    db.add(u)
    return u, pw


@router.post("/users", status_code=201, summary="Thêm tài khoản (trả về mật khẩu tạm)")
def create_user(body: AccountIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    u, pw = _create(db, body)
    db.flush()
    audit(db, admin, "create_user", u.email, u.role)
    db.commit()
    return {"user": UserOut.model_validate(u), "temp_password": pw}


@router.patch("/users/{user_id}", response_model=UserOut, summary="Sửa tài khoản")
def update_user(
    user_id: int,
    body: AccountUpdate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    u = _managed_user(db, user_id)
    data = body.model_dump(exclude_unset=True)
    if "email" in data:
        check_email_domain(data["email"])
        if db.scalar(
            select(User.id).where(func.lower(User.email) == data["email"].lower(), User.id != u.id)
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được dùng cho tài khoản khác")
        data["email"] = data["email"].lower()
    for k, v in data.items():
        setattr(u, k, v)
    audit(db, admin, "update_user", u.email, ", ".join(data))
    db.commit()
    return u


@router.post("/users/{user_id}/lock", response_model=UserOut, summary="Khóa tài khoản")
def lock_user(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    u = _managed_user(db, user_id)
    u.is_locked, u.locked_at = True, utcnow()
    audit(db, admin, "lock_user", u.email)
    db.commit()
    return u


@router.post("/users/{user_id}/unlock", response_model=UserOut, summary="Mở khóa tài khoản")
def unlock_user(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    u = _managed_user(db, user_id)
    u.is_locked, u.locked_at = False, None
    audit(db, admin, "unlock_user", u.email)
    db.commit()
    return u


@router.delete("/users/{user_id}", response_model=Msg, summary="Xóa tài khoản")
def delete_user(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    u = _managed_user(db, user_id)
    if u.role == "lecturer" and db.scalar(
        select(Classroom.id).where(Classroom.lecturer_id == u.id)
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Giảng viên đang phụ trách lớp học — hãy khóa tài khoản thay vì xóa",
        )
    audit(db, admin, "delete_user", u.email)
    db.delete(u)  # câu hỏi đã gửi vẫn giữ (ẩn danh); chỉ mất liên kết danh tính
    db.commit()
    return Msg(message="Đã xóa tài khoản")


@router.post(
    "/users/import",
    summary="Nhập tài khoản từ Excel/CSV (cột: full_name, email, role, faculty, admin_class)",
)
async def import_users(
    file: UploadFile = File(...), admin: User = Depends(admin_only), db: Session = Depends(get_db)
):
    raw = await file.read()
    name = (file.filename or "").lower()
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook

        ws = load_workbook(io.BytesIO(raw), read_only=True).active
        it = ws.iter_rows(values_only=True)
        header = [str(h or "").strip().lower() for h in next(it)]
        records = [dict(zip(header, r)) for r in it]
    elif name.endswith(".csv"):
        records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        records = [{k.strip().lower(): v for k, v in r.items()} for r in records]
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Chỉ nhận tệp .xlsx hoặc .csv")
    role_map = {
        "sinh viên": "student",
        "sv": "student",
        "student": "student",
        "giảng viên": "lecturer",
        "gv": "lecturer",
        "lecturer": "lecturer",
    }
    created, errors = [], []
    for i, r in enumerate(records, start=2):
        if not any(r.values()):
            continue
        try:
            body = AccountIn(
                full_name=str(r.get("full_name") or "").strip(),
                email=str(r.get("email") or "").strip(),
                role=role_map.get(str(r.get("role") or "").strip().lower(), "invalid"),
                faculty=str(r.get("faculty") or "").strip(),
                admin_class=(str(r["admin_class"]).strip() if r.get("admin_class") else None),
            )
            with db.begin_nested():
                u, pw = _create(db, body)
            created.append({"email": u.email, "temp_password": pw})
        except HTTPException as e:
            errors.append({"row": i, "error": e.detail})
        except Exception as e:
            errors.append({"row": i, "error": "Dữ liệu không hợp lệ: " + str(e).split("\n")[0]})
    audit(
        db, admin, "import_users", file.filename or "", f"{len(created)} tạo mới, {len(errors)} lỗi"
    )
    db.commit()
    return {"created": created, "errors": errors}


# ================================================================ KIỂM DUYỆT
def _flag_out(db: Session, f: Flag, short: bool = False) -> dict:
    q = db.get(Question, f.question_id)
    s = db.get(ClassSession, q.session_id)
    c = db.get(Classroom, q.class_id)
    by = db.get(User, f.flagged_by)
    d = {
        "id": f.id,
        "question_id": q.id,
        "question_code": question_out(db, q, with_answers=False)["code"],
        "content": q.content,
        "reason": f.reason,
        "ai_score": f.ai_score,
        "status": f.status,
        "class_code": c.code,
        "session_title": f"Tuần {s.number}" + (f" · {s.title}" if s.title else ""),
        "flagged_by": by.full_name if by else None,
        "created_at": as_utc(f.created_at),
    }
    if not short:
        d.update(note=f.note, decided_at=as_utc(f.decided_at))
    return d


@router.get("/flags", summary="Hàng đợi nội dung gắn cờ (mức độ nghiêm trọng giảm dần)")
def list_flags(
    status_filter: str = "pending", _: User = Depends(admin_only), db: Session = Depends(get_db)
):
    flags = db.scalars(
        select(Flag)
        .where(Flag.status == status_filter)
        .order_by(Flag.ai_score.desc(), Flag.created_at.desc())
    ).all()
    return [_flag_out(db, f) for f in flags]


@router.post("/flags/{flag_id}/decision", summary="Quyết định: không vi phạm / ẩn / xóa")
def decide(
    flag_id: int, body: DecisionIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)
):
    f = db.get(Flag, flag_id)
    if f is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nội dung gắn cờ")
    if f.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Nội dung này đã được xử lý")
    q = db.get(Question, f.question_id)
    f.status, f.note, f.decided_by, f.decided_at = body.decision, body.note, admin.id, utcnow()
    q.status = {
        "dismissed": "answered" if q.answered_at else "waiting",
        "hidden": "hidden",
        "deleted": "deleted",
    }[body.decision]
    c = db.get(Classroom, q.class_id)
    notify(
        db,
        c.lecturer_id,
        "Admin đã xử lý nội dung gắn cờ",
        {"dismissed": "Không vi phạm", "hidden": "Đã ẩn", "deleted": "Đã xóa"}[body.decision]
        + f" · {c.code}",
    )
    if body.decision != "dismissed":
        sid = author_of(db, q.id)
        if sid:  # báo cho sinh viên nhưng giảng viên vẫn không biết là ai
            notify(
                db,
                sid,
                "Một câu hỏi của bạn đã bị " + ("ẩn" if body.decision == "hidden" else "xóa"),
                body.note or "Nội dung không phù hợp quy định lớp học",
            )
    audit(db, admin, f"flag_{body.decision}", f"flag#{f.id}", body.note)
    db.flush()
    from app.services.core import notify_admins_flags

    notify_admins_flags(db)  # cập nhật / đánh dấu đã đọc thông báo kiểm duyệt
    db.commit()
    return _flag_out(db, f)


@router.post(
    "/flags/{flag_id}/trace", summary="Truy vết danh tính người gửi (bắt buộc lý do, ghi nhật ký)"
)
def trace(
    flag_id: int, body: TraceIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)
):
    f = db.get(Flag, flag_id)
    if f is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nội dung gắn cờ")
    sid = author_of(db, f.question_id)
    audit(db, admin, "trace_identity", f"flag#{f.id}", body.reason)
    db.commit()
    if sid is None:
        return {"found": False, "message": "Tài khoản người gửi không còn tồn tại"}
    u = db.get(User, sid)
    return {"found": True, "user": UserOut.model_validate(u)}


@router.get("/audit-logs", summary="Nhật ký thao tác nhạy cảm")
def audit_logs(limit: int = 50, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.execute(
        select(AuditLog, User.full_name)
        .join(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 200))
    ).all()
    return [
        {
            "action": a.action,
            "target": a.target,
            "detail": a.detail,
            "actor": n,
            "created_at": as_utc(a.created_at),
        }
        for a, n in rows
    ]
