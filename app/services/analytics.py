"""Số liệu dùng chung cho hai trang Tổng quan và Thống kê của admin.

Cả hai trang đếm câu hỏi bằng cùng một hàm `tally`, nên con số luôn khớp nhau.
Quy ước: câu hỏi đã xóa không được tính; "chờ trả lời" là câu có trạng thái `waiting`.
"""

import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClassSession, Question, SimilarGroup
from app.utils import VN_TZ, as_utc, today_vn, utcnow, vn_date


def question_rows(db: Session, class_ids: list[int]) -> list[tuple[Question, int]]:
    """Các câu hỏi (trừ câu đã xóa) của những lớp đã chọn, kèm số thứ tự tuần."""
    if not class_ids:
        return []
    return db.execute(
        select(Question, ClassSession.number)
        .join(ClassSession, ClassSession.id == Question.session_id)
        .where(Question.class_id.in_(class_ids), Question.status != "deleted")
    ).all()


def tally(items: list[Question]) -> dict:
    total = len(items)
    answered = sum(1 for q in items if q.status == "answered")
    waiting = [q for q in items if q.status == "waiting"]
    return {
        "questions": total,
        "answered": answered,
        "waiting": len(waiting),
        "review": sum(1 for q in waiting if q.reuse_from_id),
        "flagged": sum(1 for q in items if q.status == "flagged"),
        "hidden": sum(1 for q in items if q.status == "hidden"),
        "answer_rate": round(answered * 100 / total) if total else 0,
    }


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def grouping_stats(db: Session, class_ids: list[int], since: date | None = None) -> dict:
    """Độ chính xác gom nhóm = nhóm Giảng viên xác nhận / nhóm đã xử lý (xác nhận + từ chối)."""
    if not class_ids:
        return {"confirmed": 0, "rejected": 0, "suggested": 0, "accuracy": None}
    stmt = select(SimilarGroup.status, SimilarGroup.created_at).where(
        SimilarGroup.class_id.in_(class_ids)
    )
    rows = db.execute(stmt).all()
    if since:
        rows = [(s, c) for s, c in rows if vn_date(c) >= since]
    count = Counter(s for s, _ in rows)
    done = count["confirmed"] + count["rejected"]
    return {
        "confirmed": count["confirmed"],
        "rejected": count["rejected"],
        "suggested": count["suggested"],
        "accuracy": round(count["confirmed"] * 100 / done) if done else None,
    }


def trend_7_days(items: list[Question]) -> dict:
    """Lượng câu hỏi 7 ngày gần nhất, so với 7 ngày trước đó."""
    today = today_vn()
    per_day = Counter(vn_date(q.created_at) for q in items)
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    series = [{"date": d.isoformat(), "questions": per_day.get(d, 0)} for d in days]
    this_week = sum(x["questions"] for x in series)
    before = sum(per_day.get(today - timedelta(days=i), 0) for i in range(7, 14))
    change = round((this_week - before) * 100 / before) if before else None
    if change is None:
        label = "Chưa đủ dữ liệu" if not this_week else "Mới bắt đầu"
    elif change > 25:
        label = "Tăng mạnh"
    elif change < -25:
        label = "Giảm mạnh"
    else:
        label = "Ổn định"
    return {
        "days": series,
        "total": this_week,
        "previous_total": before,
        "average": round(this_week / 7, 1),
        "change_pct": change,
        "label": label,
    }


def hour_heatmap(items: list[Question]) -> list[list[int]]:
    """Ma trận 7 × 24: số câu hỏi theo thứ (thứ Hai = 0) và giờ gửi (giờ Việt Nam)."""
    grid = [[0] * 24 for _ in range(7)]
    for q in items:
        t = as_utc(q.created_at).astimezone(VN_TZ)
        grid[t.weekday()][t.hour] += 1
    return grid


# ------------------------------------------------------------ từ khóa theo tuần
_STOP = set(
    """là gì không có của và các những một như thế nào sao được cho em thầy cô giảng viên xin
    hỏi câu ạ vậy để khi thì mà này đó với trong ở bị bao nhiêu làm cách tại vì nên cần phải rồi
    đã sẽ đang hay hoặc nếu từ ra vào lên xuống nhiều ít rất lắm cũng còn chỉ lại đến theo về
    bằng sau trước hơn nhất mình tôi bạn chúng ta họ ai đâu mấy nữa thêm hết cả thật sự
    thể biết hiểu giúp muốn dùng dụng nào nhé nhỉ ạ ơi khác giữa sử""".split()
)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return _WORD.findall(unicodedata.normalize("NFC", text.lower()))


def top_keywords(texts: list[str], limit: int = 3, min_count: int = 2) -> list[dict]:
    """Cụm từ hay gặp nhất: ưu tiên cặp từ liền nhau (VD "load test"), bỏ từ nối thông dụng."""
    bigrams, singles = Counter(), Counter()
    for text in texts:
        words = _tokens(text)
        seen_b, seen_s = set(), set()
        for a, b in zip(words, words[1:]):
            if a not in _STOP and b not in _STOP and len(a) > 1 and len(b) > 1:
                seen_b.add(f"{a} {b}")
        for w in words:
            if w not in _STOP and len(w) >= 4:
                seen_s.add(w)
        bigrams.update(seen_b)  # mỗi câu hỏi chỉ tính một lần cho mỗi cụm
        singles.update(seen_s)
    out: list[dict] = []
    for term, n in bigrams.most_common(30):
        if n < min_count:
            break
        if all(term not in o["term"] and o["term"] not in term for o in out):
            out.append({"term": term, "count": n})
        if len(out) >= limit:
            return out
    for term, n in singles.most_common(30):
        if n < min_count or len(out) >= limit:
            break
        if not any(term in o["term"].split() for o in out):
            out.append({"term": term, "count": n})
    return sorted(out, key=lambda x: -x["count"])[:limit]


def keywords_by_week(rows: list[tuple[Question, int]], plain) -> list[dict]:
    """Từ khóa nổi bật của từng tuần học (chỉ những tuần có câu hỏi)."""
    by_week: dict[int, list[str]] = {}
    for q, num in rows:
        by_week.setdefault(num, []).append(plain(q.content))
    result = []
    for num in sorted(by_week):
        top = top_keywords(by_week[num])
        if top:
            result.append({"week": num, "questions": len(by_week[num]), "top": top})
    return result


def hours_since(dt: datetime | None) -> float | None:
    return (utcnow() - as_utc(dt)).total_seconds() / 3600 if dt else None
