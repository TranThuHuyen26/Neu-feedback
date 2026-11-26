"""Kết nối Google Gemini.

Có GEMINI_API_KEY thì gọi Gemini thật (sinh câu trả lời và embedding). Không có key thì chạy chế độ demo:
embedding tính bằng băm từ đơn giản, đủ để thử việc gộp câu hỏi và tìm tài liệu mà không cần mạng.
"""

import hashlib
import json
import logging
import math
import re
import time
import unicodedata

from app.config import get_settings

log = logging.getLogger("neu.ai")
settings = get_settings()
DEMO_DIM = 512


BUSY_MESSAGE = "NEU AI đang bận, vui lòng thử lại sau ít phút"
MESSAGES = {
    "quota": "NEU AI đã hết lượt dùng miễn phí trong thời gian này, vui lòng thử lại sau ít phút",
    "key": "Khóa NEU AI (GEMINI_API_KEY) không hợp lệ hoặc chưa được cấp quyền, hãy báo quản trị viên",
    "model": "Mô hình NEU AI không tồn tại, hãy báo quản trị viên kiểm tra GEMINI_MODEL",
    "busy": BUSY_MESSAGE,
}


class AIBusy(Exception):
    """Không gọi được Gemini. `reason`: quota | key | model | busy; `message` hiển thị cho người dùng."""

    def __init__(self, reason: str = "busy"):
        super().__init__(reason)
        self.reason = reason
        self.message = MESSAGES.get(reason, BUSY_MESSAGE)


