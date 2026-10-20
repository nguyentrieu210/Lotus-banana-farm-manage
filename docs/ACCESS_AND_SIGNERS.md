# Phân quyền và cấu hình người ký

Mở **Người dùng → Hồ sơ & quyền**:

- **Hồ sơ**: kích hoạt tài khoản và gắn đúng nhân sự HRMS. Một nhân sự chỉ gắn một tài khoản; không lấy liên kết đang thuộc người khác.
- **Vai trò & quyền**: toàn bộ Role lấy từ ERPNext, có tên tiếng Việt và mã gốc. Role mới tự xuất hiện; role tự động và role bị khóa chỉ xem. ERPNext gỡ role đã khóa khi lưu hồ sơ, UI báo rõ việc này. Mẫu vai trò chỉnh tại quản trị nâng cao.
- **Vườn & tổ**: cấp vườn bắt buộc cho nghiệp vụ vườn, kể cả tài khoản có System Manager. Tổ trưởng/giám sát hiện trường cần cấp thêm tổ. Các phạm vi nâng cao (công ty, kho, giới hạn theo loại chứng từ...) hiển thị và được giữ nguyên.
- **Kiểm tra quyền**: xem quyền theo role trên các loại dữ liệu nghiệp vụ chính, quyền đọc từng vườn đã qua controller và điều kiện ký từng bước. Đây là cấu hình đã lưu; quyền trên chứng từ cụ thể còn chịu trạng thái, chủ sở hữu và giới hạn dữ liệu.

## Người ký

Danh sách người ký gồm nhân sự **đang làm việc**, thuộc **công ty của chứng từ**, gắn tài khoản **đang hoạt động**, có một trong các role của bước ký. Chức danh hoặc phòng ban không tự cấp quyền phê duyệt.

| Bước | Một trong các role phù hợp |
| --- | --- |
| Phụ trách bộ phận | Lotus Farm Manager, Lotus Field Supervisor, Lotus Warehouse Manager, Lotus Team Leader |
| Kế toán / Mua hàng | Lotus Purchasing Buyer, Purchase Manager, Accounts User, Accounts Manager |
| Giám đốc duyệt đề xuất mua / đơn mua | Lotus Purchase Approver |
| Thủ kho | Lotus Warehouse Manager, Lotus Stock Reviewer, Stock Manager, Lotus Warehouse Receiver |
| Nhân sự duyệt kỳ công | HR Manager, HR User |
| Giám đốc duyệt kỳ công / đề xuất cấp vật tư | Lotus Purchase Approver, Lotus Farm Manager |
| Người giao / nhận phiếu kho | Nhân sự có tài khoản hoạt động trong cùng công ty |

Cấp trên trực tiếp (`Employee.reports_to`) được gợi ý ở bước Phụ trách bộ phận **khi đủ role**. Người lập có thể chọn người khác trong danh sách hợp lệ. Lựa chọn hợp lệ đã dùng trước được ưu tiên giữ lại; cấu hình không tự chọn người ngoài quyền.

Máy chủ kiểm tra lại nhân sự, công ty, trạng thái tài khoản và role khi gửi, chuyển người ký hoặc ký. Chỉ người được chỉ định và đang đến lượt mới ký. Không tự tạo nhân sự, tự gán role hoặc gửi thông báo khi chỉ mở/cấu hình màn phân quyền.

Tên Role, Department, Designation và liên kết ERPNext giữ nguyên. Bản dịch tiếng Việt nằm trong `lotus_farm/translations/vi.csv`; danh mục dùng chung ở `lotus_farm/localization.py`. `install_translations` bật dịch hiển thị Department/Designation và bổ sung bản dịch tên phòng ban có hậu tố công ty, giữ lại các bản dịch do quản trị tự cấu hình.

## Kiểm tra

`npm test`, `npm run build` trong frontend; `tools/verify_mobile_purchase_dom.mjs`; kiểm thử site `tests/integration/verify_access_catalog.py` và `tests/integration/verify_signing.py` dùng dữ liệu tạm, rollback. Khi chạy kiểm thử ký trên dữ liệu thật, vô hiệu hóa gửi thư và enqueue trong tiến trình kiểm thử.
