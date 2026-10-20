# Nhật ký công việc

Nhân sự tổng hợp nhập thủ công từ báo cáo Zalo, một bảng theo vườn/ngày.
Nhật ký chỉ để theo dõi: không tạo Daily Work Result, kế hoạch, công nhân viên,
phiếu lương, vật tư hoặc chứng từ kho. Không có bước gửi hoặc duyệt.

## Truy cập

- Máy tính: `/lotus/nhat-ky-cong-viec?farm=…&date=YYYY-MM-DD`.
- Điện thoại: `/work?tab=journal` hoặc Nhật ký công việc từ trang chủ app Công việc.
- Mọi tài khoản đăng nhập có User Permission Farm được xem toàn bộ nhật ký của vườn.
- `Lotus Work Journal Clerk` nhập và sửa nhật ký mình lập; cần quyền Farm tương ứng.
- `Lotus Farm Manager` sửa trong vườn được cấp; sửa thay người lập phải có lý do.
- Việc cài đặt chỉ tạo role; không gán tài khoản hoặc quyền vườn tự động.

## Dữ liệu

`Work Daily Journal` độc lập, có unique index `(farm, posting_date)` và lịch sử Version.
Các dòng có ID ổn định, tổ, lô lớn, danh mục việc, đơn vị snapshot, số lượng, tổng công,
ghi chú. Cờ `has_quantity`/`has_workdays` phân biệt không có số liệu với số 0.
Không cộng sản lượng khác công việc/đơn vị. Tổng công là tổng các dòng, không quy đổi từ người/giờ.

API `lotus_farm.work_journal`: bootstrap, catalogue, get, save, list, summary, history, export.
`save` yêu cầu `expected_user`, `expected_modified` và `request_id`. Lưu toàn bộ bảng nguyên tử.
Mỗi request ID chỉ dùng cho một payload. Retry giữ nguyên payload trả lại kết quả đã lưu.
Mã yêu cầu cũ với payload khác bị từ chối; thay đổi phiên bản trả TimestampMismatchError.
Các request được giữ trong Work Journal Request, không cấp đọc/ghi qua REST cho người nhập.
Đọc trực tiếp nhật ký vẫn kiểm tra Farm; ghi trực tiếp bị chặn, phải đi qua save.

## Bản nháp và đối chiếu

Bản nháp lưu trên thiết bị theo user/farm/date, không gửi nền. Chưa xác nhận được lần lưu
thì giữ nguyên request ID để thử lại. Khi xung đột, so bản máy chủ với bản đang nhập trước
khi quyết định dùng bản máy chủ hay tiếp tục chỉnh bản nháp trên phiên bản mới.
Lịch sử có người sửa, thời gian, thay đổi dòng và lý do sửa thay.
Excel dùng cùng phạm vi/bộ lọc, số trống để trống và vô hiệu hóa công thức từ ghi chú.

## Kiểm chứng

- `npm test`, `npm run build` trong frontend.
- `tests/integration/verify_work_journal.py`: fixtures rollback, quyền/API/trực tiếp,
  validation, retry, xung đột, row ID và không thay đổi sổ nghiệp vụ chính thức.
- `tests/integration/verify_work_journal_concurrency.py`: **chỉ trên DB clone disposable**,
  hai kết nối riêng đồng thời, có commit để kiểm tra lock và unique index.
- Backup trước migrate; đối chiếu DocField hiện có với source; migrate thử trên bản sao.
- Nghiệm thu nội dung báo cáo Zalo thật cần người dùng cung cấp/đối chiếu; không tự lấy tin nhắn.
