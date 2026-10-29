# Phụ cấp công việc và bảng lương theo công (29/10/2026)

## Phụ cấp công việc
- Người chấm công tick **Phụ cấp** trên dòng công ngày của từng người (máy tính: cột Phụ cấp, nút Phụ cấp / Bỏ phụ cấp
  cho các dòng đã chọn; điện thoại: ô Phụ cấp công việc trong phiếu công ngày).
- Một mức chung (`Lotus Pay Rate`, loại Allowance, theo ngày áp dụng), mặc định 20.000 đ/ngày từ 01/10/2026.
  Có mặt cả ngày được đủ mức, một buổi được nửa mức; vắng cả ngày thì không tick được.
- Số tiền được chốt vào phiếu công khi lưu (`Attendance.lotus_allowance`, `lotus_allowance_amount`): đổi mức sau đó
  không làm đổi các ngày cũ.
- Phiếu đã duyệt vẫn tick hoặc bỏ được phụ cấp khi tháng chưa khóa (`attendance_day.set_allowance`), không phải sửa công.
- Không tính thuế TNCN, không tính vào lương đóng BHXH (bảo hiểm tính trên lương cơ bản). Trên bảng lương phụ cấp được
  cộng sau thuế vào tổng thu nhập và thực lĩnh, nên bút toán lương (Tài chính – Kế toán) có luôn chi phí phụ cấp.

## Bảng lương theo công
- Bản in `/lotus/in-luong` và file Excel không còn cột giờ, giờ đêm, tăng ca:
  - **Công nhân công nhật** theo tổ (tổ trên hồ sơ, không có thì bộ phận, không có thì "Chưa xếp tổ"), mỗi tổ một
    trang: Công, Đơn giá công, Tiền công, Ngày PC, Phụ cấp, Thuế TNCN, Tạm ứng, Thực lĩnh, Ký nhận.
  - **Nhân viên hưởng lương tháng**: Lương CB, Công, Lương theo công, Phụ cấp, BH người LĐ, Thuế TNCN, Tạm ứng, Thực lĩnh.
  - Đội khoán giữ nguyên. Chỉ in người có công hoặc có tiền trong tháng.
- Tạm ứng = phiếu tạm ứng lương của tháng đã chi (Tài chính – Kế toán), giống danh sách chuyển khoản lương.
- Excel: sheet Công nhân, Lương tháng, Chi tiết (kế toán) (đủ cột cũ cho kế toán), Đội khoán, Kiểm tra.
- Bảng công tháng in `/lotus/in-cong` liệt kê theo tổ, chỉ người có ngày công; dấu + là ngày có phụ cấp,
  cột Ngày phụ cấp thay cho Giờ làm.

## Đơn giá công nhật chung
- `Lotus Pay Rate` loại Daywork, mặc định 290.000 đ/công từ 01/10/2026.
- Nhân sự › Kỳ công & bảng lương › Phụ cấp & đơn giá công: đổi mức, và **Ghi đơn giá chung** cho công nhân công nhật
  chưa có đơn giá (ghi vào hồ sơ và phân bổ lương, người đã có đơn giá riêng giữ nguyên).

## Mã
- `lotus_farm/work_allowance.py`, `payroll_rules.rate_in_force` / `allowance_amount` (`tests/test_payroll_rules.py`).
- `daily_attendance.save` / `set_allowance`, `hr_period._sheet`, `www/lotus_payroll_print.layout`, mẫu in
  `templates/print/body/payroll.html`, `timesheet.html`.
- Kiểm thử tích hợp: `tests/integration/verify_work_allowance.py`.
