"""Chuẩn bị môi trường kiểm thử: CSDL tạm + dữ liệu mẫu, không gọi AI thật."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp())
_test_url = os.environ.get("TEST_DATABASE_URL", "")
if not _test_url:
    pytest.exit(
        "Cần đặt TEST_DATABASE_URL trỏ tới một cơ sở dữ liệu PostgreSQL RIÊNG để kiểm thử, ví dụ:\n"
        "    postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/neu_feedback_test",
        returncode=2,
    )
if "test" not in _test_url.rsplit("/", 1)[-1].lower():
    # Bộ test xóa sạch mọi bảng trong cơ sở dữ liệu được chỉ định — chặn để không xóa nhầm dữ liệu thật.
    pytest.exit(
        'Tên cơ sở dữ liệu trong TEST_DATABASE_URL phải chứa chữ "test" (bộ test sẽ XÓA SẠCH các bảng trong đó).',
        returncode=2,
    )
os.environ["DATABASE_URL"] = _test_url
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["GEMINI_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"

from fastapi.testclient import TestClient  # noqa: E402

from sqlalchemy import text  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    # Xóa sạch cả schema (drop_all không xóa được khóa ngoại tham chiếu vòng questions <-> similar_groups trên PostgreSQL)
    with engine.begin() as conn:
        conn.execute(text("drop schema if exists public cascade"))
        conn.execute(text("create schema public"))
    Base.metadata.create_all(engine)
    argv = sys.argv
    sys.argv = ["seed", "--reset"]
    seed.main()
    sys.argv = argv
    yield


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def login(client, email, password="Neu@12345"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def student(client):
    return login(client, "11236004@st.neu.edu.vn", "Huyen123")


@pytest.fixture(scope="session")
def lecturer(client):
    return login(client, "hoaithu@neu.edu.vn", "Hoaithu123")


@pytest.fixture(scope="session")
def admin(client):
    return login(client, "admin@neu.edu.vn", "Admin@12345")


@pytest.fixture(scope="session")
def ktpm(client, lecturer):
    return next(
        c for c in client.get("/api/classes", headers=lecturer).json() if c["code"] == "KTPM_01"
    )
