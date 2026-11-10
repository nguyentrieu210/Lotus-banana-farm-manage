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

## Phase 7 (US6, xưởng theo nguồn buồng)

- `lotus_farm/tests/test_packout_rules.py`: 8/8 qua (tổng kg nguồn bằng kg vào; số buồng không vượt số đã thu chưa vào xưởng; thùng chia nguyên theo kg; kg/buồng, thùng/buồng, tỷ lệ; giá trị nhập kho theo kg × giá lô).
- `tests/integration/verify_packout_sources.py`: 16 kiểm tra qua (ca nhận từ hai lô, chặn nhận quá, chặn đóng quá kg vào, chia thùng 121/60, truy vết ra dòng thu và dòng phun, phiếu nhập kho nháp đúng giá trị từng lô, một phiếu một ca, chỉ kế toán lập).
- Các test tích hợp khác vẫn qua. Frontend 634/635 lần đầu (thiếu nhãn "Packhouse Shift Source"), đã sửa. Trình duyệt: màn Xưởng và hộp thêm ca không lỗi, không tràn ngang.

## Phase 9 (US1 phần sau, phiếu giấy và đọc ảnh)

- `lotus_farm/tests/test_lot_paper_form.py`: 6/6 qua (bố cục cột; lô/cột không có trên phiếu thành ghi chú; số buồng không nguyên, vượt số còn lại, thu hoạch thiếu kg, không rõ màu, hủy thiếu lý do bị đánh dấu; ô in sẵn mà trống được nêu).
- `tests/integration/verify_paper_form.py`: 14 kiểm tra qua, với kết quả AI giả lập (in phiếu, trang in có mã và cột, đọc ảnh ra dòng nháp có cờ, lô đã nhập tay giữ nguyên, chặn gửi khi còn dòng chưa kiểm, lưu lô thì hết cờ và gửi được).
- Frontend 640/640 qua. Trình duyệt: in phiếu từ màn Hôm nay mở trang A4 ngang đúng tổ, ngày, màu dây Cam tuần 46.
- Chưa đo tỷ lệ đọc đúng trên phiếu thật (T083): cần 10 ảnh phiếu thật của vườn.

## Phase 10 (US5, báo cáo theo người xem và menu 7 mục)

- `tests/integration/verify_field_reports.py`: 12 kiểm tra qua (Sáng nay đủ 6 câu hỏi; Tuần có thu hoạch, xưởng, việc theo lô, tình trạng lô cho bản đồ, thẻ dự thu nói rõ có bản chốt hay không; Tháng có kg/buồng, thùng/buồng theo lô, vật tư báo dùng so với xuất kho, công và tiền theo lô). `verify_bunch_forecast.py` vẫn qua với sổ cắt bắp chuyển sang ribbon_board.
- Frontend 611/611 qua (đã xóa các test của báo cáo pivot). Trình duyệt: menu Việc hằng ngày còn Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu, Báo cáo, Thiết lập; ba tab báo cáo và bản đồ tình trạng lô hiện đúng, không lỗi, không tràn ngang.

## Phase 11 (hoàn thiện)

- Hiệu năng trên máy test local (máy chủ, tốt nhất của 3 lần, dữ liệu LOTUS-222 bản sao): Hôm nay `lot_report.today` 123 ms; lưu một lô `save_lot` 203 ms; Giao việc `care_cycle.due` 38 ms; Màu dây `ribbon_board.board` 34 ms; báo cáo Sáng nay 147 ms, Tuần 109 ms, Tháng 19 ms; Dự thu toàn vườn `block_forecast.board` 2.159 ms. Đều trong mục tiêu của plan.md (2 giây, 1 giây, 3 giây); dự thu toàn vườn sát ngưỡng nhất.
- Hướng dẫn mới: docs/FIELD_REPORT.md, docs/CHAM_BUONG_DU_THU.md. Mục "Có gì mới" 2026-11-10. Kế hoạch triển khai: deploy.md.
