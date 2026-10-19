# Tiêu chuẩn giao diện máy tính Lotus (bản 1)

## Công nghệ giữ nguyên
- Vue 3 + Shadcn-vue/Reka UI + Tailwind 3: nút, ô nhập, thanh đầu trang, hộp thoại, thẻ số liệu, trạng thái trống.
- AG Grid v36: bảng dữ liệu nghiệp vụ lớn, bộ lọc, tiêu đề, khoảng cách hàng; vẫn dùng `grid-theme.js`.
- Apache ECharts 6: biểu đồ Dự thu, tải trễ qua thành phần `DesktopForecastChart.vue`.
- Vant 4 trên tất cả PWA điện thoại **không thay đổi**.
- Backend, DocType, quyền và luồng duyệt Frappe/ERPNext không thay đổi.

## Nơi dùng
- `frontend/src/desktop-system.css`: màu, trạng thái sáng/tối, ô nhập, bảng, hộp thoại, menu trái, lề trang, focus.
- `frontend/src/desktop-components.css`: khối tiêu đề, thẻ số liệu, trống dữ liệu, biểu đồ, màn Dự thu.
- `frontend/src/desktop-shell.css`: thanh đầu trang màu đất nung lấy Kho làm chuẩn.
- `main.js` (khung `/lotus`, mọi phân hệ máy tính) nạp `lotus-tokens.css` đầu tiên rồi ba tệp trên; không nạp trong Vant PWA. Các entry riêng của Kho/Nhân sự/Chấm công/Công việc/Giao việc đã bỏ từ 19/10/2026.
- Màu, chữ, khoảng cách, bo góc, bóng chỉ định nghĩa trong `lotus-tokens.css`; hộp thoại xác nhận dùng `WorkspaceConfirm`, icon dùng `LotusIcon`.
- Các ứng dụng máy tính thêm class `lotus-ui` vào phần tử gốc để cách ly kiểu trình bày.
- `components/DesktopPageHeading.vue`, `DesktopMetricCard.vue`, `DesktopEmptyState.vue`, `DesktopForecastChart.vue` là khối tái sử dụng.

## Nguyên tắc triển khai
1. Tiếng Việt đơn giản: Vườn, Lô, Kế hoạch, Dự thu, Kho, Mua hàng.
2. Nhập và tìm kiếm như bảng: không bắt Enter để lọc khi giao diện có sẵn dữ liệu tại máy; giữ riêng API tra cứu dữ liệu lớn.
3. Giữ nguyên quyền backend. Ẩn nút không thay cho kiểm tra quyền máy chủ.
4. Dự thu 36 tháng là **ước tính sản lượng**, không tự phát hành, không tự tạo hàng tồn hoặc cam kết bán.
5. Màn đầu nhìn ngay dữ liệu, lọc Vườn/Lô và thời gian; số liệu thiếu phải báo lý do, không tự bịa.
6. Không thay phần điện thoại và ứng dụng Kho PWA. Mọi CSS desktop mới chỉ ở min-width 901px.
7. Giao diện nhìn giống nhau nhưng không được sửa quy trình và dữ liệu chỉ để làm đẹp.
8. Trường hợp xuất/in phiếu: giữ luồng in gốc; không thay đơn vị, số lượng, chữ ký.
9. Mọi màn phải hỗ trợ bàn phím, khung nhỏ, báo lỗi, không có dữ liệu và đang tải.

## Kiểm thử
- `npm test`: bao gồm quy tắc tích hợp giao diện và tất cả kiểm thử cũ.
- `npm run build`: tạo tất cả entry desktop và mobile, kiểm tra không lỗi.
- Sau triển khai kiểm tra `/lotus`, `/lotus/kho`, `/lotus/forecast`, `/lotus/giao-viec`, `/lotus/cham-cong` và các entry HR, Công việc vườn.
- Đối chiếu quyền, phiếu nháp, phát hành, lịch sử, chi tiết, nhập tìm nhanh, màn trống và trên điện thoại.
- CSS tách riêng cho phép rollback về ảnh Docker trước khi nâng cấp.
