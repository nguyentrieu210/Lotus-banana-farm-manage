# Lotus HR / Chấm công – Bàn giao triển khai (18/10/2026)

## Mục tiêu
Quản lý ai đang làm việc ở vườn nào, đội/tổ nào, chức danh và chức vụ gì, ca nào; dữ liệu quẹt máy đến HRMS để xét công, không tự tính lương. Giữ nguyên ERPNext/HRMS và các module Kho / Công việc ngoài vườn / Mua hàng.

## Màn vận hành
- `/lotus/nhan-su`: tab **Cơ cấu · Import · Máy chấm công** gồm Sơ đồ tổ chức, Nhập Excel, Máy chấm công, Log máy.
- `/lotus/cham-cong`: chấm công nhân viên, công đội khoán và bảng tổng hợp công ngày/tháng có sẵn.
- `/app/shift-type`, `/app/shift-assignment`, `/app/employee-checkin`, `/app/attendance`, `/app/leave-application`: quản lý chuyên sâu qua HRMS.

## Cơ cấu mẫu (KHÔNG tự áp dụng)
Ban quản lý, Kỹ thuật, Vật tư, Văn phòng, Xưởng đóng gói, Cơ khí–Điện nước–Bảo vệ, Đội A/B/C/D. Mỗi đội 55 ha, mỗi đội có 2 tổ 25 ha. Tổng 4 × 55 = 220 ha. Hai tổ chỉ phụ trách 50 ha/đội nên còn **5 ha/đội chưa rõ**. Không tự điều chỉnh số liệu này. Bấm nút "Tạo bộ phận và 12 đội/tổ mẫu" chỉ sau khi xác nhận và có quyền HR Manager. Không tạo nhân viên, lương hay quyền User từ sơ đồ.

## Dữ liệu chuẩn – không nhân bản HRMS
- HRMS: `Employee`, `Department`, `Designation`, `Shift Type`, `Shift Assignment`, `Employee Checkin`, `Attendance`, `Leave Application`, bảng lương.
- Lotus: `Lotus Staff Assignment` (lịch sử đội/chức vụ), `Lotus Attendance Device` (thiết bị), `Lotus Attendance Identity` (mã máy ↔ nhân viên có hiệu lực), `Lotus Attendance Punch` (log gốc, có khóa chống trùng và cấm sửa/xóa).
- Work Team thêm trường đội cha, khu và diện tích kế hoạch. Tổ/đội nội bộ và đội khoán độc lập được phân biệt.

## Import danh mục và dữ liệu
Tải mẫu CSV theo từng loại trên giao diện; nhận `.csv` UTF-8 có BOM và `.xlsx` tối đa 2,5 MB / 500 dòng:
1. Department – bộ phận.
2. Designation – chức danh.
3. Work Team – đội/tổ.
4. Employee – hồ sơ nhân viên (Inactive, chờ tiếp nhận; không tự tạo User).
5. Staff Assignment – chức vụ/phân công theo ngày.
6. Shift Type – ca làm.
7. Shift Assignment – dự thảo phân ca (chưa submit).
8. Device Mapping – mã người trên máy ↔ Employee theo khoảng hiệu lực.
9. Checkin CSV – log giờ quẹt máy.

Giao diện xem trước báo lỗi dòng, giữ nguyên số 0 đầu khi Excel được đặt Text, xác nhận mới ghi. Các dòng sai bắt phải sửa và xem lại. Thử nghiệm dùng giao dịch rollback. Không nhập danh sách người thật hoặc tự kích hoạt khi chưa có quyết định.

## Luồng máy chấm công
Máy → file CSV/agent tại vườn → `lotus_farm.hr_operations.ingest_device_events` (API HTTPS) → Lotus Attendance Punch (chống trùng, chỉ nhận log) → ghép mã nhân viên/kiểm tra hiệu lực → HR Manager bấm chuyển → Employee Checkin HRMS → kiểm tra ca, nghỉ, thiếu quẹt → duyệt Attendance → đối soát công/lương sau khi có hồ sơ, thỏa thuận và duyệt riêng.

Bộ gửi file tham khảo: `tools/lotus_attendance_bridge.py`. Máy phải có model, firmware, giao thức và khả năng export/API phù hợp mới có thể chạy đồng bộ tự động. Không tuyên bố đã nối trực tiếp với thiết bị khi chưa có kết nối thật.

Các biến môi trường trên máy nối thiết bị:
`LOTUS_URL` (HTTPS), `LOTUS_API_KEY`, `LOTUS_API_SECRET`, `LOTUS_COMPANY`, `LOTUS_DEVICE`.
Dùng riêng tài khoản Frappe API có role `Lotus Integration User`, User Permission cho Company/Farm, quyền đọc thiết bị và tạo log. Không đặt token trong Git hoặc file CSV; không đưa mẫu vân tay, ảnh khuôn mặt lên Lotus. Máy mất mạng: giữ file nguồn rồi gửi lại, hệ thống loại log trùng.

