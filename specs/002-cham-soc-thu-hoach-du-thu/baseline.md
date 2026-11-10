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
