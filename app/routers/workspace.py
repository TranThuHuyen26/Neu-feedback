"""Tìm kiếm, tổng hợp trang chủ, danh sách câu hỏi cần xử lý (gộp mọi lớp) và ảnh chèn trong câu trả lời."""

import mimetypes
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    AnswerImage,
    ClassSession,
    Classroom,
    Enrollment,
    Flag,
    Material,
    Question,
    QuestionAuthor,
    SimilarGroup,
    User,
)
from app.security import get_current_user, require_role
from app.services.core import get_class_for_user, question_code, unit_label, week_status
from app.utils import utcnow
from app.services.files import resolve_stored, to_stored

router = APIRouter(prefix="/api", tags=["Không gian làm việc"])
IMG_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _my_classes(db: Session, user: User):
    if user.role == "lecturer":
        stmt = select(Classroom).where(
            Classroom.lecturer_id == user.id, Classroom.is_archived.is_(False)
        )
    elif user.role == "student":
        stmt = (
            select(Classroom)
            .join(Enrollment, Enrollment.class_id == Classroom.id)
            .where(Enrollment.student_id == user.id, Classroom.is_archived.is_(False))
        )
    else:
        stmt = select(Classroom).where(Classroom.is_archived.is_(False))
    return db.scalars(stmt).all()


# ---------------------------------------------------------------- ảnh trong câu trả lời
@router.post(
    "/answer-images", status_code=201, summary="Giảng viên tải ảnh để chèn vào câu trả lời"
)
async def upload_answer_image(
    class_id: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    c = get_class_for_user(db, class_id, user)
    if c.lecturer_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Chỉ Giảng viên phụ trách lớp mới chèn được ảnh"
        )
    ext = (
        ("." + (file.filename or "").rsplit(".", 1)[-1].lower())
        if "." in (file.filename or "")
        else ""
    )
    if ext not in IMG_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Chỉ nhận ảnh PNG, JPG, WEBP hoặc GIF"
        )
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Ảnh vượt quá 5 MB")
    folder = get_settings().upload_dir / "answer-images"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    img = AnswerImage(
        class_id=c.id,
        uploaded_by=user.id,
        filename=file.filename[:255],
        stored_path=to_stored(path),
        size_bytes=len(data),
    )
    db.add(img)
    db.commit()
    return {"id": img.id, "url": f"/api/answer-images/{img.id}", "filename": img.filename}


