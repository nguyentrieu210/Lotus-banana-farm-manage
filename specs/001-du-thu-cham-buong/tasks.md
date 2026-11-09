---

description: "Danh sách việc: dự thu chuối từ số liệu chăm sóc buồng hằng ngày"
---

# Tasks: Dự thu chuối từ số liệu chăm sóc buồng hằng ngày

**Input**: `specs/001-du-thu-cham-buong/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Có, theo nguyên tắc IV trong constitution: unit test cho module thuần, integration cho luồng ghi sổ, test mount cho component có hành vi.

**Quy ước đường dẫn**: Backend trong `lotus_farm/`, frontend trong `frontend/src/`, test frontend trong `frontend/tests/`.

## Phase 1: Setup (kiểm chứng)

- [x] T001 Thử ghi qua các bảng có sẵn trên bản local: ghi được nhưng bắt buộc có thửa; chủ vườn quyết chỉ dùng lô, nên đổi sang bảng riêng, ghi trong specs/001-du-thu-cham-buong/research.md mục R2

---

## Phase 2: Foundational

**Purpose**: Dữ liệu nền cho mọi phần việc

- [x] T003 Viết lệnh chuẩn bị (có chế độ chạy thử): đặt số vụ hiện tại là 2 cho 64 lô; tạo danh mục lý do loại buồng (gãy đổ, sâu bệnh, buồng xấu, khác); đánh dấu khu A là `Census Confirmed` trong lotus_farm/bunch_setup.py
- [x] T004 Thêm `lotus_current_cycle_no` cho Farm Block (cùng nơi khai báo `lotus_tree_count`) và `weight_kg`, `confirmed_by`, `confirmed_at`, `posted_event` vào lotus_farm/lotus_farm/doctype/lotus_work_entry/lotus_work_entry.json
- [x] T005 Thêm công đoạn `Sucker Select`, `Harvest`; gán `Sucker Select` cho F222-17; thêm việc thu hoạch buồng trong lotus_farm/field_report_seed.py
- [x] T006 [P] Tạo DocType Lotus Bunch Event theo data-model.md (khóa `source_key` duy nhất, không xóa) trong lotus_farm/lotus_farm/doctype/lotus_bunch_event/
- [x] T007 [P] Tạo DocType Lotus Forecast Snapshot (không sửa sau khi tạo) trong lotus_farm/lotus_farm/doctype/lotus_forecast_snapshot/
- [x] T008 [P] Thêm `cut_to_harvest_min_days`, `cut_to_harvest_max_days` (mặc định 60, 70) vào lotus_farm/forecast_parameters.py và lotus_farm/lotus_farm/doctype/lotus_block_forecast_profile/lotus_block_forecast_profile.json

**Checkpoint**: Migrate qua trên bản local

---

## Phase 3: User Story 1 - Ghi chăm sóc buồng hằng ngày theo lô (Priority: P1) 🎯 MVP

**Goal**: Tổ báo theo lô, đội trưởng xác nhận theo ngày, số được ghi vào sổ buồng

**Independent Test**: Quickstart kịch bản 4, 5, 6, 7

### Tests

- [x] T009 [P] [US1] Unit test số buồng nguyên, trần theo màu gồm thu hoạch, ánh xạ công đoạn sang sổ buồng trong lotus_farm/tests/test_bunch_posting_rules.py
- [x] T010 [P] [US1] Integration test xác nhận, chạy lại không trùng, sửa có lý do trong tests/integration/verify_bunch_forecast.py
- [x] T011 [P] [US1] Test mount bảng nhập nhanh và màn xác nhận trong frontend/tests/work-bunch-sheet.mount.test.js

### Implementation

- [x] T012 [US1] Viết quy tắc thuần: số nguyên, trần theo màu, khóa dòng, ước tính số chồi, vụ của chọn chồi (FR-026) trong lotus_farm/bunch_posting_rules.py
- [x] T013 [US1] Tính trần bao, tỉa, chống đổ từ sổ buồng (gồm số đầu kỳ) trong `_bunch_counts` của lotus_farm/field_report.py
- [x] T014 [US1] Viết `day_sheet`, `save_day`, `confirm_day`, `amend` theo contracts/api.md trong lotus_farm/bunch_posting.py
- [x] T015 [US1] Khi xác nhận, sinh dòng chọn chồi từ phiếu "Chọn F"; chặn tự xác nhận; chặn thu cộng loại vượt số cắt của màu trong lotus_farm/bunch_posting.py
- [x] T016 [US1] Tạo modal nhập nhanh theo lô cho điện thoại trong frontend/src/components/field/WorkBunchSheet.vue
- [x] T017 [US1] Thêm mục buồng loại kèm lý do và thu hoạch kèm kg, màu dây trong frontend/src/components/field/WorkBunchSheet.vue
- [x] T018 [US1] Tạo màn số trong ngày kèm xác nhận trong frontend/src/components/field/WorkBunch.vue (nhập từng việc qua modal WorkBunchSheet.vue) và nối vào frontend/src/WorkMobile.vue, frontend/src/FieldReportApp.vue

**Checkpoint**: Tổ nhập được, đội trưởng xác nhận được, có dòng sổ buồng

---

## Phase 4: User Story 2 - Dự thu 13 tuần từ buồng đã cắt bắp (Priority: P2)

**Goal**: Dự thu theo tuần, lô, màu từ số cắt bắp thật, gồm số đầu kỳ

**Independent Test**: Quickstart kịch bản 2, 3, 5, 7, 9

### Tests

- [x] T019 [P] [US2] Unit test đọc sổ cắt bắp theo vị trí cột, ra đúng 593 buồng, tuần 46 hai cột cùng nhãn, trong lotus_farm/tests/test_bunch_opening_import.py
- [x] T020 [P] [US2] Unit test tầng cắt bắp: trừ loại, trừ đã thu, trải 60 đến 70 ngày, giữ nguyên tổng, trong lotus_farm/tests/test_bunch_forecast_engine.py

### Implementation

- [x] T021 [US2] Viết tính tầng cắt bắp theo lô và màu trong lotus_farm/bunch_flow_rules.py
- [x] T022 [US2] Viết tổng hợp theo tuần, tháng, lô, khu; buồng, kg theo vụ của từng dòng, thùng trong lotus_farm/bunch_forecast_engine.py
- [x] T023 [US2] Viết `preview`, `commit` sổ cắt bắp, khóa nguồn lô-tuần-lần, ngày thứ 4 và thứ 7 trong lotus_farm/bunch_opening_import.py
- [x] T024 [US2] Mở rộng `board` và thêm `trace` trong lotus_farm/block_forecast.py
- [x] T025 [US2] Hiện 13 tuần dạng thẻ, bấm thẻ mở modal theo lô và truy nguồn, trong frontend/src/components/BunchWeeklyForecast.vue, nối vào frontend/src/BlockForecastApp.vue
- [x] T026 [US2] Thêm màn nhập sổ cắt bắp có xem trước, báo lỗi từng dòng, trong modal frontend/src/components/BunchOpeningImport.vue, mở từ frontend/src/components/BunchWeeklyForecast.vue

**Checkpoint**: Xem được dự thu 13 tuần từ số thật

---

## Phase 5: User Story 3 - Dự thu xa từ chích bắp, chọn chồi, số kiểm kê (Priority: P3)

**Goal**: Dự thu đến 12 tháng theo tầng, không đếm trùng, có mức tin cậy

**Independent Test**: Quickstart kịch bản 8, 8b

### Tests

- [x] T027 [P] [US3] Unit test tầng chích chờ cắt theo thứ tự trước sau, phần số cây trừ dần, tổng không vượt, trong lotus_farm/tests/test_bunch_flow_rules.py

### Implementation

- [x] T028 [US3] Thêm tầng chích chờ cắt (FR-025), phần còn lại theo số kiểm kê, dồn phần quá hạn (FR-028), không trừ hao hụt hai lần (FR-027) trong lotus_farm/bunch_flow_rules.py
- [x] T029 [US3] Lấy phần theo số cây từ `block_forecast_engine`, thêm vụ sau theo ngày chọn chồi thật trong lotus_farm/bunch_forecast_engine.py
- [x] T030 [US3] Tách số chưa xác nhận, ghi nhãn ước tính theo khu trong lotus_farm/block_forecast.py
- [x] T031 [US3] Hiện mức tin cậy, tách phần số thực tế và ước tính trong frontend/src/BlockForecastApp.vue

**Checkpoint**: Cả 3 mức tin cậy chạy đúng

---

## Phase 6: User Story 4 - So với thực tế, hiệu chỉnh tham số (Priority: P4)

**Goal**: Đo sai số và đề xuất tham số

**Independent Test**: Quickstart kịch bản 10, 11

### Tests

- [x] T032 [P] [US4] Unit test sai số và tham số đề xuất trong lotus_farm/tests/test_forecast_snapshot.py

### Implementation

- [x] T033 [US4] Tính số ngày từ cắt đến thu và kg/buồng thực tế theo lô và màu từ sổ buồng trong lotus_farm/forecast_snapshot.py
- [x] T034 [US4] Viết `create`, `variance`, `suggest_parameters` trong lotus_farm/forecast_snapshot.py
- [x] T035 [US4] Chốt tự động mỗi thứ 2 trong lotus_farm/hooks.py
- [x] T036 [US4] Thêm màn đối chiếu trong frontend/src/components/ForecastVariance.vue, nối vào frontend/src/BlockForecastApp.vue

**Checkpoint**: Có báo cáo sai số; tham số chỉ áp dụng khi duyệt

---

## Phase 7: User Story 5 - Lô chưa báo và số bất thường (Priority: P5)

**Goal**: Cảnh báo đầu ngày

**Independent Test**: Bỏ báo cáo một lô, nhập số vượt số cây, cả hai hiện trong danh sách

- [x] T037 [P] [US5] Unit test phát hiện lô chưa báo và số bất thường trong lotus_farm/tests/test_bunch_posting_rules.py
- [x] T038 [US5] Viết `day_status` trong lotus_farm/bunch_posting.py
- [x] T039 [US5] Hiện danh sách trên màn xác nhận trong frontend/src/components/field/WorkBunch.vue

---

## Phase 8: Polish

- [ ] T040 Liệt kê và chuyển mọi nơi đọc dự thu cũ sang số mới, rồi gỡ engine cũ (FR-022): frontend/src/App.vue, lotus_farm/reporting.py, lotus_farm/onedrive_supply.py, lotus_farm/finance/planning.py, lotus_farm/console.py, lotus_farm/forecast_calendar.py, lotus_farm/vip126_timeline.py, lotus_farm/vip126_trial.py, frontend/src/components/Vip126RollingForecast.vue
- [x] T041 [P] Viết hướng dẫn nhập liệu trong docs/CHAM_BUONG_DU_THU.md
- [x] T042 Chạy toàn bộ quickstart.md và đo thời gian mở màn dự thu toàn vườn
- [x] T043 Chạy toàn bộ test: `node --test tests/*.test.js`, unit test Python, tests/integration/verify_bunch_forecast.py
- [ ] T044 Trên VPS, sau khi chủ vườn đồng ý: sao lưu, migrate, chạy `field_report_seed.apply_bunch_stages` và lotus_farm/bunch_setup.py, tạo tài khoản tổ trưởng, rồi nhập sổ cắt bắp

---

## Dependencies & Execution Order

- Phase 1 đã xong. Phase 2 chặn mọi phần việc.
- US1 là nền cho số liệu mới. US2 làm được ngay sau Phase 2 nhờ số đầu kỳ, nhưng cần `bunch_posting` của US1 để nhận số mới.
- US3 cần US2. US4 cần US2 và lứa thu đầu tiên ngoài vườn (dự kiến cuối tháng 12/2026). US5 cần US1.
- Polish cần tất cả, riêng T040 chỉ làm khi số engine mới đã được đối chiếu.

## Parallel Example

```text
Phase 2: T006, T007, T008
US1 tests: T009, T010, T011
US2 tests: T019, T020
```

## Implementation Strategy

1. **MVP**: Phase 1, 2, US1 và US2: có nhập liệu và dự thu 13 tuần. Áp dụng cho Đội khu A + B trước.
2. Thêm US3 khi đã có số chích bắp vài tuần.
3. Thêm US5 khi đội đã quen nhập.
4. US4 chạy được khi lứa cắt bắp đầu tiên thu hoạch.
5. Gỡ engine cũ sau cùng.
