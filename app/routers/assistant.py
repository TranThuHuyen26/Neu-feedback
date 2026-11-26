"""NEU AI cho sinh viên: hỏi đáp dựa trên tài liệu của lớp (RAG), có thể gửi kèm tệp (ảnh, PDF, Word, TXT)."""

import logging
import mimetypes
import re
import time
import uuid
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ChatMessage, Material, MaterialChunk, User
from app.schemas import Msg
from app.security import require_role
from app.services import ai, documents
from app.services.core import get_class_for_user
from app.utils import as_utc
from app.services.files import resolve_stored, to_stored

router = APIRouter(prefix="/api/ai", tags=["NEU AI"])
settings = get_settings()
log = logging.getLogger("neu.ai")
TOP_K = 6
# Lời chào / cảm ơn ngắn: không cần tìm trong tài liệu (đỡ một lần gọi embedding và prompt dài)
SMALL_TALK = re.compile(
    r"^\s*(xin\s+)?(chào|chao|alo|a lô|hello|hi|hey|cảm ơn|cám ơn|thanks|ok|oke|bạn là ai)\b[^\n?]{0,12}$",
    re.I,
)
MIN_SCORE = 0.05
CHAT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".txt": "text/plain",
    ".md": "text/plain",
}
CHAT_MAX_MB, CHAT_MAX_FILES = 10, 3


def retrieve(db: Session, class_id: int, question: str) -> list[dict]:
    """Tìm đoạn tài liệu liên quan trong lớp: ưu tiên đoạn có nội dung giải thích, lấy kèm đoạn liền sau
    (nội dung thường nằm ngay sau phần tiêu đề), tối đa 8 đoạn."""
    qv = ai.embed([question])[0]
    rows = db.execute(
        select(MaterialChunk, Material.filename)
        .join(Material, Material.id == MaterialChunk.material_id)
        .where(MaterialChunk.class_id == class_id, Material.status == "ready")
    ).all()
    by_key = {(ch.material_id, ch.idx): (ch, fn) for ch, fn in rows}

    def richness(text: str) -> float:
        return 0.8 + 0.2 * min(1.0, len(text.split()) / 90)

    scored = sorted(
        ((ai.cosine(qv, ch.embedding) * richness(ch.content), ch, fn) for ch, fn in rows),
        key=lambda x: x[0],
        reverse=True,
    )
    picked, seen = [], set()
    for sc, ch, fn in scored:
        if sc < MIN_SCORE or len(picked) >= TOP_K:
            break
        group = [(sc, ch, fn)]
        nxt = (ch.material_id, ch.idx + 1)
        if nxt in by_key and len(picked) < 3:  # 3 đoạn đầu: lấy kèm đoạn liền sau
            group.append((sc * 0.9, *by_key[nxt]))
        for item in group:
            key = (item[1].material_id, item[1].idx)
            if key not in seen and len(picked) < TOP_K:
                seen.add(key)
                picked.append(item)
    return [
        {
            "material_id": ch.material_id,
            "filename": fn,
            "page": ch.page,
            "content": ch.content,
            "score": round(sc, 3),
        }
        for sc, ch, fn in picked
    ]


async def _read_attachments(
    files: list[UploadFile] | None, user: User
) -> tuple[list[dict], str, list]:
    """Lưu tệp đính kèm (riêng của sinh viên), lấy chữ (PDF/Word/TXT) và phần gửi thẳng cho Gemini (ảnh, PDF scan)."""
    files = [f for f in (files or []) if f and f.filename]
    if len(files) > CHAT_MAX_FILES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Tối đa {CHAT_MAX_FILES} tệp mỗi tin nhắn"
        )
    saved, texts, parts = [], [], []
    folder = settings.upload_dir / "chat" / str(user.id)
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in CHAT_TYPES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"“{f.filename}”: chỉ nhận ảnh (PNG, JPG, WEBP), PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), TXT",
            )
        data = await f.read()
        if len(data) > CHAT_MAX_MB * 1024 * 1024:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"“{f.filename}” vượt quá {CHAT_MAX_MB} MB"
            )
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{uuid.uuid4().hex}{ext}"
        path.write_bytes(data)
        kind = "image" if CHAT_TYPES[ext].startswith("image/") else "file"
        saved.append(
            {
                "name": Path(f.filename).name,
                "path": to_stored(path),
                "type": kind,
                "size": len(data),
            }
        )
        if kind == "image":
            if settings.ai_enabled:
                parts.append((data, CHAT_TYPES[ext]))
            else:
                texts.append(f"[Ảnh “{f.filename}” — chế độ demo không đọc được ảnh]")
            continue
        try:
            text = documents.text_of(path, max_pages=10)
        except Exception:
            text = ""
        if ext == ".pdf" and len(text) < 50 and settings.ai_enabled:
            parts.append((data, "application/pdf"))  # PDF dạng ảnh scan → gửi thẳng cho Gemini đọc
        elif text:
            texts.append(f"--- Tệp “{f.filename}” ---\n{text[:6000]}")
    return saved, "\n\n".join(texts), parts


