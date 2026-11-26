"""Sinh viên sửa / xóa câu hỏi của mình: chỉ khi còn chờ phản hồi, chưa ai trả lời."""

from tests.conftest import login


def _current_week(client, h, cid):
    weeks = client.get(f"/api/classes/{cid}/weeks", headers=h).json()["weeks"]
    return next(w for w in weeks if w["status"] == "current")


def _ask(client, student, week_id, text):
    r = client.post(f"/api/weeks/{week_id}/questions", headers=student, data={"content": text})
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_student_edits_waiting_question(client, student, lecturer, ktpm):
    wk = _current_week(client, student, ktpm["id"])
    q = _ask(client, student, wk["id"], "Câu hỏi gửi nhầm ban đầu")
    assert q["can_modify"] is True and q["edited_at"] is None
    r = client.patch(
        f"/api/questions/{q['id']}/mine", headers=student, json={"content": "  Nội dung đã sửa  "}
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["content"] == "Nội dung đã sửa" and out["edited_at"] is not None
    items = client.get(f"/api/weeks/{wk['id']}/questions", headers=lecturer).json()["questions"]
    mine = next(i for i in items if i["id"] == q["id"])
    assert mine["content"] == "Nội dung đã sửa" and mine["edited_at"] is not None
    assert "author" not in mine and "student_id" not in mine  # không lộ người hỏi


def test_student_deletes_waiting_question(client, student, lecturer, ktpm):
    wk = _current_week(client, student, ktpm["id"])
    q = _ask(client, student, wk["id"], "Câu hỏi sẽ bị xóa hẳn")
    assert client.delete(f"/api/questions/{q['id']}/mine", headers=student).status_code == 200
    mine = client.get(f"/api/weeks/{wk['id']}/my-questions", headers=student).json()
    assert q["id"] not in [i["id"] for i in mine]
    items = client.get(f"/api/weeks/{wk['id']}/questions", headers=lecturer).json()["questions"]
    assert q["id"] not in [i["id"] for i in items]
    assert client.delete(f"/api/questions/{q['id']}/mine", headers=student).status_code == 404


def test_cannot_touch_other_students_question(client, student, ktpm):
    other = login(client, "11236137@st.neu.edu.vn")
    wk = _current_week(client, student, ktpm["id"])
    q = _ask(client, student, wk["id"], "Câu hỏi của bạn Huyền")
    assert (
        client.patch(
            f"/api/questions/{q['id']}/mine", headers=other, json={"content": "đổi"}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/questions/{q['id']}/mine", headers=other).status_code == 404


def test_cannot_edit_or_delete_after_answer(client, student, lecturer, ktpm):
    wk = _current_week(client, student, ktpm["id"])
    q = _ask(client, student, wk["id"], "Câu hỏi sắp được trả lời")
    client.post(
        f"/api/questions/{q['id']}/answer", headers=lecturer, json={"content": "Đã trả lời."}
    )
    r = client.patch(f"/api/questions/{q['id']}/mine", headers=student, json={"content": "sửa"})
    assert r.status_code == 409
    assert client.delete(f"/api/questions/{q['id']}/mine", headers=student).status_code == 409
    mine = client.get(f"/api/weeks/{wk['id']}/my-questions", headers=student).json()
    assert next(i for i in mine if i["id"] == q["id"])["can_modify"] is False


def test_lecturer_cannot_use_student_endpoints(client, student, lecturer, ktpm):
    wk = _current_week(client, student, ktpm["id"])
    q = _ask(client, student, wk["id"], "Giảng viên không được xóa hộ")
    assert client.delete(f"/api/questions/{q['id']}/mine", headers=lecturer).status_code == 403
    assert (
        client.patch(
            f"/api/questions/{q['id']}/mine", headers=lecturer, json={"content": "x"}
        ).status_code
        == 403
    )
