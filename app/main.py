"""Điểm khởi động ứng dụng: uvicorn app.main:app --reload"""

import hashlib
import logging
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import (
    admin,
    admin_classes,
    assistant,
    auth,
    classes,
    materials,
    notifications,
    questions,
    semesters,
    weeks,
    workspace,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Backend cho hệ thống phản hồi ẩn danh tích hợp AI. Thử API tại trang này: bấm **Authorize** "
    "và dán token nhận được từ `/api/auth/login`.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth,
    semesters,
    classes,
    weeks,
    questions,
    materials,
    assistant,
    notifications,
    admin,
    admin_classes,
    workspace,
):
    app.include_router(r.router)


@app.get("/api/health", tags=["Hệ thống"], summary="Kiểm tra backend còn chạy")
def health():
    return {"status": "ok", "ai_mode": "gemini" if settings.ai_enabled else "demo"}


class Frontend(StaticFiles):
    """Phục vụ giao diện. Số phiên bản ?v=… của CSS/JS trong mọi trang HTML được TỰ TÍNH từ nội dung các tệp
    assets (thời điểm sửa + dung lượng) → sửa CSS/JS là trình duyệt tự tải bản mới, không cần đổi số bằng tay.
    """

    VER = re.compile(r"(assets/(?:css|js)/[\w.-]+\.(?:css|js))\?v=[\w.-]+")

    def asset_version(self) -> str:
        h = hashlib.md5()
        for f in sorted((settings.frontend_dir / "assets").rglob("*.*")):
            if f.suffix in (".css", ".js"):
                st = f.stat()
                h.update(f"{f.name}:{st.st_mtime_ns}:{st.st_size}".encode())
        return h.hexdigest()[:10]

    def page_map(self) -> dict:
        """Các trang HTML nằm trong frontend/pages/<vai trò>/ nhưng địa chỉ vẫn phẳng (/login.html,
        /lecturer-week.html…) để liên kết, thông báo và đường dẫn assets/ không phải đổi.
        """
        pages = settings.frontend_dir / "pages"
        return {
            f.name: f.relative_to(settings.frontend_dir).as_posix() for f in pages.rglob("*.html")
        }

    async def get_response(self, path, scope):
        name = path.strip("/")
        if name in ("", "."):
            name = "index.html"
        if "/" not in name and name.endswith(".html"):
            mapped = self.page_map().get(name)
            if mapped:
                path = mapped
        resp = await super().get_response(path, scope)
        file = getattr(resp, "path", None)
        if resp.status_code == 200 and file and str(file).endswith(".html"):
            html = open(file, encoding="utf-8").read()
            html = self.VER.sub(lambda m: f"{m.group(1)}?v={self.asset_version()}", html)
            return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
        return resp


# Phục vụ luôn giao diện HTML nếu có thư mục frontend/ → mở http://127.0.0.1:8000/login.html
if settings.frontend_dir.exists():
    app.mount("/", Frontend(directory=settings.frontend_dir, html=True), name="frontend")
