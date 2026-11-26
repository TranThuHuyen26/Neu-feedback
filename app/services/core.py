"""Nghiệp vụ dùng chung: quyền truy cập lớp, lịch 15 tuần học, định dạng câu hỏi (ẩn danh),
câu hỏi tương đồng (gom nhóm / gợi ý dùng lại câu trả lời — luôn chờ Giảng viên duyệt),
sửa câu trả lời, thông báo gộp."""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Semester,
    Answer,
    ClassSession,
    Classroom,
    Enrollment,
    Flag,
    Material,
    Notification,
    Question,
    QuestionAuthor,
    SimilarGroup,
    User,
)
from app.services import ai
from app.utils import as_utc, plain_text, question_code, today_vn, utcnow, vn_date, vn_day_start_utc

settings = get_settings()
STATUS_LABEL = {"done": "Đã học", "current": "Đang học", "upcoming": "Chưa học"}


# ================================================================ quyền truy cập lớp
def get_class_for_user(db: Session, class_id: int, user: User) -> Classroom:
    c = db.get(Classroom, class_id)
    if c is None or c.is_archived and user.role != "admin":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lớp học")
    if user.role == "admin":
        return c
    if user.role == "lecturer" and c.lecturer_id == user.id:
        return c
    if user.role == "student" and db.scalar(
        select(Enrollment.id).where(Enrollment.class_id == c.id, Enrollment.student_id == user.id)
    ):
        return c
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không thuộc lớp học này")


def get_owned_class(db: Session, class_id: int, user: User) -> Classroom:
    c = get_class_for_user(db, class_id, user)
    if user.role != "lecturer" or c.lecturer_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Chỉ Giảng viên phụ trách lớp mới thực hiện được"
        )
    return c


# ================================================================ lịch 15 tuần học (liền mạch, không có tuần nghỉ)
def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


TERM_NAME = {"thu": "Thu", "xuan": "Xuân", "he": "Hè"}


def term_of(d: date) -> tuple[str, str]:
    """Học kỳ theo ngày bắt đầu học: tháng 7–11 → Thu · tháng 12–4 → Xuân · tháng 5–6 → Hè. Trả về (năm học, kỳ)."""
    if 7 <= d.month <= 11:
        return f"{d.year}-{d.year + 1}", "thu"
    if d.month == 12:
        return f"{d.year}-{d.year + 1}", "xuan"
    return f"{d.year - 1}-{d.year}", ("xuan" if d.month <= 4 else "he")


def semester_for_date(db: Session, d: date) -> Semester:
    """Học kỳ tự động: tìm học kỳ chứa ngày bắt đầu, chưa có thì tạo mới (Admin không phải khai báo).
    Ngày bắt đầu học kỳ = ngày bắt đầu sớm nhất của các lớp trong kỳ."""
    year, term = term_of(d)
    start = d if term == "he" else monday_of(d)
    sem = db.scalar(select(Semester).where(Semester.year == year, Semester.term == term))
    if sem is None:
        sem = Semester(year=year, term=term, start_date=start)
        db.add(sem)
        db.flush()
    elif start < sem.start_date:
        sem.start_date = start
    return sem


def semester_label(sem: Semester) -> str:
    y1, y2 = sem.year.split("-")
    return f"Học kỳ {TERM_NAME[sem.term]} {y1 if sem.term == 'thu' else y2}"


def semester_end(sem: Semester) -> date:
    """Kỳ chính: 15 tuần · kỳ Hè: 15 buổi × 3 buổi/tuần ≈ 5 tuần (lấy tròn 6 tuần để gồm cả lịch học bù)."""
    return (
        monday_of(sem.start_date)
        + timedelta(weeks=6 if sem.term == "he" else 15)
        - timedelta(days=1)
    )


def unit_count(c: Classroom) -> int:
    return 10 if c.course_type == "political" else 15


def is_summer(c: Classroom) -> bool:
    return bool(c.semester_ref and c.semester_ref.term == "he")


def unit_label(c: Classroom) -> str:
    return "Buổi" if is_summer(c) else "Tuần"


