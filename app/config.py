"""Cấu hình ứng dụng — đọc từ biến môi trường hoặc file .env."""

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "NEU Feedback API"
    # Chuỗi kết nối PostgreSQL, đặt trong file .env (bắt buộc):
    #   DATABASE_URL=postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/neu_feedback
    database_url: str = ""

    # Bảo mật
    secret_key: str = "doi-chuoi-nay-trong-file-env"
    access_token_minutes: int = 60 * 12
    allowed_email_domains: str = "neu.edu.vn,st.neu.edu.vn"
    cors_origins: str = "*"

    # Học kỳ hiện tại (dùng khi tạo lớp mới)
    current_semester: str = "HK1 2026-2027"
    semester_start: date = date(
        2026, 8, 3
    )  # ngày bắt đầu học kỳ — thống kê mặc định tính từ ngày này

    # Lưu tệp
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    max_upload_mb: int = 20

    # AI (Gemini). Để trống GEMINI_API_KEY thì hệ thống chạy chế độ demo, không gọi AI thật.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_embed_model: str = "gemini-embedding-001"
    gemini_thinking_budget: int = 0  # 0 = tắt thinking cho nhanh; -1 = để mô hình tự quyết
    chat_max_output_tokens: int = 1024  # giới hạn độ dài câu trả lời của chatbot
    similarity_threshold: float = 0.85  # ngưỡng GỢI Ý gộp nhóm (embedding Gemini)
    auto_answer_threshold: float = (
        0.92  # ngưỡng TỰ ĐỘNG TRẢ LỜI khi nhóm đã được giảng viên xác nhận (Gemini)
    )
    demo_similarity_threshold: float = (
        0.55  # hai ngưỡng tương ứng ở chế độ demo (embedding đơn giản)
    )
    demo_auto_answer_threshold: float = 0.80

    # Quy tắc nghiệp vụ
    max_questions_per_student_per_week: int = 20
    weeks_per_class: int = 15

    # Phục vụ luôn giao diện HTML (đặt thư mục frontend vào đây nếu muốn chạy chung một địa chỉ)
    frontend_dir: Path = BASE_DIR / "frontend"

    @property
    def email_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
