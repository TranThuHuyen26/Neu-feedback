"""Tuần học: nội dung tuần, gửi câu hỏi ẩn danh (tuần 1 → tuần đang học), danh sách câu hỏi,
nhóm câu hỏi tương đồng (xác nhận + trả lời chung có gợi ý AI), duyệt câu hỏi giống câu đã trả lời, báo cáo tuần.
"""

import uuid
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Answer,
    ClassSession,
    Enrollment,
    Question,
    QuestionAttachment,
    QuestionAuthor,
    SimilarGroup,
    User,
)
from app.schemas import AnswerIn, GroupAction, Msg, WeekUpdate
from app.security import get_current_user, require_role
from app.services import ai
from app.services.core import (
    approve_reuse,
    assign_similar,
    can_ask,
    class_timeline,
    get_owned_class,
    get_week_for_user,
    next_seq,
    notify,
    original_answer,
    question_out,
    record_answer,
    set_group_answer,
    week_out,
)
from app.utils import as_utc, question_code, utcnow, vn_date
from app.services.files import to_stored

router = APIRouter(prefix="/api", tags=["Tuần học"])
settings = get_settings()
ATTACH_TYPES = {
    ".png": "IMG",
    ".jpg": "IMG",
    ".jpeg": "IMG",
    ".gif": "IMG",
    ".webp": "IMG",
    ".pdf": "PDF",
    ".docx": "DOC",
    ".pptx": "PPT",
    ".xlsx": "XLS",
}
MAX_ATTACHMENTS = 3


@router.get("/weeks/{week_id}", summary="Thông tin tuần học")
def get_week(week_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w, c = get_week_for_user(db, week_id, user)
    tl = class_timeline(db, c)
    data = week_out(db, w, tl)
    data.update(
        class_code=c.code, subject=c.subject, lecturer_name=c.lecturer.full_name, timeline=tl
    )
    return data


@router.patch("/weeks/{week_id}", summary="Giảng viên điền chủ đề & nội dung tuần")
def update_week(
    week_id: int,
    body: WeekUpdate,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    if body.title is not None:
        w.title = body.title.strip()
    if body.description is not None:
        w.description = body.description.strip()
    db.commit()
    return week_out(db, w)


# ---------------------------------------------------------------- sinh viên gửi câu hỏi
@router.post(
    "/weeks/{week_id}/questions",
    status_code=201,
    summary="Sinh viên gửi câu hỏi ẩn danh cho một tuần",
)
async def ask(
    week_id: int,
    content: str = Form(..., min_length=1, max_length=2000),
    attachments: list[UploadFile] | None = File(
        default=None, description="Tối đa 3 tệp: ảnh, PDF, Word, PowerPoint, Excel"
    ),
    attachment: UploadFile | None = File(default=None, description="(cũ) một tệp đính kèm"),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    w, c = get_week_for_user(db, week_id, user)
    ok, reason = can_ask(w, class_timeline(db, c))
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, reason)
    content = content.strip()
    if not content:
        raise HTTPException(422, "Vui lòng nhập nội dung câu hỏi")
    mine = db.scalar(
        select(func.count())
        .select_from(QuestionAuthor)
        .join(Question)
        .where(Question.session_id == w.id, QuestionAuthor.student_id == user.id)
    )
    if mine >= settings.max_questions_per_student_per_week:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Bạn đã gửi quá nhiều câu hỏi trong tuần này"
        )

    q = Question(session_id=w.id, class_id=w.class_id, seq=next_seq(db, w.id), content=content)
    files = [
        f
        for f in (attachments or []) + ([attachment] if attachment else [])
        if f is not None and f.filename
    ]
    if len(files) > MAX_ATTACHMENTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Chỉ đính kèm tối đa {MAX_ATTACHMENTS} tệp"
        )
    loaded = []
    for f in files:  # kiểm tra hết trước khi lưu tệp nào
        ext = Path(f.filename).suffix.lower()
        if ext not in ATTACH_TYPES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"“{f.filename}”: chỉ đính kèm ảnh (PNG, JPG, GIF, WEBP), PDF, Word, PowerPoint, Excel",
            )
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"“{f.filename}” vượt quá {settings.max_upload_mb} MB"
            )
        loaded.append((f, ext, data))
    folder = settings.upload_dir / "questions"
    for f, ext, data in loaded:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{uuid.uuid4().hex}{ext}"
        path.write_bytes(data)
        q.attachments.append(
            QuestionAttachment(
                filename=Path(f.filename).name,
                stored_path=to_stored(path),
                file_type=ATTACH_TYPES[ext],
                size_bytes=len(data),
            )
        )

    q.embedding = ai.embed([content])[0]
    db.add(q)
    db.flush()
    db.add(QuestionAuthor(question_id=q.id, student_id=user.id))  # danh tính lưu riêng
    assign_similar(db, q)  # chỉ gợi ý — không tự gửi câu trả lời
    db.commit()
    return question_out(db, q)


