# Lotus Kho — liên kết nhân sự HRMS & cách đặt mã kho

## Đã triển khai

- Bảng trong workspace Kho được căn giữa tiêu đề và nội dung; chỉ tác động app Kho.
- Mã kho mới dùng cơ chế chuẩn ERPNext Warehouse: `warehouse_name + ' - ' + Company.abbr`. Không sửa mã kho bằng nhập liệu thủ công. Khi người dùng **thay đổi tên kho** trong Thiết lập kho, API dùng `frappe.rename_doc` có kiểm tra quyền, cập nhật liên kết; **không tự đổi mã của 4 kho cũ nếu chỉ chỉnh thông tin liên lạc**.
- Thiết lập kho có `lotus_contact_employee` (Link → Employee). Form chọn nhân viên đang làm việc thuộc cùng Company; `lotus_contact_name`, `lotus_contact_phone` lấy từ hồ sơ Employee. Backend không tin trường tên/điện thoại do frontend gửi.
- Phiếu xuất có `lotus_receiver_employee` (Link → Employee), `lotus_receiver` là tên đọc được theo HRMS để hiển thị phiếu. Phiếu lịch sử nhập thủ công cũ vẫn giữ tên đã lưu, không xóa tự động.
- Trường chọn liên kết giữ mã ID trong dữ liệu nhưng hiển thị nhãn/tên sau khi chọn. Kho trong bảng nhập–xuất–mua hiển thị warehouse_name khi có danh mục tương ứng.

## An toàn dữ liệu

- Chỉ phục vụ tên, mã nội bộ và số điện thoại liên hệ người được phân công cho kho; không gửi CCCD, thông tin ngân hàng, địa chỉ cá nhân hay lương ra ứng dụng Kho.
- API `employee_choices` chỉ cho người có quyền sử dụng phân hệ Kho và giới hạn nhân viên đang làm việc theo Company.
- Khi sửa tên kho có đối chiếu trùng mã và dùng cơ chế rename của Frappe để cập nhật Link; không thao tác đổi khóa chính bằng SQL.
- Các kho hiện có không được đổi mã hàng loạt; chỉ đổi khi sửa **tên kho**.
- Đơn giá nhập kho, giá trị ghi nhận và kế toán vẫn giữ nguyên.

## Kiểm thử

- Frontend `npm test` (31 bài) và `npm run build`.
- Frappe schema: Warehouse.lotus_contact_employee, Stock Entry.lotus_receiver_employee đều là Link Employee.
- Rollback-only integration: tạo kho giả, link HRMS Employee, đổi tên và xác minh mã mới được tạo theo tên+Company.abbr.
- Đã backup site `frontend` trước khi tạo Custom Field mới; không dùng dữ liệu cá nhân thật để thử.