def layout_weeks(db: Session, c: Classroom) -> list[ClassSession]:
    """Tạo/cập nhật lịch học của lớp:
    - Kỳ Thu/Xuân: 1 buổi/tuần → mỗi đơn vị là 1 tuần (thứ Hai → Chủ nhật), liên tiếp, không có tuần nghỉ.
    - Kỳ Hè: 3 buổi/tuần (meeting_days) → mỗi đơn vị là 1 buổi, kéo dài tới trước buổi kế tiếp.
    - Môn thường 15 đơn vị · môn lý luận chính trị 10 đơn vị."""
    weeks = {
        w.number: w
        for w in db.scalars(select(ClassSession).where(ClassSession.class_id == c.id)).all()
    }
    n_units = unit_count(c)
    if is_summer(c):
        days, d = [], c.start_date
        wanted = sorted(set(c.meeting_days or [0, 2, 4]))
        while len(days) < n_units:
            if d.weekday() in wanted:
                days.append(d)
            d += timedelta(days=1)
        spans = [
            (days[i], days[i + 1] if i + 1 < len(days) else days[i] + timedelta(days=1))
            for i in range(n_units)
        ]
    else:
        start = monday_of(c.start_date)
        spans = [
            (start + timedelta(weeks=i), start + timedelta(weeks=i + 1)) for i in range(n_units)
        ]
    for n, (a, b) in enumerate(spans, start=1):
        w = weeks.get(n)
        if w is None:
            w = ClassSession(class_id=c.id, number=n, title="")
            db.add(w)
            weeks[n] = w
        w.starts_at, w.ends_at = vn_day_start_utc(a), vn_day_start_utc(b)
    for n in [k for k in weeks if k > n_units]:  # đổi loại học phần 15 → 10 buổi
        db.delete(weeks.pop(n))
    db.flush()
    return [weeks[i] for i in sorted(weeks)]


def week_status(w: ClassSession, today: date | None = None) -> str:
    today = today or today_vn()
    if today < vn_date(w.starts_at):
        return "upcoming"
    return "current" if today < vn_date(w.ends_at) else "done"


def class_timeline(db: Session, c: Classroom) -> dict:
    weeks = db.scalars(
        select(ClassSession).where(ClassSession.class_id == c.id).order_by(ClassSession.number)
    ).all()
    today = today_vn()
    statuses = [week_status(w, today) for w in weeks]
    current = next((w for w, s in zip(weeks, statuses) if s == "current"), None)
    done = statuses.count("done")
    ul = unit_label(c)
    if not weeks or today < vn_date(weeks[0].starts_at):
        phase, label = "not_started", "Chưa bắt đầu"
    elif done == len(weeks):
        phase, label = "ended", f"Đã kết thúc {len(weeks)} {ul.lower()}"
    else:
        phase, label = "learning", (
            f"Đang học {ul.lower()} {current.number}" if current else "Đang học"
        )
    return {
        "phase": phase,
        "label": label,
        "unit_label": ul,
        "current_week": current.number if current else None,
        "current_week_id": current.id if current else None,
        "weeks_done": done,
        "week_count": len(weeks),
        "start_date": vn_date(weeks[0].starts_at) if weeks else c.start_date,
        "end_date": vn_date(weeks[-1].ends_at) - timedelta(days=1) if weeks else None,
    }


def can_ask(w: ClassSession, timeline: dict) -> tuple[bool, str]:
    """Sinh viên chỉ gửi câu hỏi cho tuần 1 → tuần đang học; sau tuần 15 không gửi được nữa."""
    ul = (timeline.get("unit_label") or "Tuần").lower()
    if timeline["phase"] == "ended":
        return False, f"Lớp đã học xong {timeline['week_count']} {ul}, không gửi thêm câu hỏi được"
    if week_status(w) == "upcoming":
        return (
            False,
            f"{ul.capitalize()} này chưa học, bạn chỉ gửi được câu hỏi từ {ul} 1 đến {ul} đang học",
        )
    return True, ""