@router.get("/weeks/{week_id}/my-questions", summary="Câu hỏi của tôi trong tuần (sinh viên)")
def my_questions(
    week_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)
):
    get_week_for_user(db, week_id, user)
    qs = db.scalars(
        select(Question)
        .join(QuestionAuthor, QuestionAuthor.question_id == Question.id)
        .where(
            Question.session_id == week_id,
            QuestionAuthor.student_id == user.id,
            Question.status != "deleted",
        )
        .order_by(Question.created_at.desc())
    ).all()
    return [question_out(db, q) for q in qs]


# ---------------------------------------------------------------- Giảng viên xem câu hỏi
def _counts(db: Session, week_id: int) -> dict:
    counts = dict(
        db.execute(
            select(Question.status, func.count())
            .where(Question.session_id == week_id)
            .group_by(Question.status)
        ).all()
    )
    counts["review"] = db.scalar(
        select(func.count())
        .select_from(Question)
        .where(
            Question.session_id == week_id,
            Question.status == "waiting",
            Question.reuse_from_id.is_not(None),
        )
    )
    return counts


@router.get(
    "/weeks/{week_id}/questions",
    summary="Câu hỏi của tuần — mới nhất ở trên, KHÔNG kèm danh tính (Giảng viên)",
)
def week_questions(
    week_id: int,
    status_filter: str | None = None,
    after_id: int | None = None,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    """`status_filter`: waiting | review (giống câu đã trả lời, chờ duyệt) | answered | flagged."""
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    stmt = select(Question).where(
        Question.session_id == w.id, Question.status.not_in(("deleted", "hidden"))
    )
    if status_filter == "review":
        stmt = stmt.where(Question.status == "waiting", Question.reuse_from_id.is_not(None))
    elif status_filter:
        stmt = stmt.where(Question.status == status_filter)
    if after_id:
        stmt = stmt.where(Question.id > after_id)
    qs = db.scalars(stmt.order_by(Question.created_at.desc(), Question.id.desc())).all()
    return {
        "week": week_out(db, w),
        "counts": _counts(db, w.id),
        "questions": [question_out(db, q, for_lecturer=True) for q in qs],
    }


@router.post(
    "/weeks/{week_id}/approve-all", summary="Duyệt tất cả câu hỏi giống câu đã trả lời trong tuần"
)
def approve_all(
    week_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    qs = db.scalars(
        select(Question).where(
            Question.session_id == w.id,
            Question.status == "waiting",
            Question.reuse_from_id.is_not(None),
        )
    ).all()
    done = []
    for q in qs:
        approve_reuse(db, q, user)
        done.append(question_code(q.seq))
    db.commit()
    return {"approved": done}


# ---------------------------------------------------------------- nhóm câu hỏi tương đồng (trong lớp)
def group_out(db: Session, g: SimilarGroup) -> dict:
    qs = db.scalars(
        select(Question).where(Question.group_id == g.id).order_by(Question.created_at)
    ).all()
    prev = None
    for q in qs:  # câu trả lời đã có trong nhóm → "Dùng lại câu trả lời trước"
        a = original_answer(db, q) if q.status == "answered" else None
        if a:
            prev = {"question_code": question_code(q.seq), "content": a.content}
    answered = [q for q in qs if q.status == "answered"]
    src = (
        db.get(Question, g.source_question_id)
        if g.source_question_id
        else (answered[0] if answered else None)
    )
    ga = original_answer(db, src) if src else None
    if ga and ga.source_answer_id:  # luôn trả về câu trả lời gốc (không phải bản sao)
        ga = db.get(Answer, ga.source_answer_id) or ga
    answer = None
    if ga:
        copies = db.scalar(
            select(func.count()).select_from(Answer).where(Answer.source_answer_id == ga.id)
        )
        answer = {
            "id": ga.id,
            "content": ga.content,
            "created_at": as_utc(ga.created_at),
            "edited_at": as_utc(ga.edited_at),
            "copies_count": copies,
            "question_code": question_code(db.get(Question, ga.question_id).seq),
        }
    return {
        "id": g.id,
        "label": g.label,
        "status": g.status,
        "score": round(g.score, 2),
        "answer_text": g.answer_text,
        "previous_answer": prev,
        "answer": answer,
        "can_split": not answered and not g.answer_text,
        "questions": [question_out(db, q, with_answers=False) for q in qs],
    }


@router.get(
    "/weeks/{week_id}/groups",
    summary="Nhóm tương đồng có câu hỏi của tuần này (nhóm có thể gồm nhiều tuần)",
)
def list_groups(
    week_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    ids = set(
        db.scalars(
            select(Question.group_id).where(
                Question.session_id == w.id, Question.group_id.is_not(None)
            )
        ).all()
    )
    groups = (
        db.scalars(
            select(SimilarGroup).where(SimilarGroup.id.in_(ids), SimilarGroup.status != "rejected")
        ).all()
        if ids
        else []
    )
    return [group_out(db, g) for g in groups]


def _owned_group(db: Session, group_id: int, user: User) -> SimilarGroup:
    g = db.get(SimilarGroup, group_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nhóm")
    get_owned_class(db, g.class_id or db.get(ClassSession, g.session_id).class_id, user)
    return g


@router.post("/groups/{group_id}", summary="Xác nhận nhóm / không gộp / tách nhóm")
def group_action(
    group_id: int,
    body: GroupAction,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    g = _owned_group(db, group_id, user)
    if body.action == "split" and (
        g.answer_text
        or db.scalar(
            select(func.count())
            .select_from(Question)
            .where(Question.group_id == g.id, Question.status == "answered")
        )
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Nhóm đã được trả lời nên không tách được nữa"
        )
    g.status = "confirmed" if body.action == "confirm" else "rejected"
    db.commit()
    return group_out(db, g)


@router.post(
    "/groups/{group_id}/suggest",
    summary="Gợi ý câu trả lời chung cho cả nhóm bằng NEU AI (chỉ chạy khi bấm)",
)
def suggest_group(
    group_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    g = _owned_group(db, group_id, user)
    qs = db.scalars(select(Question.content).where(Question.group_id == g.id)).all()
    c = db.get(ClassSession, g.session_id).classroom
    try:
        return {"suggestion": ai.suggest_group_answer(list(qs), c.subject)}
    except ai.AIBusy as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, exc.message)


@router.post(
    "/groups/{group_id}/answer",
    summary="Trả lời chung cho nhóm đã xác nhận (gửi cho mọi câu đang chờ trong nhóm)",
)
def answer_group(
    group_id: int,
    body: AnswerIn,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    g = _owned_group(db, group_id, user)
    if g.status != "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cần xác nhận nhóm trước khi trả lời chung")
    qs = db.scalars(
        select(Question)
        .where(
            Question.group_id == g.id,
            Question.status == "waiting",
        )
        .order_by(Question.created_at)
    ).all()
    if not qs:
        raise HTTPException(status.HTTP_409_CONFLICT, "Các câu hỏi trong nhóm đều đã được trả lời")
    text = body.content.strip()
    first = record_answer(db, qs[0], user.id, text, via_group=len(qs) > 1)
    for q in qs[1:]:
        record_answer(
            db,
            q,
            user.id,
            text,
            via_group=True,
            source_question_id=qs[0].id,
            source_answer_id=first.id,
        )
    set_group_answer(g, text, user.id, qs[0].id)
    db.commit()
    return {"answered": [question_code(q.seq) for q in qs], "group": group_out(db, g)}


# ---------------------------------------------------------------- báo cáo tuần
@router.get("/weeks/{week_id}/report", summary="Báo cáo tuần (Giảng viên)")
def report(
    week_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    qs = db.scalars(
        select(Question).where(Question.session_id == w.id, Question.status != "deleted")
    ).all()
    by_day, by_day_ans, waits = Counter(), Counter(), []
    reused = 0
    for q in qs:
        d = vn_date(q.created_at).isoformat()
        by_day[d] += 1
        if q.status == "answered":
            by_day_ans[d] += 1
            first = db.scalar(
                select(Answer).where(Answer.question_id == q.id).order_by(Answer.created_at)
            )
            if first and first.source_answer_id:
                reused += 1
            if q.answered_at:
                waits.append((as_utc(q.answered_at) - as_utc(q.created_at)).total_seconds())
    answered = sum(1 for q in qs if q.status == "answered")
    return {
        "week": week_out(db, w),
        "question_count": len(qs),
        "answered_count": answered,
        "reused_count": reused,
        "answer_rate": round(answered * 100 / len(qs)) if qs else 0,
        "avg_response_seconds": int(sum(waits) / len(waits)) if waits else None,
        "group_count": len({q.group_id for q in qs if q.group_id}),
        "by_day": [
            {"date": d, "questions": by_day[d], "answered": by_day_ans[d]} for d in sorted(by_day)
        ],
        "summary": w.summary,
        "summary_at": as_utc(w.summary_at),
    }


@router.post(
    "/weeks/{week_id}/summary",
    summary="Tóm tắt câu hỏi của tuần bằng NEU AI (chỉ tạo khi bấm; có lưu lại)",
)
def summarize(
    week_id: int,
    regenerate: bool = False,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    if w.summary and not regenerate:
        return {"summary": w.summary, "cached": True}
    texts = db.scalars(
        select(Question.content).where(
            Question.session_id == w.id, Question.status.in_(("waiting", "answered"))
        )
    ).all()
    try:
        w.summary = ai.summarize_session(
            f"Tuần {w.number}" + (f" · {w.title}" if w.title else ""), list(texts)
        )
    except ai.AIBusy as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, exc.message)
    w.summary_at = utcnow()
    db.commit()
    return {"summary": w.summary, "cached": False}


@router.post("/weeks/{week_id}/share", response_model=Msg, summary="Chia sẻ báo cáo tuần với lớp")
def share_report(
    week_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    w.shared_report = True
    for sid in db.scalars(select(Enrollment.student_id).where(Enrollment.class_id == c.id)).all():
        notify(
            db,
            sid,
            f"Giảng viên đã chia sẻ báo cáo tuần {w.number}",
            c.subject,
            f"student-week.html?week={w.id}",
        )
    db.commit()
    return Msg(message="Đã chia sẻ báo cáo với lớp")
