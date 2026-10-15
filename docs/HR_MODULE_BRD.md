# Lotus HR – BRD và thực thi (15/10/2026)

## Mục tiêu & phạm vi
Chuỗi nghiệp vụ ứng tuyển → xét tuyển → tiếp nhận → phân công tổ → chấm công → nghiệm thu công → đối soát lương. **ERPNext/Frappe HRMS là nguồn chính thức cho Employee/Salary Structure Assignment/Payroll**, Lotus chỉ xây lớp nghiệp vụ nông trường. Mọi mức lương phải được phê duyệt theo cá nhân, không suy ra từ chức danh.

## Danh mục nhân sự
- Chính thức (Permanent), hợp đồng xác định hạn (Fixed-term), thời vụ (Seasonal), thử việc (Probation) → Employee của HRMS.
- Đội khoán độc lập → Work Team loại Contractor + Lotus Crew Attendance. Không tạo hồ sơ nhân viên giả cho từng người của nhà thầu.
- Cơ cấu: Company → Department → Farm → Work Team nội bộ → Employee; Designation là chức danh, Employee Grade là bậc, reports_to là người quản lý.
- Danh mục chức danh được khai báo tại `hr_workspace.DESIGNATION_GROUPS`: điều hành, chăm sóc, nhà đóng gói, QC, kho, mua hàng, kế toán, cơ điện, nông học, UAV, hành chính.

## Mapping đối tượng dữ liệu
| BRD | Doctype/Frappe | Lotus |
|---|---|---|
| Tuyển dụng văn phòng/có email | Job Opening → Job Applicant → Interview → Job Offer | Dùng native |
| Ứng tuyển công nhân chỉ có SĐT | HRMS Job Applicant site này yêu cầu email | Lotus Candidate (không tự sinh email giả) |
| Tiếp nhận | Employee Onboarding / Employee | Employee Inactive/Pending → HR Manager duyệt → Active |
| Hồ sơ nhân viên | Employee | Liên kết farm/tổ, CCCD mã hóa, liên hệ khẩn, cơ chế công/lương |
| Danh mục tổ chức | Department, Designation, Employee Grade | Chức danh Lotus chỉ seed có chủ đích |
| Công ngày | HRMS Attendance / Leave | Lotus Chấm công |
| Khoán công | Work Type, Work Plan, Work Result, Crew Attendance | Chỉ đối soát; không đưa tiền khoán đội vào lương người |
| Lương | Salary Structure Assignment, Salary Slip, Payroll Entry | Đọc cấu hình/phát hiện thiếu; không tự ghi lương |
| Điều chuyển | Employee Transfer | Tái sử dụng native |

## Quy tắc chức năng
1. Ứng viên Lotus có tên, SĐT, nguồn, chức danh, farm, trạng thái; trạng thái cho phép: New→Screening→Interview→Offered→Hired, có Hold/Rejected theo state machine; Offered→Hired chỉ qua API tiếp nhận của HR Manager, transaction lock chống tiếp nhận lặp.
2. CCCD đúng 12 chữ số; dùng Frappe Password lưu mã hóa và HMAC để chống trùng. Truy cập nhạy cảm giới hạn HR Manager; bảng danh sách không trả giá trị CCCD. Hồ sơ mới không có quyền tự cấp tài khoản User.
3. Điều kiện Ready: CCCD, ngày/nơi cấp, SĐT, địa chỉ, liên hệ khẩn, chức danh, loại lao động, cơ chế lương. Chưa đủ thì vẫn Inactive.
4. Đơn giá khoán là số dự toán; kết quả nghiệm thu/phiếu khoán đội không phải Salary Slip. Lương nhân viên theo Salary Structure Assignment đã submit; công nhật/khoán/hỗn hợp phải có thỏa thuận, phân bổ, kiểm duyệt và áp dụng thời điểm hiệu lực.
5. Kỳ đối soát báo thiếu Salary Structure Assignment, phiếu công nháp, đội khoán chưa duyệt; không phát sinh chứng từ Payroll.
6. Các chức danh (công nhân chăm sóc, tuyển chồi, phun/bao buồng, QC, kho, đóng gói, tổ/đội trưởng, giám đốc farm...) phải có tên riêng. **Không lưu mặc định lương theo chức danh**.
7. Hồ sơ Employee, Job Applicant, Salary Structure Assignment của HRMS được giữ làm nguồn chuẩn, không nhân bản sang bảng Lotus HR độc lập.

## Phân quyền
- HR User: truy cập ứng viên và danh sách theo HRMS Company scopes; không có quyền API Lotus đọc CCCD/salary.
- HR Manager: quản lý hồ sơ nhạy cảm, duyệt tiếp nhận, payroll preflight; phải vượt kiểm tra permission chuẩn Frappe.
- Farm Manager, tổ trưởng, đội khoán: xem công/đơn việc được cấp, không đọc CCCD, tài khoản ngân hàng hay tiền lương người khác.

## Tiêu chí UAT và NFR
- Ứng viên không email vẫn đăng ký được; không nhảy New→Hired, không tiếp nhận cùng ứng viên hai lần.
- Phát hiện CCCD sai/đã có; hồ sơ chỉ lộ 4 số cuối trong chi tiết được phân quyền; kiểm tra Desk permlevel=1.
- Employee mới Inactive; sau khi hoàn thiện và duyệt sẽ Active, xuất hiện trong bảng công.
- Tổ contractor không được gắn vào Employee; test company/farm scope.
- Test API HR User không xem employee_detail, payroll_overview, set_onboarding_ready.
- Migrate sau backup; các test ghi dữ liệu giả phải rollback; không import hay seed dữ liệu người thật.

## Backlog chưa tự động hóa
- Liên kết thực nghiệm nghiệm thu sản lượng → phân bổ tới từng nhân viên → Additional Salary / Payroll Entry theo phê duyệt của HRMS.
- Hồ sơ hợp đồng/bản sao giấy tờ, nhật ký truy cập PII, quy trình nhận yêu cầu xem/chỉnh/xóa thông tin, thời hạn lưu/xóa tài liệu.
- Quản trị định biên theo farm/đội, import Excel và hợp đồng theo mẫu phê duyệt.
- Phân quyền theo từng farm/đơn vị, kiểm tra pháp lý lao động, BHXH và lương tối thiểu vùng hiện hành trước tính bảng lương thực.

**Lưu ý về lương:** Khoảng tham khảo trước đây (công nhân 7,5–10 triệu; tổ trưởng ~12 triệu; đội trưởng ~15 triệu; giám đốc farm ~20–22 triệu/tháng) là ngân sách nội bộ chưa xác nhận, không phải pháp luật bắt buộc hoặc lương của cá nhân. Không seed vào HRMS khi chưa có quyết định của chủ đầu tư.
