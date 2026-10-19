# Sidebar Lotus – gom theo nghiệp vụ

Cập nhật: 20/10/2026.

## Nguyên tắc

- **Tổng quan là báo cáo**: bấm mục Tổng quan vào route `/lotus/reports`; "Cảnh báo" là mục con.
- **Bản đồ** đứng ngay sau Tổng quan.
- Người quản lý làm việc theo thứ tự: Vườn/lô → Kế hoạch → Điều hành công việc → Dự thu → Thu hoạch và đóng gói.
- Kho/mua hàng, nhân sự và thiết lập là các nhóm hỗ trợ.
- Menu là phần điều hướng, **không cấp thêm quyền**. Các route, DocType, dữ liệu và quy trình phê duyệt giữ nguyên.
- Chỉ đưa chức năng đang có vào menu; không tạo màn hình giả để lấp chỗ trống.

## Menu trên máy tính

| Nhóm | Màn hình chính | Mục con |
| --- | --- | --- |
| Tổng quan | Tổng quan (`reports`) | Cảnh báo |
| Bản đồ | Bản đồ (`map`) | – |
| Quản lý vườn | Vườn & lô (`farms`) | Đo trái, Hủy & tổn thất, Kết vụ |
| Kế hoạch sản xuất | Kế hoạch (`plans`) | – |
| Điều hành công việc | Công việc ngoài vườn (`cong-viec`) | Tiến độ & kết quả, Bố trí nhân công, Vật tư theo việc, Chốt ngày |
| Dự thu | Dự thu (`forecast`) | – |
| Thu hoạch & đóng gói | Thu hoạch (`harvest`) | QC đầu vào, Đóng gói, Truy xuất |
| Kho & mua hàng | Quản lý kho (`kho`) | Mua hàng (PWA hiện có, đường dẫn `/buying`) |
| Nhân sự | Hồ sơ nhân sự (`nhan-su`) | Chấm công |
| Thiết lập | Danh mục (`admin/masters`) | Định mức & chu kỳ, Nhập dữ liệu, Cấu hình, Người dùng & phân quyền |

- Bấm tên nhóm sẽ mở màn hình chính mà tài khoản được phép xem.
- Bấm dấu mũi tên để mở/đóng mục con. Mỗi lần chỉ một nhóm mở.
- Khi thu sidebar còn icon, dùng tên nhóm để đi đến màn hình chính. Bấm nút mở rộng sidebar chung nếu cần mục con.
- Nếu không có quyền, mục bị ẩn, nhóm trống cũng bị ẩn. Trang mới được cấp quyền nhưng chưa khai báo vào nhóm vẫn nằm trong nhóm "Khác".
- Các PWA riêng (Kho, Mua hàng, Công việc ngoài vườn) vẫn hoạt động độc lập; không đổi điều hướng hay cache offline của chúng.

## Hạn chế hiện có

- "Đo trái" là màn hình đo trái hiện có, chưa phải phần thống kê toàn bộ cây/buồng.
- "Mua hàng" dẫn tới ứng dụng độc lập. Quyền sử dụng nghiệp vụ mua vẫn được kiểm tra bởi ứng dụng đó.
- Việc đưa báo cáo chi tiết và lịch sử số liệu vào một màn hình thống nhất hơn cần thay đổi nghiệp vụ riêng, không thuộc thay đổi menu.
- Chưa có menu con độc lập cho "Chọn chồi" nếu dữ liệu/trang xử lý đó chưa được xây dựng, tránh giả vờ tính năng đã có.

## Kiểm tra

`npm test` và `npm run build` tại thư mục `frontend`.

Kiểm tra thủ công với tài khoản nhiều quyền, tài khoản chỉ Kho, chỉ Nhân sự, chỉ Công việc; thử bấm menu cha/con, thu sidebar, xem có vào được đúng trang và không lộ mục không có quyền. Thử PWA Mua hàng ở `/buying` và PWA Công việc tại `/work`.

**Bản phát hành**: triển khai trên đúng bản sản xuất `603c470` bằng hình thức cập nhật giao diện, giữ nguyên backend nghiệp vụ và dữ liệu.