def week_out(db: Session, w: ClassSession, timeline: dict | None = None) -> dict:
    timeline = timeline or class_timeline(db, w.classroom)
    counts = dict(
        db.execute(
            select(Question.status, func.count())
            .where(Question.session_id == w.id)
            .group_by(Question.status)
        ).all()
    )
    review = db.scalar(
        select(func.count())
        .select_from(Question)
        .where(
            Question.session_id == w.id,
            Question.status == "waiting",
            Question.reuse_from_id.is_not(None),
        )
    )
    st = week_status(w)
    ok, reason = can_ask(w, timeline)
    return {
        "id": w.id,
        "class_id": w.class_id,
        "number": w.number,
        "unit_label": timeline.get("unit_label", "Tuần"),
        "unit_count": timeline.get("week_count"),
        "title": w.title or "",
        "description": w.description or "",
        "start_date": vn_date(w.starts_at),
        "end_date": vn_date(w.ends_at) - timedelta(days=1),
        "status": st,
        "status_label": STATUS_LABEL[st],
        "can_ask": ok,
        "ask_blocked_reason": reason,
        "question_count": sum(v for k, v in counts.items() if k != "deleted"),
        "answered_count": counts.get("answered", 0),
        "waiting_count": counts.get("waiting", 0),
        "flagged_count": counts.get("flagged", 0),
        "review_count": review,
        "material_count": db.scalar(
            select(func.count()).select_from(Material).where(Material.week_id == w.id)
        ),
        "has_summary": bool(w.summary),
    }


def get_week_for_user(db: Session, week_id: int, user: User) -> tuple[ClassSession, Classroom]:
    w = db.get(ClassSession, week_id)
    if w is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tuần học")
    return w, get_class_for_user(db, w.class_id, user)


# ================================================================ câu hỏi (ẩn danh)
def original_answer(db: Session, q: Question) -> Answer | None:
    """Câu trả lời gốc (không phải bản sao) mới nhất của một câu hỏi."""
    return db.scalar(
        select(Answer)
        .where(Answer.question_id == q.id)
        .order_by(Answer.created_at.desc(), Answer.id.desc())
    )


def answer_out(db: Session, a: Answer, names: dict, for_lecturer: bool) -> dict:
    d = {
        "id": a.id,
        "content": a.content,
        "via_group": a.via_group or bool(a.source_answer_id),
        "lecturer_name": names.get(a.lecturer_id),
        "created_at": as_utc(a.created_at),
        "edited_at": as_utc(a.edited_at),
    }
    if for_lecturer:
        d["copies_count"] = db.scalar(
            select(func.count()).select_from(Answer).where(Answer.source_answer_id == a.id)
        )
        d["is_copy"] = bool(a.source_answer_id)
    return d


def question_out(
    db: Session, q: Question, with_answers: bool = True, for_lecturer: bool = False
) -> dict:
    """Định dạng câu hỏi trả về cho client. TUYỆT ĐỐI không có thông tin người hỏi."""
    group = None
    if q.group and q.group.status != "rejected":
        group = {
            "id": q.group.id,
            "label": q.group.label,
            "status": q.group.status,
            "score": round(q.group.score, 2),
            "has_answer": bool(q.group.answer_text),
        }
    week = db.get(ClassSession, q.session_id)
    data = {
        "id": q.id,
        "code": question_code(q.seq),
        "session_id": q.session_id,
        "week_id": q.session_id,
        "week_number": week.number if week else None,
        "content": q.content,
        "status": q.status,
        "created_at": as_utc(q.created_at),
        "answered_at": as_utc(q.answered_at),
        "attachments": [
            {"id": a.id, "name": a.filename, "type": a.file_type, "size": a.size_bytes}
            for a in q.attachments
        ],
        "attachment_name": q.attachments[0].filename if q.attachments else None,
        "has_attachment": bool(q.attachments),
        "group": group,
        "edited_at": as_utc(q.edited_at),
    }
    if not for_lecturer:  # chỉ phía sinh viên cần biết có sửa/xóa được không
        data["can_modify"] = student_edit_block(db, q) is None
    if for_lecturer and q.reuse_from_id and q.status == "waiting":
        src = db.get(Question, q.reuse_from_id)
        a = original_answer(db, src) if src else None
        if src and a:
            sw = db.get(ClassSession, src.session_id)
            data["reuse"] = {
                "question_id": src.id,
                "code": question_code(src.seq),
                "week_number": sw.number if sw else None,
                "content": src.content,
                "answer": a.content,
                "score": round(q.reuse_score or 0, 2),
            }
    if with_answers:
        answers = db.scalars(
            select(Answer).where(Answer.question_id == q.id).order_by(Answer.created_at)
        ).all()
        names = (
            {
                u.id: u.full_name
                for u in db.scalars(
                    select(User).where(User.id.in_({a.lecturer_id for a in answers}))
                ).all()
            }
            if answers
            else {}
        )
        data["answers"] = [answer_out(db, a, names, for_lecturer) for a in answers]
    return data


