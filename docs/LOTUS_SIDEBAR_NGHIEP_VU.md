# Sidebar Lotus – gom theo nghiệp vụ

Cập nhật: 10/11/2026 (sau spec 002). Nhóm và thứ tự khai báo ở `frontend/src/domain.js` (`navGroups`); nhóm liệt kê màn của chính phân hệ (Việc hằng ngày, Kho, Mua hàng, Tài chính, Nhân sự) lấy danh sách từ `frontend/src/module-navigation.js`.

## Nguyên tắc

- **Tổng quan là báo cáo**: bấm mục Tổng quan vào route `/lotus/reports`.
- Menu là phần điều hướng, **không cấp thêm quyền**. Route, DocType, dữ liệu và quy trình phê duyệt do máy chủ kiểm.
- Chỉ đưa chức năng đang có vào menu; không tạo màn hình giả để lấp chỗ trống.

## Menu trên máy tính

| Nhóm | Màn hình | Mục con |
| --- | --- | --- |
| Tổng quan | Tổng quan (`reports`) | – |
| Việc hằng ngày | Công việc ngoài vườn (`cong-viec`) | Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu (`forecast`), Báo cáo; Thiết lập: Đội, tổ & lô, Việc & cách trả, Bảng giá khoán, Vòng chăm sóc, Màu dây cắt bắp (`mau-day`), Tham số dự thu |
| Vườn & lô | Danh mục lô (`farms`) | Bản đồ lô (`map`) |
| Kho | Quản lý kho (`kho`) | Tồn kho, Nhập kho, Xuất kho, Chuyển kho, Kiểm kê, Sổ kho, Nhu cầu cấp cho công việc, Báo cáo nhập – xuất – tồn; Danh mục kho |
| Mua hàng | Mua hàng (`mua-hang`) | các màn mua hàng; Danh mục mua hàng |
| Tài chính – Kế toán | `tai-chinh` | các màn tài chính; Thiết lập kế toán |
| Nhân sự | Hồ sơ nhân viên (`nhan-su`), Chấm công (`cham-cong`) | các màn nhân sự; Thiết lập nhân sự |
| Thiết lập | Danh mục (`admin/masters`) | Người dùng & phân quyền (`nguoi-dung`) |

- Bấm tên nhóm sẽ mở màn hình đầu tiên mà tài khoản được phép xem; nhóm của một phân hệ chỉ mở/đóng danh sách màn của nó.
- Bấm dấu mũi tên để mở/đóng mục con. Mỗi lần chỉ một nhóm mở.
- Khi thu sidebar còn icon, dùng tên nhóm để đi đến màn hình chính. Bấm nút mở rộng sidebar chung nếu cần mục con.
- Nếu không có quyền, mục bị ẩn, nhóm trống cũng bị ẩn. Trang mới được cấp quyền nhưng chưa khai báo vào nhóm vẫn nằm trong nhóm "Khác".
- Các PWA riêng (`/work`, `/warehouse`, `/buying`, `/hr-mobile`) hoạt động độc lập với menu này.

## Kiểm tra

`npm test` và `npm run build` tại thư mục `frontend` (`tests/workspace-sidebar.mount.test.js` kiểm mỗi trang thuộc đúng một nhóm và có icon thật).

Kiểm tra thủ công với tài khoản nhiều quyền, tài khoản chỉ Kho, chỉ Nhân sự, chỉ Công việc; thử bấm menu cha/con, thu sidebar, xem có vào được đúng trang và không lộ mục không có quyền.
