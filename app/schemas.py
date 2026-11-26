"""Dữ liệu vào/ra của API (FastAPI tự kiểm tra và hiển thị trong trang /docs)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Tài khoản ----------
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: str
    faculty: str | None = None
    admin_class: str | None = None
    is_locked: bool = False
    must_change_password: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


# ---------- Lớp học ----------
class ClassCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40, description="Tên lớp, VD: KTPM_06")
    subject: str = Field(min_length=2, max_length=160, description="Môn học")
    start_date: date | None = Field(
        default=None, description="Ngày bắt đầu học — hệ thống tự xác định học kỳ (Thu/Xuân/Hè)"
    )
    semester_id: int | None = Field(
        default=None, description="(cũ) Học kỳ có sẵn; bỏ trống khi đã gửi start_date"
    )
    course_type: str = Field(
        default="regular",
        pattern="^(regular|political)$",
        description="regular: 15 buổi · political: lý luận chính trị 10 buổi",
    )
    meeting_days: list[int] | None = Field(
        default=None, description="Kỳ Hè: 3 thứ học trong tuần (0 = thứ Hai … 5 = thứ Bảy)"
    )


class ClassUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=40)
    subject: str | None = Field(default=None, min_length=2, max_length=160)


class JoinIn(BaseModel):
    join_code: str = Field(min_length=4, max_length=20)


class LecturerChangeIn(BaseModel):
    lecturer_id: int


class AddStudentsIn(BaseModel):
    emails: list[EmailStr] = Field(min_length=1, max_length=200)


# ---------- Phiên học ----------
class WeekUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=160, description="Chủ đề tuần")
    description: str | None = Field(
        default=None, max_length=5000, description="Nội dung / mục tiêu tuần"
    )


class QuestionEdit(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class AnswerEdit(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    apply_to_copies: bool = Field(
        default=False, description="Cập nhật luôn cho các câu tương tự đã nhận câu trả lời này"
    )


# ---------- Câu hỏi ----------
class AnswerIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class FlagIn(BaseModel):
    reason: str = Field(default="Nội dung cần kiểm tra", max_length=120)


class GroupAction(BaseModel):
    action: Literal["confirm", "reject", "split"]


# ---------- Tài liệu ----------
class RenameIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)


# ---------- AI ----------
class ChatIn(BaseModel):
    class_id: int
    message: str = Field(min_length=1, max_length=2000)


# ---------- Admin ----------
class AccountIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: Literal["student", "lecturer"]
    faculty: str = Field(min_length=1, max_length=80)
    admin_class: str | None = None


class AccountUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    role: Literal["student", "lecturer"] | None = None
    faculty: str | None = None
    admin_class: str | None = None


class DecisionIn(BaseModel):
    decision: Literal["dismissed", "hidden", "deleted"]
    note: str | None = Field(default=None, max_length=1000)


class TraceIn(BaseModel):
    reason: str = Field(
        min_length=10, max_length=1000, description="Lý do truy vết (bắt buộc, được ghi nhật ký)"
    )


class Msg(BaseModel):
    message: str


class NotificationOut(ORM):
    id: int
    title: str
    body: str | None
    link: str | None
    count: int = 1
    is_read: bool
    created_at: datetime
