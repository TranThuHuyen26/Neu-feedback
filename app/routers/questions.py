"""Thao tác trên từng câu hỏi: trả lời, duyệt / bỏ gợi ý dùng lại câu trả lời,
sửa câu trả lời, gợi ý AI, gắn cờ, nhờ NEU AI giải thích (sinh viên), tệp đính kèm, lịch sử câu hỏi.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Answer,
    ChatMessage,
    ClassSession,
    Classroom,
    Flag,
    Question,
    QuestionAuthor,
    User,
)
from app.schemas import AnswerEdit, AnswerIn, FlagIn, QuestionEdit
from app.security import get_current_user, require_role
from app.services import ai
from app.services.core import (
    approve_reuse,
    assign_similar,
    author_of,
    can_ask,
    class_timeline,
    detach_from_group,
    drop_new_question_notice,
    edit_answer,
    get_owned_class,
    original_answer,
    question_out,
    record_answer,
    reject_reuse,
    set_group_answer,
    student_edit_block,
    week_status,
)
from app.utils import as_utc, utcnow
from app.services.files import resolve_stored

router = APIRouter(prefix="/api", tags=["Câu hỏi"])


def _lecturer_question(db: Session, question_id: int, user: User) -> tuple[Question, Classroom]:
    q = db.get(Question, question_id)
    if q is None or q.status == "deleted":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy câu hỏi")
    return q, get_owned_class(db, q.class_id, user)


def _student_question(db: Session, question_id: int, user: User) -> Question:
    q = db.get(Question, question_id)
    if q is None or q.status == "deleted" or author_of(db, q.id) != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy câu hỏi của bạn")
    return q


@router.post(
    "/questions/{question_id}/answer",
    summary="Giảng viên trả lời câu hỏi",
)
def answer(
    question_id: int,
    body: AnswerIn,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    q, _ = _lecturer_question(db, question_id, user)
    if q.status in ("flagged", "hidden"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Câu hỏi đang chờ Admin kiểm duyệt")
    text = body.content.strip()
    record_answer(db, q, user.id, text)
    g = q.group
    if g and g.status == "confirmed" and not g.answer_text:
        set_group_answer(g, text, user.id, q.id)
    db.commit()
    return question_out(db, q, for_lecturer=True)


@router.post(
    "/questions/{question_id}/approve-reuse",
    summary="Duyệt & gửi: dùng lại câu trả lời của câu tương đồng trước",
)
def approve(
    question_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    q, _ = _lecturer_question(db, question_id, user)
    if q.status != "waiting" or not q.reuse_from_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Câu hỏi này không có gợi ý dùng lại câu trả lời"
        )
    approve_reuse(db, q, user)
    db.commit()
    return question_out(db, q, for_lecturer=True)


@router.post(
    "/questions/{question_id}/reject-reuse",
    summary="Không giống: bỏ gợi ý, câu hỏi thành câu chờ bình thường",
)
def reject(
    question_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    q, _ = _lecturer_question(db, question_id, user)
    reject_reuse(q)
    db.commit()
    return question_out(db, q, for_lecturer=True)


@router.patch(
    "/answers/{answer_id}",
    summary="Sửa câu trả lời (có thể cập nhật cho các câu tương tự đã nhận câu trả lời này)",
)
def edit(
    answer_id: int,
    body: AnswerEdit,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    a = db.get(Answer, answer_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy câu trả lời")
    q, _ = _lecturer_question(db, a.question_id, user)
    n = edit_answer(db, a, body.content.strip(), body.apply_to_copies)
    db.commit()
    return {"question": question_out(db, q, for_lecturer=True), "copies_updated": n}


# ---------------------------------------------------------------- sinh viên sửa / xóa câu hỏi của mình
@router.patch(
    "/questions/{question_id}/mine",
    summary="Sinh viên sửa câu hỏi của mình (chỉ khi còn chờ phản hồi)",
)
def edit_my_question(
    question_id: int,
    body: QuestionEdit,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    q = _student_question(db, question_id, user)
    reason = student_edit_block(db, q)
    if reason:
        raise HTTPException(status.HTTP_409_CONFLICT, reason)
    content = body.content.strip()
    if not content:
        raise HTTPException(422, "Vui lòng nhập nội dung câu hỏi")
    if content != q.content:
        q.content = content
        q.embedding = ai.embed([content])[0]  # nội dung đổi nên gộp nhóm lại từ đầu
        q.edited_at = utcnow()
        detach_from_group(db, q)
        db.flush()
        assign_similar(db, q, notify_new=False)
    db.commit()
    db.refresh(q)
    return question_out(db, q)


@router.delete(
    "/questions/{question_id}/mine",
    summary="Sinh viên xóa câu hỏi của mình (chỉ khi còn chờ phản hồi) — xóa hẳn, không khôi phục",
)
def delete_my_question(
    question_id: int,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    q = _student_question(db, question_id, user)
    reason = student_edit_block(db, q)
    if reason:
        raise HTTPException(status.HTTP_409_CONFLICT, reason)
    files = [resolve_stored(a.stored_path) for a in q.attachments]
    detach_from_group(db, q)
    drop_new_question_notice(db, q)
    db.delete(q)  # kéo theo người hỏi (question_authors) và tệp đính kèm trong CSDL
    db.commit()
    for f in files:
        f.unlink(missing_ok=True)
    return {"deleted": True}


# ---------------------------------------------------------------- sinh viên: nhờ NEU AI giải thích
@router.post(
    "/questions/{question_id}/explain",
    summary="Nhờ NEU AI giải thích thêm câu trả lời của Giảng viên",
)
def explain(
    question_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)
):
    q = _student_question(db, question_id, user)
    a = original_answer(db, q)
    if a is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Câu hỏi chưa có câu trả lời để giải thích thêm"
        )
    from app.routers.assistant import retrieve

    w = db.get(ClassSession, q.session_id)
    contexts = retrieve(db, q.class_id, q.content + "\n" + a.content)
    try:
        text = ai.explain_answer(q.content, a.content, contexts, w.classroom.subject)
    except ai.AIBusy as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, exc.message)
    sources = [
        {"material_id": x["material_id"], "filename": x["filename"], "page": x["page"]}
        for x in contexts[:4]
    ]
    db.add(
        ChatMessage(
            user_id=user.id,
            class_id=q.class_id,
            role="user",
            content=f"Giải thích thêm câu trả lời cho câu hỏi: {q.content}",
        )
    )
    db.add(
        ChatMessage(user_id=user.id, class_id=q.class_id, role="ai", content=text, sources=sources)
    )
    db.commit()
    return {"explanation": text, "sources": sources}


@router.post(
    "/questions/{question_id}/suggest",
    summary="Gợi ý trả lời bằng NEU AI (chỉ chạy khi Giảng viên bấm)",
)
def suggest(
    question_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    q, c = _lecturer_question(db, question_id, user)
    try:
        return {"suggestion": ai.suggest_answer(q.content, c.subject)}
    except ai.AIBusy as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, exc.message)


@router.post("/questions/{question_id}/flag", summary="Gắn cờ để Admin kiểm duyệt")
def flag(
    question_id: int,
    body: FlagIn,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    q, _ = _lecturer_question(db, question_id, user)
    if db.scalar(select(Flag.id).where(Flag.question_id == q.id, Flag.status == "pending")):
        raise HTTPException(status.HTTP_409_CONFLICT, "Câu hỏi đã được gắn cờ")
    db.add(
        Flag(
            question_id=q.id,
            flagged_by=user.id,
            reason=body.reason,
            ai_score=ai.moderation_score(q.content),
        )
    )
    q.status = "flagged"
    db.flush()
    from app.services.core import notify_admins_flags

    notify_admins_flags(db)  # Admin nhận thông báo: có N nội dung chờ kiểm duyệt
    db.commit()
    return question_out(db, q)


@router.get(
    "/questions/{question_id}/attachments/{attachment_id}",
    summary="Tải một tệp đính kèm của câu hỏi",
)
def attachment_file(
    question_id: int,
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.get(Question, question_id)
    a = next((x for x in (q.attachments if q else []) if x.id == attachment_id), None)
    return _send_attachment(db, q, a, user)


@router.get(
    "/questions/{question_id}/attachment", summary="(cũ) Tải tệp đính kèm đầu tiên của câu hỏi"
)
def attachment(
    question_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    q = db.get(Question, question_id)
    return _send_attachment(db, q, q.attachments[0] if q and q.attachments else None, user)


def _send_attachment(db: Session, q: Question | None, a, user: User):
    if q is None or a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có tệp đính kèm")
    allowed = (
        user.role == "admin"
        or (user.role == "lecturer" and db.get(Classroom, q.class_id).lecturer_id == user.id)
        or (user.role == "student" and author_of(db, q.id) == user.id)
    )
    if not allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền xem tệp này")
    path = resolve_stored(a.stored_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tệp không còn trên máy chủ")
    return FileResponse(path, filename=a.filename)


@router.get("/me/questions", summary="Tất cả câu hỏi tôi đã gửi (trang Theo dõi phản hồi)")
def my_all_questions(
    class_id: int | None = None,
    status_filter: str | None = None,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Question, ClassSession, Classroom)
        .join(QuestionAuthor, QuestionAuthor.question_id == Question.id)
        .join(ClassSession, ClassSession.id == Question.session_id)
        .join(Classroom, Classroom.id == Question.class_id)
        .where(QuestionAuthor.student_id == user.id, Question.status != "deleted")
    )
    if class_id:
        stmt = stmt.where(Question.class_id == class_id)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    rows = db.execute(stmt.order_by(Question.created_at.desc())).all()
    out = []
    for q, s, c in rows:
        d = question_out(db, q)
        d.update(
            class_id=c.id,
            class_code=c.code,
            subject=c.subject,
            week_title=s.title,
            week_status=week_status(s),
            week_start=as_utc(s.starts_at),
        )
        out.append(d)
    return out
