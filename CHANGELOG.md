# Lịch sử thay đổi

Chỉ ghi các mốc chính của dự án.

## Bản 3.26
- Trang Tổng quan của quản trị chỉ còn "việc cần làm hôm nay": câu hỏi mới chưa trả lời, nội dung bị gắn cờ, tỷ lệ AI gom nhóm thành công, xu hướng 7 ngày, lớp cần chú ý, hoạt động gần đây.
- Trang Thống kê tập trung vào phân tích: lọc theo năm học, học kỳ, khoa, Giảng viên; so sánh khoa; khung giờ hay hỏi; chủ đề nổi bật theo tuần; hiệu suất AI.
- Hai trang dùng chung một cách đếm câu hỏi nên số liệu luôn khớp nhau (trước đây lệch 47 và 43).
- Lưu thời gian NEU AI trả lời mỗi tin nhắn (migration `0011`).
- Danh sách tuần của sinh viên: lớp đã kết thúc hiện nút "Xem câu hỏi" thay cho "Đặt câu hỏi".
- NEU AI hiển thị gọn hơn trên điện thoại.
- Chia lại thư mục giao diện: CSS và JavaScript tách theo thành phần và theo trang, thêm `frontend/HUONG-DAN-SUA.md`.
- Viết lại README, bỏ mã không còn dùng.

## Bản 3.25
- Khôi phục ảnh tòa nhà NEU ở banner trang chủ Giảng viên.

## Bản 3.17 đến 3.24
- Trang chủ sinh viên và Giảng viên làm lại theo mẫu mới, có robot NEU AI.
- Thẻ câu hỏi của sinh viên tách riêng từng thẻ, có cửa sổ chi tiết, sửa và xóa ngay trên dòng.
- Thanh bên trái có hai trạng thái (đầy đủ và chỉ biểu tượng).
- NEU AI trả lời nhanh hơn: tắt chế độ suy nghĩ của Gemini, giới hạn độ dài, bỏ qua tìm tài liệu với câu chào.
- Sửa lỗi 503 của NEU AI, phân loại lỗi và hiện đúng nguyên nhân.
- Bỏ tính năng "Hỏi thêm Giảng viên" (migration `0010`), sinh viên dùng "Nhờ NEU AI giải thích thêm".

## Bản 3.0 đến 3.16
- Bảng màu xanh NEU, banner ảnh trường, thông báo góc phải.
- Danh sách tuần học dạng thẻ, tài liệu từng tuần, kho tài liệu dạng bảng.
- Ô soạn thảo có định dạng cho câu trả lời và câu hỏi.
- NEU AI đọc được ảnh, PDF, Word, PowerPoint, Excel; hiển thị Markdown.
- Admin quản lý tài khoản theo lớp, học kỳ, gắn cờ nội dung.

## Bản 2.x
- 15 tuần học cho mỗi lớp, tải tài liệu kéo thả.
- Trả lời tự động cho câu hỏi giống câu đã trả lời, nhóm câu hỏi tương đồng.

## Bản 1.x
- Backend FastAPI và PostgreSQL, gộp giao diện với backend.
- Đăng nhập, lớp học, câu hỏi ẩn danh, thống kê, nhận diện của Trường Đại học Kinh tế Quốc dân.
