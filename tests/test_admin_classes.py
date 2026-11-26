"""Admin quản lý giảng viên và sinh viên theo lớp học phần."""

from tests.conftest import login


def _ktpm(client, admin):
    return next(
        c for c in client.get("/api/admin/classes", headers=admin).json() if c["code"] == "KTPM_01"
    )


def test_only_admin_can_use_class_management(client, student, lecturer):
    for h in (student, lecturer):
        assert client.get("/api/admin/classes", headers=h).status_code == 403
        assert client.get("/api/admin/classes/1", headers=h).status_code == 403


def test_list_and_detail(client, admin):
    classes = client.get("/api/admin/classes", headers=admin).json()
    assert {"KTPM_01", "HQTCSDL_01"} <= {c["code"] for c in classes}
    k = _ktpm(client, admin)
    assert k["lecturer"]["email"] == "hoaithu@neu.edu.vn" and "join_code" not in k
    sid = k["semester_id"]
    only = client.get(f"/api/admin/classes?semester_id={sid}&q=ktpm", headers=admin).json()
    assert only and all("ktpm" in c["code"].lower() or "ktpm" in c["subject"].lower() for c in only)
    d = client.get(f"/api/admin/classes/{k['id']}", headers=admin).json()
    assert d["student_count"] == len(d["students"]) > 0
    st = d["students"][0]
    assert {"id", "full_name", "email", "is_locked", "joined_at"} <= set(st)
    assert client.get("/api/admin/classes/999999", headers=admin).status_code == 404


def test_add_and_remove_student(client, admin):
    k = _ktpm(client, admin)
    members = {
        s["email"]
        for s in client.get(f"/api/admin/classes/{k['id']}", headers=admin).json()["students"]
    }
    users = client.get("/api/admin/users?role=student", headers=admin).json()
    items = users["items"] if isinstance(users, dict) else users
    outsider = next(u for u in items if u["email"] not in members)
    r = client.post(
        f"/api/admin/classes/{k['id']}/students",
        headers=admin,
        json={"emails": [outsider["email"], "khong.ton.tai@st.neu.edu.vn"]},
    ).json()
    assert r["added"] == [outsider["email"].lower()] and r["not_found"] == [
        "khong.ton.tai@st.neu.edu.vn"
    ]
    again = client.post(
        f"/api/admin/classes/{k['id']}/students",
        headers=admin,
        json={"emails": [outsider["email"]]},
    ).json()
    assert again["already_in_class"] == [outsider["email"].lower()] and not again["added"]
    sv = login(client, outsider["email"])
    assert any(c["code"] == "KTPM_01" for c in client.get("/api/classes", headers=sv).json())
    assert (
        client.delete(
            f"/api/admin/classes/{k['id']}/students/{outsider['id']}", headers=admin
        ).status_code
        == 200
    )
    assert not any(c["code"] == "KTPM_01" for c in client.get("/api/classes", headers=sv).json())
    assert (
        client.delete(
            f"/api/admin/classes/{k['id']}/students/{outsider['id']}", headers=admin
        ).status_code
        == 404
    )
    acts = [a["action"] for a in client.get("/api/admin/audit-logs", headers=admin).json()]
    assert "class.add_students" in acts and "class.remove_student" in acts


def test_change_lecturer(client, admin):
    k = _ktpm(client, admin)
    lec = client.get("/api/admin/lecturers", headers=admin).json()
    other = next(u for u in lec if u["email"] != "hoaithu@neu.edu.vn")
    assert (
        client.patch(
            f"/api/admin/classes/{k['id']}/lecturer",
            headers=admin,
            json={"lecturer_id": k["lecturer"]["id"]},
        ).status_code
        == 409
    )
    r = client.patch(
        f"/api/admin/classes/{k['id']}/lecturer", headers=admin, json={"lecturer_id": other["id"]}
    )
    assert r.status_code == 200 and r.json()["lecturer"]["email"] == other["email"]
    assert (
        client.patch(
            f"/api/admin/classes/{k['id']}/lecturer", headers=admin, json={"lecturer_id": 999999}
        ).status_code
        == 404
    )
    back = client.patch(
        f"/api/admin/classes/{k['id']}/lecturer",
        headers=admin,
        json={"lecturer_id": k["lecturer"]["id"]},
    )
    assert back.status_code == 200 and back.json()["lecturer"]["email"] == "hoaithu@neu.edu.vn"
    acts = [a["action"] for a in client.get("/api/admin/audit-logs", headers=admin).json()]
    assert "class.change_lecturer" in acts
