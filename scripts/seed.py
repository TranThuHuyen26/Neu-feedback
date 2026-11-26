"""Tạo dữ liệu mẫu cho một học kỳ 15 tuần (dùng để demo).

Học kỳ bắt đầu thứ Hai SEMESTER_START (mặc định 03/08/2026). Mỗi lớp có 15 tuần học liền nhau; buổi trùng ngày
lễ 02/09 được học bù vào thứ Bảy cùng tuần. Câu hỏi có ở các tuần đã học và tuần đang học. Có sẵn ví dụ câu
chờ duyệt, nhóm tương đồng và thông báo. Không tạo tài liệu, Giảng viên tự tải lên.

Tài khoản chính: sinh viên 11236004@st.neu.edu.vn / Huyen123, Giảng viên hoaithu@neu.edu.vn / Hoaithu123.

Chạy từ thư mục gốc:
    python -m scripts.seed            # chỉ chạy khi cơ sở dữ liệu còn trống
    python -m scripts.seed --reset    # xóa dữ liệu cũ rồi tạo lại
"""

import random
import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select

from app.config import get_settings
from app.database import Base, SessionLocal
from app.models import (
    Semester,
    Answer,
    AuditLog,
    ClassSession,
    Classroom,
    Enrollment,
    Flag,
    Notification,
    Question,
    QuestionAttachment,
    QuestionAuthor,
    SimilarGroup,
    User,
)
from app.security import hash_password
from app.services import ai
from app.services.core import semester_label, layout_weeks, monday_of, week_status
from app.utils import plain_text, VN_TZ, question_code, utcnow, vn_date
from app.services.files import to_stored

settings = get_settings()
PASSWORD = "Neu@12345"
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]
HOLIDAY = date(2026, 9, 2)  # Quốc khánh: buổi học trùng ngày này được học bù vào thứ Bảy cùng tuần

# ---------------------------------------------------------------- câu hỏi tuần đang học của KTPM_01
LIVE_QUESTIONS = [  # (số hiệu, phút sau khi bắt đầu buổi học, trạng thái, nhóm, nội dung, câu trả lời)
    (
        101,
        8,
        "answered",
        None,
        "Performance testing gồm những loại nào?",
        "Gồm load, stress, spike, endurance (soak) và volume testing.",
    ),
    (102, 15, "waiting", "G_A", "Stress Test khác Load Test như thế nào?", None),
    (
        103,
        21,
        "answered",
        None,
        "Response time bao nhiêu là chấp nhận được?",
        "Tùy yêu cầu nghiệp vụ; thường đặt mục tiêu dưới 2 giây cho thao tác thông thường và ghi rõ trong tiêu chí chấp nhận.",
    ),
    (105, 32, "waiting", "G_A", "Khi nào nên dùng Stress Test thay vì Load Test?", None),
    (
        106,
        36,
        "answered",
        None,
        "Thread Group trong JMeter là gì?",
        "Là nhóm người dùng ảo: số thread, ramp-up và số vòng lặp quyết định mức tải.",
    ),
    (
        108,
        45,
        "answered",
        "G_B",
        "Làm thế nào để mô phỏng 500 user trong JMeter?",
        "Tạo Thread Group 500 threads, đặt ramp-up hợp lý và chạy chế độ non-GUI; nếu máy yếu thì dùng distributed testing.",
    ),
    (
        109,
        47,
        "answered",
        None,
        "Nên đặt Ramp-up period bao nhiêu?",
        "Chọn theo tốc độ tăng tải mong muốn, ví dụ 500 user trong 100 giây là tăng 5 user mỗi giây.",
    ),
    (
        111,
        50,
        "answered",
        "G_B",
        "Muốn giả lập 500 người dùng cùng lúc thì cấu hình JMeter ra sao?",
        "Tạo Thread Group 500 threads, đặt ramp-up hợp lý và chạy chế độ non-GUI; nếu máy yếu thì dùng distributed testing.",
    ),
    (
        113,
        53,
        "answered",
        None,
        "Listener nào dùng để xem kết quả tổng hợp?",
        "Dùng Summary Report hoặc Aggregate Report; khi chạy thật nên xuất file .jtl rồi tạo HTML report.",
    ),
    (
        115,
        55,
        "answered",
        None,
        "Có cần chạy test trên máy riêng không?",
        "Nên chạy trên máy hoặc agent riêng để máy tạo tải không làm sai lệch kết quả.",
    ),
    (118, 58, "waiting", None, "Có cần chạy 500 users cho mọi kịch bản không?", None),
    (120, 62, "flagged", None, "Giảng viên giảng kiểu này thì ai mà hiểu nổi, học chán quá.", None),
]

