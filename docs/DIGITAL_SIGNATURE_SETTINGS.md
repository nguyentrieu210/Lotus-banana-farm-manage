# Ảnh chữ ký điện tử Lotus

## Mục Tôi
- Một thành phần chung cho Kho, Mua hàng, Nhân sự, Công việc ngoài vườn.
- Chọn ảnh chữ ký PNG/JPG (tối đa 1,5 MB), xem trước, thay ảnh và xóa ảnh.
- Ảnh được kiểm tra định dạng thật, bỏ metadata, chuyển PNG và lưu private theo User đang đăng nhập.
- Người dùng không thể đặt chữ ký hay thay chữ ký hộ tài khoản khác qua API.
- Cột cấu hình nhà cung cấp chữ ký số cũ vẫn giữ trong dữ liệu để tránh làm hỏng schema, nhưng giao diện không sử dụng.

## Tự in chữ ký khi duyệt mua hàng
- Nút Duyệt của đơn mua giữ nguyên phân quyền duyệt và phòng ngừa người lập tự duyệt.
- Khi tài khoản duyệt đã đăng ký ảnh chữ ký: giao dịch duyệt chụp ảnh chữ ký hiện tại, tạo file PDF từ mẫu Purchase Order, chèn ảnh cùng tên/tài khoản/thời gian duyệt, lưu file private dưới đơn mua. Sau đó chia sẻ/tải đơn mua qua endpoint có kiểm tra quyền sẽ trả về chính file đã lưu.
- Nếu tạo hoặc lưu PDF thất bại, toàn bộ giao dịch duyệt được rollback.
- Nếu người duyệt chưa cài ảnh, giữ nguyên quy trình duyệt cũ và dùng mẫu PDF thông thường (chưa ký).
- Thay hoặc xóa ảnh chữ ký sau này không thay đổi file PDF duyệt đã lưu.

## Giới hạn
- Chỉ là ảnh chữ ký và ghi nhận người duyệt; **không phải chữ ký số có chứng thư**.
- Giai đoạn này nối tự động ký PDF cho **Đơn mua hàng**. Các phiếu Kho/nhân sự/công việc cần xác định luồng duyệt và mẫu in chính thức để tích hợp tương tự.
- Ảnh ký từ tay không bảo đảm chống chỉnh sửa độc lập; audit, tệp đã lưu và quyền truy cập vẫn cần bảo vệ.
