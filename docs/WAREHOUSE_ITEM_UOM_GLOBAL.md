# Thiết lập vật tư — tồn tối thiểu chung và quy đổi đơn vị (Lotus)

## Nghiệp vụ

- Khi thêm/sửa vật tư: mã vật tư, tên, nhóm, **đơn vị tồn kho gốc** (ví dụ Kg), **tồn tối thiểu chung toàn bộ kho** (đơn vị Kg), đơn vị phụ đóng gói (ví dụ Bao), **số đơn vị gốc trong một đơn vị đóng gói** (1 Bao = 25 Kg). Không chọn kho tại bước khai báo vật tư.
- Tồn tối thiểu được đối chiếu trên tổng tồn ở **mọi kho hoạt động của công ty**. Khi người dùng lọc riêng kho vẫn hiển thị ngưỡng tối thiểu/chênh lệch **chung**; tồn thực tế hiển thị cho kho được lọc.
- Tồn kho được ghi theo **đơn vị gốc ERPNext Item.stock_uom**. Cột *Tồn quy đổi* hiển thị tương đương theo đơn vị phụ; không sinh thêm một tồn kho độc lập.
- Quy đổi dùng bảng ERPNext chuẩn **UOM Conversion Detail** trên Item. Đơn vị `Bao` được tạo một lần trong danh mục UOM toàn hệ thống. Hệ số **tùy vật tư** (bao phân 25 Kg, bao khác có thể 50 Kg). Không đặt quy đổi `Bao` = 25 Kg trên danh mục UOM chung.
- Khi lập phiếu nhập thông thường: chọn đơn vị gốc hoặc đơn vị phụ; nhập số lượng và đơn giá theo **đơn vị đang chọn**. Backend kiểm tra đơn vị đã khai báo trong Item.uoms, lấy conversion factor từ server, không tin giá trị do client tự gửi. ERPNext lưu `qty` theo đơn vị nhập, `transfer_qty` theo đơn vị tồn gốc, `basic_rate` theo đơn vị gốc.
- Ví dụ 4.000 Bao × 25 Kg/Bao = 100.000 Kg. Giá 125.000 VND/Bao → giá vốn gốc 5.000 VND/Kg, tiền vật tư 500.000.000 VND. Hoặc nhập 100.000 Kg với đơn giá 5.000 VND/Kg cho cùng kết quả.
- Phiếu xuất và kế hoạch vật tư hiện giữ đơn vị gốc theo các luồng có sẵn. Không tự đổi đơn vị của chứng từ đã ghi sổ.
- Không cho sửa hệ số quy đổi cũ sau khi vật tư có phát sinh Stock Ledger Entry, để không làm thay đổi cách hiểu dữ liệu lịch sử.

## Kiểm thử

- Frontend: `npm test` và `npm run build`.
- Backend: `tests/integration/verify_item_uom_global.py`, sử dụng dữ liệu thử và `frappe.db.rollback()`.
- Site `frontend` được sao lưu trước khi cập nhật Custom Field và UOM.
- Không tự sửa tồn tối thiểu legacy theo từng kho vì rà soát dữ liệu thực tế trả về không có bản ghi đã cấu hình.

## Giới hạn

- Ngưỡng tồn tối thiểu dùng trường trên Item, nên **chung danh mục Item** khi có nhiều Company. Hiện Lotus vận hành một Company; nếu triển khai nhiều pháp nhân với mức ngưỡng khác nhau cần bổ sung chính sách riêng theo Company.
- Không tạo số lượng nhập tồn khi khai báo vật tư: số 100.000 Kg phải được ghi nhận bằng phiếu nhập kho đã duyệt, không gõ vào master Item.