# ---------------------------------------------------------------- nội dung các lớp
KTPM_TOPICS = [
    "Chương 1: Tổng quan về kiểm thử và đảm bảo chất lượng phần mềm",
    "Chương 2: Kiểm thử hộp trắng và hộp đen",
    "Chương 2: Phân lớp tương đương và phân tích giá trị biên",
    "Chương 2: Bảng quyết định và đồ thị nhân quả",
    "Chương 3: Thiết kế và đặc tả test case",
    "Chương 3: Quy trình và kế hoạch kiểm thử",
    "Chương 4: Kiểm thử API",
    "Chương 4: Kiểm thử tự động với Selenium",
    "Chương 5: Kiểm thử hiệu năng",
    "Chương 5: Kiểm thử bảo mật",
    "Chương 6: Kiểm thử đơn vị",
    "Chương 6: Kiểm thử tích hợp và kiểm thử hệ thống",
    "Chương 7: Kiểm thử chấp nhận",
    "Chương 7: Quản lý lỗi và báo cáo kiểm thử",
    "Ôn tập và tổng kết",
]
KTPM_Q = [
    "Selenium chờ phần tử thế nào cho ổn định?",
    "Có nên viết test cho mọi hàm không?",
    "Phân lớp tương đương khác phân tích giá trị biên thế nào?",
    "Test case cần những trường thông tin gì?",
    "Kiểm thử hồi quy nên làm khi nào?",
    "Độ bao phủ mã bao nhiêu là đủ ạ?",
    "Mock khác stub ở điểm nào?",
    "Bảng quyết định có bao nhiêu cột là đủ?",
]
QLDA_TOPICS = [
    "Chương 1: Tổng quan về quản lý dự án",
    "Chương 2: Khởi tạo dự án và bản điều lệ dự án",
    "Chương 3: Quản lý phạm vi dự án",
    "Chương 3: Cấu trúc phân rã công việc (WBS)",
    "Chương 4: Lập lịch và quản lý tiến độ",
    "Chương 4: Sơ đồ mạng và đường găng",
    "Chương 5: Ước lượng và quản lý chi phí",
    "Chương 6: Quản lý chất lượng dự án",
    "Chương 7: Quản lý rủi ro",
    "Chương 8: Quản lý nguồn nhân lực dự án",
    "Chương 8: Quản lý truyền thông và các bên liên quan",
    "Chương 9: Agile và Scrum",
    "Chương 9: Theo dõi và kiểm soát dự án",
    "Chương 10: Kết thúc dự án",
    "Ôn tập và tổng kết",
]
QLDA_Q = [
    "WBS nên chia nhỏ đến mức nào ạ?",
    "Đường găng xác định như thế nào?",
    "Ước lượng chi phí theo phương pháp nào chính xác hơn?",
    "Rủi ro và vấn đề khác nhau thế nào?",
    "Scrum Master khác Project Manager ra sao?",
    "Khi nào nên dùng Agile thay vì Waterfall?",
    "Earned Value tính như thế nào?",
    "Bản điều lệ dự án gồm những nội dung gì?",
]
LTUD_TOPICS = [
    "Chương 1: Tổng quan về lập trình ứng dụng",
    "Chương 2: Lập trình hướng đối tượng nâng cao",
    "Chương 2: Kế thừa, đa hình và interface",
    "Chương 3: Thiết kế giao diện người dùng",
    "Chương 3: Xử lý sự kiện",
    "Chương 4: Các điều khiển và bố cục giao diện",
    "Chương 5: Kết nối cơ sở dữ liệu",
    "Chương 5: Thao tác dữ liệu (thêm, sửa, xóa, tìm kiếm)",
    "Chương 6: Xử lý ngoại lệ",
    "Chương 6: Làm việc với tệp",
    "Chương 7: Mô hình MVC",
    "Chương 7: Đa luồng trong ứng dụng",
    "Chương 8: Kiểm thử và gỡ lỗi ứng dụng",
    "Chương 8: Đóng gói và triển khai ứng dụng",
    "Ôn tập và tổng kết",
]
LTUD_Q = [
    "Interface khác abstract class ở điểm nào ạ?",
    "Làm sao tách giao diện và xử lý nghiệp vụ theo MVC?",
    "Kết nối cơ sở dữ liệu nên mở và đóng ở đâu?",
    "Tại sao giao diện bị treo khi xử lý lâu?",
    "Nên bắt ngoại lệ ở tầng nào?",
    "Data binding hoạt động thế nào?",
    "Đọc ghi tệp cấu hình như thế nào ạ?",
    "Đóng gói ứng dụng ra tệp chạy thế nào?",
]
HQT_TOPICS = [
    "Chương 1: Tổng quan về hệ quản trị cơ sở dữ liệu",
    "Chương 2: SQL nâng cao: truy vấn lồng và phép kết nối",
    "Chương 2: Hàm gộp, GROUP BY và HAVING",
    "Chương 3: View",
    "Chương 4: Chỉ mục và tối ưu truy vấn",
    "Chương 5: Thủ tục lưu trữ",
    "Chương 5: Hàm người dùng",
    "Chương 6: Trigger",
    "Chương 7: Giao dịch và điều khiển đồng thời",
    "Chương 7: Khóa và deadlock",
    "Chương 8: Phân quyền và bảo mật",
    "Chương 9: Sao lưu và phục hồi dữ liệu",
    "Chương 10: Tối ưu hiệu năng cơ sở dữ liệu",
    "Chương 10: Cơ sở dữ liệu phân tán",
    "Ôn tập và tổng kết",
]
HQT_Q = [
    "Khi nào nên tạo chỉ mục composite?",
    "Isolation level nào hay dùng?",
    "Deadlock xảy ra khi nào?",
    "Đọc kết quả EXPLAIN ra sao?",
    "Có nên dùng trigger không?",
    "Stored procedure khác function thế nào?",
    "View có cập nhật dữ liệu được không ạ?",
    "Sao lưu full và differential khác nhau thế nào?",
]