def classify_error(exc: Exception) -> str:
    """Phân loại lỗi Gemini để báo đúng nguyên nhân thay vì luôn nói "đang bận"."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    msg = str(exc)
    if code == 404 or "NOT_FOUND" in msg:
        return "model"
    if code == 429 or "RESOURCE_EXHAUSTED" in msg:
        return "quota"
    if code in (400, 401, 403) and ("API key" in msg or "API_KEY" in msg or code in (401, 403)):
        return "key"
    if "API_KEY_INVALID" in msg or "PERMISSION_DENIED" in msg:
        return "key"
    return "busy"


_client = None
_thinking_ok = True  # đặt False nếu mô hình từ chối cấu hình thinking
_model_override: str | None = None  # mô hình tự dò được khi tên trong cấu hình không tồn tại


def _unit(c: dict) -> str:
    """Excel trích theo sheet, các loại khác theo trang/slide."""
    return "sheet" if str(c.get("filename", "")).lower().endswith(".xlsx") else "trang"


def _gemini():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ---------------------------------------------------------------- embedding
def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text.lower())
    words = re.findall(r"\w+", text)
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def _demo_embed(text: str) -> list[float]:
    vec = [0.0] * DEMO_DIM
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % DEMO_DIM] += 1.0 if (h >> 9) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if not settings.ai_enabled:
        return [_demo_embed(t) for t in texts]
    try:
        out = []
        for i in range(0, len(texts), 50):  # gửi theo lô để tiết kiệm lượt gọi
            res = _gemini().models.embed_content(
                model=settings.gemini_embed_model, contents=texts[i : i + 50]
            )
            out.extend(e.values for e in res.embeddings)
        return out
    except Exception as exc:  # hết lượt → dùng tạm embedding demo
        log.warning("Gemini embedding lỗi, dùng embedding demo: %s", exc)
        return [_demo_embed(t) for t in texts]


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def similarity_threshold() -> float:
    """Ngưỡng gợi ý gộp nhóm câu hỏi tương đồng."""
    return (
        settings.similarity_threshold if settings.ai_enabled else settings.demo_similarity_threshold
    )


def auto_answer_threshold() -> float:
    """Ngưỡng tự động trả lời (cao hơn ngưỡng gợi ý để hạn chế ghép nhầm)."""
    return (
        settings.auto_answer_threshold
        if settings.ai_enabled
        else settings.demo_auto_answer_threshold
    )


# ---------------------------------------------------------------- sinh văn bản
def _find_model() -> str | None:
    """Tra danh sách mô hình khóa API đang dùng được, ưu tiên dòng flash-lite rồi flash."""
    names = []
    for m in _gemini().models.list():
        if "generateContent" in (getattr(m, "supported_actions", None) or []):
            names.append(m.name.removeprefix("models/"))
    stable = [
        n
        for n in names
        if "flash" in n
        and not any(x in n for x in ("preview", "exp", "tts", "image", "live", "thinking"))
    ]
    for key in ("flash-lite", "flash"):
        picks = sorted(n for n in stable if key in n and (key != "flash" or "lite" not in n))
        if picks:
            return picks[-1]
    return None


def _cfg(system: str | None, max_tokens: int | None):
    """Cấu hình gọi Gemini. Tắt "thinking" (mặc định) để trả lời nhanh: hỏi đáp bài học không cần suy nghĩ lâu."""
    from google.genai import types

    kw: dict = {}
    if system:
        kw.update(system_instruction=system, temperature=0.4)
    if max_tokens:
        kw["max_output_tokens"] = max_tokens
    if _thinking_ok and settings.gemini_thinking_budget >= 0:
        kw["thinking_config"] = types.ThinkingConfig(
            thinking_budget=settings.gemini_thinking_budget
        )
    return types.GenerateContentConfig(**kw) if kw else None


def _call(model: str, contents, system: str | None, max_tokens: int | None) -> str:
    global _thinking_ok
    try:
        res = _gemini().models.generate_content(
            model=model, contents=contents, config=_cfg(system, max_tokens)
        )
    except Exception as exc:
        if _thinking_ok and "thinking" in str(exc).lower():
            log.warning("Mô hình %s không nhận cấu hình thinking, bỏ qua: %s", model, exc)
            _thinking_ok = False
            res = _gemini().models.generate_content(
                model=model, contents=contents, config=_cfg(system, max_tokens)
            )
        else:
            raise
    return (res.text or "").strip()


def generate(
    prompt: str,
    system: str | None = None,
    parts: list | None = None,
    max_tokens: int | None = None,
) -> str:
    """Gọi Gemini. `parts`: danh sách (bytes, mime_type) — ảnh / PDF sinh viên đính kèm."""
    global _model_override
    if not settings.ai_enabled:
        raise RuntimeError("demo")
    from google.genai import types

    contents = [prompt] + [types.Part.from_bytes(data=b, mime_type=m) for b, m in (parts or [])]
    contents = contents if parts else prompt
    model = _model_override or settings.gemini_model
    t0 = time.perf_counter()
    try:
        out = _call(model, contents, system, max_tokens)
        log.info(
            "Gemini %s trả lời sau %.2fs (%d ký tự)", model, time.perf_counter() - t0, len(out)
        )
        return out
    except Exception as exc:
        reason = classify_error(exc)
        log.error("Gemini lỗi (%s) với mô hình %s: %s", reason, model, exc)
        if reason == "model" and _model_override is None:
            try:
                found = _find_model()
            except Exception as exc2:
                log.error("Không tra được danh sách mô hình Gemini: %s", exc2)
                found = None
            if found and found != model:
                log.warning(
                    "Mô hình %s không tồn tại, tạm dùng %s. Hãy đặt GEMINI_MODEL=%s trong .env",
                    model,
                    found,
                    found,
                )
                try:
                    out = _call(found, contents, system, max_tokens)
                    _model_override = found
                    return out
                except Exception as exc3:
                    log.error("Gemini lỗi với mô hình dự phòng %s: %s", found, exc3)
                    reason = classify_error(exc3)
        raise AIBusy(reason) from exc


SYSTEM_VI = (
    'Bạn là NEU AI, trợ lý học tập của hệ thống. Khi người dùng chào hoặc hỏi bạn là ai, chỉ giới thiệu ngắn gọn một hai câu (ví dụ: "Mình là NEU AI, trợ lý học tập của hệ thống. Bạn muốn hỏi gì về bài học?"), không liệt kê ví dụ câu hỏi. Trả lời bằng tiếng Việt, rõ ràng, '
    'chính xác, thân thiện. Không bịa thông tin. Khi nhắc tới người dạy luôn viết "Giảng viên" (viết hoa chữ G), '
    'không dùng "thầy/cô". Không chèn ký hiệu trích dẫn dạng [1], [2] vào câu trả lời.'
    "Trình bày đơn giản, dễ đọc: đoạn văn ngắn; khi liệt kê dùng gạch đầu dòng bắt đầu bằng dấu '-'; hạn chế in đậm, không dùng tiêu đề bắt đầu bằng '#'. "
)

EXTRA_MARK = "Kiến thức bổ sung:"  # giao diện tách phần này thành khối riêng, có ghi chú "không có trong tài liệu lớp"


def _ctx_text(contexts: list[dict]) -> str:
    return "\n\n".join(
        f"--- Trích từ “{c['filename']}”"
        + (f", {_unit(c)} {c['page']}" if c.get("page") else "")
        + f" ---\n{c['content']}"
        for c in contexts
    )


def _demo_from_contexts(question: str, contexts: list[dict], attach_text: str = "") -> str:
    """Chế độ demo (chưa có API key): trích phần nội dung liên quan nhất, không trích mục lục/trang bìa."""
    if not contexts and not attach_text:
        return (
            "[Chế độ demo] Mình chưa tìm thấy nội dung liên quan trong tài liệu của lớp. "
            "Bạn thử hỏi cụ thể hơn, hoặc gửi câu hỏi cho Giảng viên trong tuần học nhé."
        )
    out = [
        "[Chế độ demo — chưa cấu hình GEMINI_API_KEY, đây là nội dung trích từ tài liệu chứ chưa phải câu trả lời của AI]"
    ]
    for c in contexts[:2]:
        out.append(
            f"Theo “{c['filename']}”"
            + (f" ({_unit(c)} {c['page']})" if c.get("page") else "")
            + f":\n{c['content'][:700]}"
        )
    if attach_text:
        out.append("Nội dung tệp bạn gửi (trích):\n" + attach_text[:500])
    return "\n\n".join(out)


def answer_from_materials(
    question: str,
    contexts: list[dict],
    subject: str,
    attach_text: str = "",
    attach_parts: list | None = None,
) -> str:
    """Chatbot cho sinh viên: ưu tiên tài liệu của lớp; được bổ sung kiến thức chung nhưng phải tách riêng, đánh dấu rõ."""
    if not settings.ai_enabled:
        return _demo_from_contexts(question, contexts, attach_text)
    attach = (
        ("\n\nTỆP SINH VIÊN GỬI KÈM (nội dung chữ):\n" + attach_text[:12000]) if attach_text else ""
    )
    if attach_parts:
        attach += (
            "\n\n(Sinh viên có gửi kèm ảnh/tệp ở cuối tin nhắn — hãy đọc và dùng nếu liên quan.)"
        )
    prompt = (
        f"Môn học: {subject}\n\nTÀI LIỆU CỦA LỚP:\n{_ctx_text(contexts) or '(không tìm thấy đoạn tài liệu liên quan)'}{attach}\n\n"
        f"CÂU HỎI CỦA SINH VIÊN: {question}\n\n"
        "Yêu cầu trả lời:\n"
        "1. Giải thích TRỰC TIẾP nội dung (khái niệm, cách làm, ví dụ) dựa trên tài liệu của lớp. "
        'Tuyệt đối không trả lời kiểu "xem chương X, trang Y" — số trang đã hiển thị ở phần Nguồn.\n'
        "2. Trình bày dễ hiểu: 1 câu trả lời ngắn gọn trước, sau đó các ý chính (gạch đầu dòng) và ví dụ nếu có.\n"
        "3. Nếu tài liệu chưa đủ chi tiết, được bổ sung bằng kiến thức chung đáng tin cậy, NHƯNG phải đặt ở cuối, "
        f'trong một đoạn riêng bắt đầu đúng bằng dòng "{EXTRA_MARK}". Không trộn kiến thức bổ sung vào phần trên.\n'
        "4. Nếu câu hỏi nằm ngoài môn học, trả lời ngắn và gợi ý sinh viên hỏi Giảng viên."
    )
    return generate(prompt, SYSTEM_VI, attach_parts, max_tokens=settings.chat_max_output_tokens)


GREETING = re.compile(
    r"^\s*(xin\s+)?chào\s+(các\s+)?(em|bạn|cả lớp|lớp)[^\n.!:,]{0,20}[,.!:]?\s*", re.I
)


def strip_greeting(text: str) -> str:
    """Bỏ lời chào ở đầu gợi ý (phòng khi mô hình vẫn viết "Chào các em, …")."""
    out = GREETING.sub("", text or "", count=1).lstrip()
    return (out[:1].upper() + out[1:]) if out else text


def suggest_answer(question: str, subject: str) -> str:
    """Gợi ý trả lời cho Giảng viên — dựa trên nội dung câu hỏi."""
    if not settings.ai_enabled:
        return (
            f"[Chế độ demo] Gợi ý: trả lời trực tiếp ý chính của câu hỏi “{question[:120]}”, "
            "kèm một ví dụ ngắn liên hệ bài học. Giảng viên chỉnh sửa trước khi gửi."
        )
    prompt = (
        f"Môn học: {subject}\nCâu hỏi ẩn danh của sinh viên: {question}\n\n"
        "Hãy soạn một câu trả lời mẫu (3–5 câu) để Giảng viên tham khảo, giọng văn của Giảng viên nói với sinh viên. "
        'Không mở đầu bằng lời chào (không viết "Chào em", "Chào các em", "Chào bạn"), không ký tên; '
        "đi thẳng vào nội dung trả lời."
    )
    return strip_greeting(generate(prompt, SYSTEM_VI))


def suggest_group_answer(questions: list[str], subject: str) -> str:
    """Gợi ý MỘT câu trả lời chung bao quát mọi cách hỏi trong nhóm câu hỏi tương đồng."""
    if not settings.ai_enabled:
        return (
            "[Chế độ demo] Gợi ý trả lời chung cho "
            + str(len(questions))
            + " câu hỏi: nêu khái niệm chính, "
            "so sánh các ý sinh viên hỏi và cho một ví dụ minh họa. Giảng viên chỉnh sửa trước khi gửi."
        )
    joined = "\n".join(f"- {q}" for q in questions[:20])
    prompt = (
        f"Môn học: {subject}\nCác câu hỏi ẩn danh có cùng ý của sinh viên:\n{joined}\n\n"
        "Hãy soạn MỘT câu trả lời chung (4–6 câu) trả lời được tất cả các cách hỏi trên, "
        "giọng văn của Giảng viên nói với sinh viên, có ví dụ ngắn nếu phù hợp. "
        'Không mở đầu bằng lời chào (không viết "Chào em", "Chào các em", "Chào bạn"), không ký tên; '
        "đi thẳng vào nội dung trả lời."
    )
    return strip_greeting(generate(prompt, SYSTEM_VI))


def explain_answer(question: str, answer: str, contexts: list[dict], subject: str) -> str:
    """Sinh viên nhờ NEU AI giải thích thêm câu trả lời của Giảng viên."""
    if not settings.ai_enabled:
        return (
            "[Chế độ demo] NEU AI sẽ diễn giải lại câu trả lời của Giảng viên chi tiết hơn và thêm ví dụ.\n\n"
            + _demo_from_contexts(question, contexts)[:900]
        )
    prompt = (
        f"Môn học: {subject}\nCâu hỏi của sinh viên: {question}\nCâu trả lời của Giảng viên: {answer}\n\n"
        f"TÀI LIỆU CỦA LỚP:\n{_ctx_text(contexts) or '(không có)'}\n\n"
        "Sinh viên chưa hiểu hết câu trả lời trên. Hãy giải thích lại chi tiết, dễ hiểu hơn, có ví dụ cụ thể. "
        "Giữ đúng ý của Giảng viên, không mâu thuẫn với câu trả lời đó. "
        f'Phần kiến thức không có trong tài liệu lớp đặt cuối, bắt đầu bằng dòng "{EXTRA_MARK}".'
    )
    return generate(prompt, SYSTEM_VI)


def summarize_session(title: str, questions: list[str]) -> str:
    if not questions:
        return "Tuần học chưa có câu hỏi nào."
    if not settings.ai_enabled:
        return (
            f"[Chế độ demo] Tuần “{title}” có {len(questions)} câu hỏi. "
            f"Một số câu tiêu biểu: " + "; ".join(q[:80] for q in questions[:3]) + "."
        )
    joined = "\n".join(f"- {q}" for q in questions[:150])
    prompt = (
        f"Tuần học: {title}\nDanh sách câu hỏi ẩn danh của sinh viên:\n{joined}\n\n"
        "Tóm tắt trong 3–5 câu: các chủ đề sinh viên quan tâm nhiều nhất, những điểm còn nhầm lẫn, "
        "và 1–2 gợi ý cho tuần học sau. Không nhắc tới danh tính."
    )
    return generate(prompt, SYSTEM_VI)


BAD_WORDS = ("chán", "ngu", "ngớ ngẩn", "zalo", "bán tài liệu", "số điện thoại", "đm", "vl")


def moderation_score(content: str) -> int:
    """Chấm mức độ vi phạm 0–100 cho nội dung bị gắn cờ."""
    if settings.ai_enabled:
        try:
            raw = generate(
                f"Chấm mức độ vi phạm quy định lớp học (xúc phạm, spam, lộ thông tin cá nhân, lạc đề) "
                f'của nội dung sau trên thang 0–100. Chỉ trả về JSON dạng {{"score": số}}.\n\n{content}'
            )
            m = re.search(r"\{.*\}", raw, re.S)
            return max(0, min(100, int(json.loads(m.group(0))["score"]))) if m else 50
        except Exception:
            pass
    low = content.lower()
    return min(100, 35 + 20 * sum(w in low for w in BAD_WORDS))
