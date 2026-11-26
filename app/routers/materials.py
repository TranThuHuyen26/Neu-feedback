"""Tài liệu theo tuần học: tải lên (tự tách chữ + tạo embedding cho NEU AI), đổi tên, xóa, tải xuống."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ClassSession, Classroom, Enrollment, Material, MaterialChunk, User
from app.schemas import Msg, RenameIn
from app.security import get_current_user, require_role
from app.services import ai, documents
from app.services.core import get_class_for_user, get_owned_class, get_week_for_user, notify
from app.utils import as_utc
from app.services.files import resolve_stored, to_stored

router = APIRouter(prefix="/api", tags=["Tài liệu"])
settings = get_settings()
log = logging.getLogger("neu.materials")


def material_out(m: Material, c: Classroom | None = None, db: Session | None = None) -> dict:
    d = {
        "id": m.id,
        "class_id": m.class_id,
        "week_id": m.week_id,
        "filename": m.filename,
        "file_type": m.file_type,
        "size_bytes": m.size_bytes,
        "status": m.status,
        "chunk_count": m.chunk_count,
        "created_at": as_utc(m.created_at),
    }
    if c:
        d.update(class_code=c.code, subject=c.subject)
    if db is not None and m.week_id:
        w = db.get(ClassSession, m.week_id)
        d.update(week_number=w.number if w else None, week_title=w.title if w else None)
    return d


@router.get(
    "/materials", summary="Danh sách tài liệu (Giảng viên: mọi lớp của mình · sinh viên: theo lớp)"
)
def list_materials(
    class_id: int | None = None,
    week_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if week_id:
        w, _ = get_week_for_user(db, week_id, user)
        stmt = select(Material, Classroom).join(Classroom).where(Material.week_id == week_id)
    elif class_id:
        get_class_for_user(db, class_id, user)
        stmt = select(Material, Classroom).join(Classroom).where(Material.class_id == class_id)
    elif user.role == "lecturer":
        stmt = (
            select(Material, Classroom)
            .join(Classroom)
            .where(Classroom.lecturer_id == user.id, Classroom.is_archived.is_(False))
        )
    elif user.role == "student":
        stmt = (
            select(Material, Classroom)
            .join(Classroom)
            .join(Enrollment, Enrollment.class_id == Classroom.id)
            .where(Enrollment.student_id == user.id)
        )
    else:
        stmt = select(Material, Classroom).join(Classroom)
    rows = db.execute(stmt.order_by(Material.created_at.desc())).all()
    return [material_out(m, c, db) for m, c in rows]


def _index_material(db: Session, m: Material, path: Path) -> None:
    """Tách chữ → chia đoạn → tạo embedding → lưu để NEU AI tìm kiếm."""
    try:
        chunks = documents.chunk(
            documents.extract_pages(path), table=path.suffix.lower() == ".xlsx"
        )
        vectors = ai.embed([t for _, t in chunks])
        db.execute(delete(MaterialChunk).where(MaterialChunk.material_id == m.id))
        for i, ((page, text), vec) in enumerate(zip(chunks, vectors)):
            db.add(
                MaterialChunk(
                    material_id=m.id,
                    class_id=m.class_id,
                    idx=i,
                    page=page,
                    content=text,
                    embedding=vec,
                )
            )
        m.chunk_count, m.status = len(chunks), "ready"
    except Exception:
        log.exception("Không xử lý được tài liệu %s", m.filename)
        m.status, m.chunk_count = "failed", 0


@router.post(
    "/weeks/{week_id}/materials",
    status_code=201,
    summary="Tải tài liệu cho một tuần học (PDF, Word, PowerPoint, Excel, TXT)",
)
async def upload(
    week_id: int,
    files: list[UploadFile] = File(...),
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    w, c = get_week_for_user(db, week_id, user)
    get_owned_class(db, c.id, user)
    folder = settings.upload_dir / "materials" / str(c.id)
    folder.mkdir(parents=True, exist_ok=True)
    created = []
    for f in files:
        ftype = documents.file_type(f.filename or "")
        if ftype is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"“{f.filename}” không được hỗ trợ. Chỉ nhận PDF, DOCX, PPTX, XLSX, TXT",
            )
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"“{f.filename}” vượt quá {settings.max_upload_mb} MB"
            )
        path = folder / f"{uuid.uuid4().hex}{Path(f.filename).suffix.lower()}"
        path.write_bytes(data)
        m = Material(
            class_id=c.id,
            week_id=w.id,
            filename=Path(f.filename).name,
            stored_path=to_stored(path),
            file_type=ftype,
            size_bytes=len(data),
            uploaded_by=user.id,
        )
        db.add(m)
        db.flush()
        _index_material(db, m, path)
        created.append(m)
    for sid in db.scalars(select(Enrollment.student_id).where(Enrollment.class_id == c.id)).all():
        notify(
            db,
            sid,
            f"{user.full_name} đã thêm {len(created)} tài liệu cho tuần {w.number}",
            c.subject,
            f"student-week.html?week={w.id}",
        )
    db.commit()
    return [material_out(m, c, db) for m in created]


def _owned_material(db: Session, material_id: int, user: User) -> Material:
    m = db.get(Material, material_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tài liệu")
    get_owned_class(db, m.class_id, user)
    return m


@router.patch("/materials/{material_id}", summary="Đổi tên tài liệu")
def rename(
    material_id: int,
    body: RenameIn,
    user: User = Depends(require_role("lecturer")),
    db: Session = Depends(get_db),
):
    m = _owned_material(db, material_id, user)
    new = body.filename.strip()
    if Path(new).suffix.lower() != Path(m.filename).suffix.lower():
        new += Path(m.filename).suffix  # giữ nguyên đuôi tệp
    m.filename = new
    db.commit()
    return material_out(m, None, db)


@router.delete(
    "/materials/{material_id}",
    response_model=Msg,
    summary="Xóa tài liệu (NEU AI không dùng được nữa)",
)
def remove(
    material_id: int, user: User = Depends(require_role("lecturer")), db: Session = Depends(get_db)
):
    m = _owned_material(db, material_id, user)
    resolve_stored(m.stored_path).unlink(missing_ok=True)
    db.delete(m)
    db.commit()
    return Msg(message="Đã xóa tài liệu")


@router.get("/materials/{material_id}/download", summary="Tải xuống / xem tài liệu")
def download(
    material_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    m = db.get(Material, material_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tài liệu")
    get_class_for_user(db, m.class_id, user)
    path = resolve_stored(m.stored_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tệp không còn trên máy chủ")
    return FileResponse(path, filename=m.filename)
