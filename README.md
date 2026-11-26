# NEU Feedback

Hệ thống phản hồi ẩn danh cho lớp học, có tích hợp AI. Đây là đồ án tốt nghiệp của Trần Thu Huyền, Trường Đại học Kinh tế Quốc dân, do TS. Tống Thị Hảo Tâm hướng dẫn.

Sinh viên đặt câu hỏi ẩn danh theo từng tuần học, Giảng viên trả lời, quản trị viên theo dõi số liệu. Hệ thống gom các câu hỏi giống nhau và có trợ lý NEU AI trả lời dựa trên tài liệu của lớp.

## Yêu cầu

- Python 3.11 trở lên
- PostgreSQL (cài trên máy hoặc dùng dịch vụ trên mạng như Supabase)
- Khóa API của Google Gemini (không bắt buộc, không có thì NEU AI chạy chế độ demo)

## Cài đặt

1. Tạo một cơ sở dữ liệu trống tên `neu_feedback` trong PostgreSQL.
2. Cài thư viện và tạo file cấu hình:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

3. Mở `.env`, sửa `DATABASE_URL` cho đúng mật khẩu PostgreSQL, ví dụ:

```
DATABASE_URL=postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/neu_feedback
```

4. Tạo bảng và nạp dữ liệu mẫu:

```bash
alembic upgrade head
python -m scripts.seed
```

Trên Windows có thể bấm đúp `1-cai-dat-lan-dau.bat` thay cho các bước 2 đến 4 (lần đầu file sẽ dừng để bạn sửa `.env`, sau đó bấm đúp lại).

## Chạy

```bash
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000. Trên Windows có thể bấm đúp `2-chay-web.bat`. Tài liệu API ở http://127.0.0.1:8000/docs.

Muốn đưa dữ liệu về như ban đầu: `python -m scripts.seed --reset` (hoặc `3-tao-lai-du-lieu-mau.bat`). Lệnh này xóa hết dữ liệu hiện có.

## Tài khoản dùng thử

| Vai trò | Email | Mật khẩu |
| --- | --- | --- |
| Sinh viên | 11236004@st.neu.edu.vn | Huyen123 |
| Giảng viên | hoaithu@neu.edu.vn | Hoaithu123 |
| Quản trị | admin@neu.edu.vn | Admin@12345 |

Mã tham gia lớp KTPM_01 là `KTPM-X31M`. Các lớp mẫu chưa có tài liệu, Giảng viên tự tải lên ở trang lớp. NEU AI chỉ trả lời được khi lớp đã có tài liệu.

## Bật AI thật

1. Lấy khóa tại https://aistudio.google.com/apikey.
2. Điền vào `.env`: `GEMINI_API_KEY=...`, rồi chạy lại máy chủ.
3. Mở http://127.0.0.1:8000/api/health, nếu thấy `"ai_mode": "gemini"` là đã nhận khóa.

Mặc định dùng model `gemini-3.5-flash-lite`. Khi hết lượt miễn phí, NEU AI báo "đang bận" và thử lại sau. Nếu tài liệu được tải lên trước khi bật khóa, chạy `python -m scripts.reindex` để đọc lại.

## Cấu trúc thư mục

```
app/                 máy chủ FastAPI
  routers/           các nhóm API: đăng nhập, lớp, câu hỏi, tài liệu, quản trị...
  services/          xử lý: AI (ai.py), đọc tài liệu, thống kê (analytics.py)
  models.py          các bảng trong cơ sở dữ liệu
alembic/             các bước tạo và thay đổi bảng
scripts/             nạp dữ liệu mẫu, sao lưu, đọc lại tài liệu
tests/               kiểm thử tự động
frontend/            giao diện web (HTML, CSS, JavaScript thuần)
data/uploads/        tệp Giảng viên tải lên (không đưa vào git)
```

## Sửa giao diện

Giao diện không cần build, sửa file rồi tải lại trang (Ctrl + F5). File `frontend/HUONG-DAN-SUA.md` có bảng "muốn sửa gì thì mở file nào": đổi màu, chữ ở banner, menu, thẻ câu hỏi, nhãn trạng thái.

## Kiểm thử

Bộ kiểm thử xóa sạch bảng trong cơ sở dữ liệu nó dùng, nên cần một cơ sở dữ liệu riêng có chữ `test` trong tên:

```bash
set TEST_DATABASE_URL=postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/neu_feedback_test
pytest
```

## Sao lưu

Dữ liệu nằm ở hai nơi: cơ sở dữ liệu (`pg_dump -U postgres -F c -f neu_feedback.dump neu_feedback`) và thư mục `data/uploads`. Cần sao chép cả hai. Có thể xuất thêm bản JSON bằng `python -m scripts.backup`.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `'python' is not recognized` | Cài lại Python và chọn "Add python.exe to PATH" |
| Cổng 8000 đang bận | Chạy `uvicorn app.main:app --port 8001` và mở cổng 8001 |
| Trang báo không kết nối được máy chủ | Cửa sổ chạy máy chủ đã bị tắt, mở lại |
