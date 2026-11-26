from app.services.analytics import top_keywords


def test_top_keywords_prefers_phrases_and_skips_filler():
    qs = [
        "Load test khác stress test như thế nào?",
        "Load test dùng công cụ gì ạ?",
        "Em muốn hỏi về load test và postman",
        "Stress test cần bao nhiêu người dùng?",
    ]
    top = [x["term"] for x in top_keywords(qs)]
    assert "load test" in top and "stress test" in top
    assert not any(w in top for w in ("như", "gì", "ạ"))


def test_top_keywords_needs_repetition():
    assert top_keywords(["Deadlock xảy ra khi nào"], min_count=2) == []
