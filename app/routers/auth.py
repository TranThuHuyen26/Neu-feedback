"""Đăng nhập và thông tin tài khoản đang đăng nhập."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ChangePasswordIn, LoginIn, Msg, ProfileIn, TokenOut, UserOut
from app.security import create_token, get_current_user, hash_password, verify_password
from app.utils import utcnow

router = APIRouter(prefix="/api/auth", tags=["Đăng nhập"])


@router.post("/login", response_model=TokenOut, summary="Đăng nhập bằng email trường")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")
    if user.is_locked:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa, vui lòng liên hệ quản trị viên"
        )
    user.last_active_at = utcnow()
    db.commit()
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut, summary="Thông tin tài khoản đang đăng nhập")
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut, summary="Cập nhật hồ sơ (sinh viên, Giảng viên)")
def update_profile(
    body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if user.role == "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản quản trị không có trang hồ sơ")
    user.full_name = body.full_name.strip()
    db.commit()
    return user


@router.post("/change-password", response_model=Msg, summary="Đổi mật khẩu")
def change_password(
    body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mật khẩu hiện tại không đúng")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    return Msg(message="Đã đổi mật khẩu")
