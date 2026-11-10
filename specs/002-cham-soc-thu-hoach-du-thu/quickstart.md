# Quickstart: kiểm chứng tính năng

Chạy trên bản local (Frappe cổng 8097, Vite 5173) với bản sao dữ liệu thật. Tham khảo [contracts/api.md](contracts/api.md) và [data-model.md](data-model.md).

## Chuẩn bị

1. Build bản local bằng `rebuild-local.cmd` (có migrate).
2. Chạy `lot_ledger_migrate.preview`, rồi `commit`. Kết quả: 593 dòng cắt bắp đầu kỳ chuyển sang sổ lô (Đỏ 113, Trắng 182, Tím 298). Chạy lại thì không tăng.
3. Tạo tài khoản thử cho một tổ trưởng và cho đội trưởng Đội khu A + B.

## Kịch bản

| # | Làm | Kết quả mong đợi |
|---|---|---|
| 1 | Tổ trưởng mở Hôm nay | Thấy thẻ các lô của tổ. Mở một lô thì có đủ các nhóm việc trong một hộp |
| 2 | Nhập cắt bắp 120 buồng ở A5 vào ngày thứ Ba | Màu dây tự gán đúng tuần, lần cắt 1 |
| 3 | Nhập phun thuốc có cách ly 14 ngày ở A5, gửi, đội trưởng xác nhận | Bắt buộc nhập vật tư và liều; A5 cách ly đến đúng ngày |
| 4 | Nhập thu hoạch A5 trong thời gian cách ly | Bị chặn, báo ngày hết cách ly |
| 5 | Đội trưởng nhập hộ cho tổ rồi tự xác nhận | Không cho; phải do quản lý vườn xác nhận |
| 6 | Sửa một dòng đã xác nhận | Phải ghi lý do; dòng cũ chuyển Voided, có dòng mới thay |
| 7 | Cùng một người làm cùng việc ở hai lô trong một buổi | Tổng của người đó trong buổi là 1, chia theo khối lượng hai lô |
| 8 | Nhập bao buồng vượt số đã cắt của đợt màu | Bị chặn |
| 9 | Mở bảng màu dây | Từng ô khớp số đã nhập; đợt đến tuổi nằm trong danh sách cần thu |
| 10 | Đặt vòng cắt lá 14 ngày; báo xong cắt lá A5 ngày 01/11 | Ngày 15/11 A5 đến hạn; ngày 17/11 quá hạn 2 ngày |
| 11 | Đội trưởng giao 6 lô đến hạn cho tổ 2 | Có 6 Round; 6 lô hiện trên Hôm nay của tổ 2 |
| 12 | Tổ báo xong một việc khoán cả lô | Lô chờ nghiệm thu; chỉ có tiền khi nghiệm thu đạt |
| 13 | Không ai mở ứng dụng từ thứ Bảy đến trưa thứ Hai, sau đó mở | Có bản chốt tuần theo mốc 0 giờ thứ Hai; dòng xác nhận sau mốc không nằm trong bản chốt |
| 14 | So số dự thu ở Tổng quan, kế hoạch tài chính và trang dự thu | Ba nơi cùng một số |
| 15 | In phiếu giấy của tổ 3, ghi tay, chụp ảnh, tải lên | Các dòng được điền sẵn, dòng nghi ngờ có đánh dấu; chưa kiểm hết thì không gửi được |
| 16 | Một ca đóng gói nhận buồng từ hai lô | Thùng chia theo kg; truy vết ra lô, đợt màu và các lần phun |
| 17 | Mở Sáng nay, Tuần, Tháng | Mỗi câu "tổ nào chưa báo", "lô nào quá hạn", "tuần này cần thu bao nhiêu" trả lời được bằng một thẻ; xuất được Excel |
| 18 | Đếm số mục menu của cả mảng | Tối đa 7 |
| 19 | Ca đóng gói xong, kế toán lập nhập kho thành phẩm | Phiếu nháp có thành phẩm, phụ phẩm theo kg; giá trị chia theo kg nguồn của từng lô |
| 20 | Chạy `legacy_purge.preview` trên bản sao dữ liệu thật | Có số dòng từng bảng cũ và số giá trị trên chứng từ; không ghi gì |
| 21 | Chạy `legacy_purge.commit` | Có tệp JSON cho từng bảng, số dòng khớp `preview`. Không còn bảng cũ trong cơ sở dữ liệu, mã và menu. Chạy lại không lỗi |
| 22 | So sổ cái, tồn kho và bảng lương các tháng đã khóa trước và sau khi dọn | Không thay đổi |
| 23 | Lập phiếu xuất kho thuốc | Chỉ còn "Thủ công" và "Theo yêu cầu đã duyệt" |
| 24 | Nhập kiểm tra sâu bệnh ở A5 | Bắt buộc bệnh, số cây và mức độ; hiện ở báo cáo phun bón |

## Kiểm thử

- `cd frontend && node --test tests/*.test.js`
- Unit test Python cho các module thuần: `lot_ledger_rules`, `care_cycle_rules`, `packout_rules`, `field_report_rules`.
- Integration qua bench: `tests/integration/verify_lot_ledger.py`, `verify_care_cycle.py`, `verify_packout_sources.py`, và `verify_bunch_forecast.py` sau khi đổi nguồn sang sổ lô.
- Chạy lại toàn bộ integration của kho, tài chính, lương (`verify_costing.py`, `verify_purchase_flow.py`, `verify_warehouse_audit.py`, `verify_timekeeping.py`, `verify_hr_audit_fixes.py`) sau khi bỏ phần dùng bảng cũ.
- Test quét mã: không còn tên bảng nào trong danh sách xóa ở [cleanup.md](cleanup.md).
- Tổng kiểm:
  - Công của mỗi người trong mỗi buổi bằng 1.
  - Tổng tiền đã chia bằng tiền của dòng.
  - Tổng buồng dự thu của mỗi lô không vượt số tính theo cây của lô đó.
