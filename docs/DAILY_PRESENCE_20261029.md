# Chấm công theo buổi trên một dòng/ngày

- Một lượt chấm buổi sáng: 0,5 công. Một lượt buổi chiều: 0,5 công. Có cả hai: 1 công (8 giờ công quy đổi).
- Lượt trước 12:00 thuộc sáng; từ 12:00 thuộc chiều. Chọn lượt đầu mỗi buổi, các lượt lặp cùng buổi chỉ tính một lần. Nhãn IN/OUT không quyết định có mặt theo buổi.
- Desktop và PWA dùng một dòng/nhân viên/ngày. Hai ô Sáng/Chiều cùng cập nhật cột Công. Giờ chấm giữ đúng dữ liệu máy; xác nhận tay không tạo giờ chấm giả.
- Tick chọn dòng của DataTable mở thao tác Chấm sáng/Chấm chiều cho những người đã chọn; lưu và duyệt theo cả ngày.
- Một HRMS Attendance lưu cả hai buổi. Bảng lương lấy 4/8 giờ công quy đổi từ các buổi đã duyệt; tăng ca vẫn được xác nhận riêng.
- Phiếu cũ và raw check-in giữ nguyên. Phiếu đã duyệt sửa qua cancel/amend với lý do; kỳ đã khóa, quyền đọc/ghi, chống gửi trùng, phiên bản duyệt và tăng ca thủ công vẫn được bảo vệ.
- API ca cũ giữ tương thích. Hai giao diện chấm công gửi `daily_presence=1` để dùng quy tắc mới, không yêu cầu chọn/phê duyệt từng ca.

Kiểm thử gồm: nhiều lượt cùng buổi chỉ nửa công; hai IN khác buổi đủ công; một phiếu/ngày; giờ chấm thật; dữ liệu duyệt cũ; retry; tăng ca thủ công; sửa phiếu đã duyệt; quyền chỉ đọc và riêng tư lượt máy. Mount tests kiểm tra chọn hàng chung, chấm buổi hàng loạt và nhập/sửa trên điện thoại.
