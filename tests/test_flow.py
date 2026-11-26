"""Kiểm thử các luồng chính và quy tắc nghiệp vụ: 15 tuần học, ẩn danh, trả lời tự động, quản trị."""

import json
from datetime import date

from tests.conftest import login

FORBIDDEN_KEYS = {"student_id", "author", "author_id", "email", "student", "full_name"}


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def _weeks(client, h, cid):
    return client.get(f"/api/classes/{cid}/weeks", headers=h).json()


def _current(client, h, cid):
    return next(w for w in _weeks(client, h, cid)["weeks"] if w["status"] == "current")


# ---------------------------------------------------------------- đăng nhập & phân quyền
def test_health(client):
    assert client.get("/api/health").json()["ai_mode"] == "demo"


def test_login_rules(client):
    assert (
        client.post(
            "/api/auth/login", json={"email": "hoaithu@neu.edu.vn", "password": "sai"}
        ).status_code
        == 401
    )


def test_role_guard(client, student, lecturer):
    assert client.get("/api/admin/overview", headers=student).status_code == 403
    assert client.get("/api/admin/overview", headers=lecturer).status_code == 403
    assert client.get("/api/classes").status_code == 401


def test_lecturer_cannot_open_other_lecturers_class(client, lecturer, student):
    csdl = next(
        c for c in client.get("/api/classes", headers=student).json() if c["code"] == "HQTCSDL_01"
    )
    assert client.get(f"/api/classes/{csdl['id']}/students", headers=lecturer).status_code == 403


# ---------------------------------------------------------------- 15 tuần học
def test_cannot_ask_future_week(client, student, ktpm):
    future = next(
        w for w in _weeks(client, student, ktpm["id"])["weeks"] if w["status"] == "upcoming"
    )
    r = client.post(
        f"/api/weeks/{future['id']}/questions",
        headers=student,
        data={"content": "Hỏi trước được không?"},
    )
    assert r.status_code == 409


def test_can_ask_past_week(client, student, ktpm):
    past = next(w for w in _weeks(client, student, ktpm["id"])["weeks"] if w["status"] == "done")
    r = client.post(
        f"/api/weeks/{past['id']}/questions",
        headers=student,
        data={"content": "Em hỏi lại bài tuần trước ạ"},
    )
    assert r.status_code == 201


def test_new_class_gets_15_weeks(client, lecturer):
    r = client.post(
        "/api/classes", headers=lecturer, json={"code": "KTPM_99", "subject": "Kiểm thử nâng cao"}
    )
    assert r.status_code == 201
    assert len(_weeks(client, lecturer, r.json()["id"])["weeks"]) == 15