# 15 sinh viên (cùng khóa 65): (họ tên, mã SV, lớp hành chính)
STUDENTS = [
    ("Trần Thị Thu Hà", "11235996", "KHMT65"),
    ("Bùi Thúy Liên", "11236011", "KHMT65"),
    ("Trương Lê Ly", "11236016", "KHMT65"),
    ("Đỗ Thị Dịu", "11235987", "KHMT65"),
    ("Nguyễn Minh Đức", "11236102", "CNTT65A"),
    ("Phạm Thu Trang", "11236118", "CNTT65A"),
    ("Lê Quang Huy", "11236125", "CNTT65A"),
    ("Đỗ Hà My", "11236194", "CNTT65A"),
    ("Vũ Ngọc Anh", "11236137", "CNTT65B"),
    ("Đặng Hải Nam", "11236149", "CNTT65B"),
    ("Trịnh Văn Khánh", "11236181", "CNTT65B"),
    ("Hoàng Thị Mai", "11236153", "HTTT65A"),
    ("Ngô Đức Long", "11236166", "HTTT65A"),
    ("Bùi Phương Thảo", "11236178", "HTTT65A"),
]
# chỉ số trong danh sách students (0 = Trần Thu Huyền): mỗi lớp 11–12 sinh viên, mỗi sinh viên học 3 lớp
ROSTER = {
    "KTPM_01": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "QLDA_01": [1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 14],
    "LTUD_01": [0, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    "HQTCSDL_01": [0, 1, 2, 3, 5, 6, 7, 8, 12, 13, 14],
}


def reset(db):
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(delete(table))
    db.commit()


def vn(d: date, hour: int, minute: int = 0) -> datetime:
    """Giờ Việt Nam hour:minute của ngày d, đổi ra UTC để lưu CSDL."""
    return datetime.combine(d, time(hour, minute), VN_TZ).astimezone(utcnow().tzinfo)


def user(db, email, name, role, faculty=None, admin_class=None, pw=PASSWORD):
    u = User(
        email=email,
        full_name=name,
        role=role,
        faculty=faculty,
        admin_class=admin_class,
        password_hash=hash_password(pw),
    )
    db.add(u)
    return u


def _sample_png(w: int = 360, h: int = 200) -> bytes:
    """Ảnh PNG đơn giản (nền xanh nhạt, 3 cột biểu đồ) — không cần thư viện ảnh."""
    import struct
    import zlib

    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            bar = next(
                (
                    c
                    for i, c in enumerate([(47, 127, 168), (46, 139, 110), (183, 112, 58)])
                    if 60 + i * 100 <= x < 120 + i * 100 and y >= h - 40 - (i + 1) * 40
                ),
                None,
            )
            row += bytes(bar or (228, 241, 250))
        rows.append(bytes(row))

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


def add_question(
    db,
    week,
    class_id,
    content,
    created,
    status,
    author_id,
    lecturer_id=None,
    answer=None,
    *,
    via_group=False,
    source_question_id=None,
    source_answer_id=None,
    group_id=None,
    embedding=None,
    attachment=None,
    now=None,
):
    q = Question(
        session_id=week.id,
        class_id=class_id,
        seq=0,
        content=content,
        status=status,
        created_at=created,
        group_id=group_id,
        embedding=embedding,
    )
    if attachment:  # tệp đính kèm mẫu (ảnh PNG thật để xem được)
        folder = settings.upload_dir / "questions"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"seed_{attachment}"
        data = _sample_png()
        path.write_bytes(data)
        q.attachments.append(
            QuestionAttachment(
                filename=attachment,
                stored_path=to_stored(path),
                file_type="IMG",
                size_bytes=len(data),
                created_at=created,
            )
        )
    if answer:
        q.answered_at = min(
            created + timedelta(minutes=random.randint(2, 9)),
            (now or utcnow()) - timedelta(minutes=1),
        )
    db.add(q)
    db.flush()
    db.add(QuestionAuthor(question_id=q.id, student_id=author_id))
    if answer:
        db.add(
            Answer(
                question_id=q.id,
                lecturer_id=lecturer_id,
                content=answer,
                via_group=via_group,
                source_question_id=source_question_id,
                source_answer_id=source_answer_id,
                created_at=q.answered_at,
            )
        )
    return q


def main():
    random.seed(2026)
    db = SessionLocal()
    if "--reset" in sys.argv:
        reset(db)
    elif db.scalar(select(func.count()).select_from(User)):
        print("CSDL đã có dữ liệu. Chạy lại với --reset nếu muốn xóa và tạo lại.")
        return
    now = utcnow()
    now_vn = now.astimezone(VN_TZ)
    today = now_vn.date()
    # Nếu học kỳ cấu hình đã kết thúc (hoặc chưa bắt đầu) thì lùi về 7 tuần trước để luôn có
    # tuần đang học và tuần sắp tới phục vụ demo và kiểm thử.
    configured = settings.semester_start
    in_session = configured <= today < configured + timedelta(weeks=14)
    sem_start = monday_of(configured if in_session else today - timedelta(weeks=7))

    ktpm_slot = (7, 30)  # KTPM_01: thứ Hai 07:30, buổi đầu tiên 03/08

    # ---------------- tài khoản (tạo trước học kỳ ~2 tuần)
    admin = user(db, "admin@neu.edu.vn", "Admin NEU", "admin", pw="Admin@12345")
    thu = user(db, "hoaithu@neu.edu.vn", "Trần Thị Hoài Thu", "lecturer", "CNTT", pw="Hoaithu123")
    ngoc = user(db, "minhngoc@neu.edu.vn", "Tống Thị Minh Ngọc", "lecturer", "CNTT")
    huyen = user(
        db, "11236004@st.neu.edu.vn", "Trần Thu Huyền", "student", "CNTT", "KHMT65", pw="Huyen123"
    )
    students = [huyen] + [
        user(db, f"{msv}@st.neu.edu.vn", n, "student", "CNTT", ac) for n, msv, ac in STUDENTS
    ]
    db.flush()
    admin.created_at = vn(date(2026, 7, 1), 9)  # hệ thống đưa vào sử dụng
    thu.created_at = vn(date(2026, 7, 6), 9, 15)  # Admin tạo tài khoản Giảng viên
    ngoc.created_at = vn(date(2026, 7, 6), 9, 17)
    for k, u in enumerate(students):  # Admin nhập danh sách sinh viên từ Excel
        u.created_at = vn(date(2026, 7, 8), 10) + timedelta(seconds=k * 2)
    # học kỳ Thu năm học 2026-2027
    sem = Semester(
        year=f"{sem_start.year}-{sem_start.year + 1}",
        term="thu",
        start_date=sem_start,
        created_at=vn(sem_start - timedelta(days=30), 9),
    )
    db.add(sem)
    db.flush()
    R = {code: [students[i] for i in idx] for code, idx in ROSTER.items()}

    # ---------------- lớp học: (mã, môn, GV, mã tham gia, khoa, thứ lên lớp, (giờ, phút), phút, chủ đề, câu hỏi, SV)
    plans = [
        (
            "KTPM_01",
            "Kiểm thử phần mềm",
            thu,
            "KTPM-X31M",
            "CNTT",
            0,
            ktpm_slot,
            180,
            KTPM_TOPICS,
            KTPM_Q,
            R["KTPM_01"],
        ),
        (
            "QLDA_01",
            "Quản lý dự án",
            thu,
            "QLDA-7K4P",
            "CNTT",
            1,
            (7, 0),
            150,
            QLDA_TOPICS,
            QLDA_Q,
            R["QLDA_01"],
        ),
        (
            "LTUD_01",
            "Lập trình ứng dụng",
            ngoc,
            "LTUD-2H9D",
            "CNTT",
            2,
            (15, 0),
            150,
            LTUD_TOPICS,
            LTUD_Q,
            R["LTUD_01"],
        ),
        (
            "HQTCSDL_01",
            "Hệ quản trị cơ sở dữ liệu",
            ngoc,
            "HQTC-4M7T",
            "CNTT",
            4,
            (9, 30),
            120,
            HQT_TOPICS,
            HQT_Q,
            R["HQTCSDL_01"],
        ),
    ]

    # lịch cố định thứ Hai → thứ Bảy theo lịch trường; buổi đầu tiên của mỗi lớp nằm trong tuần 03/08 – 08/08.
    # Kiểm tra: một sinh viên không có hai lớp chồng giờ.
    def overlap(a, b):
        s1, s2 = a[6][0] * 60 + a[6][1], b[6][0] * 60 + b[6][1]
        return a[5] == b[5] and s1 < s2 + b[7] and s2 < s1 + a[7]

    for a in plans:
        for b in plans:
            if a is not b and set(a[10]) & set(b[10]):
                assert not overlap(a, b), f"Trùng lịch {a[0]} / {b[0]}"

    weeks_of, classes = {}, {}
    for (
        code,
        subject,
        lecturer,
        join,
        fac,
        weekday,
        (h, m),
        minutes,
        topics,
        bank,
        members,
    ) in plans:
        c = Classroom(
            code=code,
            subject=subject,
            semester=semester_label(sem),
            semester_id=sem.id,
            course_type="regular",
            faculty=fac,
            lecturer_id=lecturer.id,
            join_code=join,
            start_date=sem_start,
            created_at=vn(sem_start - timedelta(days=random.randint(7, 9)), random.randint(8, 17)),
        )
        db.add(c)
        db.flush()
        classes[code] = c
        for st in members:
            db.add(
                Enrollment(
                    class_id=c.id,
                    student_id=st.id,
                    joined_at=vn(
                        sem_start - timedelta(days=random.randint(1, 6)),
                        random.randint(7, 22),
                        random.randint(0, 59),
                    ),
                )
            )
        db.flush()
        db.refresh(c)
        weeks = layout_weeks(db, c)
        weeks_of[code] = weeks
        current_no = next((w.number for w in weeks if week_status(w, today) == "current"), None)
        filled_to = 15  # mọi lớp đều có đủ nội dung 15 tuần
        for w in weeks:
            if w.number <= filled_to:
                w.title = topics[min(w.number - 1, len(topics) - 1)]
                w.description = (
                    f"Mục tiêu: nắm được nội dung “{w.title}”. Sinh viên đọc trước tài liệu tuần, "
                    "làm bài tập nhỏ trên lớp và gửi câu hỏi ẩn danh nếu chưa rõ."
                )
            st = week_status(w, today)
            if st == "upcoming" or (code == "KTPM_01" and st == "current"):
                continue  # tuần đang học của KTPM_01 có bộ câu hỏi riêng bên dưới
            class_day = vn_date(w.starts_at) + timedelta(days=weekday)
            if class_day == HOLIDAY:  # trùng ngày lễ → học bù thứ Bảy cùng tuần
                class_day = vn_date(w.starts_at) + timedelta(days=5)
            lesson_start = vn(class_day, h, m)
            if lesson_start >= now:  # tuần đang học nhưng chưa tới buổi lên lớp
                continue
            total = random.randint(9, 22) if code == "KTPM_01" else random.randint(4, 13)
            rate = random.uniform(0.78, 1.0)
            week_end = min(w.ends_at, now)
            times = []
            for _ in range(total):
                if random.random() < 0.8:  # phần lớn gửi trong giờ học
                    t = lesson_start + timedelta(
                        minutes=random.randint(3, minutes - 5), seconds=random.randint(0, 59)
                    )
                else:  # một số gửi sau buổi học, trong tuần
                    t = lesson_start + timedelta(minutes=minutes, hours=random.randint(2, 48))
                    if (
                        t.astimezone(VN_TZ).weekday() == 6
                    ):  # không để câu hỏi rơi vào Chủ nhật → tối thứ Bảy
                        t = vn(
                            t.astimezone(VN_TZ).date() - timedelta(days=1),
                            20,
                            random.randint(0, 59),
                        )
                if t < week_end:
                    times.append(t)
            for t in sorted(times):
                ok = random.random() < rate
                add_question(
                    db,
                    w,
                    c.id,
                    random.choice(bank),
                    t,
                    "answered" if ok else "waiting",
                    random.choice(members).id,
                    lecturer.id,
                    (
                        "Nội dung này đã được giải thích trong buổi học, em xem lại tài liệu tuần nhé."
                        if ok
                        else None
                    ),
                    now=now,
                )

    # ---------------- KTPM_01: ví dụ nhóm tương đồng đã xác nhận ở tuần trước + trả lời tự động ở tuần này
    k = classes["KTPM_01"]
    kweeks = weeks_of["KTPM_01"]
    current = next((w for w in kweeks if week_status(w, today) == "current"), None)
    done = [w for w in kweeks if week_status(w, today) == "done"]
    n_group = 0

    def new_group(week, status, score, answer=None, source=None):
        nonlocal n_group
        n_group += 1
        g = SimilarGroup(
            class_id=k.id,
            session_id=week.id,
            label=f"SIM-{n_group:02d}",
            status=status,
            score=score,
            answer_text=answer,
            answered_by=thu.id if answer else None,
            source_question_id=source,
        )
        db.add(g)
        db.flush()
        return g

    postman_answer = (
        "Postman chủ yếu để kiểm thử chức năng API. Muốn đo hiệu năng (nhiều người dùng đồng thời) em nên dùng "
        "JMeter hoặc k6; Postman chỉ chạy lặp tuần tự nên không mô phỏng được tải thật."
    )
    g_postman, q_src = None, None
    if done:
        w_api = next((w for w in done if "Kiểm thử API" in w.title), done[-1])
        t0 = vn(vn_date(w_api.starts_at) + timedelta(days=plans[0][5]), *ktpm_slot) + timedelta(
            minutes=35
        )
        vecs = ai.embed(
            [
                "Postman có kiểm thử hiệu năng được không?",
                "Postman có dùng để kiểm thử hiệu năng được không ạ?",
            ]
        )
        q_src = add_question(
            db,
            w_api,
            k.id,
            "Postman có kiểm thử hiệu năng được không?",
            t0,
            "answered",
            random.choice(R["KTPM_01"][1:]).id,
            thu.id,
            postman_answer,
            embedding=vecs[0],
            now=now,
        )
        g_postman = new_group(w_api, "confirmed", 0.94, postman_answer)
        db.flush()
        src_ans = db.scalar(select(Answer).where(Answer.question_id == q_src.id))
        q2 = add_question(
            db,
            w_api,
            k.id,
            "Postman có dùng để kiểm thử hiệu năng được không ạ?",
            t0 + timedelta(minutes=9),
            "answered",
            random.choice(R["KTPM_01"][1:]).id,
            thu.id,
            postman_answer,
            via_group=True,
            source_question_id=q_src.id,
            source_answer_id=src_ans.id,
            embedding=vecs[1],
            group_id=g_postman.id,
            now=now,
        )
        q_src.group_id = g_postman.id
        g_postman.source_question_id = q_src.id
        w_auto = next((w for w in done if "Kiểm thử tự động" in w.title), done[-1])
        # Huyền hỏi ở một tuần đã học
        t1 = vn(vn_date(w_auto.starts_at) + timedelta(days=plans[0][5]), *ktpm_slot) + timedelta(
            minutes=26
        )
        q_sel = add_question(
            db,
            w_auto,
            k.id,
            "Selenium có dùng được cho ứng dụng mobile không?",
            t1,
            "answered",
            huyen.id,
            thu.id,
            "Selenium chủ yếu dành cho web. Với ứng dụng mobile, em dùng Appium — cùng giao thức WebDriver nên cách viết script khá giống.",
            now=now,
        )

    lesson = (
        vn(vn_date(current.starts_at) + timedelta(days=plans[0][5]), *ktpm_slot)
        if current
        else None
    )
    if current and lesson + timedelta(minutes=60) <= now:  # buổi lên lớp tuần này đã diễn ra
        groups = {
            "G_A": new_group(current, "suggested", 0.91),
            "G_B": new_group(current, "confirmed", 0.88, LIVE_QUESTIONS[5][5]),
        }
        vectors = ai.embed([x[4] for x in LIVE_QUESTIONS])
        for (code, minute, st, g, text, ans), vec in zip(LIVE_QUESTIONS, vectors):
            t = lesson + timedelta(
                minutes=round(minute * 150 / 62), seconds=random.randint(0, 50)
            )  # rải trong giờ học
            author = huyen if code in (102, 103) else random.choice(R["KTPM_01"][1:])
            q = add_question(
                db,
                current,
                k.id,
                text,
                t,
                st,
                author.id,
                thu.id,
                ans,
                via_group=bool(g and ans),
                group_id=groups[g].id if g else None,
                embedding=vec,
                attachment="ketqua_jmeter.png" if code == 102 else None,
                now=now,
            )
            if code == 108:
                groups["G_B"].source_question_id = q.id
            if st == "flagged":
                db.add(
                    Flag(
                        question_id=q.id,
                        flagged_by=thu.id,
                        reason="Ngôn từ thiếu tôn trọng",
                        ai_score=78,
                        created_at=t + timedelta(minutes=2),
                    )
                )
        db.flush()
        by_code = {
            q.content: q
            for q in db.scalars(select(Question).where(Question.session_id == current.id)).all()
        }
        a108 = db.scalar(
            select(Answer)
            .join(Question, Question.id == Answer.question_id)
            .where(Question.session_id == current.id, Question.content == LIVE_QUESTIONS[5][4])
        )
        a111 = db.scalar(
            select(Answer)
            .join(Question, Question.id == Answer.question_id)
            .where(Question.session_id == current.id, Question.content == LIVE_QUESTIONS[7][4])
        )
        if a108 and a111:  # SIM: trả lời chung → câu sau là bản sao của câu trả lời gốc
            a111.source_answer_id, a111.source_question_id, a111.via_group = (
                a108.id,
                a108.question_id,
                True,
            )
            a108.via_group = True
        # câu hỏi giống câu đã trả lời → CHỜ Giảng viên duyệt (chưa gửi gì cho sinh viên)
        reviews = []
        if g_postman is not None:
            text = "Có thể dùng Postman để kiểm thử hiệu năng không ạ?"
            reviews.append(
                add_question(
                    db,
                    current,
                    k.id,
                    text,
                    lesson + timedelta(minutes=152),
                    "waiting",
                    huyen.id,
                    embedding=ai.embed([text])[0],
                    now=now,
                )
            )
            reviews[-1].reuse_from_id, reviews[-1].reuse_score = q_src.id, 0.93
        a103q = by_code.get(LIVE_QUESTIONS[2][4])
        if a103q is not None:
            text = "Thời gian phản hồi bao nhiêu thì đạt yêu cầu ạ?"
            reviews.append(
                add_question(
                    db,
                    current,
                    k.id,
                    text,
                    lesson + timedelta(minutes=155),
                    "waiting",
                    random.choice(R["KTPM_01"][1:]).id,
                    embedding=ai.embed([text])[0],
                    now=now,
                )
            )
            reviews[-1].reuse_from_id, reviews[-1].reuse_score = a103q.id, 0.9
    # ---------------- nội dung gắn cờ khác (tuần đã học gần nhất của lớp) cho hàng đợi Admin
    for code, lecturer, text, reason, score in [
        ("QLDA_01", thu, "Bán tài liệu ôn thi giá rẻ, liên hệ Zalo 09xx…", "Quảng cáo / spam", 92),
        ("LTUD_01", ngoc, "Số điện thoại của bạn Nam trong nhóm là 09…", "Thông tin cá nhân", 70),
        ("HQTCSDL_01", ngoc, "Tối nay có ai đi xem bóng đá không?", "Lạc đề", 41),
    ]:
        past = [w for w in weeks_of[code] if week_status(w, today) == "done"]
        if not past:
            continue
        w = past[-1]
        p = next(x for x in plans if x[0] == code)
        members = db.scalars(
            select(Enrollment.student_id).where(Enrollment.class_id == w.class_id)
        ).all()
        t = vn(vn_date(w.starts_at) + timedelta(days=p[5]), *p[6]) + timedelta(minutes=40)
        q = add_question(db, w, w.class_id, text, t, "flagged", random.choice(members), now=now)
        db.add(
            Flag(
                question_id=q.id,
                flagged_by=lecturer.id,
                reason=reason,
                ai_score=score,
                created_at=t + timedelta(minutes=3),
            )
        )

    # ---------------- số thứ tự câu hỏi trong từng tuần theo đúng thời gian gửi (tuần đang học KTPM_01 giữ mã A1xx)
    db.flush()
    for code, ws in weeks_of.items():
        for w in ws:
            qs = db.scalars(
                select(Question)
                .where(Question.session_id == w.id)
                .order_by(Question.created_at, Question.id)
            ).all()
            if code == "KTPM_01" and w is current:
                for q in qs:
                    if q.seq == 0:
                        q.seq = max(x.seq for x in qs) + 1
                continue
            for i, q in enumerate(qs, start=1):
                q.seq = i
    if current:
        live = {x[4]: x[0] - 100 for x in LIVE_QUESTIONS}
        for q in db.scalars(select(Question).where(Question.session_id == current.id)).all():
            if q.content in live:
                q.seq = live[q.content]
        extra = [
            q
            for q in db.scalars(select(Question).where(Question.session_id == current.id)).all()
            if q.content not in live
        ]
        for i, q in enumerate(extra, start=21):
            q.seq = i

    # ---------------- thông báo mẫu (để chuông có nội dung khi demo)
    if current and lesson is not None and lesson + timedelta(minutes=60) <= now:
        lbl, base = f"KTPM_01 · Tuần {current.number}", lesson + timedelta(minutes=160)
        waiting = (
            db.scalar(
                select(func.count())
                .select_from(Question)
                .where(Question.session_id == current.id, Question.status == "waiting")
            )
            or 0
        )
        for key, title, body, link, cnt, mins in [
            (
                f"newq:{k.id}:{current.id}",
                f"{lbl}: {waiting} câu hỏi mới đang chờ trả lời",
                "Bấm để xem và trả lời",
                f"lecturer-week.html?week={current.id}",
                waiting,
                0,
            ),
            (
                f"group:{k.id}:{current.id}",
                f"{lbl}: NEU AI đề xuất nhóm câu hỏi tương đồng — cần xác nhận",
                "1 nhóm đang chờ xác nhận",
                f"lecturer-week.html?week={current.id}&groups=1",
                1,
                2,
            ),
            (
                f"review:{k.id}:{current.id}",
                f"{lbl}: 2 câu hỏi mới giống câu đã trả lời, chờ duyệt",
                "Duyệt để gửi lại câu trả lời trước, hoặc trả lời riêng",
                f"lecturer-week.html?week={current.id}&filter=review",
                2,
                4,
            ),
        ]:
            db.add(
                Notification(
                    user_id=thu.id,
                    key=key,
                    title=title,
                    body=body,
                    link=link,
                    count=cnt,
                    created_at=min(base + timedelta(minutes=mins), now - timedelta(minutes=5)),
                )
            )
        db.add(
            Notification(
                user_id=huyen.id,
                title="Giảng viên đã trả lời câu hỏi A103",
                body=LIVE_QUESTIONS[2][4],
                link=f"student-week.html?week={current.id}&tab=mine",
                is_read=True,
                created_at=min(lesson + timedelta(minutes=60), now - timedelta(minutes=30)),
            )
        )
    # ---------------- thông báo cũ của các tuần đã học (để khung thông báo đủ dài, cuộn được — như dùng thật)
    db.flush()
    cur_ids = {w.id for ws in weeks_of.values() for w in ws if week_status(w, today) == "current"}
    for cls in db.scalars(select(Classroom)).all():
        rows = db.execute(
            select(
                ClassSession.id,
                ClassSession.number,
                func.count(Question.id),
                func.min(Question.created_at),
            )
            .join(Question, Question.session_id == ClassSession.id)
            .where(ClassSession.class_id == cls.id)
            .group_by(ClassSession.id, ClassSession.number)
        ).all()
        for wid, num, cnt, first in rows:
            if wid in cur_ids or not first:
                continue
            db.add(
                Notification(
                    user_id=cls.lecturer_id,
                    key=f"newq:{cls.id}:{wid}",
                    count=cnt,
                    is_read=True,
                    title=f"{cls.code} · Tuần {num}: {cnt} câu hỏi mới đang chờ trả lời",
                    body="Bấm để xem và trả lời",
                    link=f"lecturer-week.html?week={wid}",
                    created_at=first + timedelta(hours=2),
                )
            )
    for sid, qid, seq, content, sess, ans_at in db.execute(
        select(
            QuestionAuthor.student_id,
            Question.id,
            Question.seq,
            Question.content,
            Question.session_id,
            Question.answered_at,
        )
        .join(Question, Question.id == QuestionAuthor.question_id)
        .where(Question.status == "answered", Question.answered_at.is_not(None))
    ).all():
        if sess in cur_ids:
            continue
        db.add(
            Notification(
                user_id=sid,
                title=f"Giảng viên đã trả lời câu hỏi {question_code(seq)}",
                body=plain_text(content)[:120],
                is_read=True,
                link=f"student-week.html?week={sess}&tab=mine",
                created_at=ans_at,
            )
        )

    db.flush()
    for sid, last in db.execute(
        select(QuestionAuthor.student_id, func.max(Question.created_at))
        .join(Question, Question.id == QuestionAuthor.question_id)
        .group_by(QuestionAuthor.student_id)
    ).all():
        db.get(User, sid).last_active_at = last
    for lid, last in db.execute(
        select(Answer.lecturer_id, func.max(Answer.created_at))
        .where(Answer.source_answer_id.is_(None))
        .group_by(Answer.lecturer_id)
    ).all():
        db.get(User, lid).last_active_at = last
    admin.last_active_at = now - timedelta(minutes=40)

    # ---------------- thông báo cho Admin: nội dung bị gắn cờ đang chờ kiểm duyệt
    db.flush()
    pend = db.scalar(select(func.count()).select_from(Flag).where(Flag.status == "pending")) or 0
    if pend:
        last_flag = db.scalar(select(func.max(Flag.created_at)))
        db.add(
            Notification(
                user_id=admin.id,
                key="flags",
                count=pend,
                title=f"Có {pend} nội dung bị gắn cờ, chờ kiểm duyệt",
                body="Bấm để mở hàng đợi kiểm duyệt",
                link="admin-reports.html",
                created_at=last_flag or now,
            )
        )

    # vài dòng nhật ký để trang Tổng quan của admin có hoạt động gần đây
    for hours_ago, action, target in [
        (30, "create_user", "11236010@st.neu.edu.vn"),
        (26, "import_users", "15 tài khoản"),
        (20, "flag_dismissed", "A101"),
        (9, "flag_hidden", "A099"),
        (3, "unlock_user", "11236012@st.neu.edu.vn"),
    ]:
        db.add(
            AuditLog(
                actor_id=admin.id,
                action=action,
                target=target,
                created_at=utcnow() - timedelta(hours=hours_ago),
            )
        )
    db.commit()
    print(
        "Đã tạo dữ liệu mẫu: "
        + semester_label(sem)
        + " (năm học "
        + sem.year
        + "), bắt đầu "
        + sem_start.strftime("%d/%m/%Y")
    )
    print("  4 lớp · 15 tuần liền mạch · 15 sinh viên (mỗi bạn học 3 lớp)")
    for code, _, lect, join, _, weekday, (h, m), minutes, *_ in plans:
        ws = weeks_of[code]
        cur = next((w.number for w in ws if week_status(w, today) == "current"), None)
        print(
            f"    {code:<11} {THU[weekday]:<8} {h:02d}:{m:02d} · {lect.full_name:<20} · mã tham gia {join} · "
            + (f"đang học tuần {cur}/15" if cur else "chưa học")
        )
    print("  Admin:      admin@neu.edu.vn / Admin@12345")
    print("  Giảng viên: hoaithu@neu.edu.vn / Hoaithu123   ·   minhngoc@neu.edu.vn / " + PASSWORD)
    print(
        "  Sinh viên:  11236004@st.neu.edu.vn / Huyen123   ·   các bạn khác: <mã SV>@st.neu.edu.vn / "
        + PASSWORD
    )


if __name__ == "__main__":
    main()
