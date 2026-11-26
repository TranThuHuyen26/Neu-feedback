# Hướng dẫn sửa giao diện

Tài liệu này dành cho lúc cần sửa nhanh giao diện: muốn sửa gì thì mở file nào.

Mọi file nằm trong `frontend/`. Sau khi sửa, tải lại trang bằng **Ctrl + F5** (hoặc Cmd + Shift + R trên Mac) để trình duyệt lấy file mới. Không cần build hay cài thêm gì.

## Muốn sửa gì → mở file nào

| Muốn sửa | Mở file | Tìm gì |
| --- | --- | --- |
| Màu chủ đạo của cả trang (xanh NEU, đỏ, vàng) | `assets/css/base/tokens.css` | `--neu-blue-ink`, `--accent`, `--bg` |
| Màu riêng cho từng vai trò | `assets/css/base/tokens.css` | khối `body.lecturer`, `body.admin` |
| Cỡ chữ, font chữ | `assets/css/base/tokens.css` và `base/base.css` | `--font` |
| Chữ chào ở banner trang chủ sinh viên | `assets/js/pages/student/home.js` | `Chào <span class="hero-name">` |
| Chữ chào ở banner trang chủ Giảng viên | `assets/js/pages/lecturer/home.js` | `Chào Giảng viên` |
| Ảnh nền banner trang chủ | `assets/css/pages/student-home.css` | `.sh-hero::before`, dòng `background: url(...)` |
| Thay ảnh banner bằng ảnh khác | `assets/images/neu-hero.jpg` | ghi đè file này bằng ảnh mới, giữ nguyên tên |
| Ảnh nền trang đăng nhập | `assets/css/layers/13-dang-nhap-ai-noi.css` | `neu-hero.jpg` |
| Menu bên trái (tên mục, thứ tự, thêm mục) | file HTML của trang, trong `pages/<vai trò>/` | thẻ `<nav class="nav">` |
| Tên hiển thị và logo ở góc trên bên trái | file HTML của trang | thẻ `<a class="brand">` |
| Thẻ câu hỏi (bố cục, viền, khoảng cách) | `assets/css/pages/question-cards.css` | `.qr`, `.qr-list` |
| Nội dung trong thẻ câu hỏi (hiện gì, thứ tự) | `assets/js/pages/student/common.js` | hàm `qRow` |
| Nhãn trạng thái câu hỏi ("Chờ trả lời", "Đã trả lời") | `assets/js/shared/questions.js` (hàm `qPill`) và `assets/js/core/util.js` (hàm `qBadge`) | `Chờ trả lời` |
| Nhãn trạng thái tuần ("Đã học", "Đang học", "Chưa học") | `assets/js/shared/classes.js` | `WEEK_LABEL` |
| Nút "Đặt câu hỏi" / "Xem câu hỏi" ở danh sách tuần | `assets/js/shared/classes.js` | `Đặt câu hỏi` |
| Cửa sổ chi tiết câu hỏi (modal) | `assets/js/shared/questions.js` và `assets/css/layers/32-danh-sach-cau-hoi-gon.css` | `.qm-` |
| Trang NEU AI của sinh viên | `pages/student/student-ai.html` và `assets/js/pages/student/ai.js` | |
| Nút chat NEU AI nổi ở góc màn hình | `assets/js/shared/ai-widget.js` | |
| NEU AI trên điện thoại | `assets/css/pages/chat-mobile.css` | |
| Trang Tổng quan của admin | `pages/admin/admin.html`, `assets/js/pages/admin/home.js`, `assets/css/pages/admin-overview.css` | |
| Trang Thống kê của admin | `pages/admin/admin-stats.html`, `assets/js/pages/admin/stats.js`, `assets/css/pages/admin-stats.css` | |
| Độ rộng thanh bên, thanh trên cùng | `assets/css/layout/shell.css`, `assets/css/layout/topbar.css` | `.sidebar`, `.topbar` |
| Nút bấm | `assets/css/components/buttons.css` | `.btn` |
| Thông báo nhỏ (toast), hộp thoại | `assets/css/components/modal-toast.css` | `.toast`, `.modal` |

## Cấu trúc thư mục

```
frontend/
  pages/                 các trang HTML
    student/  lecturer/  admin/  common/   (đăng nhập, hồ sơ, giới thiệu...)
  assets/
    images/              logo, ảnh banner, hình robot NEU AI
    css/
      style.css          chỉ liệt kê các file bên dưới, không chứa luật nào
      base/              màu (tokens.css), nền, chuyển động, responsive
      layout/            thanh bên, thanh trên cùng, khung trang
      components/        nút, thẻ, bảng, tab, form, biểu đồ, modal...
      pages/             giao diện riêng của từng trang
      layers/            các lần chỉnh sửa trước đó, đánh số theo thứ tự
    js/
      core/              api.js, app.js, tiện ích chung, khung trang, khởi động
      shared/            phần dùng chung giữa nhiều trang
      pages/student/     mỗi file là một trang của sinh viên
      pages/lecturer/    mỗi file là một trang của Giảng viên
      pages/admin/       mỗi file là một trang của quản trị
      pages/common/      đăng nhập, hồ sơ
```

Trong `assets/js/pages/<vai trò>/`, file `common.js` chứa các hàm dùng chung cho các trang của vai trò đó.

## Cách tìm đoạn cần sửa khi không nhớ file nào

1. Mở trang cần sửa, bấm F12, chọn công cụ chọn phần tử (mũi tên ở góc trên bên trái) rồi bấm vào chỗ cần sửa. Ghi lại tên class (ví dụ `sh-hero`, `qr-row`).
2. Trong VS Code bấm **Ctrl + Shift + F**, gõ tên class đó và tìm trong thư mục `frontend/assets`.
3. Nếu không dùng được F12: tìm theo chữ đang hiển thị trên màn hình (ví dụ "Chờ trả lời"), chữ nằm trong file `.js` hoặc `.html`.

Lưu ý về CSS: file nằm sau trong `assets/css/style.css` ghi đè file nằm trước. Nếu một class xuất hiện ở nhiều file và sửa file đầu không thấy thay đổi, hãy sửa ở file có số thứ tự lớn hơn (thư mục `layers/` rồi đến `pages/`). Có thể thêm tạm `!important` để kiểm tra nhanh, sau đó bỏ đi.

## Thêm một trang mới

1. Sao chép một file HTML gần giống trong `pages/<vai trò>/` và đổi tên.
2. Tạo file JS mới trong `assets/js/pages/<vai trò>/`, viết một hàm lấy dữ liệu và vẽ trang, rồi đăng ký bằng `NEU.pages.tenHam = tenHam;` ở cuối file.
3. Thêm tên file HTML vào bảng `CONTROLLERS` trong `assets/js/core/boot.js`.
4. Thêm thẻ `<script>` cho file JS mới vào trang HTML, đặt trước `core/boot.js`.
