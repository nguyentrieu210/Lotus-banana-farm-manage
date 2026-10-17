# Dự thu chuối — giao diện máy tính (17/10/2026)

## Phạm vi thực tế

**Dự thu = dự báo sản lượng chuối có khả năng thu hoạch**, khác hoàn toàn công nợ/tiền bán. Nguồn nghiệp vụ là `Harvest Forecast`, dữ liệu thực tế từ `Harvest Actual`; bản đã phát hành có thể tiếp tục liên kết với giữ hàng cho đơn bán. Mọi con số ví dụ phải kiểm tra trên phiếu nguồn thật.

Trang `/lotus/forecast` có ba cách xem: Theo tuần, Theo lô và Phiếu dự thu. Thanh phạm vi chung lọc theo Công ty/Vườn/Lô/Vụ/Từ ngày/Đến ngày. Một phiếu nhiều tuần được đặt vào tuần bắt đầu (sau khi cắt theo khoảng đang lọc), **không chia kg theo tuần khi chưa có quy tắc phân bổ thật**.

## Hiển thị

- **Dự thu (kg buồng):** Tổng `gross_forecast_kg` của các phiếu `Released` còn hiệu lực, trong khoảng thời gian chọn.
- **Dự kiến đóng gói:** Tổng `packed_forecast_kg` đã tính các tỷ lệ chất lượng/đóng gói.
- **Còn có thể giữ:** Tổng `available_to_promise_kg` do backend tính, có thể âm khi thiếu nguồn.
- **Đã thu hoạch:** Tổng `gross_weight_kg` của `Harvest Actual` đã nộp, theo ngày thu hoạch, chỉ hiện nếu có quyền đọc. Đây là **kg buồng**, không phải kg thành phẩm, không so trực tiếp với kg đóng gói.
- Bản `Draft`, `Superseded`, `Closed` hiển thị ở danh sách/lịch sử nhưng **không cộng vào nguồn đang có thể cam kết**.
- Lô được ưu tiên, không hiển thị cấp thửa nhỏ trong bảng mới.

## Thao tác và quyền

- Người có quyền tạo: tạo phiếu; dữ liệu nhập gọn thành các nhóm phạm vi, hệ số, thành phẩm, lý do sửa.
- Lưu nháp: dùng `lotus_farm.console.save`; máy chủ lấy nguồn và tính lại. Màn hình chỉ hiển thị con số của lần lưu gần nhất, không giả vờ tính kết quả chính thức khi đang nhập.
- Phát hành: có phiếu nháp đã lưu và role `Lotus Farm Manager`, bấm **Phát hành dự thu**. Lúc này backend khóa snapshot, kiểm tra profile, gối nguồn, trùng khoảng thu, quyền và các nguồn đã giữ.
- Bản phát hành chỉ xem; tạo bản điều chỉnh kèm `supersedes` và `revision_reason`. Backend tự kiểm điều kiện thay thế: không có buồng đã thu hoặc lượng đang giữ chưa xử lý.
- Sửa, nộp hoặc hủy thực tế vẫn đi theo các luồng chứng từ hiện hữu.

## Nguồn dữ liệu

- `lotus_farm.forecast_workspace.board` (chỉ đọc): nhận company/farm/block/cycle/from_date/to_date, xác nhận quyền, giới hạn cửa sổ 366 ngày; dùng `frappe.get_list` có quyền và ranh giới vườn như giao diện chung. Trả về `rows`, `weeks`, `summary`, `actual_readable`.
- `lotus_farm.console.schema/detail/save`: dùng lại backend chung cho phiếu; không tạo bảng dữ liệu, không thay đổi DocType hoặc công thức dự thu.
- `lotus_farm.reporting.forecast_vintages`: trang Báo cáo cho sai lệch 8/4/2/1 tuần, **chỉ** xác nhận sai lệch khi nguồn thực tế đã xử lý đủ QC/xưởng/kho.

## Kiểm thử

1. Frontend `npm test`, `npm run build`.
2. Kiểm kết quả rỗng; hai vườn; lô; 8 tuần; lọc trạng thái; tìm phiếu; quyền xem thực tế bị từ chối.
3. Nháp không cộng sản lượng; bản cũ thay thế không cộng trùng; phiếu đa tuần không bị chia kg tự động.
4. Lưu nháp và phát hành phải giữ backend validation: sai profile, nguồn âm, trùng khoảng, sửa phiếu cũ, không đúng quyền.
5. Đối chiếu mẫu vài phiếu với Harvest Forecast/Harvest Actual, không nhầm kg buồng và kg thành phẩm.
6. Test khói trên Docker `localhost:8080/lotus/forecast` bằng tài khoản có quyền, thử hồ sơ demo/trống trước khi dùng sản xuất.

## Triển khai / khôi phục

Ảnh Docker mới kế thừa image đang chạy, chỉ thay mã `console.py`, thêm `forecast_workspace.py` và cập nhật assets frontend. Không chạy migrate/schema/seed hay sửa dữ liệu vườn. Nếu phát sinh lỗi, bỏ override forecast desktop và `docker compose up -d` để chạy lại image trước đó.
