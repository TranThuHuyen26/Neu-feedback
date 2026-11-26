"""Phân loại lỗi Gemini và tự dò mô hình khi tên mô hình không tồn tại."""

import pytest

from app.services import ai


class FakeError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


@pytest.mark.parametrize(
    "code,msg,reason",
    [
        (404, "404 NOT_FOUND. models/x is not found", "model"),
        (429, "429 RESOURCE_EXHAUSTED", "quota"),
        (403, "403 PERMISSION_DENIED", "key"),
        (400, "400 API key not valid. API_KEY_INVALID", "key"),
        (503, "503 UNAVAILABLE", "busy"),
    ],
)
def test_classify_error(code, msg, reason):
    assert ai.classify_error(FakeError(code, msg)) == reason
    assert ai.AIBusy(reason).message


def test_model_not_found_falls_back(monkeypatch):
    calls = []

    def fake_call(model, contents, system, max_tokens):
        calls.append(model)
        if model == "ten-sai":
            raise FakeError(404, "404 NOT_FOUND")
        return "ok"

    monkeypatch.setattr(ai.settings, "gemini_api_key", "k")
    monkeypatch.setattr(ai.settings, "gemini_model", "ten-sai")
    monkeypatch.setattr(ai, "_call", fake_call)
    monkeypatch.setattr(ai, "_find_model", lambda: "gemini-x-flash-lite")
    monkeypatch.setattr(ai, "_model_override", None)
    assert ai.generate("xin chào") == "ok"
    assert calls == ["ten-sai", "gemini-x-flash-lite"]
    assert ai._model_override == "gemini-x-flash-lite"
    ai._model_override = None


def test_quota_error_message(monkeypatch):
    def boom(model, contents, system, max_tokens):
        raise FakeError(429, "429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(ai.settings, "gemini_api_key", "k")
    monkeypatch.setattr(ai, "_call", boom)
    monkeypatch.setattr(ai, "_model_override", None)
    with pytest.raises(ai.AIBusy) as e:
        ai.generate("x")
    assert e.value.reason == "quota"


def test_fast_config_turns_thinking_off(monkeypatch):
    monkeypatch.setattr(ai, "_thinking_ok", True)
    monkeypatch.setattr(ai.settings, "gemini_thinking_budget", 0)
    cfg = ai._cfg("sys", 512)
    assert cfg.thinking_config.thinking_budget == 0
    assert cfg.max_output_tokens == 512
    monkeypatch.setattr(ai.settings, "gemini_thinking_budget", -1)
    assert ai._cfg(None, None) is None  # -1: để mô hình tự quyết, không ép cấu hình


def test_small_talk_skips_retrieval():
    from app.routers.assistant import SMALL_TALK

    for ok in ("alo", "Xin chào", "hello bạn", "cảm ơn nhé", "bạn là ai"):
        assert SMALL_TALK.match(ok), ok
    for no in ("alo cho mình hỏi Load Test là gì", "Stress test khác load test thế nào?"):
        assert not SMALL_TALK.match(no), no
