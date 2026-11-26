"""Hàm tiện ích dùng chung."""

import secrets
import string
from datetime import date, datetime, time, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")  # Việt Nam không đổi giờ theo mùa


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """Thời gian không kèm múi giờ thì coi như UTC để so sánh được."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def new_join_code(prefix: str) -> str:
    """Tạo mã tham gia lớp, VD: KTPM-X31M."""
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
    head = "".join(ch for ch in prefix.upper() if ch.isalnum())[:5] or "LOP"
    return f"{head}-{''.join(secrets.choice(alphabet) for _ in range(4))}"


def temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Neu@" + "".join(secrets.choice(alphabet) for _ in range(6))


def question_code(seq: int) -> str:
    """Mã hiển thị của câu hỏi trong phiên: 1 → A101, 25 → A125."""
    return f"A{100 + seq}"


def vn_date(dt: datetime) -> date:
    """Ngày theo giờ Việt Nam của một mốc thời gian (CSDL lưu UTC)."""
    return as_utc(dt).astimezone(VN_TZ).date()


def today_vn() -> date:
    return utcnow().astimezone(VN_TZ).date()


def vn_day_start_utc(d: date) -> datetime:
    """00:00 giờ Việt Nam của ngày d, đổi ra UTC để so sánh với dữ liệu trong CSDL."""
    return datetime.combine(d, time.min, VN_TZ).astimezone(timezone.utc)


def plain_text(text: str | None) -> str:
    """Bỏ ký hiệu định dạng gọn (**đậm**, *nghiêng*, ++gạch chân++, - danh sách, [liên kết](url)) → chữ thường một dòng."""
    import re as _re

    t = _re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text or "")
    t = _re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = _re.sub(r"\*\*([^*]+)\*\*|\+\+([^+]+)\+\+", lambda m: m.group(1) or m.group(2), t)
    t = _re.sub(r"(^|[\s(])\*([^*\s][^*]*?)\*", r"\1\2", t)
    t = _re.sub(r"(?m)^\s*([-*•]|\d+[.)])\s+", "", t)
    return " ".join(t.split())
