"""Đăng nhập, mã hóa mật khẩu và phân quyền theo vai trò."""

from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.utils import utcnow

settings = get_settings()
password_hasher = PasswordHash.recommended()  # Argon2
bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(raw: str) -> str:
    return password_hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(raw, hashed)
    except Exception:
        return False


def create_token(user: User) -> str:
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bạn chưa đăng nhập")
    try:
        payload = jwt.decode(cred.credentials, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại"
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ")
    user = db.get(User, int(payload["sub"]))
    if (
        user is not None and payload.get("email") != user.email
    ):  # dữ liệu đã được tạo lại → phiên cũ hết hiệu lực
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại"
        )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại")
    if user.is_locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa")
    return user


def require_role(*roles: str):
    """Dùng trong router: user = Depends(require_role('lecturer'))"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Bạn không có quyền thực hiện thao tác này"
            )
        return user

    return checker


def check_email_domain(email: str) -> None:
    domain = email.split("@")[-1].lower()
    if domain not in settings.email_domains:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Chỉ chấp nhận email trường ({', '.join(settings.email_domains)})",
        )
