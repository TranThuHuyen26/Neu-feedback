"""Thông báo của người dùng (chuông trên thanh trên cùng)."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, User
from app.schemas import Msg, NotificationOut
from app.security import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Thông báo"])


@router.get("", summary="Thông báo gần đây + số chưa đọc")
def list_notifications(
    offset: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mới nhất trước. `offset`: bỏ qua N thông báo đã tải — cuộn xuống cuối khung thông báo để tải thêm."""
    stmt = select(Notification).where(Notification.user_id == user.id)
    limit = max(1, min(limit, 50))
    items = db.scalars(
        stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(max(0, offset))
        .limit(limit + 1)
    ).all()
    more, items = len(items) > limit, items[:limit]
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return {
        "unread": unread,
        "has_more": more,
        "items": [NotificationOut.model_validate(n) for n in items],
    }


@router.post("/read-all", response_model=Msg, summary="Đánh dấu tất cả là đã đọc")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    db.commit()
    return Msg(message="Đã đánh dấu tất cả là đã đọc")


@router.post(
    "/{notification_id}/read",
    response_model=Msg,
    summary="Đánh dấu một thông báo đã đọc (khi bấm vào)",
)
def read_one(
    notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    n = db.get(Notification, notification_id)
    if n is not None and n.user_id == user.id:
        n.is_read = True
        db.commit()
    return Msg(message="Đã đọc")
