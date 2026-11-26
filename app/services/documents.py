"""Đọc tài liệu (PDF, Word, PowerPoint, Excel, TXT) và chia thành đoạn cho NEU AI tìm kiếm.

Bỏ qua trang ít nội dung (bìa, mục lục, trang chỉ có tiêu đề, tài liệu tham khảo), gộp 2 đến 3 slide ngắn
liền nhau thành một đoạn, và gắn tên mục gần nhất vào mỗi đoạn để AI hiểu ngữ cảnh.
"""

import re
from pathlib import Path

ALLOWED = {
    ".pdf": "PDF",
    ".docx": "DOC",
    ".pptx": "PPT",
    ".xlsx": "XLS",
    ".txt": "TXT",
    ".md": "TXT",
}
MAX_SHEET_ROWS = 3000
CHUNK_CHARS = 1100
OVERLAP = 180
MIN_WORDS = 15  # trang ít hơn số từ này coi là trang tiêu đề / trang bìa
SLIDE_TARGET_WORDS = 160  # gộp slide đến khi đủ khoảng này
MAX_MERGE = 3


def file_type(filename: str) -> str | None:
    return ALLOWED.get(Path(filename).suffix.lower())


def extract_pages(path: Path, max_pages: int | None = None) -> list[tuple[int | None, str]]:
    """Trả về danh sách (số trang/slide, nội dung)."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pymupdf

        with pymupdf.open(path) as doc:
            return [
                (i + 1, page.get_text())
                for i, page in enumerate(doc)
                if max_pages is None or i < max_pages
            ]
    if ext == ".docx":
        import docx

        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs if p.text.strip()]
        for table in d.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return [(None, "\n".join(parts))]
    if ext == ".pptx":
        from pptx import Presentation

        pres = Presentation(str(path))
        out = []
        for i, slide in enumerate(pres.slides):
            texts = [
                sh.text_frame.text
                for sh in slide.shapes
                if sh.has_text_frame and sh.text_frame.text.strip()
            ]
            out.append((i + 1, "\n".join(texts)))
        return out
    if ext == ".xlsx":
        return _xlsx_pages(path, max_pages)
    return [(None, path.read_text(encoding="utf-8", errors="ignore"))]


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if hasattr(v, "strftime"):
        return (
            v.strftime("%d/%m/%Y")
            if not getattr(v, "hour", 0) and not getattr(v, "minute", 0)
            else v.strftime("%d/%m/%Y %H:%M")
        )
    return " ".join(str(v).split())


def _xlsx_pages(path: Path, max_pages: int | None = None) -> list[tuple[int | None, str]]:
    """Excel: mỗi sheet là một "trang" (trích nguồn ghi sheet thứ mấy). Dòng đầu coi là tiêu đề cột."""
    import openpyxl

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out = []
    try:
        for i, ws in enumerate(wb.worksheets):
            if max_pages is not None and i >= max_pages:
                break
            lines = []
            for r, row in enumerate(ws.iter_rows(values_only=True)):
                if r >= MAX_SHEET_ROWS:
                    lines.append("…")
                    break
                cells = [_cell(v) for v in row]
                while cells and not cells[-1]:
                    cells.pop()
                if any(cells):
                    lines.append(" | ".join(cells))
            if lines:
                out.append((i + 1, f"Bảng tính “{ws.title}”\n" + "\n".join(lines)))
    finally:
        wb.close()
    return out


def _words(t: str) -> int:
    return len(re.findall(r"\w+", t))


def _first_line(t: str) -> str:
    for line in t.splitlines():
        line = line.strip(" \t•-–")
        if len(line) >= 3:
            return line[:120]
    return ""


def page_kind(text: str) -> str:
    """'content' | 'title' (bìa / slide tiêu đề) | 'toc' (mục lục) | 'refs' (tài liệu tham khảo)."""
    t = text.strip()
    low = t.lower()
    if re.match(r"^\s*(mục lục|table of contents|contents|nội dung chính)\b", low):
        return "toc"
    if re.match(r"^\s*(tài liệu tham khảo|references|bibliography)\b", low):
        return "refs"
    lines = [ln for ln in t.splitlines() if ln.strip()]
    if lines:
        toc_like = sum(
            1
            for ln in lines
            if re.search(r"(\.{3,}|…+|\s{3,})\s*\d{1,4}\s*$", ln)
            or re.match(r"^\s*(chương|chapter|bài|phần|mục)\s*[\dIVX]+.*\s\d{1,4}\s*$", ln, re.I)
        )
        if len(lines) >= 4 and toc_like / len(lines) >= 0.4:
            return "toc"
    if _words(t) < MIN_WORDS:
        return "title"
    return "content"


def chunk(pages: list[tuple[int | None, str]], table: bool = False) -> list[tuple[int | None, str]]:
    """Chia đoạn thông minh. Trả về [(trang bắt đầu, nội dung đoạn)].
    table=True (Excel): giữ mọi sheet kể cả sheet ngắn, giữ xuống dòng giữa các hàng, không gộp sheet.
    """
    if table:
        out = []
        for page, text in pages:
            lines = [ln for ln in (text or "").splitlines() if ln.strip()]
            head, buf = (lines[0] + "\n") if lines else "", ""
            for ln in lines[1:] or lines[:1]:
                if buf and len(buf) + len(ln) > CHUNK_CHARS:
                    out.append((page, head + buf.rstrip()))
                    buf = ""
                buf += ln + "\n"
            if buf.strip():
                out.append((page, head + buf.rstrip()))
        return out
    section = ""
    items = []  # (page, text, section) của các trang có nội dung
    for page, text in pages:
        text = re.sub(r"[ \t]+", " ", text or "").strip()
        if not text:
            continue
        kind = page_kind(text)
        if kind == "title":
            section = _first_line(text) or section  # slide tiêu đề → làm ngữ cảnh cho các trang sau
            continue
        if kind in ("toc", "refs"):
            continue
        items.append((page, text, section))
    if not items:
        return []
    avg = sum(_words(t) for _, t, _ in items) / len(items)
    chunks: list[tuple[int | None, str]] = []
    if avg < 120 and len(items) > 1:  # tài liệu dạng slide → gộp các trang liền nhau
        buf, start, sec = [], None, ""
        for page, text, s in items:
            if buf and (
                s != sec
                or sum(_words(x) for x in buf) >= SLIDE_TARGET_WORDS
                or len(buf) >= MAX_MERGE
            ):
                chunks.append((start, (f"Mục: {sec}\n" if sec else "") + "\n".join(buf)))
                buf = []
            if not buf:
                start, sec = page, s
            buf.append(text)
        if buf:
            chunks.append((start, (f"Mục: {sec}\n" if sec else "") + "\n".join(buf)))
        return chunks
    for page, text, sec in items:  # tài liệu dạng văn bản → cắt theo đoạn, có chồng lấn
        flat = " ".join(text.split())
        prefix = f"Mục: {sec}\n" if sec else ""
        start = 0
        while start < len(flat):
            end = min(len(flat), start + CHUNK_CHARS)
            if end < len(flat):
                cut = max(flat.rfind(". ", start, end), flat.rfind(" ", start, end))
                if cut > start + CHUNK_CHARS // 2:
                    end = cut + 1
            chunks.append((page, prefix + flat[start:end].strip()))
            if end >= len(flat):
                break
            start = max(end - OVERLAP, start + 1)
    return chunks


def text_of(path: Path, max_pages: int = 10) -> str:
    """Lấy chữ từ tệp sinh viên gửi kèm NEU AI (PDF chỉ đọc 10 trang đầu)."""
    return "\n".join(t for _, t in extract_pages(path, max_pages=max_pages)).strip()
