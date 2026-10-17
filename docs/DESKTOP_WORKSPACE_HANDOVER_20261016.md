# Lotus Workspace — bàn giao ngày 16/10/2026

Đã triển khai giao diện Kho desktop tại `/lotus/kho` bằng image `lotus-desktop-workspace:v4-20261016` cho backend và frontend. Các module vườn/chấm công/nhân sự giữ giao diện hiện có; đây là đợt triển khai Kho đầu tiên.

## Quyết định cuối của người dùng

- Bỏ toàn bộ khối tiêu đề lớn, breadcrumb, mô tả nghiệp vụ, phạm vi kho lặp và nhóm Dễ đọc/Gọn phía trên các bảng.
- Chỉ dùng thanh điều hướng để xác định màn hình; khu vực bảng ưu tiên bộ lọc và thao tác.
- Kho, Từ ngày, Đến ngày, Làm mới, Tìm kiếm nằm trên một hàng ở desktop. Nhu cầu vật tư gom các trường này vào cùng toolbar bằng slot; không còn hai thanh lọc riêng.
- Các yêu cầu này được lưu ở `AGENTS.md`, thay thế đề xuất PageHeader trong bản nghiên cứu ban đầu.

## Thay đổi

- Thanh trên chuyển sắc cam, dùng logo gốc; sidebar sáng với icon SVG đồng bộ, mục chọn rõ, giữ thu gọn và theme tối.
- CSS desktop và token có phạm vi riêng, kích hoạt từ 901px. `/warehouse` giữ entry mobile độc lập.
- Bảng giữ toàn bộ cột, căn giữa theo quy ước đang có, server sort/filter và phân trang. Mật độ chọn qua Tìm nhanh/Ctrl K, nhớ trên trình duyệt; không chiếm hàng giao diện riêng.
- Thao tác Tạo đơn mua mở form hiện có sau khi tải setup và kiểm tra quyền của module Mua hàng. Bootstrap bổ sung cờ quyền tạo Purchase Order, không thay đổi quyền thực tế.
- Form có control, khoảng cách, nhóm dòng hàng và footer lưu rõ hơn; không đổi giao dịch hoặc migration.
- Hai test dựa trên selector chuỗi cũ được cập nhật để nhận cấu trúc scope mới. Những kiểm tra hành vi lọc nghiệp vụ vẫn giữ nguyên.

## Kiểm tra đã hoàn thành

- Suite frontend: 92/92 đạt. Vite production build thành công; cảnh báo chunk AG Grid lớn vẫn tồn tại.
- Audit DOM mobile hiện có đạt; kiểm tra DOM mới cho mật độ, lưu lựa chọn, giá trị không hợp lệ, chuyển breakpoint và gỡ class khi unmount đạt.
- Browser: Tồn kho, Nhu cầu, Mua hàng, Phiếu, Lịch sử và Thiết lập; không có thông báo lỗi trên các màn đã xem.
- Tạo đơn mua mở được; footer nằm trong viewport. Không lưu đơn hoặc giao dịch để kiểm tra.
- Tìm `Cào` cho 2 kết quả; lọc Nhóm hàng `Nông cụ` cho 18 vật tư rồi xóa lọc. Bộ lọc cột tiếp tục dùng popup và máy chủ.
- Theme tối/sáng và thu gọn sidebar hoạt động. Kiểm tra thanh lọc ở 1366×768, 1024×768: các control có cùng tâm dọc, không tràn ngang toàn trang.
- 1280×720: tồn kho và phân trang vừa chiều cao viewport. Mobile 390×844 không tràn ngang, giữ bố cục thẻ cam. Bản mobile có thể hiện thông báo cập nhật PWA do đổi phiên bản asset.
- Runtime: API ping trả pong, DB healthy, backend/frontend chạy image v4.

Giới hạn: kiểm tra browser dùng Administrator và Chromium; chưa kiểm tra iPhone/Android vật lý hoặc toàn bộ tổ hợp quyền. Không thực hiện giao dịch thật.

## Bản sao và quay lại

Bản sao trước thay đổi ở `C:/Users/ADMIN/Documents/ChatGPT/a/lotus-runtime/desktop-workspace-backup-20261016`: compose, source/public frontend và warehouse.py. Image `lotus-warehouse-mobile-v6:20261016` vẫn được giữ.

Nếu cần quay lại runtime, đổi riêng image backend/frontend trong compose về image mobile v6 rồi chạy `docker compose -p lotus up -d --no-deps backend frontend` từ thư mục runtime. Không cần migrate, không xóa volume. Không khôi phục source bằng cách ghi đè toàn bộ checkout đang có các thay đổi chưa commit.

Log build/test và ảnh xác nhận ở `C:/Users/ADMIN/Documents/ChatGPT/a/lotus-runtime/desktop-workspace-*`.
