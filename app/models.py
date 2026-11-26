"""Các bảng dữ liệu.

Bảng `questions` không có cột sinh viên. Thông tin ai hỏi câu nào nằm riêng ở
`question_authors`; chỉ backend dùng, admin xem qua chức năng truy vết (phải nêu lý do, có ghi nhật ký).
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import utcnow

# ---- Giá trị hợp lệ (lưu dạng chuỗi để dùng được trên mọi CSDL) ----
ROLES = ("student", "lecturer", "admin")
WEEK_STATUS = ("done", "current", "upcoming")  # Đã học / Đang học / Chưa học (tính theo ngày)
WEEKS_PER_CLASS = 15
QUESTION_STATUS = ("waiting", "answered", "flagged", "hidden", "deleted")
GROUP_STATUS = ("suggested", "confirmed", "rejected")
FLAG_STATUS = ("pending", "dismissed", "hidden", "deleted")


class UTCDateTime(TypeDecorator):
    """Mốc thời gian luôn mang múi giờ UTC khi đọc ra (nếu thiếu múi giờ, giao diện sẽ bị lệch 7 tiếng)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), index=True)
    faculty: Mapped[str | None] = mapped_column(String(80))
    admin_class: Mapped[str | None] = mapped_column(String(40))  # lớp hành chính, VD: CNTT 64A
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    last_active_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Semester(Base):
    """Học kỳ: năm học (VD 2026-2027) + kỳ Thu / Xuân / Hè + ngày bắt đầu (thứ Hai). Kỳ chính học 1 buổi/tuần, kỳ Hè 3 buổi/tuần."""

    __tablename__ = "semesters"
    __table_args__ = (UniqueConstraint("year", "term"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[str] = mapped_column(String(9))  # 2026-2027
    term: Mapped[str] = mapped_column(String(4))  # thu | xuan | he
    start_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Classroom(Base):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("code", "semester_id", name="uq_classes_code_semester"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(40), index=True
    )  # VD: KTPM_01 — duy nhất trong cùng học kỳ
    subject: Mapped[str] = mapped_column(String(160))  # VD: Kiểm thử phần mềm
    semester: Mapped[str] = mapped_column(String(40), index=True)
    faculty: Mapped[str | None] = mapped_column(String(80))
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    join_code: Mapped[str] = mapped_column(String(20), unique=True)  # VD: KTPM-X31M
    start_date: Mapped[date] = mapped_column(Date)  # thứ Hai của tuần học 1
    semester_id: Mapped[int | None] = mapped_column(ForeignKey("semesters.id"), index=True)
    course_type: Mapped[str] = mapped_column(
        String(12), default="regular"
    )  # regular (15 buổi) | political (10 buổi)
    meeting_days: Mapped[list | None] = mapped_column(
        JSON
    )  # kỳ Hè: 3 thứ học trong tuần, VD [0, 2, 4]
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    lecturer: Mapped[User] = relationship()
    semester_ref: Mapped[Semester | None] = relationship()


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("class_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class ClassSession(Base):
    """TUẦN HỌC của lớp (mỗi lớp 15 tuần). Trạng thái Đã học / Đang học / Chưa học được tính theo ngày,
    không lưu cố định. Tên bảng giữ là `sessions` để tương thích dữ liệu cũ."""

    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)  # tuần 1..15
    title: Mapped[str] = mapped_column(String(160), default="")  # chủ đề tuần (giảng viên điền)
    description: Mapped[str | None] = mapped_column(Text)  # nội dung / mục tiêu tuần
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())  # 00:00 thứ Hai (giờ VN)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime())  # 00:00 thứ Hai tuần sau (không tính)
    summary: Mapped[str | None] = mapped_column(Text)  # tóm tắt AI (lưu lại)
    summary_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    shared_report: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    classroom: Mapped[Classroom] = relationship()


Week = ClassSession


class SimilarGroup(Base):
    """Nhóm câu hỏi tương đồng trong một LỚP (có thể gồm câu hỏi của nhiều tuần).
    Khi giảng viên xác nhận nhóm và đã có câu trả lời, câu hỏi mới rất giống sẽ được trả lời tự động.
    """

    __tablename__ = "similar_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int | None] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )  # tuần tạo nhóm
    label: Mapped[str] = mapped_column(String(20))  # VD: SIM-01
    status: Mapped[str] = mapped_column(String(12), default="suggested")
    score: Mapped[float] = mapped_column(Float, default=0)
    answer_text: Mapped[str | None] = mapped_column(
        Text
    )  # câu trả lời chung dùng để trả lời tự động
    answered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    source_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)  # số thứ tự trong phiên → mã A101
    content: Mapped[str] = mapped_column(Text)  # có thể có định dạng gọn (**đậm**, - danh sách…)
    status: Mapped[str] = mapped_column(String(12), default="waiting", index=True)
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("similar_groups.id", ondelete="SET NULL")
    )
    no_auto: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Giảng viên bấm "Không giống" → không gợi ý ghép nữa
    reuse_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )  # gợi ý dùng lại câu trả lời của câu này
    reuse_score: Mapped[float | None] = mapped_column(Float)  # độ giống với câu được gợi ý
    embedding: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    answered_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime())  # sinh viên sửa lần cuối

    group: Mapped[SimilarGroup | None] = relationship(foreign_keys=[group_id])
    reuse_from: Mapped["Question | None"] = relationship(
        foreign_keys=[reuse_from_id], remote_side=[id]
    )
    attachments: Mapped[list["QuestionAttachment"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuestionAttachment.id"
    )


class QuestionAttachment(Base):
    """Tệp sinh viên đính kèm câu hỏi (tối đa 3 tệp: ảnh, PDF, Word, PowerPoint, Excel). Chỉ chủ câu hỏi,
    Giảng viên của lớp và Admin xem được."""

    __tablename__ = "question_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))  # IMG / PDF / DOC / PPT / XLS
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    question: Mapped["Question"] = relationship(back_populates="attachments")


class QuestionAuthor(Base):
    """Bảng tách riêng danh tính người hỏi — KHÔNG bao giờ trả về cho giảng viên."""

    __tablename__ = "question_authors"
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    via_group: Mapped[bool] = mapped_column(Boolean, default=False)
    source_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )
    source_answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("answers.id", ondelete="SET NULL"), index=True
    )  # bản sao của câu trả lời này
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Material(Base):
    """Tài liệu của lớp, gắn với một tuần học (week_id)."""

    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    week_id: Mapped[int | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))  # PDF / DOC / PPT / XLS / TXT
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(12), default="ready")  # ready | failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class MaterialChunk(Base):
    """Đoạn văn bản tách từ tài liệu + embedding, dùng cho RAG."""

    __tablename__ = "material_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), index=True
    )
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON)


class Flag(Base):
    __tablename__ = "flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    flagged_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(120))
    ai_score: Mapped[int] = mapped_column(Integer, default=50)  # 0–100, càng cao càng nghiêm trọng
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(String(300))
    link: Mapped[str | None] = mapped_column(String(300))
    key: Mapped[str | None] = mapped_column(
        String(120), index=True
    )  # gộp thông báo cùng loại (VD: new_q:lớp:tuần)
    count: Mapped[int] = mapped_column(Integer, default=1)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class ChatMessage(Base):
    """Lịch sử trò chuyện với NEU AI của sinh viên."""

    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user | ai
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSON)
    attachments: Mapped[list | None] = mapped_column(JSON)  # [{name, path, type, size}]
    latency_ms: Mapped[int | None] = mapped_column(Integer)  # thời gian NEU AI trả lời (tin của AI)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AnswerImage(Base):
    """Ảnh Giảng viên chèn vào câu trả lời (tham chiếu trong nội dung bằng /api/answer-images/{id})."""

    __tablename__ = "answer_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AuditLog(Base):
    """Nhật ký thao tác nhạy cảm (truy vết danh tính, khóa/xóa tài khoản, quyết định kiểm duyệt)."""

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60), index=True)
    target: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
