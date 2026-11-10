---

description: "Danh sách việc: làm lại chăm sóc vườn, chăm sóc buồng, thu hoạch, báo cáo và dự thu"
---

# Tasks: Làm lại chăm sóc vườn, chăm sóc buồng, thu hoạch, báo cáo và dự thu

**Input**: `specs/002-cham-soc-thu-hoach-du-thu/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md, cleanup.md

**Tests**: Có, theo nguyên tắc IV của constitution: unit test cho module thuần, integration test cho luồng ghi sổ, mount test cho component có hành vi.

**Quy ước đường dẫn**: Backend ở `lotus_farm/`, DocType ở `lotus_farm/lotus_farm/doctype/`, patch ở `lotus_farm/patches/` và đăng ký trong `lotus_farm/patches.txt`. Frontend ở `frontend/src/`, test frontend ở `frontend/tests/`, unit test Python ở `lotus_farm/tests/`, integration ở `tests/integration/`.

**Thứ tự phase** theo plan.md, không theo số ưu tiên:
- US6 làm trước US7, để có cách nhập kho thành phẩm mới rồi mới xóa cách cũ.
- US5 làm sau cùng vì đọc mọi phần.
- Phần nào được thay trong phase nào thì xóa phần cũ ngay trong phase đó.

## Phase 1: Setup (kiểm chứng)

**Purpose**: Có mốc để so trước khi đổi

- [x] T001 Kiểm nhánh `002-cham-soc-thu-hoach-du-thu` sạch và bản local chạy được (`rebuild-local.cmd`, site `frontend` cổng 8097, Vite 5173); ghi kết quả vào specs/002-cham-soc-thu-hoach-du-thu/baseline.md
- [x] T002 Chạy toàn bộ test hiện có làm mốc (`node --test` trong frontend/tests, unit test Python trong lotus_farm/tests, integration chính trong tests/integration); ghi các lỗi có sẵn vào specs/002-cham-soc-thu-hoach-du-thu/baseline.md
- [x] T003 Sao lưu cơ sở dữ liệu bản local trước khi đổi cấu trúc (bench backup); ghi đường dẫn tệp vào specs/002-cham-soc-thu-hoach-du-thu/baseline.md

---

## Phase 2: Foundational (sổ lô nền)

**Purpose**: Sổ lô, báo cáo ngày, buổi công có trọng số, chuyển sổ buồng, chặn thu hoạch khi cách ly. Mọi phần việc sau dựa vào phase này.

**⚠️ CRITICAL**: Không bắt đầu phần việc nào khi phase này chưa xong

- [x] T004 [P] Viết unit test cho quy tắc sổ lô trong lotus_farm/tests/test_lot_ledger_rules.py, gồm:
  - trạng thái Draft → Sent → Confirmed → Voided;
  - việc buồng "số lượng phải là số nguyên lớn hơn 0";
  - Cut Bud tự gán màu theo ngày làm (tuần và nửa tuần của `Bunch Tag`);
  - Bag, Harvest, Reject sau cắt: "bao, hủy sau cắt và thu cộng dồn không vượt số cắt bắp của lô và đợt màu đó";
  - Bud Injection, Care, Prop: "cộng dồn trong vụ không vượt số cây của lô";
  - Harvest: "kg phải lớn hơn 0", bị chặn khi ngày thu không sau ngày hết cách ly;
  - phun bón: bắt buộc vật tư, số lượng, liều;
  - kiểm tra sâu bệnh: bắt buộc bệnh, số cây bị, mức độ;
  - người xác nhận khác người nhập;
  - trọng số buổi "lớn hơn 0 và không quá 1; tổng theo người × ngày × buổi bằng 1";
  - ngày hết cách ly lấy ngày muộn nhất của các dòng phun đã xác nhận.
- [x] T005 Viết module thuần, không phụ thuộc Frappe, cho mọi quy tắc của T004 trong lotus_farm/lot_ledger_rules.py
- [x] T006 [P] Đổi Lotus Work Entry thành dòng sổ lô theo data-model.md trong lotus_farm/lotus_farm/doctype/lotus_work_entry/lotus_work_entry.json:
  - `assignment` bỏ bắt buộc; `farm_block`, `work_team`, `work_type` thành bắt buộc;
  - thêm `daily_report`, `stage`, `cycle_no`, `uom`, `area_ha`, `reason`, `reject_stage` (Before Cut, After Cut), `weight_kg`, `disease`, `severity` (Nhẹ, Vừa, Nặng);
  - thêm `state` (Draft, Sent, Confirmed, Voided), `source_type` (Daily, Photo, Opening Import, Manual), `source_key` (duy nhất);
  - thêm `machine_read`, `review_flags`, `rate`, `amount`, `voided_at`, `void_reason`, `replaces`;
  - bỏ `posted_event`, `over_cut`.
- [x] T007 Viết controller trong lotus_farm/lotus_farm/doctype/lotus_work_entry/lotus_work_entry.py:
  - kiểm tra bằng lot_ledger_rules;
  - dòng Confirmed không sửa trường số liệu, chỉ hủy có lý do;
  - dòng Draft xóa được;
  - khi một dòng phun được xác nhận hoặc bị hủy, tính lại `Farm Block.lotus_quarantine_until`.
- [x] T008 [P] Tạo DocType Lotus Daily Report trong lotus_farm/lotus_farm/doctype/lotus_daily_report/ theo data-model.md:
  - khóa duy nhất vườn × tổ × ngày;
  - `state` (Draft, Sent, Confirmed, Reopened); `reopen_reason` bắt buộc khi mở lại;
  - `on_behalf`, `source` (Phone, Paper, Photo), `machine_draft`, `present_morning`, `present_afternoon`.
- [x] T009 [P] Sửa Lotus Work Session trong lotus_farm/lotus_farm/doctype/lotus_work_session/lotus_work_session.json:
  - thêm `weight` ("lớn hơn 0 và không quá 1");
  - `assignment` bỏ bắt buộc;
  - đổi khóa duy nhất `lotus_work_session_once` (người × ngày × buổi) sang người × ngày × buổi × dòng: sửa trong `install_fields` của lotus_farm/field_report.py, kèm patch lotus_farm/patches/lot_session_weight.py đăng ký trong lotus_farm/patches.txt.
- [x] T010 [P] Cập nhật công đoạn và việc mới trong lotus_farm/field_report.py và lotus_farm/field_report_seed.py:
  - thêm Reject, Harvest vào `lotus_bunch_stage`;
  - thêm việc "Hủy buồng" (Reject, không trả tiền), "Thu hoạch" (Harvest, công nhật), "Kiểm tra sâu bệnh" (nhóm Protection, không bắt buộc vật tư), nếu danh mục chưa có.
- [x] T011 Viết `preview` và `commit` trong lotus_farm/lot_ledger_migrate.py:
  - chuyển Lotus Bunch Event đã xác nhận sang sổ lô, `stage` theo `event_type`, giữ nguyên khóa nguồn; bỏ dòng nháp;
  - Lotus Work Entry cũ chuyển Voided với lý do "Bản thử trước sổ lô";
  - Round đang mở chuyển Cancelled cùng lý do; giữ giao cố định chăm buồng;
  - chạy lại không ghi trùng.
- [x] T012 Viết integration test chuyển dữ liệu trong tests/integration/verify_lot_ledger.py: 593 dòng cắt bắp đầu kỳ (Đỏ 113, Trắng 182, Tím 298); chạy lại không tăng; không còn Work Entry cũ nào được tính tiền
- [x] T013 Đổi chỗ nạp dữ liệu của dự thu và tồn màu dây sang sổ lô trong lotus_farm/block_forecast.py, lotus_farm/forecast_snapshot.py và lotus_farm/bunch_report.py (file này giữ tạm, xóa ở US5). Các engine thuần `bunch_flow_rules`, `bunch_forecast_engine`, `block_forecast_engine` giữ nguyên
- [x] T014 Sửa tests/integration/verify_bunch_forecast.py đọc sổ lô; dự thu trước và sau khi chuyển dữ liệu phải bằng nhau

**Checkpoint**: Migrate qua trên bản local, số dự thu không đổi sau khi chuyển

---

## Phase 3: User Story 1 - Một báo cáo ngày cho mỗi tổ (Priority: P1) 🎯 MVP

**Goal**: Mỗi tổ nhập mọi việc của mọi lô trong một báo cáo ngày (thẻ lô, hộp nhập). Đội trưởng xác nhận một lần. Tiền khoán tạm tính hiện ngay sau khi xác nhận.

**Independent Test**: Quickstart kịch bản 1 đến 8 và 24

### Tests for User Story 1

- [x] T015 [P] [US1] Unit test chia buổi theo trọng số (cùng việc chia theo khối lượng, khác việc chia đều, tổng của mỗi người mỗi buổi bằng 1) và tiền tạm tính khoán số lượng trong lotus_farm/tests/test_field_report_rules.py
- [x] T016 [P] [US1] Integration test luồng tổ-ngày trong tests/integration/verify_lot_ledger.py:
  - lưu nháp, gửi, xác nhận;
  - chặn tự xác nhận; đội trưởng nhập hộ thì quản lý vườn xác nhận;
  - sửa có lý do (Voided kèm `replaces`); mở lại có lý do;
  - chặn ngày tương lai và tháng đã khóa sổ;
  - kiểm tra sâu bệnh bắt buộc đủ trường;
  - bảng lương cộng đúng trọng số.
- [x] T017 [P] [US1] Unit test gom dòng theo lô, giữ nháp trên máy và khôi phục sau khi mất sóng trong frontend/tests/lot-entry-model.test.js
- [x] T018 [P] [US1] Mount test LotCards, LotEntryModal, DayConfirm trong frontend/tests/lot-entry.mount.test.js

### Implementation for User Story 1

- [x] T019 [US1] Viết `today(farm, team, date)` trong lotus_farm/lot_report.py:
  - tạo báo cáo nháp nếu chưa có;
  - thẻ lô gồm lô giao cố định và Round đang mở của tổ;
  - kèm đợt màu còn buồng, cách ly, các dòng đã nhập, người có lượt máy theo buổi.
- [x] T020 [US1] Viết `save_lot(report, block, lines[], expected_modified)` trong lotus_farm/lot_report.py:
  - có lỗi thì không lưu dòng nào;
  - `source_key` = `day:<báo cáo>:<lô>:<việc>:<màu>:<lý do>`;
  - ghi buổi công có trọng số.
- [x] T021 [US1] Viết các hàm còn lại trong lotus_farm/lot_report.py:
  - `send`; `confirm`: chụp `rate`, `amount` với khoán số lượng, chặn người xác nhận là người nhập, cập nhật cách ly;
  - `amend(entry, values, reason)`, `reopen(report, reason)`, `status(farm, crew, date)`.
- [x] T022 [US1] Sửa tiền khoán theo trọng số buổi trong lotus_farm/field_report_rules.py và lotus_farm/field_report.py:
  - `split_by_sessions` nhận trọng số;
  - `month_piece` và `work_rows` cộng `weight` thay vì đếm dòng;
  - xóa `save_entry` và `_write_sessions` cũ.
- [x] T023 [US1] Bảng lương và chi phí công theo lô đọc trọng số trong lotus_farm/hr_period.py và lotus_farm/finance/payroll.py (`_work_rows`)
- [x] T024 [US1] Viết `my_pay(farm, month)` trong lotus_farm/lot_report.py: tiền khoán tạm tính của tổ và của từng người, theo quyền xem
- [x] T025 [P] [US1] Viết model thuần trong frontend/src/lot-entry-model.js: gom dòng theo lô; giữ nháp trên máy (bọc try/catch); so `expected_modified`
- [x] T026 [US1] Viết component thẻ lô của tổ trong ngày, có dấu cách ly và đã nhập, trong frontend/src/components/field/LotCards.vue
- [x] T027 [US1] Viết hộp nhập mọi việc của một lô trong frontend/src/components/field/LotEntryModal.vue:
  - đủ các nhóm: việc vườn, phun bón kèm vật tư và liều, việc buồng, thu hoạch, kiểm tra sâu bệnh;
  - cắt bắp tự gán màu dây;
  - người làm mặc định theo chấm công, người nhập chỉ bỏ ra người không làm;
  - máy tính dùng ModalForm/WorkspaceModal, điện thoại dùng Vant.
- [x] T028 [US1] Viết màn xác nhận tổ-ngày trong frontend/src/components/field/DayConfirm.vue: xem lại, xác nhận một lần, sửa có lý do, mở lại có lý do
- [x] T029 [US1] Nối các màn vào frontend/src/FieldReportApp.vue và frontend/src/WorkMobile.vue:
  - máy tính: mục Hôm nay trong frontend/src/FieldReportApp.vue;
  - điện thoại: tab Hôm nay, Xác nhận, Tôi (tiền tạm tính) trong frontend/src/WorkMobile.vue.
- [x] T030 [US1] Xóa phần bị thay trong lotus_farm/ và frontend/src/components/field/:
  - backend: lotus_farm/bunch_posting.py;
  - frontend: frontend/src/components/field/WorkBunch.vue, WorkBunchSheet.vue, WorkTicket.vue, WorkEntryForm.vue, WorkToday.vue;
  - các test cũ tương ứng trong frontend/tests.

**Checkpoint**: Tổ nhập được, đội trưởng xác nhận được, tiền tạm tính đúng. Đủ để chạy thử với Đội khu A + B.

---

## Phase 4: User Story 2 - Bảng màu dây và thu hoạch theo lô và đợt màu (Priority: P2)

**Goal**: Thấy buồng còn trên cây theo lô và đợt màu, danh sách cần thu của tuần. Ghi thu hoạch theo lô và đợt màu, bị chặn khi lô đang cách ly.

**Independent Test**: Quickstart kịch bản 4, 8, 9

### Tests for User Story 2

- [x] T031 [P] [US2] Unit test bảng màu dây trong lotus_farm/tests/test_ribbon_board.py:
  - cắt, bao, hủy sau cắt, đã thu, còn trên cây, tuổi tuần;
  - hai chu kỳ cùng màu tách riêng;
  - đến tuổi thu theo bộ tham số đang hiệu lực.
- [x] T032 [P] [US2] Mount test RibbonBoard trong frontend/tests/ribbon-board.mount.test.js

### Implementation for User Story 2

- [x] T033 [US2] Viết `board(farm, zone, block)` và `harvest_due(farm, week)` trong lotus_farm/ribbon_board.py: đọc sổ lô qua bunch_flow_rules, đánh dấu lô đang cách ly
- [x] T034 [US2] Sửa phần thu hoạch trong frontend/src/components/field/LotEntryModal.vue: chỉ chọn đợt màu còn buồng, bắt buộc kg, hiện số còn lại, chặn khi vượt
- [x] T035 [US2] Viết frontend/src/components/field/RibbonBoard.vue: thẻ theo đợt màu, bấm vào mở hộp chi tiết theo lô, danh sách cần thu của tuần
- [x] T036 [US2] Thêm mục "Màu dây & thu hoạch" vào frontend/src/FieldReportApp.vue và phần tồn màu cho đội trưởng trên frontend/src/WorkMobile.vue; xóa frontend/src/components/report/BunchStockCards.vue

**Checkpoint**: Bảng màu dây khớp từng ô với số đã nhập. Thu hoạch ở lô cách ly bị chặn.

---

## Phase 5: User Story 3 - Vòng chăm sóc theo lô thay cho giao từng phiếu (Priority: P3)

**Goal**: Mỗi việc vườn có vòng. Hệ thống tự ra danh sách lô đến hạn và quá hạn. Đội trưởng giao nhiều lô một lần.

**Independent Test**: Quickstart kịch bản 10, 11, 12

### Tests for User Story 3

- [x] T037 [P] [US3] Unit test vòng chăm sóc trong lotus_farm/tests/test_care_cycle_rules.py:
  - đến hạn = ngày xong gần nhất + vòng;
  - lô chưa từng làm thì đến hạn từ ngày áp dụng;
  - việc làm nhiều ngày chỉ tính xong vòng khi báo xong cả lô;
  - luật theo khu được ưu tiên hơn luật cả vườn;
  - việc chưa có vòng thì không hiện đến hạn.
- [x] T038 [P] [US3] Integration test trong tests/integration/verify_care_cycle.py:
  - giao nhiều lô, đổi tổ, hủy có lý do;
  - báo xong lô thì Round sang Reported;
  - khoán cả lô đi qua nghiệm thu; cách trả khác khóa khi xác nhận.
- [x] T039 [P] [US3] Mount test CareDueList trong frontend/tests/care-due-list.mount.test.js

### Implementation for User Story 3

- [x] T040 [US3] Rút gọn Work Schedule Rule trong lotus_farm/lotus_farm/doctype/work_schedule_rule/work_schedule_rule.json:
  - giữ `farm`, `rule_name`, `work_type`, `repeat_days`, `valid_from`, `valid_to`, `version`, `approval_state`; thêm `farm_zone`;
  - bỏ `anchor`, `offset_days`, `offset_months`, `repeat_months`, `quantity_basis`, `norm_profile`;
  - patch lotus_farm/patches/care_cycle_rules.py: lưu trữ các luật định mức cũ ra JSON rồi xóa.
- [x] T041 [US3] Xóa định mức cũ, vì dùng các trường vừa bỏ: lotus_farm/plan_norm.py, lotus_farm/plan_book2_reference.py, frontend/src/components/PlanNormSettings.vue, frontend/src/plan-norm-engine.js và test tương ứng (frontend/tests/plan-norm-safety.test.js, tools/verify_plan_norm_live.py)
- [x] T042 [US3] Viết module thuần cho quy tắc ở T037 trong lotus_farm/care_cycle_rules.py
- [x] T043 [US3] Viết lotus_farm/care_cycle.py:
  - `due`;
  - `assign`: tạo Round, chụp cách trả và đơn giá; lô đã có Round mở cho việc đó thì báo ra;
  - `reassign`, `cancel`: phải có lý do;
  - `rules`; `save_rule`: tạo phiên bản mới chờ duyệt, chỉ quản lý vườn được dùng.
- [x] T044 [US3] Nối Round với báo cáo ngày trong lotus_farm/lot_report.py và lotus_farm/field_report.py:
  - dòng `done` thuộc Round thì Round sang Reported;
  - khoán cả lô chờ nghiệm thu (Lotus Work Inspection); cách trả khác khóa khi xác nhận;
  - thêm `cycle_rule` và đổi đích `done_report` sang Lotus Daily Report trong lotus_farm/lotus_farm/doctype/lotus_work_assignment/lotus_work_assignment.json.
- [x] T045 [US3] Viết frontend/src/components/field/CareDueList.vue: ma trận lô × việc (lần xong gần nhất, đến hạn, quá hạn), chọn nhiều lô rồi chọn tổ để giao
- [x] T046 [US3] Viết màn thiết lập vòng chăm sóc (theo việc, khu, ngày hiệu lực, duyệt) trong frontend/src/components/field/CareCycleSettings.vue
- [x] T047 [US3] Xóa phần bị thay trong frontend/src/components/ và lotus_farm/block_forecast.py:
  - frontend/src/components/ForecastCarePlan.vue ("Lịch chăm sóc theo lô");
  - frontend/src/components/field/WorkAssign.vue và frontend/src/components/field/FieldBoard.vue;
  - phần lịch chăm sóc trong lotus_farm/block_forecast.py.

**Ghi chú khi làm (10/11)**: care_cycle.assign/reassign/cancel gọi lại field_report.assign/reassign/cancel_assignment (một chỗ giao phiếu). WorkAssign.vue được giữ làm danh sách "Phiếu đã giao" và phiếu riêng cho khoán cả lô, nằm dưới danh sách đến hạn; FieldBoard.vue, ForecastCarePlan.vue, block_care_engine.py, field_report.board, field.suggest_work/make_suggested_plan và trang "Cấu hình kế hoạch & định mức" đã xóa. Phiên bản vòng: bản mới nhất đã bắt đầu của cùng tên vòng thay các bản cũ; bản có ngày hết hạn đã qua thì vòng dừng.

**Checkpoint**: Danh sách đến hạn đúng ngày, giao nhiều lô một lần được, nghiệm thu khoán cả lô chạy

---

## Phase 6: User Story 4 - Một con số dự thu, tự chốt mỗi tuần (Priority: P4)

**Goal**: Mọi màn có dự thu dùng chung một con số. Bản chốt đầu tuần luôn có mà không cần bộ chạy lịch.

**Independent Test**: Quickstart kịch bản 13, 14

### Tests for User Story 4

- [x] T048 [P] [US4] Unit test dựng bản chốt theo mốc trong lotus_farm/tests/test_forecast_snapshot.py:
  - chỉ lấy dòng xác nhận trước mốc và chưa bị hủy trước mốc;
  - lấy tham số đang hiệu lực tại mốc;
  - tuần bị bỏ lỡ được tạo bù.
- [x] T049 [P] [US4] Integration test trong tests/integration/verify_bunch_forecast.py:
  - không mở ứng dụng cả tuần, sau đó mở thì có bản chốt đúng mốc;
  - hai phiên mở cùng lúc không tạo trùng;
  - Tổng quan, kế hoạch tài chính và trang dự thu cùng một số.

### Implementation for User Story 4

- [x] T050 [US4] Thêm `week_start`, `as_of`, `limits` và khóa duy nhất vườn × `week_start` × `kind` (với Weekly) trong lotus_farm/lotus_farm/doctype/lotus_forecast_snapshot/lotus_forecast_snapshot.json
- [x] T051 [US4] Viết `ensure_weeks(farm)` trong lotus_farm/forecast_snapshot.py:
  - dựng bản chốt theo mốc 0 giờ thứ Hai, dùng `confirmed_at` và `voided_at`;
  - ghi giới hạn vào `limits`: số cây và ngày trổ lấy giá trị hiện tại.
- [x] T052 [US4] Gọi `ensure_weeks` khi khởi động phiên trong lotus_farm/console.py; nếu lỗi thì ghi lại và không chặn việc mở ứng dụng
- [x] T053 [US4] Cho Tổng quan và kế hoạch tài chính gọi `block_forecast.board` và bỏ đọc Harvest Forecast trong lotus_farm/reporting.py, frontend/src/components/OverviewBoard.vue và lotus_farm/finance/planning.py
- [x] T054 [US4] Gỡ các nơi đọc dự thu cũ (danh sách T040 của spec 001) trong lotus_farm/ và frontend/src/:
  - sửa: frontend/src/App.vue, lotus_farm/console.py;
  - xóa: lotus_farm/forecast_calendar.py, lotus_farm/vip126_timeline.py, lotus_farm/vip126_trial.py, lotus_farm/vip126_live.py, lotus_farm/vip126_profile.py, lotus_farm/vip126_zone_plan.py, lotus_farm/onedrive_supply.py, frontend/src/components/Vip126RollingForecast.vue, frontend/src/components/OneDriveSupplyDialog.vue và test tương ứng.
- [x] T055 [US4] Sửa `variance` và `suggest_parameters` đọc thu hoạch thật từ sổ lô (kg/buồng, tỷ lệ thu, số ngày từ cắt bắp đến thu) trong lotus_farm/forecast_snapshot.py
- [x] T056 [US4] Sửa trang Dự thu trong frontend/src/BlockForecastApp.vue: bỏ các khóa của engine cũ, thêm nút "Tạo bản chốt" cho quản lý

**Ghi chú khi làm (10/11)**: Không có bộ chạy lịch trên máy chủ, nên bootstrap (console và field_report) xếp `forecast_snapshot.ensure_all` vào hàng đợi short một lần mỗi tuần (job_id theo thứ Hai, có dedupe; đánh dấu trong cache khi xong). Khóa duy nhất là trường `weekly_key` = vườn:thứ Hai (bản Manual để trống). T053 và T054 làm cùng US7 (dọn đồ cũ) và US5 (báo cáo): Tổng quan cũ, kế hoạch tài chính và các bộ dự thu cũ đều nằm trong danh sách xóa hoặc thay ở hai phần đó.

**Checkpoint**: Có bản chốt tuần dù không ai mở trang; ba màn cùng một số

---

## Phase 7: User Story 6 - Nối thu hoạch với xưởng đóng gói, nhập kho thành phẩm theo ca (Priority: P6)

**Goal**: Ca đóng gói biết buồng từ lô và đợt màu nào, tính được kg/buồng và thùng/buồng thật, truy vết được, và lập được phiếu nhập kho thành phẩm theo ca.

**Hạn**: Phải xong trước lứa thu đầu, khoảng cuối tháng 12/2026.

**Independent Test**: Quickstart kịch bản 16, 19

### Tests for User Story 6

- [x] T057 [P] [US6] Unit test trong lotus_farm/tests/test_packout_rules.py:
  - chia thùng và thành phẩm theo kg;
  - kg/buồng, thùng/buồng, tỷ lệ đóng gói;
  - "tổng kg các nguồn bằng `input_kg` của ca";
  - "số buồng nhận của một đợt không vượt số đã thu mà chưa vào xưởng".
- [x] T058 [P] [US6] Integration test trong tests/integration/verify_packout_sources.py:
  - ca nhận buồng từ hai lô, thùng chia đúng, truy vết ra lô;
  - phiếu nhập kho thành phẩm nháp có giá trị chia theo kg từ chi phí dở dang của từng lô.

### Implementation for User Story 6

- [x] T059 [US6] Tạo bảng con Packhouse Shift Source (`farm_block`, `bunch_tag`, `bunches`, `kg`, `harvest_entry`) và gắn vào Packhouse Shift. Bỏ trường trỏ Harvest Lot ở Packhouse Preprocessing. Sửa trong lotus_farm/lotus_farm/doctype/packhouse_shift_source/, packhouse_shift/packhouse_shift.json và packhouse_preprocessing/packhouse_preprocessing.json
- [x] T060 [US6] Viết module thuần cho quy tắc ở T057 trong lotus_farm/packout_rules.py
- [x] T061 [US6] Sửa lotus_farm/shift.py: lưu ca với `sources[]` và kiểm tổng kg; thêm `trace(shift)` (nguồn → dòng thu hoạch → các dòng phun ở lô đó trước ngày thu)
- [x] T062 [US6] Viết `receive_shift(shift)` trong lotus_farm/finance/costing.py và lotus_farm/finance/rules.py:
  - tạo phiếu nhập kho thành phẩm nháp, là phiếu kho chuẩn, gồm thành phẩm và phụ phẩm theo kg;
  - giá trị lấy từ chi phí dở dang tập theo lô, chia theo kg nguồn;
  - chỉ kế toán dùng được.
- [x] T063 [US6] Viết màn Xưởng trong frontend/src/components/field/PackhouseShifts.vue: danh sách ca; hộp nhập ca có nguồn buồng chọn từ thu hoạch trong ngày; kết quả chia; truy vết. Thêm mục "Xưởng" vào frontend/src/FieldReportApp.vue
- [x] T064 [US6] Thêm thùng/buồng từ xưởng vào phần so dự thu với thực tế trong lotus_farm/forecast_snapshot.py

**Ghi chú khi làm (10/11)**: Ca nhập trực tiếp (không qua Packout Run/Harvest Lot); kg vào = tổng kg nguồn; hao và tỷ lệ đóng gói tự tính. Kiểm công một người trong ngày dùng buổi của sổ lô thay Labor Allocation. Mặt hàng thành phẩm, phụ phẩm và kho thành phẩm đặt ở Tài chính – Kế toán › Thiết lập; phiếu nhập kho gắn ca qua trường `lotus_packhouse_shift`. Màn Xưởng nằm trong Công việc ngoài vườn; quyền xưởng theo quyền Packhouse Shift (Lotus Packing Supervisor, Lotus Farm Manager).

**Checkpoint**: Ca đóng gói chia đúng theo lô, có phiếu nhập kho thành phẩm nháp

---

## Phase 8: User Story 7 - Dọn sạch đồ cũ (Priority: P7)

**Goal**: Xóa hẳn 76 bảng đời cũ cùng màn hình, menu và mã (danh sách ở cleanup.md), sau khi đã chuyển kho, tài chính, lương sang nguồn mới và lưu trữ dữ liệu.

**Independent Test**: Quickstart kịch bản 20, 21, 22, 23

### Tests for User Story 7

- [x] T065 [P] [US7] Viết test quét mã trong tests/test_no_legacy_names.py: không còn tên bảng nào ở cleanup.md mục 1 trong lotus_farm/, frontend/src/, tests/, tools/
- [x] T066 [P] [US7] Integration test lotus_farm/legacy_purge.py trong tests/integration/verify_legacy_purge.py:
  - `preview` không ghi gì;
  - `commit` tạo đủ tệp JSON, số dòng khớp với `preview`, chạy lại không lỗi;
  - `commit` dừng khi có giá trị nằm trên chứng từ đã ghi sổ.

### Implementation for User Story 7

- [x] T067 [US7] Sửa giá thành và tài sản trong lotus_farm/finance/:
  - bỏ chiều kế toán "Vụ" (`lotus_crop_cycle`) trong lotus_farm/finance/rules.py;
  - Lotus Costing Row: đổi trường trỏ Crop Cycle thành `cycle_no` (Int);
  - Lotus Asset Allocation Row và lotus_farm/finance/assets.py: bỏ trường vụ;
  - lotus_farm/finance/costing.py: bỏ `receive_harvest`, `lots_to_receive` và phần đọc Harvest Forecast;
  - lotus_farm/finance/setup.py: bỏ trường `lotus_harvest_lot`.
- [x] T068 [US7] Sửa lương: bỏ nhánh Daily Work Result, Work Actual Labor, Labor Allocation, Daily Work Plan Line trong lotus_farm/finance/payroll.py; bỏ Labor Allocation khỏi `GUARDED` trong lotus_farm/hr_period.py
- [x] T069 [US7] Sửa kho trong lotus_farm/warehouse_issue.py và các file sau:
  - lotus_farm/warehouse_issue.py, lotus_farm/warehouse.py: bỏ chế độ xuất theo kế hoạch (Daily Work Plan), Material Requirement, Material Consumption, Material Recovery;
  - lotus_farm/warehouse_planning.py: chỉ còn Material Request, phần nhận hàng giữ nguyên;
  - lotus_farm/stock_bridge.py: bỏ cầu nối Packout Run, Harvest Lot, Forecast Allocation, giữ các kiểm tra khác;
  - lotus_farm/finance/stock.py; lotus_farm/install.py (bỏ trường trỏ Packout Run);
  - lotus_farm/www/lotus_stock_print.py, lotus_farm/www/lotus_material_proposal_print.py;
  - frontend/src/components/stock/StockDocumentForm.vue, StockDocumentDetail.vue: bỏ "Theo kế hoạch đã duyệt";
  - frontend/src/components/WarehousePlanning.vue.
- [x] T070 [US7] Bỏ phần Daily Work Plan/Result trong lotus_farm/push_notifications.py và lotus_farm/user_admin.py; xóa lotus_farm/rate_approval.py
- [x] T071 [US7] Bỏ Farm Plot, Plot Geometry và các bảng ghi chép cũ khỏi Vườn & lô và bản đồ trong lotus_farm/farm_land.py, lotus_farm/field.py, lotus_farm/scoping.py, lotus_farm/map_import.py, frontend/src/FarmLandApp.vue và frontend/src/components/land/LandBlockDetail.vue. Phần việc và sản lượng của lô đọc sổ lô
- [x] T072 [US7] Bỏ các trường trỏ bảng cũ trên bảng giữ trong lotus_farm/lotus_farm/doctype/:
  - Bunch Tag: trường trỏ Bunch Operation, `process_adoption` trong lotus_farm/lotus_farm/doctype/bunch_tag/bunch_tag.json;
  - Work Type: trường trỏ Work Category trong lotus_farm/lotus_farm/doctype/work_type/work_type.json;
  - các file lotus_farm/lotus_weekly_ribbon_2026.py, lotus_farm/bunch_tag_catalog.py.
- [x] T073 [US7] Gỡ đăng ký đồ cũ trong khung ứng dụng (lotus_farm/hooks.py và các file sau):
  - backend: lotus_farm/hooks.py, lotus_farm/install.py, lotus_farm/permissions.py, lotus_farm/console.py, lotus_farm/controls.py, lotus_farm/api.py;
  - frontend: frontend/src/App.vue, frontend/src/router.js, frontend/src/mobile-menu.js (gồm mục "Kiểm tra sâu bệnh" cũ), frontend/src/preload.js.
- [x] T074 [US7] Xóa module, màn, tool và test cũ theo cleanup.md mục 4. File có dấu * chỉ xóa sau khi kiểm không còn nơi dùng
- [x] T075 [US7] Viết `preview` và `commit(archive_dir)` trong lotus_farm/legacy_purge.py theo contracts/api.md:
  - `preview` đếm số dòng từng bảng;
  - `preview` đếm giá trị khác rỗng: `lotus_crop_cycle` trên GL Entry, Journal Entry Account, Stock Entry Detail và chứng từ mua bán; `lotus_work_plan`, `lotus_harvest_lot` trên Stock Entry; trường trỏ Material Requirement trên Material Request Item;
  - `preview` liệt kê kỳ lương đã hạch toán có dùng Labor Allocation;
  - `commit` sao lưu, xuất JSON từng bảng kèm số dòng và mã kiểm, rồi xóa theo thứ tự: dữ liệu → trường tùy chỉnh và chiều kế toán → DocType;
  - `commit` dừng nếu `preview` có danh sách chặn.
- [x] T076 [US7] Viết patch lotus_farm/patches/purge_legacy_doctypes.py theo mẫu lotus_farm/patches/remove_work_journal.py, đăng ký trong lotus_farm/patches.txt. Xóa 76 thư mục DocType ở cleanup.md mục 1 khỏi lotus_farm/lotus_farm/doctype/. Kiểm deployment/Dockerfile.release vẫn xóa lotus_farm/lotus_farm trước COPY
- [ ] T077 [US7] Chạy lại integration của kho, tài chính, lương (tests/integration/verify_costing.py, verify_purchase_flow.py, verify_warehouse_audit.py, verify_timekeeping.py, verify_hr_audit_fixes.py). So sổ cái, tồn kho và bảng lương các tháng đã khóa trước và sau khi dọn (SC-012); ghi kết quả vào specs/002-cham-soc-thu-hoach-du-thu/baseline.md

**Ghi chú khi làm (10/11 tối)**: Làm song song trên năm nhánh (`us7/a` tài chính và lương, `us7/b` kho và in phiếu, `us7/s` khung ứng dụng cũ, `us7/v` vườn & lô, bản đồ, dự thu, `us7/x` đăng ký và xóa module), gộp vào `us7/coord`. `legacy_purge.commit` lưu từng bảng cũ ra JSON (số dòng, mã kiểm, đọc lại để so) cùng các dòng lịch sử, bình luận, thùng rác nhắc tới chúng, rồi gỡ chiều kế toán và trường (kể cả cột), xóa DocType, bảng và các dòng nhắc tên. Giá thành tháng không còn bị chặn khi còn tồn thành phẩm: chênh lệch thực tế so với tạm tính chia theo tỷ lệ kg còn tồn, phần đã bán vào 632, phần còn tồn ở lại 154. Kết quả kiểm ở baseline.md mục "US7".

**Checkpoint**: Mảng vườn còn 25 bảng; không còn tên bảng cũ trong mã, cơ sở dữ liệu và menu; tháng đã khóa không đổi số

---

## Phase 9: User Story 1 phần sau - Phiếu giấy và đọc ảnh (Priority: P1)

**Goal**: In phiếu giấy cho từng tổ. Chụp phiếu đã ghi thì máy điền sẵn các dòng, người nhập kiểm lại rồi mới gửi.

**Independent Test**: Quickstart kịch bản 15

### Tests

- [x] T078 [P] [US1] Unit test các kiểm tra cố định cho dòng máy đọc trong lotus_farm/tests/test_lot_paper_form.py: lô hay việc không có trên phiếu; số buồng không nguyên; vượt trần; ô trống mà phiếu in có
- [x] T079 [P] [US1] Mount test PaperPhotoReview trong frontend/tests/paper-photo-review.mount.test.js

### Implementation

- [x] T080 [US1] Viết trang in phiếu tổ-ngày trong lotus_farm/www/lotus_daily_form.html và lotus_farm/www/lotus_daily_form.py: mã báo cáo, bảng lô × việc đến hạn, ô số to, màu dây cắt bắp in sẵn
- [x] T081 [US1] Viết `form_url` và `read_photo` trong lotus_farm/lot_paper_form.py, thêm khuôn đọc phiếu ngày trong lotus_farm/document_ai.py:
  - lưu kết quả vào `machine_draft`;
  - tạo dòng Nháp có `machine_read` và `review_flags`;
  - dùng chung giới hạn lượt với `document_ai.read`.
- [x] T082 [US1] Viết frontend/src/components/field/PaperPhotoReview.vue: đặt ảnh cạnh các dòng, kiểm từng dòng bị đánh dấu, chặn gửi khi còn dòng máy đọc chưa kiểm
- [ ] T083 [US1] Đo tỷ lệ đọc đúng trên 10 phiếu thật của vườn và ghi kết quả vào mục R9 của specs/002-cham-soc-thu-hoach-du-thu/research.md trước khi bật cho các tổ

**Ghi chú khi làm (10/11)**: Trang in ở /lotus/in-phieu-ngay (service worker bỏ qua như các trang in khác). form_url (POST) chốt bố cục phiếu vào machine_draft để ảnh đọc sau khớp cột in. Mọi dòng máy đọc đều mang cờ "Máy đọc, chưa kiểm" cộng các cờ cố định; lưu lô (kể cả không sửa, nút "Đã kiểm, lưu lô này") là bước kiểm và xóa cờ. Lô đã có số nhập tay thì giữ nguyên, số máy đọc chỉ thành ghi chú. T083 chờ ảnh phiếu thật của vườn (chưa có), nên chưa bật cho các tổ.

**Checkpoint**: Ảnh phiếu thật cho ra các dòng nháp đúng, dòng nghi ngờ được đánh dấu

---

## Phase 10: User Story 5 - Báo cáo theo người xem: Sáng nay, Tuần, Tháng (Priority: P5)

**Goal**: Ba màn báo cáo dạng thẻ, bấm vào mở chi tiết, xuất Excel được, có bản đồ lô. Menu gom còn 7 mục.

**Independent Test**: Quickstart kịch bản 17, 18

### Tests for User Story 5

- [x] T084 [P] [US5] Integration test `morning`, `week`, `month` trên dữ liệu mẫu một tuần trong tests/integration/verify_field_reports.py
- [x] T085 [P] [US5] Mount test MorningReport, WeekReport, MonthReport (thẻ, hộp chi tiết, xuất Excel) trong frontend/tests/field-reports.mount.test.js
- [x] T086 [P] [US5] Test menu của cả mảng có tối đa 7 mục trong frontend/tests/field-navigation.test.js

### Implementation for User Story 5

- [x] T087 [US5] Viết lotus_farm/field_reports.py:
  - `morning`: tổ chưa gửi, chưa xác nhận, số bất thường, việc quá hạn, lô cách ly, đợt đến tuổi thu;
  - `week`: việc theo lô, bảng màu dây, thu hoạch và đóng gói, dự thu so với thực tế, tình trạng lô để tô bản đồ;
  - `month`: sản lượng và các tỷ lệ cắt bắp/cây, thu/cắt bắp, kg/buồng, thùng/buồng; công và tiền khoán theo lô; vật tư xuất kho so với vật tư báo dùng theo lô.
- [x] T088 [US5] Viết frontend/src/components/report/MorningReport.vue, WeekReport.vue (bản đồ lô qua CareMap thêm lớp tình trạng) và MonthReport.vue; xuất Excel bằng frontend/src/excel-export.js
- [x] T089 [US5] Gom menu trong frontend/src/field-report-navigation.js và các file sau:
  - máy tính 7 mục trong frontend/src/field-report-navigation.js, frontend/src/workspace-routes.js, frontend/src/workspace-directory.js: Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu, Báo cáo, Thiết lập;
  - Thiết lập gồm đội tổ lô, việc và cách trả, bảng giá, vòng chăm sóc, màu dây (chuyển frontend/src/ColorTagCatalogApp.vue vào đây), tham số dự thu;
  - điện thoại 4 tab trong frontend/src/WorkMobile.vue: Hôm nay, Giao việc, Xác nhận, Tôi.
- [x] T090 [US5] Xóa các báo cáo kiểu Pivot và phần backend cũ trong frontend/src/components/report/ và lotus_farm/:
  - frontend: frontend/src/components/report/GardenCareReport.vue, BunchCareReport.vue, PackhouseReport.vue, ProtectionReport.vue, PivotChart.vue, PivotFilter.vue, frontend/src/bunch-pivot.js, frontend/src/pivot-filter.js;
  - backend: lotus_farm/work_report.py, lotus_farm/work_report_rules.py, lotus_farm/bunch_report.py;
  - các route `bao-cao-*` cũ.

**Ghi chú khi làm (10/11)**: Ba màn nằm trong một component FieldReports.vue (ba tab) dùng chung ReportCards.vue; bảng chi tiết là DataTable nên lọc và xuất Excel sẵn. Bản đồ Tuần dùng CareMap với chế độ màu mới `status` (map-land.js). Sổ cắt bắp (xuất Excel theo mẫu sổ của vườn) được giữ, chuyển sang `ribbon_board.export_cut_book` (nút trên màn Màu dây & thu hoạch) trước khi xóa bunch_report.py; bunch_report_rules chỉ còn stock, ribbon, due_rows, cut_weeks. Nghiệm thu nằm trong Giao việc (máy tính và điện thoại); Tiền khoán theo người mở từ Báo cáo › Tháng. Dự thu và Màu dây cắt bắp vẫn hiện cho người không có quyền Công việc ngoài vườn.

**Checkpoint**: Ba câu hỏi chính trả lời được bằng một thẻ, menu còn 7 mục

---

## Phase 11: Polish & Cross-Cutting Concerns

- [x] T091 [P] Viết lại hướng dẫn cho tổ trưởng, đội trưởng, quản lý vườn và kế toán (phần nhập kho thành phẩm theo ca) trong docs/FIELD_REPORT.md và docs/CHAM_BUONG_DU_THU.md
- [x] T092 [P] Thêm mục "Có gì mới" ở đầu frontend/src/release-notes.js
- [x] T093 Đo hiệu năng theo plan.md (mở Hôm nay dưới 2 giây, lưu một lô dưới 1 giây, báo cáo và dự thu toàn vườn dưới 3 giây); ghi kết quả vào specs/002-cham-soc-thu-hoach-du-thu/baseline.md
- [x] T094 Chạy đủ specs/002-cham-soc-thu-hoach-du-thu/quickstart.md và toàn bộ test (`node --test`, unit Python, integration), so với mốc ở T002
- [x] T095 Chuẩn bị triển khai VPS trong specs/002-cham-soc-thu-hoach-du-thu/deploy.md. Chỉ chạy khi chủ vườn ra lệnh và cung cấp mật khẩu SSH. Các bước:
  - sao lưu;
  - migrate;
  - `lot_ledger_migrate.commit`;
  - `legacy_purge.preview` trên bản thật, chủ vườn xem kết quả, rồi `commit`;
  - tạo tài khoản tổ trưởng Đội khu A + B (cần danh sách từ chủ vườn).
- [x] T096 Tùy chọn, chỉ khi chủ vườn yêu cầu trước khi bản mới lên: sửa nóng trên main, chặn dòng thu hoạch khi lô đang cách ly trong lotus_farm/bunch_posting.py của bản đang chạy. **Không cần nữa**: bản mới (có chặn thu hoạch khi cách ly) đã lên ngày 10/11.

**Ghi chú triển khai (10/11)**: lần 1 đã lên bản thật lúc 20:29 (`lotus-release:40f8330`), kết quả ở baseline.md mục "Rà soát độc lập và triển khai lần 1". Còn chờ chủ vườn: danh sách tổ trưởng Đội khu A + B để tạo tài khoản; 10 ảnh phiếu giấy thật cho T083.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: làm ngay.
- **Foundational (Phase 2)**: sau Setup; chặn mọi phần việc khác.
- **US1 (Phase 3)**: sau Foundational. Là MVP.
- **US2 (Phase 4)**: sau US1, vì dùng hộp nhập của US1 cho thu hoạch.
- **US3 (Phase 5)**: sau US1, vì Round được báo xong qua báo cáo ngày. Làm song song được với US2.
- **US4 (Phase 6)**: sau Foundational (đã đổi nguồn đọc). Làm song song được với US2, US3.
- **US6 (Phase 7)**: sau US2, vì cần dòng thu hoạch. Phải xong trước lứa thu đầu.
- **US7 (Phase 8)**: sau US3 (định mức cũ đã xóa), US4 (dự thu cũ đã gỡ) và US6 (đã có nhập kho theo ca).
- **US1 phần sau (Phase 9)**: sau US1; làm lúc nào cũng được.
- **US5 (Phase 10)**: sau US2, US3, US4, US6, vì đọc tất cả.
- **Polish (Phase 11)**: sau các phase muốn đưa lên.

### Within Each Phase

- Viết test trước và thấy test hỏng, rồi mới viết mã.
- Module thuần trước, rồi API, rồi giao diện.
- Xóa phần bị thay ở cuối phase, sau khi test của phase đã qua.

### Parallel Opportunities

- Phase 2: T004, T006, T008, T009, T010 khác file nhau, chạy song song được.
- Mỗi phase: các task test có [P] chạy song song.
- Sau US1: US2, US3, US4 có thể làm song song.

---

## Parallel Example: User Story 1

```text
Task: "T015 Unit test chia buổi theo trọng số trong lotus_farm/tests/test_field_report_rules.py"
Task: "T016 Integration test luồng tổ-ngày trong tests/integration/verify_lot_ledger.py"
Task: "T017 Unit test lot-entry-model trong frontend/tests/lot-entry-model.test.js"
Task: "T018 Mount test LotCards, LotEntryModal, DayConfirm trong frontend/tests/lot-entry.mount.test.js"
```

---

## Implementation Strategy

### MVP trước

1. Phase 1, Phase 2, Phase 3.
2. Dừng lại, chạy quickstart 1 đến 8, cho Đội khu A + B dùng thử trên bản local hoặc VPS (khi chủ vườn cho phép).

### Giao từng phần

1. US2 và US3: bảng màu dây, thu hoạch, vòng chăm sóc.
2. US4: một con số dự thu.
3. US6: xưởng và nhập kho thành phẩm, trước lứa thu đầu.
4. US7: dọn sạch đồ cũ (lần triển khai có `legacy_purge.commit`).
5. US1 phần sau và US5: phiếu giấy, đọc ảnh, ba màn báo cáo, menu 7 mục.

---

## Notes

- [P] là khác file và không chờ việc chưa xong.
- [USx] gắn việc với user story để truy lại.
- Chỉ commit, đẩy code hay triển khai khi chủ vườn yêu cầu (constitution).
- Mọi thay đổi dữ liệu thật phải sao lưu trước và chạy lại được không ghi trùng.