def next_seq(db: Session, week_id: int) -> int:
    return (
        db.scalar(select(func.max(Question.seq)).where(Question.session_id == week_id)) or 0
    ) + 1


def author_of(db: Session, question_id: int) -> int | None:
    return db.scalar(
        select(QuestionAuthor.student_id).where(QuestionAuthor.question_id == question_id)
    )


# ================================================================ thông báo
def notify(
    db: Session, user_id: int, title: str, body: str | None = None, link: str | None = None
) -> None:
    db.add(Notification(user_id=user_id, title=title, body=body, link=link))


def notify_upsert(
    db: Session, user_id: int, key: str, make_title, body: str | None, link: str | None
) -> None:
    """Thông báo gộp: nếu đã có thông báo CHƯA ĐỌC cùng loại thì chỉ tăng con số và đưa lên đầu."""
    n = db.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.key == key,
            Notification.is_read.is_(False),
        )
    )
    if n is None:
        n = Notification(user_id=user_id, key=key, count=0, title="", body=body, link=link)
        db.add(n)
    n.count = (n.count or 0) + 1
    n.title, n.body, n.link, n.created_at = make_title(n.count), body, link, utcnow()


def _week_label(db: Session, q: Question) -> tuple[Classroom, ClassSession, str]:
    c = db.get(Classroom, q.class_id)
    w = db.get(ClassSession, q.session_id)
    return c, w, f"{c.code} · {unit_label(c)} {w.number}"


# ================================================================ trả lời
def record_answer(
    db: Session,
    q: Question,
    lecturer_id: int,
    content: str,
    via_group: bool = False,
    source_question_id: int | None = None,
    source_answer_id: int | None = None,
) -> Answer:
    a = Answer(
        question_id=q.id,
        lecturer_id=lecturer_id,
        content=content,
        via_group=via_group,
        source_question_id=source_question_id,
        source_answer_id=source_answer_id,
    )
    db.add(a)
    db.flush()
    if q.status == "waiting":
        q.status, q.answered_at = "answered", utcnow()
    q.reuse_from_id, q.reuse_score = None, None
    student_id = author_of(db, q.id)
    if student_id:
        notify(
            db,
            student_id,
            f"Giảng viên đã trả lời câu hỏi {question_code(q.seq)}",
            plain_text(q.content)[:120],
            f"student-week.html?week={q.session_id}&tab=mine",
        )
    return a


def set_group_answer(
    g: SimilarGroup, content: str, lecturer_id: int, source_question_id: int | None
) -> None:
    g.answer_text, g.answered_by, g.source_question_id = content, lecturer_id, source_question_id


def edit_answer(db: Session, a: Answer, content: str, apply_to_copies: bool) -> int:
    """Sửa câu trả lời; nếu là câu trả lời gốc và được chọn, cập nhật luôn các bản sao. Trả về số bản sao đã cập nhật."""
    now = utcnow()
    a.content, a.edited_at = content, now
    updated = 0
    q = db.get(Question, a.question_id)
    sid = author_of(db, q.id)
    if sid:
        notify(
            db,
            sid,
            f"Giảng viên đã cập nhật câu trả lời cho câu hỏi {question_code(q.seq)}",
            plain_text(q.content)[:120],
            f"student-week.html?week={q.session_id}&tab=mine",
        )
    if not a.source_answer_id:
        for g in db.scalars(
            select(SimilarGroup).where(SimilarGroup.source_question_id == a.question_id)
        ).all():
            g.answer_text = content
        if apply_to_copies:
            for c in db.scalars(select(Answer).where(Answer.source_answer_id == a.id)).all():
                c.content, c.edited_at = content, now
                cq = db.get(Question, c.question_id)
                csid = author_of(db, cq.id)
                if csid:
                    notify(
                        db,
                        csid,
                        f"Giảng viên đã cập nhật câu trả lời cho câu hỏi {question_code(cq.seq)}",
                        plain_text(cq.content)[:120],
                        f"student-week.html?week={cq.session_id}&tab=mine",
                    )
                updated += 1
    return updated