## Quyền
- HR Manager: nhập và duyệt cơ cấu, danh mục, nhân viên, máy, log và liên kết Employee Checkin theo quyền HRMS.
- HR User: xem danh mục và dữ liệu nhân sự thuộc phạm vi được cấp.
- Lotus Integration User: chỉ nhận log qua API và xem thiết bị khi đã có Company/Farm User Permission.
- Đội trưởng/tổ trưởng: dùng chức năng chấm công/công việc được cấp riêng; không được quyền quản trị hồ sơ nhạy cảm hoặc tính lương.
- Guest: không đọc hay tạo dữ liệu HR. Sinh trắc học không được ghi.

## Kiểm thử bắt buộc trước phát hành
- `npm test`, `npm run build`.
- Python compile; reload-doc bốn DocType mới, `bench --site frontend execute lotus_farm.hr_setup.install_fields`.
- `bench --site frontend execute lotus_farm.hr_full_uat_check.run` (sinh dữ liệu giả, kiểm tra log trùng, map, checkin, ca, import, Guest; luôn rollback).
- Sao lưu database + files trước nâng cấp. Không tự chạy full `migrate` trên production khi không cần.
- Đường dẫn công khai yêu cầu login, JS assets trả HTTP 200, 5 container backend/frontend/queue/scheduler healthy.

## Giới hạn và quyết định của Lotus
- Chưa kiểm chứng kết nối LAN/ADMS/cloud đến **máy thực tế** do chưa có model/firmware/IP/SDK/API và thông số bảo mật. File CSV và bridge HTTPS đã có.
- Việc chấm công từ xa/không mạng cần quy trình ngoại lệ đã xác nhận. Không tự xem log quẹt là 1 công; không tự duyệt công/khoán hoặc phát hành lương.
- Phải xác định ai duyệt công, lịch ca, cách xử lý ca đêm, giờ tăng ca, người chuyển tổ giữa ngày và phần 5 ha/đội còn lại.
- Thu thập và sử dụng dữ liệu cá nhân theo phạm vi cần thiết; thời gian lưu, thông báo, quyền truy cập hồ sơ và nghĩa vụ lao động/pháp lý phải được Lotus kiểm tra.

## Phục hồi
- Image trước nâng cấp: `lotus-plan-norm-live:v1-20261018`.
- Image HR dự kiến: `lotus-hr-complete:v1-20261018`.
- Script `deployment/deploy-hr-complete.ps1 -Rollback` trả Docker về image trước; **không tự khôi phục DB**. Bảng mới không tự làm thay đổi Employee/Attendance thật.
## Kết quả triển khai live thực tế 18/10/2026
- **Đã cập nhật** 5 dịch vụ: `lotus-backend-1`, `lotus-frontend-1`, `lotus-scheduler-1`, `lotus-queue-short-1`, `lotus-queue-long-1` sang `lotus-hr-complete:v1-20261018`.
- MariaDB hoạt động healthy; scheduler có 2 worker online. Redis/websocket giữ nguyên.
- **Sao lưu trước deploy** thành công: `/home/frappe/frappe-bench/sites/frontend/private/backups/20261018_234229-frontend-*` (database, private/public file, site config).
- Đã reload-doc 4 DocType mới, thêm 3 trường Work Team, clear cache; KHÔNG chạy full bench migrate.
- **Build Vite** thành công, frontend `npm test` **220/220 pass**.
- **UAT Frappe chạy sau deploy**: schema, tổ chức (seed lặp không tạo trùng), máy/mapping, log trùng, chuyển Employee Checkin, chống overlap, phân công, CSV, XLSX giữ số 0, Employee nhập mới Inactive và không User, import Shift Type / Shift Assignment nháp, Guest bị chặn. Tất cả đạt và `UAT_ROLLBACK_COMPLETE`.
- `https://lotus.gpcds.site/lotus/nhan-su`, `/lotus/cham-cong`, `/lotus/kho` đều phản hồi redirect đúng về đăng nhập nếu chưa xác thực. Không kiểm thử giao diện bằng một tài khoản người dùng thật trong trình duyệt.
- **Không import dữ liệu nhân sự thật**, không tự seed cơ cấu mẫu, không tự bật Attendance Auto Attendance, không tự tạo Salary Slip.
- Đồng bộ liên tục từ máy chấm công vật lý cần thiết lập bridge/token của từng máy; chỉ luồng nhập CSV/XLSX và API chuẩn đã có.