# ---------------------------------------------------------------- ẩn danh
def test_lecturer_view_is_anonymous(client, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    data = client.get(f"/api/weeks/{cur['id']}/questions", headers=lecturer).json()
    assert data["questions"]
    leaked = FORBIDDEN_KEYS & set(_keys(data["questions"]))
    assert not leaked, f"Lộ danh tính: {leaked}"
    assert "Trần Thu Huyền" not in json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------- hỏi - đáp & trả lời tự động
def test_answer_and_notify(client, student, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    q = client.post(
        f"/api/weeks/{cur['id']}/questions",
        headers=student,
        data={"content": "Throughput là gì vậy ạ?"},
    ).json()
    assert (
        client.post(
            f"/api/questions/{q['id']}/answer", headers=student, json={"content": "x"}
        ).status_code
        == 403
    )
    r = client.post(
        f"/api/questions/{q['id']}/answer",
        headers=lecturer,
        json={"content": "Số yêu cầu xử lý được mỗi giây."},
    )
    assert r.json()["status"] == "answered"
    assert client.get("/api/notifications", headers=student).json()["unread"] >= 1
    assert (
        client.post(
            f"/api/weeks/{cur['id']}/questions", headers=student, data={"content": "   "}
        ).status_code
        == 422
    )


def test_ai_suggest_and_summary(client, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    q = next(
        x
        for x in client.get(
            f"/api/weeks/{cur['id']}/questions?status_filter=waiting", headers=lecturer
        ).json()["questions"]
    )
    assert client.post(f"/api/questions/{q['id']}/suggest", headers=lecturer).json()["suggestion"]
    s1 = client.post(f"/api/weeks/{cur['id']}/summary", headers=lecturer).json()
    s2 = client.post(f"/api/weeks/{cur['id']}/summary", headers=lecturer).json()
    assert s1["cached"] is False and s2["cached"] is True
    rep = client.get(f"/api/weeks/{cur['id']}/report", headers=lecturer).json()
    assert rep["question_count"] == sum(d["questions"] for d in rep["by_day"])


# ---------------------------------------------------------------- tài liệu theo tuần & NEU AI
def test_admin_accounts(client, admin):
    users = client.get("/api/admin/users?size=100", headers=admin).json()
    assert all(u["role"] in ("student", "lecturer") for u in users["items"])
    bad = {
        "full_name": "Ngoài Trường",
        "email": "a@gmail.com",
        "role": "student",
        "faculty": "CNTT",
    }
    assert client.post("/api/admin/users", headers=admin, json=bad).status_code == 400
    uid = next(u["id"] for u in users["items"] if u["email"] == "11236137@st.neu.edu.vn")
    assert client.post(f"/api/admin/users/{uid}/lock", headers=admin).json()["is_locked"] is True
    assert (
        client.post(
            "/api/auth/login", json={"email": "11236137@st.neu.edu.vn", "password": "Neu@12345"}
        ).status_code
        == 403
    )
    client.post(f"/api/admin/users/{uid}/unlock", headers=admin)
    an_id = next(u["id"] for u in users["items"] if u["email"] == "hoaithu@neu.edu.vn")
    assert client.delete(f"/api/admin/users/{an_id}", headers=admin).status_code == 409
    csv_data = (
        "full_name,email,role,faculty\nNguyễn A,a2006@st.neu.edu.vn,Sinh viên,CNTT\nLỗi,khong-phai-email,sv,CNTT\n"
        "Trần B,b.tran@neu.edu.vn,Giảng viên,QTKD\n"
    )
    body = client.post(
        "/api/admin/users/import",
        headers=admin,
        files={"file": ("ds.csv", csv_data.encode(), "text/csv")},
    ).json()
    assert len(body["created"]) == 2 and len(body["errors"]) == 1


def test_moderation_and_trace(client, admin):
    flags = client.get("/api/admin/flags", headers=admin).json()
    assert flags[0]["ai_score"] >= flags[-1]["ai_score"] and flags[0]["session_title"].startswith(
        "Tuần "
    )
    f = next(x for x in flags if x["question_code"] == "A120")
    assert (
        client.post(
            f"/api/admin/flags/{f['id']}/trace", headers=admin, json={"reason": "ngắn"}
        ).status_code
        == 422
    )
    assert client.post(
        f"/api/admin/flags/{f['id']}/trace",
        headers=admin,
        json={"reason": "Nội dung xúc phạm giảng viên, cần xác minh"},
    ).json()["found"]
    assert (
        client.post(
            f"/api/admin/flags/{f['id']}/decision", headers=admin, json={"decision": "hidden"}
        ).json()["status"]
        == "hidden"
    )
    logs = [x["action"] for x in client.get("/api/admin/audit-logs", headers=admin).json()]
    assert "trace_identity" in logs and "flag_hidden" in logs


# ================================================================ v2.2
def test_fifteen_weeks_contiguous(client, student, ktpm):
    data = _weeks(client, student, ktpm["id"])
    ws = data["weeks"]
    assert (
        len(ws) == 15
        and date.fromisoformat(ws[0]["start_date"]).weekday() == 0  # tuần 1 bắt đầu thứ Hai
        and "breaks" not in data["timeline"]
    )
    for a, b in zip(ws, ws[1:]):  # không có tuần nghỉ: tuần sau = tuần trước + 7 ngày
        assert (date.fromisoformat(b["start_date"]) - date.fromisoformat(a["start_date"])).days == 7
    statuses = [w["status"] for w in ws]
    cur = statuses.index("current")
    assert all(w["can_ask"] for w in ws[: cur + 1]) and not any(w["can_ask"] for w in ws[cur + 1 :])
    assert client.post(
        f"/api/classes/{ktpm['id']}/breaks", json={"week_number": 12}
    ).status_code in (401, 404, 405)


def test_lecturer_edits_week(client, lecturer, ktpm):
    last = _weeks(client, lecturer, ktpm["id"])["weeks"][-1]
    r = client.patch(
        f"/api/weeks/{last['id']}",
        headers=lecturer,
        json={"title": "Tổng kết", "description": "Ôn tập và giải đáp"},
    )
    assert r.json()["title"] == "Tổng kết"


def test_seeded_review_waits_for_approval(client, student, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    data = client.get(
        f"/api/weeks/{cur['id']}/questions?status_filter=review", headers=lecturer
    ).json()
    assert data["counts"]["review"] == 2 and len(data["questions"]) == 2
    q = next(x for x in data["questions"] if "Postman" in x["content"])
    assert (
        q["status"] == "waiting"
        and q["reuse"]["answer"]
        and q["reuse"]["week_number"] < cur["number"]
    )
    mine = client.get(f"/api/weeks/{cur['id']}/my-questions", headers=student).json()
    sq = next(x for x in mine if x["id"] == q["id"])
    assert (
        sq["status"] == "waiting" and not sq["answers"] and "reuse" not in sq
    )  # chưa duyệt → SV chưa nhận gì
    r = client.post(f"/api/questions/{q['id']}/approve-reuse", headers=lecturer).json()
    assert r["status"] == "answered" and r["answers"][0]["via_group"]
    sq = next(
        x
        for x in client.get(f"/api/weeks/{cur['id']}/my-questions", headers=student).json()
        if x["id"] == q["id"]
    )
    assert sq["answers"][0]["content"] == q["reuse"]["answer"]


def test_new_similar_to_answered_is_not_auto_answered(client, student, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    before = client.get("/api/notifications", headers=lecturer).json()
    q = client.post(
        f"/api/weeks/{cur['id']}/questions",
        headers=student,
        data={"content": "Response time bao nhiêu là chấp nhận được ạ?"},
    ).json()
    assert q["status"] == "waiting" and not q["answers"]
    lq = next(
        x
        for x in client.get(
            f"/api/weeks/{cur['id']}/questions?status_filter=review", headers=lecturer
        ).json()["questions"]
        if x["id"] == q["id"]
    )
    assert lq["reuse"]["code"] == "A103"
    r = client.post(f"/api/questions/{q['id']}/reject-reuse", headers=lecturer).json()
    assert r["status"] == "waiting" and "reuse" not in r
    after = client.get("/api/notifications", headers=lecturer).json()
    assert any("chờ duyệt" in n["title"] for n in after["items"])


def test_cluster_group_then_answer_together(client, student, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    g = next(
        x
        for x in client.get(f"/api/weeks/{cur['id']}/groups", headers=lecturer).json()
        if x["status"] == "suggested"
    )
    q102 = next(x for x in g["questions"] if x["code"] == "A102")
    # trả lời thẳng 1 câu trong nhóm CHƯA xác nhận → chỉ câu đó được trả lời
    client.post(
        f"/api/questions/{q102['id']}/answer",
        headers=lecturer,
        json={"content": "Trả lời riêng câu A102."},
    )
    g2 = next(
        x
        for x in client.get(f"/api/weeks/{cur['id']}/groups", headers=lecturer).json()
        if x["id"] == g["id"]
    )
    assert (
        sum(1 for x in g2["questions"] if x["status"] == "waiting") >= 1
        and g2["status"] == "suggested"
    )
    assert (
        g2["previous_answer"]["content"] == "Trả lời riêng câu A102."
    )  # "Dùng lại câu trả lời trước"
    assert client.post(f"/api/groups/{g['id']}/suggest", headers=lecturer).json()["suggestion"]
    assert (
        client.post(
            f"/api/groups/{g['id']}/answer", headers=lecturer, json={"content": "x"}
        ).status_code
        == 409
    )
    client.post(f"/api/groups/{g['id']}", headers=lecturer, json={"action": "confirm"})
    r = client.post(
        f"/api/groups/{g['id']}/answer",
        headers=lecturer,
        json={"content": "Câu trả lời chung cho cả nhóm."},
    ).json()
    assert "A105" in r["answered"]


def test_edit_answer_and_copies(client, student, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    qs = client.get(
        f"/api/weeks/{cur['id']}/questions?status_filter=answered", headers=lecturer
    ).json()["questions"]
    orig = next(x for x in qs if x["code"] == "A108")
    a = orig["answers"][0]
    assert a["copies_count"] >= 1 and not a["is_copy"]
    r = client.patch(
        f"/api/answers/{a['id']}",
        headers=lecturer,
        json={"content": "Bản đã sửa (không áp dụng).", "apply_to_copies": False},
    ).json()
    assert r["copies_updated"] == 0 and r["question"]["answers"][0]["edited_at"]
    copy = next(
        x
        for x in client.get(
            f"/api/weeks/{cur['id']}/questions?status_filter=answered", headers=lecturer
        ).json()["questions"]
        if x["code"] == "A111"
    )
    assert copy["answers"][0]["content"] != "Bản đã sửa (không áp dụng)."
    r = client.patch(
        f"/api/answers/{a['id']}",
        headers=lecturer,
        json={"content": "Bản đã sửa cho cả nhóm.", "apply_to_copies": True},
    ).json()
    assert r["copies_updated"] >= 1
    copy = next(
        x
        for x in client.get(
            f"/api/weeks/{cur['id']}/questions?status_filter=answered", headers=lecturer
        ).json()["questions"]
        if x["code"] == "A111"
    )
    assert (
        copy["answers"][0]["content"] == "Bản đã sửa cho cả nhóm."
        and copy["answers"][0]["edited_at"]
    )


def test_no_followups_and_explain(client, student, lecturer, ktpm):
    """Đã bỏ tính năng hỏi thêm; sinh viên vẫn nhờ NEU AI giải thích thêm được."""
    cur = _current(client, lecturer, ktpm["id"])
    q103 = next(
        x
        for x in client.get(f"/api/weeks/{cur['id']}/my-questions", headers=student).json()
        if x["code"] == "A103"
    )
    assert "followups" not in q103 and "followup_pending" not in q103
    assert q103["status"] == "answered"
    assert client.post(
        f"/api/questions/{q103['id']}/followups", headers=student, json={"content": "Thêm?"}
    ).status_code in (404, 405)
    ex = client.post(f"/api/questions/{q103['id']}/explain", headers=student).json()
    assert ex["explanation"]


def test_grouped_notifications(client, student, lecturer, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    client.post("/api/notifications/read-all", headers=lecturer)
    for t in [
        "Câu hỏi hoàn toàn mới số một về JMeter plugin?",
        "Một câu hỏi khác hẳn về báo cáo HTML?",
    ]:
        client.post(f"/api/weeks/{cur['id']}/questions", headers=student, data={"content": t})
    items = client.get("/api/notifications", headers=lecturer).json()["items"]
    newq = [n for n in items if not n["is_read"] and "câu hỏi mới đang chờ trả lời" in n["title"]]
    assert len(newq) == 1 and newq[0]["title"].split(": ")[1].startswith(
        "2 "
    )  # gộp, không tạo 2 thông báo


def test_week_materials_filtering_and_rag(client, lecturer, student, ktpm):
    cur = _current(client, lecturer, ktpm["id"])
    from io import BytesIO
    from pptx import Presentation

    pres = Presentation()
    for title, body in [
        ("Chương 2: Kiểm thử hộp trắng", None),
        (
            "Mục lục",
            "1. Hộp đen ...... 3\n2. Hộp trắng ...... 25\n3. Bài tập ...... 40\n4. Tổng kết ...... 45",
        ),
        ("Kiểm thử hộp trắng", None),
        (
            "Khái niệm",
            "Kiểm thử hộp trắng (white-box) thiết kế test case dựa trên cấu trúc bên trong của mã nguồn, người kiểm thử phải đọc được code.",
        ),
        (
            "Kỹ thuật",
            "Các kỹ thuật gồm phủ câu lệnh, phủ nhánh và phủ đường đi; ví dụ với hàm có một câu lệnh if cần ít nhất hai test case.",
        ),
    ]:
        s = pres.slides.add_slide(pres.slide_layouts[1 if body else 0])
        s.shapes.title.text = title
        if body:
            s.placeholders[1].text = body
    buf = BytesIO()
    pres.save(buf)
    r = client.post(
        f"/api/weeks/{cur['id']}/materials",
        headers=lecturer,
        files=[
            (
                "files",
                (
                    "Chapter2.pptx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ),
            )
        ],
    )
    assert (
        r.status_code == 201 and r.json()[0]["chunk_count"] == 1
    )  # bìa, mục lục, slide tiêu đề bị bỏ; 2 slide nội dung gộp 1
    r = client.post(
        "/api/ai/chat",
        headers=student,
        data={"class_id": str(ktpm["id"]), "message": "Kiểm thử hộp trắng là gì?"},
    ).json()
    assert r["sources"][0]["filename"] == "Chapter2.pptx" and "cấu trúc bên trong" in r["answer"]
    bad = [("files", ("virus.exe", b"x", "application/octet-stream"))]
    assert (
        client.post(f"/api/weeks/{cur['id']}/materials", headers=lecturer, files=bad).status_code
        == 400
    )
    mid = client.get(f"/api/materials?week_id={cur['id']}", headers=lecturer).json()[0]["id"]
    assert client.delete(f"/api/materials/{mid}", headers=lecturer).status_code == 200


def test_chat_with_attachments(client, student, ktpm):
    files = [
        (
            "files",
            (
                "de_bai.txt",
                "Đề bài: thiết kế test case cho hàm tính điểm trung bình.".encode(),
                "text/plain",
            ),
        )
    ]
    r = client.post(
        "/api/ai/chat",
        headers=student,
        data={"class_id": str(ktpm["id"]), "message": "Giúp em đề bài này"},
        files=files,
    )
    assert r.status_code == 200 and r.json()["attachments"][0]["name"] == "de_bai.txt"
    hist = client.get(f"/api/ai/history?class_id={ktpm['id']}", headers=student).json()
    m = next(x for x in hist if x["attachments"])
    assert (
        client.get(f"/api/ai/messages/{m['id']}/attachments/0", headers=student).status_code == 200
    )
    bad = [("files", ("a.exe", b"x", "application/octet-stream"))]
    assert (
        client.post(
            "/api/ai/chat",
            headers=student,
            data={"class_id": str(ktpm["id"]), "message": "x"},
            files=bad,
        ).status_code
        == 400
    )
    many = [("files", (f"f{i}.txt", b"abc", "text/plain")) for i in range(4)]
    assert (
        client.post(
            "/api/ai/chat",
            headers=student,
            data={"class_id": str(ktpm["id"]), "message": "x"},
            files=many,
        ).status_code
        == 400
    )


# ---------------------------------------------------------------- học kỳ, loại học phần, kỳ Hè
def test_semesters_and_course_types(client, admin, lecturer):
    """Học kỳ tự động theo ngày bắt đầu học — Admin không khai báo."""
    sems = client.get("/api/semesters", headers=lecturer).json()
    assert sems[0]["label"] == "Học kỳ Thu 2026" and sems[0]["is_default"]
    assert client.post(
        "/api/admin/semesters",
        headers=admin,
        json={"year": "2026-2027", "term": "he", "start_date": "2027-06-07"},
    ).status_code in (404, 405)
    # môn lý luận chính trị: 10 tuần (không gửi ngày → theo học kỳ đang diễn ra)
    c = client.post(
        "/api/classes",
        headers=lecturer,
        json={"code": "TRIET_01", "subject": "Triết học Mác - Lênin", "course_type": "political"},
    ).json()
    ws = client.get(f"/api/classes/{c['id']}/weeks", headers=lecturer).json()
    assert (
        c["unit_count"] == 10
        and len(ws["weeks"]) == 10
        and ws["timeline"]["unit_label"] == "Tuần"
        and c["semester"] == "Học kỳ Thu 2026"
    )
    # ngày bắt đầu tháng 6 → tự tạo Học kỳ Hè 2027; kỳ Hè phải chọn 3 thứ học; 15 buổi, hiển thị "Buổi"
    body = {"code": "KTPM_H1", "subject": "Kiểm thử phần mềm", "start_date": "2027-06-07"}
    assert client.post("/api/classes", headers=lecturer, json=body).status_code == 422
    c = client.post(
        "/api/classes", headers=lecturer, json={**body, "meeting_days": [0, 2, 4]}
    ).json()
    assert c["semester"] == "Học kỳ Hè 2027"
    ws = client.get(f"/api/classes/{c['id']}/weeks", headers=lecturer).json()["weeks"]
    assert (
        c["unit_label"] == "Buổi"
        and len(ws) == 15
        and ws[0]["start_date"] == "2027-06-07"
        and ws[1]["start_date"] == "2027-06-09"
    )
    # ngày giữa tuần tháng 1 → Học kỳ Xuân 2027, tuần 1 bắt đầu từ thứ Hai của tuần đó
    c = client.post(
        "/api/classes",
        headers=lecturer,
        json={"code": "CSDL_X1", "subject": "Cơ sở dữ liệu", "start_date": "2027-01-27"},
    ).json()
    ws = client.get(f"/api/classes/{c['id']}/weeks", headers=lecturer).json()["weeks"]
    assert c["semester"] == "Học kỳ Xuân 2027" and ws[0]["start_date"] == "2027-01-25"
    labels = [s["label"] for s in client.get("/api/semesters", headers=lecturer).json()]
    assert "Học kỳ Hè 2027" in labels and "Học kỳ Xuân 2027" in labels


def test_flag_notifies_admin_and_times_are_utc(client, admin, lecturer, ktpm):
    cur = next(
        w
        for w in client.get(f"/api/classes/{ktpm['id']}/weeks", headers=lecturer).json()["weeks"]
        if w["status"] == "current"
    )
    q = next(
        x
        for x in client.get(
            f"/api/weeks/{cur['id']}/questions?status_filter=waiting", headers=lecturer
        ).json()["questions"]
    )
    before = client.get("/api/notifications", headers=admin).json()
    assert any(
        "gắn cờ" in n["title"] for n in before["items"]
    )  # dữ liệu mẫu có sẵn thông báo cho Admin
    assert (
        client.post(
            f"/api/questions/{q['id']}/flag",
            headers=lecturer,
            json={"reason": "Nội dung cần kiểm tra"},
        ).status_code
        == 200
    )
    n = next(
        x
        for x in client.get("/api/notifications", headers=admin).json()["items"]
        if "gắn cờ" in x["title"]
    )
    assert n["link"] == "admin-reports.html" and not n["is_read"]
    assert (
        n["created_at"].endswith("Z") or "+00:00" in n["created_at"]
    )  # có múi giờ → giao diện không lệch 7 tiếng


# ---------------------------------------------------------------- tên lớp theo học kỳ, xóa lớp còn trống
def test_class_code_and_delete_empty_only(client, admin, lecturer, student):
    r = client.post(
        "/api/classes", headers=lecturer, json={"code": "ktpm_01", "subject": "Kiểm thử phần mềm"}
    )
    cur = client.get("/api/semesters", headers=lecturer).json()
    assert r.status_code in (201, 409)
    ok = client.post(
        "/api/classes",
        headers=lecturer,
        json={"code": "ktpm_01", "subject": "Kiểm thử phần mềm", "start_date": "2027-01-25"},
    )
    assert (
        ok.status_code == 201 and ok.json()["code"] == "KTPM_01"
    )  # học kỳ khác: dùng lại được tên
    assert (
        client.get(
            "/api/classes-check-code?code=KTPM_01&start_date=2027-02-01", headers=lecturer
        ).json()["available"]
        is False
    )
    cid = ok.json()["id"]
    assert cur is not None
    # không còn chức năng lưu trữ / khôi phục
    assert client.post(f"/api/classes/{cid}/archive", headers=lecturer).status_code in (404, 405)
    assert client.post(f"/api/classes/{cid}/restore", headers=lecturer).status_code in (404, 405)
    # lớp có sinh viên thì không xóa được
    code = client.get(f"/api/classes/{cid}", headers=lecturer).json()["join_code"]
    assert (
        client.post("/api/classes/join", headers=student, json={"join_code": code}).status_code
        == 200
    )
    blocked = client.delete(f"/api/classes/{cid}", headers=lecturer)
    assert blocked.status_code == 409 and "sinh viên" in blocked.json()["detail"]
    # lớp còn trống thì xóa được
    empty = client.post(
        "/api/classes",
        headers=lecturer,
        json={"code": "TRONG_01", "subject": "Lớp tạo nhầm", "start_date": "2027-01-25"},
    ).json()
    assert client.delete(f"/api/classes/{empty['id']}", headers=lecturer).status_code == 200
    ktpm = next(
        c for c in client.get("/api/classes", headers=lecturer).json() if c["code"] == "KTPM_01"
    )
    assert (
        client.delete(f"/api/classes/{ktpm['id']}", headers=lecturer).status_code == 409
    )  # đã có câu hỏi và sinh viên


def test_class_list_filters_by_semester(client, lecturer):
    allc = client.get("/api/classes", headers=lecturer).json()
    sid = allc[0]["semester_id"]
    only = client.get(f"/api/classes?semester_id={sid}", headers=lecturer).json()
    assert only and all(c["semester_id"] == sid for c in only)


def test_stale_token_and_stats_terms(client, admin):
    from app.security import create_token as create_access_token
    from app.models import User
    from sqlalchemy.orm import Session
    from app.database import engine

    db = Session(engine)
    u = (
        db.query(User)
        .filter(User.role == "student", User.email != "11236004@st.neu.edu.vn")
        .order_by(User.id.desc())
        .first()
    )
    tok = create_access_token(u)
    u.email = "doi-email@st.neu.edu.vn"
    db.commit()
    db.close()  # như khi tạo lại dữ liệu mẫu
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    st = client.get("/api/admin/stats", headers=admin).json()
    assert [s["term"] for s in st["semesters"]] == ["thu", "xuan", "he"] and "2025-2026" in st[
        "years"
    ]
    empty = client.get(
        "/api/admin/stats?year=2025-2026&term=he", headers=admin
    ).json()  # năm trước, chưa khai báo
    assert (
        empty["empty"]
        and empty["total"]["questions"] == 0
        and empty["range"]["label"] == "Học kỳ Hè 2026"
    )
    assert isinstance(client.get("/api/admin/faculties", headers=admin).json(), list)


# ---------------------------------------------------------------- tìm kiếm, tổng hợp, danh sách cần xử lý, ảnh trong câu trả lời
def test_workspace_search_inbox_images(client, student, lecturer, ktpm):
    r = client.get("/api/search?q=KTPM", headers=lecturer).json()
    assert r["classes"] and r["classes"][0]["code"] == "KTPM_01"
    assert client.get("/api/search?q=Chương", headers=student).json()["weeks"]
    s = client.get("/api/lecturer/summary", headers=lecturer).json()
    assert s["total"] == s["new"] + s["groups"] + s["flagged"] and s["new"] > 0
    inbox = client.get("/api/lecturer/inbox?kind=new", headers=lecturer).json()
    assert inbox["total"] == s["new"] and inbox["sections"][0]["items"][0]["code"].startswith("A")
    assert (
        client.get("/api/lecturer/inbox?kind=groups", headers=lecturer).json()["total"]
        == s["groups"]
    )
    me = client.get("/api/me/summary", headers=student).json()
    assert set(me) >= {"answered", "waiting", "new_materials", "waiting_by_class"}
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    up = client.post(
        "/api/answer-images",
        headers=lecturer,
        data={"class_id": str(ktpm["id"])},
        files={"file": ("so-do.png", png, "image/png")},
    )
    assert up.status_code == 201
    url = up.json()["url"]
    assert (
        client.get(url, headers=lecturer).status_code == 200
        and client.get(url, headers=student).status_code == 200
    )
    bad = client.post(
        "/api/answer-images",
        headers=lecturer,
        data={"class_id": str(ktpm["id"])},
        files={"file": ("x.exe", b"MZ", "application/octet-stream")},
    )
    assert bad.status_code == 422


def test_future_week_materials_and_excel(client, lecturer, student, ktpm):
    """Bản 3.4: tài liệu tuần chưa học xem được ngay (câu hỏi vẫn khóa); NEU AI đọc Excel theo từng sheet."""
    from io import BytesIO
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lịch thi"
    ws.append(["Môn", "Ngày thi", "Phòng"])
    ws.append(["Kiểm thử phần mềm", "15/12/2026", "A2-301"])
    ws2 = wb.create_sheet("Điểm thành phần")
    ws2.append(["Thành phần", "Trọng số"])
    ws2.append(["Chuyên cần", "10%"])
    ws2.append(["Bài tập lớn kiểm thử tự động", "30%"])
    buf = BytesIO()
    wb.save(buf)
    future = next(
        w for w in _weeks(client, lecturer, ktpm["id"])["weeks"] if w["status"] == "upcoming"
    )
    r = client.post(
        f"/api/weeks/{future['id']}/materials",
        headers=lecturer,
        files=[
            (
                "files",
                (
                    "Thong-tin-mon.xlsx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
    )
    assert (
        r.status_code == 201
        and r.json()[0]["file_type"] == "XLS"
        and r.json()[0]["chunk_count"] == 2
    )
    # sinh viên xem được tài liệu + thông tin tuần chưa học, có thông báo
    assert client.get(f"/api/weeks/{future['id']}", headers=student).status_code == 200
    mats = client.get(f"/api/materials?week_id={future['id']}", headers=student).json()
    assert [m["filename"] for m in mats] == ["Thong-tin-mon.xlsx"]
    items = client.get("/api/notifications", headers=student).json()["items"]
    assert any(f"tuần {future['number']}" in n["title"] for n in items)
    # nhưng chưa gửi câu hỏi được
    assert (
        client.post(
            f"/api/weeks/{future['id']}/questions", headers=student, data={"content": "Hỏi trước"}
        ).status_code
        == 409
    )
    # NEU AI dùng tài liệu tuần chưa học, trích theo sheet
    r = client.post(
        "/api/ai/chat",
        headers=student,
        data={
            "class_id": str(ktpm["id"]),
            "message": "Bài tập lớn kiểm thử tự động chiếm trọng số bao nhiêu?",
        },
    ).json()
    src = next(s for s in r["sources"] if s["filename"] == "Thong-tin-mon.xlsx")
    assert src["page"] == 2 and "30%" in r["answer"] and "sheet 2" in r["answer"]


def test_question_attachments_groups_and_stats(client, lecturer, student, ktpm):
    """Bản 3.5: tối đa 3 tệp đính kèm; nhóm đã trả lời có câu trả lời, không tách được; thống kê ghi tuần hiện tại."""
    cur = _current(client, lecturer, ktpm["id"])
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 50
    files = [
        ("attachments", ("loi.png", png, "image/png")),
        ("attachments", ("bai-tap.pdf", b"%PDF-1.4 x", "application/pdf")),
        ("attachments", ("so-lieu.xlsx", b"PK\x03\x04x", "application/octet-stream")),
    ]
    r = client.post(
        f"/api/weeks/{cur['id']}/questions",
        headers=student,
        data={"content": "Em chưa hiểu **phủ nhánh**:\n- Ví dụ 2 lệnh if cần mấy test case?"},
        files=files,
    )
    assert r.status_code == 201, r.text
    q = r.json()
    assert [a["type"] for a in q["attachments"]] == ["IMG", "PDF", "XLS"] and q["has_attachment"]
    a = q["attachments"][1]
    assert (
        client.get(f"/api/questions/{q['id']}/attachments/{a['id']}", headers=lecturer).content
        == b"%PDF-1.4 x"
    )
    assert (
        client.get(f"/api/questions/{q['id']}/attachment", headers=student).status_code == 200
    )  # đường dẫn cũ
    four = files + [("attachments", ("x.png", png, "image/png"))]
    assert (
        client.post(
            f"/api/weeks/{cur['id']}/questions",
            headers=student,
            data={"content": "Hỏi"},
            files=four,
        ).status_code
        == 400
    )
    bad = [("attachments", ("virus.exe", b"x", "application/octet-stream"))]
    assert (
        client.post(
            f"/api/weeks/{cur['id']}/questions", headers=student, data={"content": "Hỏi"}, files=bad
        ).status_code
        == 400
    )
    # nhóm đã trả lời: có câu trả lời gốc, không cho tách
    groups = client.get(f"/api/weeks/{cur['id']}/groups", headers=lecturer).json()
    done = next(g for g in groups if g["status"] == "confirmed" and not g["can_split"])
    assert done["answer"] and done["answer"]["content"]
    assert (
        client.post(
            f"/api/groups/{done['id']}", headers=lecturer, json={"action": "split"}
        ).status_code
        == 409
    )
    st = client.get("/api/lecturer/stats", headers=lecturer).json()
    assert st["current_week_label"] == f"Tuần {cur['number']}" and st["questions_this_week"] >= 1


def test_notifications_paging(client, lecturer):
    first = client.get("/api/notifications?limit=2", headers=lecturer).json()
    assert len(first["items"]) <= 2 and "has_more" in first
    if first["has_more"]:
        nxt = client.get("/api/notifications?limit=2&offset=2", headers=lecturer).json()
        ids = {n["id"] for n in first["items"]}
        assert nxt["items"] and not ids & {n["id"] for n in nxt["items"]}
        assert nxt["items"][0]["created_at"] <= first["items"][-1]["created_at"]


def test_lecturer_stats_by_semester(client, lecturer):
    base = client.get("/api/lecturer/stats", headers=lecturer).json()
    assert base["semesters"] and base["current_semester_id"]
    cur = client.get(
        f"/api/lecturer/stats?semester_id={base['current_semester_id']}", headers=lecturer
    ).json()
    everything = client.get("/api/lecturer/stats?semester_id=all", headers=lecturer).json()
    assert 0 < cur["class_count"] <= everything["class_count"]
    assert all(c["id"] for c in cur["classes"])
    assert client.get("/api/lecturer/stats?semester_id=abc", headers=lecturer).status_code == 422


def test_admin_overview_by_semester(client, admin):
    ov = client.get("/api/admin/overview", headers=admin).json()
    st = client.get("/api/admin/stats", headers=admin).json()
    # mặc định cả hai trang cùng chọn học kỳ hiện tại
    assert (
        ov["year"] == st["year"]
        and ov["term"] == st["term"]
        and ov["semester_id"] == st["semester_id"]
    )
    assert ov["classes"] == st["total"]["classes"]
    # hai trang dùng chung một cách đếm nên các con số luôn khớp
    for key in ("questions", "answered", "waiting", "answer_rate"):
        assert ov["questions"][key] == st["total"][key], key
    assert ov["range"]["label"] and ov["range"]["from"]
    assert len(ov["trend"]["days"]) == 7 and ov["trend"]["label"]
    assert {"new_waiting", "waiting", "over_48h"} <= set(ov["today"])
    assert ov["today"]["waiting"] == st["total"]["waiting"]
    assert {"by_faculty", "by_day", "heatmap", "keywords", "ai"} <= set(st)
    assert len(st["heatmap"]) == 7 and all(len(r) == 24 for r in st["heatmap"])
    # chọn cả năm học: vẫn khớp với Thống kê
    ov_year = client.get(f"/api/admin/overview?year={ov['year']}", headers=admin).json()
    st_year = client.get(f"/api/admin/stats?year={ov['year']}", headers=admin).json()
    assert ov_year["term"] == "" and ov_year["classes"] == st_year["total"]["classes"]
    # học kỳ chưa khai báo: trống, không lỗi
    empty = client.get("/api/admin/overview?year=2025-2026&term=he", headers=admin).json()
    assert (
        empty["classes"] == 0
        and empty["questions"]["questions"] == 0
        and empty["attention_classes"] == []
        and empty["range"]["from"] is None
    )
    # tham số khoảng ngày cũ không còn tác dụng và không gây lỗi
    assert client.get("/api/admin/overview?date_from=2026-01-01", headers=admin).status_code == 200