# ================================================================ câu hỏi tương đồng — LUÔN chờ Giảng viên duyệt
def _ensure_group(
    db: Session, a: Question, b: Question, score: float, status_: str = "suggested"
) -> SimilarGroup:
    g = a.group if a.group and a.group.status != "rejected" else None
    if g is None:
        n = (
            db.scalar(
                select(func.count())
                .select_from(SimilarGroup)
                .where(SimilarGroup.class_id == a.class_id)
            )
            or 0
        )
        g = SimilarGroup(
            class_id=a.class_id,
            session_id=b.session_id,
            label=f"SIM-{n + 1:02d}",
            status=status_,
            score=score,
        )
        db.add(g)
        db.flush()
        a.group_id = g.id
    b.group_id = g.id
    g.score = min(g.score, score)
    return g


def assign_similar(db: Session, q: Question, notify_new: bool = True) -> str:
    """So câu hỏi mới với các câu khác CÙNG LỚP (mọi tuần):
    - Giống một câu ĐÃ được Giảng viên trả lời → gợi ý dùng lại câu trả lời (chờ Giảng viên "Duyệt & gửi").
    - Giống một câu CHƯA có câu trả lời → gom nhóm đề xuất (Giảng viên xác nhận rồi trả lời chung).
    Không bao giờ tự gửi câu trả lời. Trả về 'review' | 'group' | 'none'."""
    c, w, label = _week_label(db, q)
    others = db.scalars(
        select(Question).where(
            Question.class_id == q.class_id,
            Question.id != q.id,
            Question.no_auto.is_(False),
            Question.status.in_(("waiting", "answered")),
        )
    ).all()
    best, best_score = None, 0.0
    for o in others:
        sc = ai.cosine(q.embedding, o.embedding)
        if sc > best_score:
            best, best_score = o, sc
    result = "none"
    if (
        best is not None
        and best_score >= ai.similarity_threshold()
        and not (best.group and best.group.status == "rejected")
    ):
        src = None
        if original_answer(db, best):  # đã có câu trả lời
            src = best
        elif best.group and best.group.status == "confirmed" and best.group.source_question_id:
            src = db.get(Question, best.group.source_question_id)
        if src is not None:
            q.reuse_from_id, q.reuse_score = src.id, best_score
            if best.group and best.group.status != "rejected":
                q.group_id = best.group.id
            notify_upsert(
                db,
                c.lecturer_id,
                f"review:{c.id}:{w.id}",
                lambda n: f"{label}: {n} câu hỏi mới giống câu đã trả lời, chờ duyệt",
                "Duyệt để gửi lại câu trả lời trước, hoặc trả lời riêng",
                f"lecturer-week.html?week={w.id}&filter=review",
            )
            return "review"
        new_group = best.group is None or best.group.status == "rejected"
        g = _ensure_group(db, best, q, best_score)
        if new_group:
            pending = (
                db.scalar(
                    select(func.count())
                    .select_from(SimilarGroup)
                    .where(SimilarGroup.class_id == c.id, SimilarGroup.status == "suggested")
                )
                or 1
            )
            notify_upsert(
                db,
                c.lecturer_id,
                f"group:{c.id}:{w.id}",
                lambda n: f"{label}: NEU AI đề xuất nhóm câu hỏi tương đồng — cần xác nhận",
                f"{pending} nhóm đang chờ xác nhận",
                f"lecturer-week.html?week={w.id}&groups=1",
            )
        result = "group"
    if notify_new:  # sửa câu hỏi không tính là câu hỏi mới
        notify_upsert(
            db,
            c.lecturer_id,
            f"newq:{c.id}:{w.id}",
            lambda n: f"{label}: {n} câu hỏi mới đang chờ trả lời",
            "Bấm để xem và trả lời",
            f"lecturer-week.html?week={w.id}",
        )
    return result


