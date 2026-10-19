# Chữ ký số trong mục Tôi — bản chuẩn bị

## Đã có
- Kho, Mua hàng, Công việc ngoài vườn và Nhân sự dùng cùng giao diện `LotusMobileSignatureSettings` trong tab **Tôi**.
- Người dùng xem danh tính tài khoản và chọn nhà cung cấp chữ ký số dự kiến. Lựa chọn lưu theo `frappe.session.user`, không lưu theo điện thoại/PWA.
- API `lotus_farm.digital_signature.my_signature_profile` và `set_signature_provider`.
- Trường `User.lotus_signature_provider` được tạo qua `install.setup` khi migrate.
- Mọi tài khoản luôn hiện **Chưa kết nối** cho đến khi hệ thống thật sự tích hợp và xác minh chứng thư.

## Chưa có — KHÔNG được nhầm là đã ký PDF
- Chưa thực hiện ký số PAdES vào PDF khi bấm Duyệt.
- Chưa có kết nối/kích hoạt với nhà cung cấp chứng thư số, chưa có xác thực khóa ký.
- Không cho người dùng tải lên khóa bí mật (.p12/.pfx), mật khẩu khóa, OTP hay mã PIN vào ứng dụng.

## Bước tiếp theo khi tích hợp nhà cung cấp
1. Chọn dịch vụ ký số và quy trình cấp/ủy quyền chứng thư cho từng người duyệt.
2. Xác minh chứng thư server-side, gồm người sở hữu, thời hạn và trạng thái thu hồi; chỉ lúc đó mới trả trạng thái sẵn sàng.
3. Kết xuất PDF chính thức từ mẫu in đã khóa dữ liệu; khi Duyệt, gọi dịch vụ ký số có xác thực người ký và chèn chữ ký PDF chuẩn PAdES. Không gửi khóa bí mật cho ứng dụng Lotus.
4. Hoàn thành ký và lưu file bất biến mới chuyển trạng thái Đã duyệt; lỗi ký giữ trạng thái Chờ duyệt.
5. Mỗi cấp ký nối tiếp phải bảo toàn chữ ký đã có; lưu lịch sử, dấu thời gian và tham chiếu chứng từ.
