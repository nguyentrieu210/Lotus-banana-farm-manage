# Chấm công theo buổi trên một dòng/ngày

- Một lượt chấm buổi sáng: 0,5 công. Một lượt buổi chiều: 0,5 công. Có cả hai: 1 công (8 giờ công quy đổi).
- Theo cập nhật của chủ vườn: sáng lấy lượt trước **07:00**, chiều lấy lượt sau **17:00**. Chọn lượt hợp lệ đầu tiên mỗi buổi, các lượt lặp chỉ tính một lần; không dùng nhãn IN/OUT. Lượt trong khoảng 07:00–17:00 (kể cả đúng hai mốc) giữ trong log gốc, không tự tính công.
- Desktop và PWA dùng một dòng/nhân viên/ngày. Hai ô Sáng/Chiều cùng cập nhật cột Công. Giờ chấm giữ đúng dữ liệu máy; xác nhận tay không tạo giờ chấm giả.
- Tick chọn dòng của DataTable mở thao tác Chấm sáng/Chấm chiều cho những người đã chọn; lưu và duyệt theo cả ngày.
- Một HRMS Attendance lưu cả hai buổi. Bảng lương lấy 4/8 giờ công quy đổi từ các buổi đã duyệt; lượt máy không phát sinh tăng ca. Màn ngày, chi tiết và sửa công theo buổi trên desktop/PWA không có trường tăng ca. Giá trị tăng ca lịch sử giữ nguyên khi chỉ sửa ghi chú hoặc buổi có mặt.
- Phiếu cũ và raw check-in giữ nguyên. Phiếu đã duyệt sửa qua cancel/amend với lý do; kỳ đã khóa, quyền đọc/ghi, chống gửi trùng, phiên bản duyệt và tăng ca thủ công vẫn được bảo vệ.
- API ca cũ giữ tương thích. Hai giao diện chấm công gửi `daily_presence=1` để dùng quy tắc mới, không yêu cầu chọn/phê duyệt từng ca.

Kiểm thử gồm: nhiều lượt cùng buổi chỉ nửa công; hai IN khác buổi đủ công; một phiếu/ngày; giờ chấm thật; dữ liệu duyệt cũ; retry; tăng ca thủ công; sửa phiếu đã duyệt; quyền chỉ đọc và riêng tư lượt máy. Mount tests kiểm tra chọn hàng chung, chấm buổi hàng loạt và nhập/sửa trên điện thoại.

Mã chính sách nằm trong fingerprint duyệt để trang mở trước lần cập nhật không thể duyệt bằng bản xem cũ. Lượt chỉ có trong khoảng giữa ngày không được gợi ý duyệt vắng tự động. Phiếu cũ vẫn đọc theo giá trị đã lưu; không tự sửa dữ liệu lịch sử.