# ================================================================ sinh viên sửa / xóa câu hỏi của mình
def student_edit_block(db: Session, q: Question) -> str | None:
    """Lý do KHÔNG được sửa/xóa câu hỏi (None = được). Chỉ khi còn chờ phản hồi, chưa ai trả lời,
    chưa bị gắn cờ và chưa nằm trong nhóm tương đồng đã được giảng viên xác nhận."""
    if q.status != "waiting":
        return "Câu hỏi đã được xử lý nên không thể sửa hoặc xóa"
    if db.scalar(select(func.count()).select_from(Answer).where(Answer.question_id == q.id)):
        return "Câu hỏi đã có phản hồi nên không thể sửa hoặc xóa"
    if db.scalar(select(func.count()).select_from(Flag).where(Flag.question_id == q.id)):
        return "Câu hỏi đang được kiểm duyệt nên không thể sửa hoặc xóa"
    if q.group is not None and q.group.status == "confirmed":
        return "Câu hỏi đã nằm trong nhóm được giảng viên xác nhận nên không thể sửa hoặc xóa"
    return None


def detach_from_group(db: Session, q: Question) -> None:
    """Gỡ câu hỏi khỏi nhóm đề xuất; nhóm chỉ còn 1 câu (hoặc rỗng) thì xóa luôn nhóm."""
    q.reuse_from_id, q.reuse_score = None, None
    g = q.group
    q.group_id = None
    if g is None:
        return
    db.flush()
    members = db.scalars(
        select(Question).where(Question.group_id == g.id, Question.id != q.id)
    ).all()
    if g.status == "suggested" and len(members) < 2:
        for m in members:
            m.group_id = None
        db.flush()
        db.delete(g)


def drop_new_question_notice(db: Session, q: Question) -> None:
    """Trừ 1 trong thông báo gộp 'N câu hỏi mới đang chờ trả lời' khi câu hỏi bị xóa."""
    c, w, label = _week_label(db, q)
    n = db.scalar(
        select(Notification).where(
            Notification.user_id == c.lecturer_id,
            Notification.key == f"newq:{c.id}:{w.id}",
            Notification.is_read.is_(False),
        )
    )
    if n is None:
        return
    if (n.count or 0) <= 1:
        db.delete(n)
    else:
        n.count -= 1
        n.title = f"{label}: {n.count} câu hỏi mới đang chờ trả lời"


def approve_reuse(db: Session, q: Question, lecturer: User) -> Answer:
    """Giảng viên duyệt: lúc này mới tạo câu trả lời giống câu tương đồng trước và gửi cho sinh viên."""
    src = db.get(Question, q.reuse_from_id) if q.reuse_from_id else None
    orig = original_answer(db, src) if src else None
    if orig is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Câu được gợi ý không còn câu trả lời để dùng lại"
        )
    root = (
        db.get(Answer, orig.source_answer_id) if orig.source_answer_id else orig
    )  # luôn trỏ về câu trả lời gốc
    g = _ensure_group(db, src, q, q.reuse_score or 0.9, "confirmed")
    g.status = "confirmed"
    if not g.answer_text:
        set_group_answer(g, root.content, root.lecturer_id, root.question_id)
    return record_answer(
        db,
        q,
        lecturer.id,
        root.content,
        via_group=True,
        source_question_id=root.question_id,
        source_answer_id=root.id,
    )


def reject_reuse(q: Question) -> None:
    """Giảng viên bấm "Không giống": bỏ gợi ý, câu hỏi thành câu chờ bình thường."""
    q.reuse_from_id, q.reuse_score, q.no_auto = None, None, True
    if q.group and q.group.status == "confirmed":
        q.group_id = None


def notify_admins_flags(db: Session) -> None:
    """Báo cho Admin số nội dung bị gắn cờ đang chờ kiểm duyệt (gộp vào một thông báo chưa đọc)."""
    from app.models import Flag

    pending = db.scalar(select(func.count()).select_from(Flag).where(Flag.status == "pending")) or 0
    for aid in db.scalars(select(User.id).where(User.role == "admin")).all():
        n = db.scalar(
            select(Notification).where(
                Notification.user_id == aid,
                Notification.key == "flags",
                Notification.is_read.is_(False),
            )
        )
        if pending == 0:
            if n:
                n.is_read = True
            continue
        if n is None:
            n = Notification(user_id=aid, key="flags", count=0, title="")
            db.add(n)
        n.count, n.created_at, n.link = pending, utcnow(), "admin-reports.html"
        n.title = f"Có {pending} nội dung bị gắn cờ, chờ kiểm duyệt"
        n.body = "Bấm để mở hàng đợi kiểm duyệt"
