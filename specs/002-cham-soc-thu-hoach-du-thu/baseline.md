# Mốc kiểm chứng

## T001 Bản local (10/11/2026)

- Nhánh `002-cham-soc-thu-hoach-du-thu` tách từ main `df7bd70`. Container `lotus-vps-test-*` chạy đúng mã `df7bd70` (so nội dung, bỏ qua kiểu xuống dòng).
- Site `frontend` cổng 8097. Dữ liệu là bản sao site local cũ, không phải dữ liệu VPS.
- Nạp mã vào container: `scratchpad/sync.sh` (chép mã, xóa file đã bỏ, `migrate` hoặc `restart`).

## T002 Test mốc trước khi sửa

- Frontend: `node --test tests/*.test.js` → 645 qua, 0 lỗi (3 phút 52 giây).
- Python thuần, chạy bằng Python 3.12 trên Windows (`PYTHONUTF8=1`): test_bunch_flow_rules 28, test_bunch_forecast_engine 30, test_bunch_posting_rules 29, test_bunch_report_rules 35, test_forecast_snapshot 11, test_care_stage_rules 5, test_work_report_rules 11, test_report_filter_rules 13, tests/test_field_report_rules 10, tests/test_block_forecast_engine 13, tests/test_payroll_rules 7, tests/test_finance_rules 13: đều qua.

## T003 Sao lưu bản local

- `sites/frontend/private/backups/20261110_151446-frontend-database.sql.gz` (sau khi chuyển sổ buồng).

## Phase 2 (sổ lô nền)

- Dữ liệu local trước khi chuyển: 38 dòng Lotus Bunch Event (sổ cắt bắp đầu kỳ, 593 buồng), 0 Lotus Work Entry, 25 Lotus Work Assignment.
- Dự thu LOTUS-222 trước và sau khi chuyển sang sổ lô: 7.347 buồng (cắt bắp 577, theo cây 6.770), 144.001,2 kg, 1.446 đợt. Bằng nhau.
- `lot_ledger_migrate.commit` chạy lần hai: 0 dòng chuyển thêm.
- `tests/integration/verify_lot_ledger.py`: 24/24 qua.

## Phase 3 (US1, báo cáo ngày theo lô)

- `tests/integration/verify_bunch_forecast.py` viết lại cho lot_report: tất cả qua.
- Frontend: 635/635 test qua; kiểm trên trình duyệt (máy tính và điện thoại): chọn lô, nhập Cắt bắp 12, lưu, thẻ lô hiện "1 việc · Chưa gửi", không lỗi console.

## Phase 4 (US2, màu dây và thu hoạch)

- Bảng màu dây LOTUS-222 local: 593 buồng còn trên cây, 4 đợt màu (Đỏ 43 lần 1: 113; Trắng 44 lần 1: 182; Tím 45 lần 1: 236; Tím 45 lần 2: 62), khớp sổ cắt bắp đầu kỳ. Chưa màu nào đến tuổi thu (cắt sớm nhất 21/10, thu từ khoảng 20/12).
- `lotus_farm/tests/test_ribbon_board.py` + `test_bunch_report_rules.py`: 39/39 qua. `verify_bunch_forecast.py`: tất cả qua (thêm 7 kiểm tra bảng màu dây và danh sách cần thu).
- Frontend: 638/638 test qua. Trình duyệt máy tính và điện thoại (tab Xác nhận): không tràn ngang, không lỗi console.
- `bunch_report.stock` và `BunchStockCards.vue` đã xóa; tồn theo màu có lọc kiểu pivot vẫn ở `bunch_report.sections`.

## Phase 5 (US3, vòng chăm sóc)

- `lotus_farm/tests/test_care_cycle_rules.py`: 9/9 qua (đến hạn = xong gần nhất + vòng; chưa làm thì từ ngày áp dụng; chỉ dòng "xong cả lô" mới tính; luật khu trước luật vườn; phiên bản và luật theo mùa; việc không có vòng thì không hiện).
- `tests/integration/verify_care_cycle.py`: 36 kiểm tra qua (đặt và duyệt vòng, giao 2 lô một lần, đổi tổ và huỷ phải có lý do, làm dở không tính xong, báo xong thì sang vòng sau, khoán cả lô chờ nghiệm thu rồi khóa và tính tiền). `verify_lot_ledger.py`, `verify_bunch_forecast.py` vẫn qua.
- Patch `care_cycle_rules` chạy trên local: 0 luật cũ (local không có). Trên VPS luật cũ có mốc trồng/chọn chồi sẽ được lưu ra `private/files/work_schedule_rule_legacy_*.json` rồi xóa.
- Frontend: 631/631 test qua. Trình duyệt: Giao việc theo vòng (Cắt lá 64 lô quá hạn, Sửa ống nước khu A 13 lô), hộp giao theo khu, bảng lô × việc, Vòng chăm sóc với bản chờ duyệt; không tràn ngang, không lỗi console.

## Phase 6 (US4, dự thu chốt tuần)

- `lotus_farm/tests/test_forecast_snapshot.py`: 15/15 qua (thêm: chỉ dòng xác nhận trước mốc và chưa hủy trước mốc; tham số duyệt sau mốc không tính; tuần lỡ được bù, tối đa 8 tuần).
- `verify_bunch_forecast.py`: tất cả qua, thêm 7 kiểm tra bản chốt tuần (mở app sau nhiều tuần thì có đủ bản các thứ Hai; bản chốt đúng 0 giờ thứ Hai; không tính dòng xác nhận sau mốc; tổng bằng dự thu tính theo mốc; mở lại không tạo thêm; hai phiên cùng lúc vẫn một bản).
- Chạy thật trên máy test: bootstrap xếp `ensure_all` vào hàng short, worker chạy xong trong khoảng 1 giây, cache đánh dấu tuần 2026-11-09.
