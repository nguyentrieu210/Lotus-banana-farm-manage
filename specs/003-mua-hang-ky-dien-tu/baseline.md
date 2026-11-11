# Mốc kiểm thử ban đầu (T003)

Ngày 10/11/2026, mã nhánh `003-mua-hang-ky-dien-tu` từ main df7bd70. Môi trường: container `lotus-003-test` (image `lotus-local-test:20261104`, mount worktree), site `mua.test` khôi phục từ bản sao lưu `frontend` lúc 15:14 ngày 10/11, kèm file riêng tư.

## Lỗi có sẵn, không do spec 003

| Bộ test | Kết quả | Nguyên nhân |
|---|---|---|
| `python -m unittest discover -s tests` | 336 test; 3 lỗi, 1 hỏng | 3 ca của `test_warehouse_guards` gọi `warehouse.create_draft`; hàm này dùng `frappe.get_meta`, nhưng bản `frappe` giả trong test không có. `test_block_forecast_integration` chờ 22 tham số dự thu, mã hiện có 24. Không file nào trong hai vùng này bị spec 003 sửa |

## Test phải sửa theo thay đổi của spec 003

Đã sửa trong cùng nhánh. Lần chạy `npm test` sau đó: 651 test, qua hết.

- `frontend/tests/approval-self-role.test.js`: đơn mua phải có chữ ký người duyệt được chỉ định, không còn duyệt theo vai trò hay theo chính sách.
- `frontend/tests/mobile-signature-settings.test.js`: bản PDF đơn mua đã ký nay do `signed_copy` lưu.
- `frontend/tests/signature-v2.test.js`: đã gỡ QR ký và ký nháy riêng của đơn mua; ký nháy lấy từ bước kiểm tra; QR chỉ để xác minh, có so với bản lưu.
- `frontend/tests/ui-language-audit.test.js`: thêm tên tiếng Việt cho DocType `Lotus Signed Copy`.

## Test tích hợp đã chạy trên `mua.test`

`tests/integration/verify_signing.py` qua hết. Nội dung kiểm:
- phiếu kho;
- đơn mua do đúng người duyệt được chỉ định ký;
- kỳ công;
- thông báo phiếu chi đến app Mua hàng;
- thông báo lỗi chỉ ghi nhật ký, không làm hỏng thao tác ký.

Script cần ba chỉnh sửa để chạy trên bản sao này:
- đọc `SITE`;
- nhân viên thử vào làm từ 01/10/2026 để không lọt vào kỳ công tháng 9;
- đơn mua mẫu được coi là đơn trước luồng mua mới.
