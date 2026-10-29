# Tham khảo màn chấm công đơn giản

Đã đọc mã nguồn ngày 29/10/2026:

- [AttendIQ Attendance.jsx](https://github.com/keerthu678/student-Attendence-Management-System/blob/main/src/components/Attendance.jsx): chọn ngày, danh sách người, nút trạng thái trực tiếp, đánh dấu hàng loạt, số đếm theo ngày.
- [Frappe HRMS Employee Attendance Tool](https://github.com/frappe/hrms/blob/develop/hrms/hr/doctype/employee_attendance_tool/employee_attendance_tool.js): chọn nhân viên, thao tác chấm tập trung, danh sách đã chấm.
- [Leave & Employee Attendance Management System](https://github.com/tsvishwas23/leave-attendance-management-system): khảo sát bộ lọc ngày/nhân viên và quy trình sửa, duyệt. Mô hình check-in/check-out tính giờ không phù hợp quy tắc hai buổi của Lotus.

Áp dụng nguyên tắc danh sách ngày và thao tác trực tiếp, viết bằng component Vue hiện có, không thêm dependency hay sao chép mã nguồn từ các repo.

Bảng chính gồm tên, sáng, chiều, tổng công và trạng thái. Nút cả ô bật/tắt buổi; buổi từ máy hiện giờ thật, buổi xác nhận tay hiện Có mặt. Ghi chú trong Sheet; tăng ca không hiển thị theo yêu cầu. Lọc bằng một dropdown, thao tác chấm hàng loạt luôn ở ngay trên bảng. Lưu dựa trên các dòng đã sửa, độc lập các ô chọn hàng. DataTable vẫn giữ header và tổng, chỉ thân cuộn.
