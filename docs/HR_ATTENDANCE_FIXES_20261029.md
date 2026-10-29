# Chấm công ca và nhân sự — 29/10/2026

Khắc phục các phát hiện F01–F09 của audit bản `c4b5859`.

- Bảng ngày và đề xuất máy dùng đúng lịch có hiệu lực, gồm nhiều ca không chồng giờ trong ngày. Chọn ca chỉ lọc dữ liệu. Khóa chọn/lưu theo nhân viên + ca và kiểm tra lại ca ở server.
- Log có nhãn phải đủ IN/OUT đúng thứ tự. Chưa phân ca hoặc gặp phiếu cũ chưa gắn ca thì chờ kiểm tra, không duyệt tự động.
- So khớp máy gồm tăng ca, ca, cờ muộn/về sớm và thời gian chính xác. Duyệt chỉ những phiên bản người dùng đã xem; thay đổi chưa lưu chặn duyệt. Số tăng ca bằng 0 được giữ trong báo cáo tháng.
- Bảng lương lấy Salary Structure Assignment có hiệu lực cho từng khoảng ngày trong thời gian làm việc; bảo hiểm/thuế tính một lần theo kỳ. Thay đổi thông tin liên hệ không phát sinh mức lương mới. Snapshot lưu nguồn và các khoảng mức lương đã dùng; thiếu dữ liệu lương sẽ chặn gửi/ký khóa kỳ.
- Cho phép bổ sung Attendance và Employee Checkin lịch sử trong thời gian làm việc của nhân viên Left, vẫn chạy các kiểm tra trùng/ca/ngày/phép của HRMS. Mapping máy hết hiệu lực ở ngày nghỉ nhưng vẫn nhận log tải lên muộn. Ngày nghỉ tương lai cần chờ đến hiệu lực.
- Mỗi chữ ký kiểm tra lại điều kiện khóa kỳ và hash. Các đường ghi công, log máy, hồ sơ và mức lương dùng khóa Company để tránh chen giữa lần kiểm tra và đóng kỳ.
- Người chỉ đọc xem được bảng; quyền permlevel của giờ quẹt máy được giữ nguyên. API tạo phiếu lương HRMS đã đăng ký POST đúng hàm.
- Cảnh báo tải lại/đóng trang và guard điều hướng bao phủ dữ liệu chấm công, đội khoán, danh mục và sửa công.

## Nâng cấp

Giữ một image cho backend/frontend/worker/scheduler/websocket bằng `compose.release.yaml`. Backup database + files trước triển khai. Bản này chỉ thêm Custom Field `Salary Structure Assignment.lotus_payment_basis`; chạy `lotus_farm.hr_payroll.install_fields` và clear-cache, không cần full migrate hay thay DocField JSON hiện hữu.

Hai lớp `hr_historical` kế thừa HRMS và giữ trình tự validate của bản HRMS 16.50 đang cài; cần chạy lại integration khi nâng HRMS.

Lịch vận hành được người dùng xác nhận: toàn bộ nhân viên cùng **Ca sáng 07:00–11:00 + Ca chiều 13:00–17:00**, từ **29/10/2026**. Script `deployment/apply_common_hr_roster.py` mặc định rollback, chỉ commit với `--apply`, kiểm tra số nhân viên và không tạo Attendance.

## Kiểm tra

`tests/test_hr_audit_rules.py` bao phủ log thiếu cặp, ca đêm, hiệu lực lao động, mức lương tương lai/giữa tháng và thiếu mức lịch sử. `tests/integration/verify_hr_audit_fixes.py` chỉ chạy trên site disposable có cờ bảo vệ, kiểm tra API thật, quyền chỉ đọc, hai ca/ngày, log muộn của người nghỉ việc, lương và ký khóa kỳ; fixture rollback.

Frontend dùng test mount cho hai dòng cùng nhân viên, giữ lựa chọn theo ca, chặn duyệt khi đang sửa, beforeunload, gửi phiên bản đã xem và xếp nhiều ca. Chạy bộ tests frontend, build và kiểm tra desktop/PWA trước phát hành.
## Tích hợp bản báo cáo ngày mới

Bản phát hành giữ các thay đổi báo cáo ngày trong `99bc35e`. Báo cáo còn công khoán chưa xác nhận
sẽ chặn khóa kỳ. Ghi báo cáo khóa Company trước khi kiểm tra tháng đã khóa, cùng thứ tự khóa
với bước ký cuối kỳ. Kiểm thử database bao phủ thêm nguồn công khoán này.