@router.post(
    "/chat",
    summary="Hỏi NEU AI về bài học (dựa trên tài liệu của lớp, có thể gửi kèm tối đa 3 tệp)",
)
async def chat(
    class_id: int = Form(...),
    message: str = Form(..., min_length=1, max_length=2000),
    files: list[UploadFile] | None = File(default=None),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    c = get_class_for_user(db, class_id, user)
    saved, attach_text, parts = await _read_attachments(files, user)
    t0 = time.perf_counter()
    small = bool(SMALL_TALK.match(message)) and not attach_text and not parts
    contexts = (
        []
        if small
        else await run_in_threadpool(
            retrieve, db, c.id, message + ("\n" + attach_text[:400] if attach_text else "")
        )
    )
    t1 = time.perf_counter()
    try:
        # chạy trong luồng phụ để lúc chờ Gemini không làm đứng các yêu cầu khác của máy chủ
        answer = await run_in_threadpool(
            ai.answer_from_materials, message, contexts, c.subject, attach_text, parts
        )
        log.info(
            "NEU AI chat: tìm tài liệu %.2fs (%d đoạn%s) · sinh câu trả lời %.2fs",
            t1 - t0,
            len(contexts),
            ", bỏ qua vì là câu chào" if small else "",
            time.perf_counter() - t1,
        )
    except ai.AIBusy as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, exc.message)
    sources, seen = [], set()
    for x in contexts:
        k = (x["material_id"], x["page"])
        if k not in seen and len(sources) < 4:
            seen.add(k)
            sources.append(
                {"material_id": x["material_id"], "filename": x["filename"], "page": x["page"]}
            )
    um = ChatMessage(
        user_id=user.id, class_id=c.id, role="user", content=message, attachments=saved or None
    )
    db.add(um)
    db.add(
        ChatMessage(
            user_id=user.id,
            class_id=c.id,
            role="ai",
            content=answer,
            sources=sources,
            latency_ms=round((time.perf_counter() - t0) * 1000),
        )
    )
    db.commit()
    return {
        "answer": answer,
        "sources": sources,
        "message_id": um.id,
        "attachments": [
            {"index": i, "name": a["name"], "type": a["type"], "size": a["size"]}
            for i, a in enumerate(saved)
        ],
    }


@router.get("/history", summary="Lịch sử trò chuyện với NEU AI theo lớp")
def history(
    class_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)
):
    get_class_for_user(db, class_id, user)
    msgs = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.class_id == class_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    ).all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources or [],
            "created_at": as_utc(m.created_at),
            "attachments": [
                {"index": i, "name": a["name"], "type": a["type"], "size": a["size"]}
                for i, a in enumerate(m.attachments or [])
            ],
        }
        for m in msgs
    ]


@router.get(
    "/messages/{message_id}/attachments/{index}",
    summary="Xem lại tệp đã gửi kèm (chỉ chủ tin nhắn)",
)
def attachment(
    message_id: int,
    index: int,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    m = db.get(ChatMessage, message_id)
    if m is None or m.user_id != user.id or not m.attachments or index >= len(m.attachments):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tệp")
    a = m.attachments[index]
    path = resolve_stored(a["path"])
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tệp không còn trên máy chủ")
    return FileResponse(path, filename=a["name"], media_type=mimetypes.guess_type(a["name"])[0])


@router.delete(
    "/history", response_model=Msg, summary="Bắt đầu cuộc trò chuyện mới (xóa lịch sử của lớp)"
)
def clear_history(
    class_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)
):
    db.execute(
        delete(ChatMessage).where(ChatMessage.user_id == user.id, ChatMessage.class_id == class_id)
    )
    db.commit()
    return Msg(message="Đã bắt đầu cuộc trò chuyện mới")
