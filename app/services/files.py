"""Đường dẫn tệp tải lên.

Cơ sở dữ liệu chỉ lưu đường dẫn tương đối so với `upload_dir` (ví dụ `materials/3/abc.pdf`) để chuyển dự án
sang máy khác vẫn mở được tệp. Bản ghi cũ lưu đường dẫn tuyệt đối vẫn đọc được qua `resolve_stored`.
"""

import re
from pathlib import Path

from app.config import get_settings

_ABSOLUTE = re.compile(r"^([A-Za-z]:/|/)")


def to_stored(path) -> str:
    """Giá trị để lưu vào cơ sở dữ liệu: tương đối so với upload_dir, dùng dấu /."""
    root = get_settings().upload_dir.resolve()
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)  # nằm ngoài upload_dir: giữ nguyên


def resolve_stored(stored: str) -> Path:
    """Đổi giá trị lưu trong cơ sở dữ liệu thành đường dẫn thật trên máy hiện tại."""
    root = get_settings().upload_dir
    text = (stored or "").replace("\\", "/")
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if ".." in parts:  # không bao giờ cho thoát khỏi thư mục tải lên
        return root / (parts[-1] if parts else "")
    if not _ABSOLUTE.match(text):  # dạng mới: tương đối
        return root / Path(*parts) if parts else root
    old = Path(stored)  # dạng cũ: tuyệt đối — dùng nếu tệp vẫn ở đó
    if old.exists():
        return old
    lowered = [p.lower() for p in parts]
    if "uploads" in lowered:  # lấy phần sau thư mục "uploads" của máy cũ
        idx = len(lowered) - 1 - lowered[::-1].index("uploads")
        candidate = root.joinpath(*parts[idx + 1 :])
        if parts[idx + 1 :] and candidate.exists():
            return candidate
    for n in (3, 2, 1):  # thử ghép 3/2/1 đoạn cuối: materials/<id>/<tệp>, questions/<tệp>...
        candidate = root.joinpath(*parts[-n:])
        if len(parts) >= n and candidate.exists():
            return candidate
    return root / parts[-1] if parts else root