@router.get("/answer-images/{image_id}", summary="Xem ảnh trong câu trả lời (thành viên lớp)")
def get_answer_image(
    image_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    img = db.get(AnswerImage, image_id)
    if img is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy ảnh")
    get_class_for_user(db, img.class_id, user)  # sinh viên của lớp, Giảng viên phụ trách hoặc Admin
    ext = "." + img.stored_path.rsplit(".", 1)[-1].lower()
    return FileResponse(
        resolve_stored(img.stored_path), media_type=IMG_TYPES.get(ext, "application/octet-stream")
    )


# ---------------------------------------------------------------- tìm kiếm trên thanh trên cùng
@router.get("/search", summary="Tìm lớp học, tuần học, tài liệu trong phạm vi của người dùng")
def search(q: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = q.strip()
    if len(q) < 2:
        return {"classes": [], "weeks": [], "materials": []}
    like = f"%{q.lower()}%"
    classes = _my_classes(db, user)
    ids = [c.id for c in classes]
    by_id = {c.id: c for c in classes}
    cls = [c for c in classes if q.lower() in (c.code + " " + c.subject).lower()][:5]
    weeks = []
    if ids:
        num = int(q.split()[-1]) if q.split()[-1].isdigit() else None
        wq = select(ClassSession).where(ClassSession.class_id.in_(ids))
        wq = wq.where(
            or_(func.lower(ClassSession.title).like(like), ClassSession.number == num)
            if num
            else func.lower(ClassSession.title).like(like)
        )
        weeks = db.scalars(wq.order_by(ClassSession.class_id, ClassSession.number).limit(6)).all()
    mats = (
        db.scalars(
            select(Material)
            .where(Material.class_id.in_(ids), func.lower(Material.filename).like(like))
            .order_by(Material.created_at.desc())
            .limit(6)
        ).all()
        if ids
        else []
    )
    week_no = (
        {
            w.id: w.number
            for w in db.scalars(
                select(ClassSession).where(
                    ClassSession.id.in_([m.week_id for m in mats if m.week_id])
                )
            ).all()
        }
        if mats
        else {}
    )
    return {
        "classes": [
            {"id": c.id, "code": c.code, "subject": c.subject, "semester": c.semester} for c in cls
        ],
        "weeks": [
            {
                "id": w.id,
                "number": w.number,
                "unit_label": unit_label(by_id[w.class_id]),
                "title": w.title,
                "class_id": w.class_id,
                "class_code": by_id[w.class_id].code,
                "status": week_status(w),
            }
            for w in weeks
        ],
        "materials": [
            {
                "id": m.id,
                "filename": m.filename,
                "class_code": by_id[m.class_id].code,
                "week_id": m.week_id,
                "week_number": week_no.get(m.week_id),
            }
            for m in mats
        ],
    }


# ---------------------------------------------------------------- Giảng viên: tổng hợp & danh sách cần xử lý
def _lecturer_scope(db: Session, user: User, class_id: int | None):
    classes = _my_classes(db, user)
    if class_id:
        classes = [c for c in classes if c.id == class_id]
    return classes


@router.get("/lecturer/summary", summary="Tổng hợp việc cần xử lý của Giảng viên (trang chủ)")
def lecturer_summary(user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)):
    ids = [c.id for c in _my_classes(db, user)]
    if not ids:
        return {
            "new": 0,
            "groups": 0,
            "flagged": 0,
            "total": 0,
            "answered_rate": None,
            "classes_total": 0,
            "classes_in_session": 0,
            "weekly": [],
        }
    new = (
        db.scalar(
            select(func.count())
            .select_from(Question)
            .where(
                Question.class_id.in_(ids),
                Question.status == "waiting",
            )
        )
        or 0
    )
    groups = (
        db.scalar(
            select(func.count())
            .select_from(SimilarGroup)
            .where(SimilarGroup.class_id.in_(ids), SimilarGroup.status == "suggested")
        )
        or 0
    )
    flagged = (
        db.scalar(
            select(func.count())
            .select_from(Flag)
            .join(Question, Question.id == Flag.question_id)
            .where(Question.class_id.in_(ids), Flag.status == "pending")
        )
        or 0
    )
    return {
        "new": new,
        "groups": groups,
        "flagged": flagged,
        "total": new + groups + flagged,
        **_lecturer_progress(db, user, ids),
    }


def _lecturer_progress(db: Session, user: User, ids: list[int]) -> dict:
    """Tỷ lệ đã trả lời, số lớp đang học tuần này và số câu hỏi / đã trả lời theo từng tuần."""
    rows = db.execute(
        select(ClassSession.number, Question.status, func.count())
        .join(Question, Question.session_id == ClassSession.id)
        .where(ClassSession.class_id.in_(ids), Question.status != "deleted")
        .group_by(ClassSession.number, Question.status)
    ).all()
    per: dict = {}
    for number, st, n in rows:
        d = per.setdefault(number, {"week": number, "asked": 0, "answered": 0})
        d["asked"] += n
        if st == "answered":
            d["answered"] += n
    weekly = [per[k] for k in sorted(per)]
    asked = sum(d["asked"] for d in weekly)
    answered = sum(d["answered"] for d in weekly)
    classes = _my_classes(db, user)
    in_session = sum(1 for c in classes if _in_session(db, c))
    return {
        "answered_rate": round(100 * answered / asked) if asked else None,
        "classes_total": len(classes),
        "classes_in_session": in_session,
        "weekly": weekly,
    }


def _in_session(db: Session, c: Classroom) -> bool:
    now = utcnow()
    return (
        db.scalar(
            select(func.count())
            .select_from(ClassSession)
            .where(
                ClassSession.class_id == c.id,
                ClassSession.starts_at <= now,
                ClassSession.ends_at > now,
            )
        )
        or 0
    ) > 0


@router.get(
    "/lecturer/inbox", summary="Danh sách gộp mọi lớp: câu hỏi mới, nhóm tương đồng, câu bị gắn cờ"
)
def lecturer_inbox(
    kind: str = "new",
    class_id: int | None = None,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    classes = _lecturer_scope(db, user, class_id)
    by_id = {c.id: c for c in classes}
    ids = list(by_id)
    weeks = (
        {
            w.id: w
            for w in db.scalars(select(ClassSession).where(ClassSession.class_id.in_(ids))).all()
        }
        if ids
        else {}
    )
    sections: dict = {}

    def section(cid, wid):
        key = (cid, wid)
        if key not in sections:
            c, w = by_id[cid], weeks.get(wid)
            sections[key] = {
                "class_id": cid,
                "class_code": c.code,
                "subject": c.subject,
                "week_id": wid,
                "week_number": w.number if w else None,
                "unit_label": unit_label(c),
                "items": [],
            }
        return sections[key]

    def qmini(q, **extra):
        return {
            "id": q.id,
            "code": question_code(q.seq),
            "content": q.content,
            "created_at": q.created_at,
            "has_attachment": bool(q.attachments),
            **extra,
        }

    if ids and kind == "new":
        qs = db.scalars(
            select(Question)
            .where(
                Question.class_id.in_(ids),
                Question.status == "waiting",
            )
            .order_by(Question.created_at.desc())
        ).all()
        for q in qs:
            tag = "Chờ duyệt" if q.reuse_from_id else "Chờ trả lời"
            section(q.class_id, q.session_id)["items"].append(qmini(q, tag=tag))
    elif ids and kind == "groups":
        for g in db.scalars(
            select(SimilarGroup)
            .where(SimilarGroup.class_id.in_(ids), SimilarGroup.status == "suggested")
            .order_by(SimilarGroup.created_at.desc())
        ).all():
            members = db.scalars(select(Question).where(Question.group_id == g.id)).all()
            section(g.class_id, g.session_id)["items"].append(
                {
                    "id": g.id,
                    "group": True,
                    "label": g.label,
                    "score": g.score,
                    "created_at": g.created_at,
                    "questions": [qmini(q) for q in members],
                }
            )
    elif ids and kind == "flagged":
        rows = db.execute(
            select(Flag, Question)
            .join(Question, Question.id == Flag.question_id)
            .where(Question.class_id.in_(ids), Flag.status == "pending")
            .order_by(Flag.created_at.desc())
        ).all()
        for f, q in rows:
            section(q.class_id, q.session_id)["items"].append(
                qmini(q, reason=f.reason, ai_score=f.ai_score)
            )
    out = sorted(sections.values(), key=lambda s: (s["class_code"], -(s["week_number"] or 0)))
    return {
        "kind": kind,
        "sections": out,
        "total": sum(len(s["items"]) for s in out),
        "classes": [
            {"id": c.id, "code": c.code, "subject": c.subject} for c in _my_classes(db, user)
        ],
    }


# ---------------------------------------------------------------- sinh viên: tổng hợp trang chủ
@router.get("/me/summary", summary="Tổng hợp trang chủ sinh viên")
def my_summary(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    ids = [c.id for c in _my_classes(db, user)]
    mine = db.execute(
        select(Question.class_id, Question.status)
        .join(QuestionAuthor, QuestionAuthor.question_id == Question.id)
        .where(QuestionAuthor.student_id == user.id, Question.status != "deleted")
    ).all()
    per_class: dict = {}
    for cid, st in mine:
        if st == "waiting":
            per_class[cid] = per_class.get(cid, 0) + 1
    week_ago = utcnow() - timedelta(days=7)
    new_mats = (
        db.scalar(
            select(func.count())
            .select_from(Material)
            .where(Material.class_id.in_(ids), Material.created_at >= week_ago)
        )
        if ids
        else 0
    )
    return {
        "answered": sum(1 for _, st in mine if st == "answered"),
        "waiting": sum(per_class.values()),
        "new_materials": new_mats or 0,
        "waiting_by_class": per_class,
    }
