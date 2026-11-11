---

description: "Danh sách việc: yêu cầu cấp vật tư từ vườn đến Kho"
---

# Tasks: Yêu cầu cấp vật tư từ vườn đến Kho

**Input**: `specs/005-yeu-cau-cap-vat-tu/`

**Prerequisites**: plan.md, spec.md

**Tests**: Có, theo nguyên tắc IV: unit test cho module thuần, integration test cho luồng duyệt → xuất → ghi sổ, mount test cho component có hành vi. Viết test trước, thấy test hỏng rồi mới làm.

**Chạy test ở đâu**: Không chạy test, build, docker hay python trên máy này. Mọi bước "chạy" là trên khu test VPS (bản sao site thật) hoặc GitHub Actions.

**Quyết định chủ vườn 11/11/2026** ("đội trưởng duyệt, không cần tổ trưởng, đội trưởng nhập luôn"): tổ trưởng không lập yêu cầu; đội trưởng lập cho đội và duyệt, kể cả yêu cầu của mình ("Lưu và duyệt" một lần); quản lý vườn lập và duyệt mọi đội. Các việc dưới đây nói "tổ trưởng lập", "không tự duyệt", "tab Vật tư cho tổ trưởng" đọc theo quyết định này (xem spec.md, Clarifications). Backend và test Python đã theo quyết định này.

**Quy ước đường dẫn**: Backend ở `lotus_farm/`. Unit test Python ở `tests/`. Integration ở `tests/integration/`, chạy bằng `tests/integration/run_from_tmp.py`. Frontend ở `frontend/src/`, test ở `frontend/tests/`.

**Không được sửa** (spec 003 và 004): `lotus_farm/purchase_proposal.py`, `purchasing.py`, `purchase_flow.py`, `proposal_rules.py`, `purchase_status.py`, `signing.py`, `signing_rules.py`, `signed_copy.py`, `digital_signature.py`, `procurement*.py`, `warehouse_buying_lite.py`, `warehouse_planning.py`, `www/lotus_material_proposal_print.py` và template in; `frontend/src/components/ProcurementWorkspace.vue`, `MobilePurchaseProposal.vue`, `BuyingMobile.vue`, `components/procurement/*`, `components/WarehousePlanning.vue`, `LotusMobileShell.vue`, `LotusMobileHeader.vue`, `LotusMobileBottomNav.vue`, `components/field/CareDueList.vue`, `LotCards.vue`, `RibbonBoard.vue`, `lot-entry-model.js`, `lotus-tokens.css`, `mobile-ui.css`, `components/ui/*`, `workspace.js`, `DataTable.vue`, `App.vue`, `router.js`, `domain.js`. Nếu một việc tưởng phải sửa các file này thì dừng và hỏi.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: làm song song được (khác file, không phụ thuộc)
- **[Story]**: US1…US5 theo spec.md

---

## Phase 1: Setup

**Purpose**: Đứng trên bản đang chạy thật

- [x] T001 Gộp `main` (a8a304a, spec 003 chạy thật bản 68dd563) vào nhánh `005-yeu-cau-cap-vat-tu`; giải xung đột; đọc lại `lotus_farm/hooks.py`, `lotus_farm/push_notifications.py`, `lotus_farm/warehouse_issue.py`, `frontend/src/WarehouseMobile.vue` và sửa số dòng dẫn trong plan.md nếu lệch
- [ ] T002 Trên khu test VPS (bản sao site thật), kiểm và ghi vào `specs/005-yeu-cau-cap-vat-tu/baseline.md`: Material Request Item có cột `lotus_farm`, `lotus_farm_block`, `lotus_work_type`; tên status Material Request của ERPNext 16 (Pending, Partially Ordered, Issued, Stopped) và `update_status('Stopped'|'Submitted')`; ERPNext có chặn Stock Entry gắn yêu cầu Stopped không; số đếm hiện tại (0 Material Issue, 78 phiếu xuất Thủ công)
- [ ] T003 Trên khu test VPS chạy toàn bộ test hiện có làm mốc; ghi lỗi có sẵn (vd. `verify_farm_land`) vào `specs/005-yeu-cau-cap-vat-tu/baseline.md`; chụp số giá thành tháng và chi phí theo lô/việc để so ở T060

---

## Phase 2: Foundational

**Purpose**: Trường, luật thuần, hook chặn. Mọi user story dựa vào phase này.

**⚠️ CRITICAL**: Không làm user story nào khi phase này chưa xong

### Tests trước

- [x] T004 [P] Viết `tests/test_issue_request_rules.py`: `state` cho mọi tổ hợp (Nháp, Chờ duyệt, Trả lại, Chờ cấp, Kho đang lập phiếu, Đã cấp một phần, Đã cấp đủ, Đã đóng, Đã hủy, cờ quá hạn); `approver_for` và `may_approve` (tổ trưởng → đội trưởng; đội trưởng hoặc đội không đội trưởng → quản lý vườn; quản lý → quản lý khác; không tự duyệt; quản lý duyệt thay; người vừa tổ trưởng vừa đội trưởng = đội trưởng); `may_request`; `line_issues` (lô ngoài khu, trùng vật tư × lô, qty ≤ 0, > 100 dòng, ngày quá khứ, hai việc); `lowered` (giảm, bỏ dòng được; tăng, thêm dòng bị từ chối); `split_by_area` (giữ tổng, đơn vị nguyên theo phần dư lớn nhất, lô thiếu diện tích, lô nhận 0 bị bỏ); `progress`; `duplicates`; `actions` theo vai và trạng thái
- [x] T005 [P] Viết `tests/test_issue_request_guards.py` (frappe giả như `tests/test_warehouse_issue.py`): `before_submit` từ chối khi thiếu cờ duyệt hoặc người duyệt = người lập; `validate` từ chối ghi ngoài API và đổi dòng khi đang chờ duyệt; `before_cancel` và `on_trash` từ chối ngoài lệnh; `on_change` chặn Stopped/mở lại ngoài lệnh nhưng để ERPNext tự đổi Pending/Partially Ordered/Issued; mọi hook bỏ qua Material Request loại Purchase
- [x] T006 [P] Thêm vào `tests/test_push_notifications.py` (hoặc tạo nếu chưa có): `_recipients` trả `[]` cho Material Request loại Material Issue, giữ nguyên cho Purchase
- [x] T007 [P] Viết `frontend/tests/issue-request-model.test.js`: nhãn và màu trạng thái; `splitByArea` giữ tổng và đơn vị nguyên; payload; khóa nháp trên máy

### Làm

- [x] T008 Viết `lotus_farm/issue_request_rules.py` (không import frappe) cho T004
- [x] T009 Viết `lotus_farm/issue_request.py` phần nền: `install_fields()` (9 trường đầu phiếu `lotus_crew`, `lotus_work_team`, `lotus_issue_receiver`, `lotus_issue_approver`, `lotus_issue_sent_at`, `lotus_issue_approved_by`, `lotus_issue_approved_at`, `lotus_issue_return_reason`, `lotus_issue_close_reason`; `lotus_work_assignment` trên Material Request Item); ContextVar `_writing`; hook `validate`, `before_submit`, `before_cancel`, `on_trash`, `on_change`, `issue_posted` cho T005
- [x] T010 Gọi `issue_request.install_fields()` trong `setup()` của `lotus_farm/install.py`
- [x] T011 Thêm một khối riêng sau vòng "Shared mobile PWA notification hooks" trong `lotus_farm/hooks.py`: Material Request `validate`, `before_submit`, `before_cancel`, `on_trash`, `on_change` → `lotus_farm.issue_request.*`; Stock Entry `on_submit`, `on_cancel` → `lotus_farm.issue_request.issue_posted`. Không sửa dòng `doc_events['Material Request']` của 003
- [x] T012 Thêm điều kiện `if doc.material_request_type != "Purchase": return []` đầu nhánh Material Request trong `_recipients` của `lotus_farm/push_notifications.py` (T006)
- [x] T013 Viết `frontend/src/issue-request-model.js` cho T007
- [x] T014 Viết `tests/integration/issue_request_fixture.py`: lập và duyệt một yêu cầu Material Issue qua `issue_request.save/send/approve` với user tạm; sửa `tests/integration/audit_warehouse_edge_cases.py`, `verify_issue_uom.py`, `verify_purchase_flow.py`, `verify_warehouse_audit.py`, `verify_warehouse_regressions.py` để dùng fixture thay vì submit thẳng

**Checkpoint**: unit test T004–T007 qua trên VPS; 5 integration cũ qua với fixture

---

## Phase 3: User Story 1 - Lập, gửi và duyệt (Priority: P1) 🎯 MVP

**Goal**: Tổ trưởng/đội trưởng lập và gửi; người duyệt duyệt, giảm số, trả lại; chặn tự duyệt.

**Independent Test**: spec.md US1.

### Tests trước

- [x] T015 [P] [US1] Viết bước 1–4 và 8 của `tests/integration/verify_issue_request.py` (lập, gửi, chống trùng, từ chối tự duyệt và đường Desk/REST, giảm số + duyệt, sự kiện APPROVE, không có "Có đề xuất mua mới", yêu cầu của đội trưởng do quản lý vườn duyệt) — viết xong, chưa chạy (cần bản sao site thật)
- [x] T016 [P] [US1] Viết `frontend/tests/material-request-form.mount.test.js`: chọn cả khu; mỗi lô / tổng chia theo diện tích; làm tròn đơn vị nguyên; thông báo lỗi; cảnh báo trùng; khôi phục số đang gõ; bấm hai lần gửi một lần với một `client_event_id`; báo "quản lý vườn sẽ duyệt" khi đội trưởng nhập hộ
- [x] T017 [P] [US1] Viết `frontend/tests/material-request-detail.mount.test.js` phần duyệt: nút Duyệt / Giảm số rồi duyệt / Trả lại / Rút lại theo quyền; ReasonDialog bắt lý do; không tăng được số khi giảm
- [x] T018 [P] [US1] Viết `frontend/tests/work-mobile-tabs.mount.test.js`: tổ trưởng thấy Hôm nay · Vật tư · Tôi; đội trưởng giữ 4 tab và thấy thẻ chờ duyệt đầu tab Xác nhận; `?request=` mở đúng tab và chi tiết
- [x] T019 [P] [US1] Mở rộng `frontend/tests/field-navigation.test.js`: `materials` ẩn nhưng vào được, menu trên vẫn 7 mục

### Làm

- [x] T020 [US1] Trong `lotus_farm/issue_request.py`: `form_data`, `item_options`, `stock`, `save`, `send`, `withdraw`, `approve`, `return_request`, `delete_draft`, `detail` (phần đầu phiếu, dòng, lịch sử, `actions`); mọi lệnh ghi qua `controls.lock`, kiểm `modified`, `erp_workbench._command`; duyệt trong `controls.command(doc, 'issue-approve')`, gọi `digital_signature._event(doc, 'APPROVE', user, now, signature_type='NAME')`; thông báo qua `push_notifications._add_alert` / `_send_alert` trong savepoint (app `work`, link `/work?request=…`; email cho quản lý vườn link `/lotus/cong-viec?field_view=materials&request=…`)
- [x] T021 [P] [US1] Viết `frontend/src/components/field/MaterialRequestForm.vue` (ModalForm 860px; `mobile` toàn màn; phần 1, 2, 3, 4 như plan, chưa có chip US4)
- [x] T022 [P] [US1] Viết `frontend/src/components/field/MaterialRequestDetail.vue` phần duyệt (tóm tắt, dòng theo vật tư × lô, tồn ở kho cho người duyệt, nút theo `actions`)
- [x] T023 [US1] Viết `frontend/src/components/field/MaterialRequests.vue` (thẻ đếm, thẻ yêu cầu, `openForm(prefill)`, `openDetail(name)`; props farm, crew, setup, view, team, assignment, compact, mobile)
- [x] T024 [US1] Thêm mục ẩn `materials` vào `frontend/src/field-report-navigation.js`
- [x] T025 [US1] Sửa `frontend/src/FieldReportApp.vue`: mục "Yêu cầu cấp vật tư" trong Giao việc; thẻ "chờ bạn duyệt" trong Hôm nay (không sửa LotToday); view `materials` với bộ chọn vườn/đội; đọc `?request=`
- [x] T026 [US1] Sửa `frontend/src/WorkMobile.vue`: tab `materials` cho người chỉ là tổ trưởng; thẻ chờ duyệt trong Xác nhận; mục yêu cầu trong Giao việc; deep link `?request=`
- [x] T027 [US1] Thêm `MaterialRequestForm.vue` vào danh sách của `frontend/tests/form-standard.test.js`

**Checkpoint**: US1 chạy riêng được trên VPS; yêu cầu đã duyệt hiện trong danh sách nguồn đang có của form Xuất kho

---

## Phase 4: User Story 2 - Kho cấp theo yêu cầu, chi phí đúng lô và việc (Priority: P1)

**Goal**: Hàng chờ "Cấp theo yêu cầu", mở form xuất kho điền sẵn, chiều lô/việc chép từ yêu cầu.

**Independent Test**: spec.md US2.

### Tests trước

- [x] T028 [P] [US2] Mở rộng `tests/test_warehouse_issue.py`: dòng Request nhận `lotus_farm`, `lotus_farm_block`, `lotus_work_type` từ `source_line` và đè giá trị client; lệch vật tư/lô vẫn bị chặn; `choices` bỏ status Issued và có nhãn mới; `lines` trả `header`; module vẫn nạp với mock hiện có (import trong hàm)
- [x] T029 [P] [US2] Viết bước 5, 6, 9, 10, 11, 12 của `tests/integration/verify_issue_request.py` (hàng chờ, phiếu nháp một phần, ghi sổ với chiều lô/việc, GL 621, cấp vượt, Issued, Kho hủy phiếu, snapshot kế hoạch, thẻ tháng, bản in) — viết xong, chưa chạy (cần bản sao site thật)
- [x] T030 [P] [US2] Viết `frontend/tests/issue-request-queue.mount.test.js`: thẻ xếp theo ngày cần, quá hạn tô đỏ; "Lập phiếu xuất" gọi `openFromRequest`
- [x] T031 [P] [US2] Mở rộng `frontend/tests/stock-issue-uom.mount.test.js`: `openFromRequest` đặt chế độ Request, kho xuất, người nhận, dòng = phần còn lại, lô cố định

### Làm

- [x] T032 [US2] Sửa `lotus_farm/warehouse_issue.py`: `source_line` trả thêm `farm`, `farm_block`, `work_type`; `validate_issue` chép 3 chiều vào dòng Request; `choices` bỏ `Issued`, nhãn "số · đội/tổ · lô · việc · cần dd/mm"; `lines` thêm `header`; hàm mới `queue(company, warehouse=None)`
- [x] T033 [US2] Thêm wrapper whitelisted `issue_queue(company, warehouse=None)` trong `lotus_farm/warehouse.py` cạnh `issue_sources`/`issue_lines`
- [x] T034 [P] [US2] Viết `frontend/src/components/stock/IssueRequestQueue.vue` (hộp thoại, thẻ: số, đội/tổ, lô, việc, ngày cần, kho, dòng còn, người duyệt)
- [x] T035 [US2] Sửa `frontend/src/components/stock/StockDocumentForm.vue`: `openFromRequest(name)` lộ ra trong `defineExpose`; điền người nhận từ `header`; hiện "Người đề nghị · Duyệt bởi · Việc"; nhãn nguồn mới
- [x] T036 [US2] Sửa `frontend/src/components/stock/StockDocumentList.vue`: nút "Cấp theo yêu cầu (N)" trong `#actions` khi `kind === 'issues'`
- [x] T037 [US2] Sửa `frontend/src/StockApp.vue`: mở IssueRequestQueue, nối "Lập phiếu xuất" với `openFromRequest`, đọc `?issue_request=`
- [x] T038 [US2] Trong `lotus_farm/issue_request.py`: thông báo khi duyệt cho người Kho tạo được Stock Entry và đọc được kho đó (app `warehouse`, `/warehouse?issue_request=…`; email `/lotus/kho?stock_view=issues&issue_request=…`); `issue_posted` báo "Kho đã cấp …" cho người lập và người duyệt

**Checkpoint**: US1 + US2 = bản dùng được (MVP). Có thể dừng ở đây để triển khai.

---

## Phase 5: User Story 3 - Theo dõi, đóng, mở lại, hủy (Priority: P2)

**Goal**: Tiến độ theo lô, đóng/mở lại/hủy có lý do, thông báo.

**Independent Test**: spec.md US3.

### Tests trước

- [x] T039 [P] [US3] Viết bước 7 của `tests/integration/verify_issue_request.py` (đóng bị chặn khi có nháp, đóng, Kho không chọn được, mở lại, hủy bị chặn khi có phiếu, hủy yêu cầu chưa cấp; mỗi bước có bình luận và thông báo) — viết xong, chưa chạy (cần bản sao site thật)
- [x] T040 [P] [US3] Mở rộng `frontend/tests/material-request-detail.mount.test.js`: Đóng / Mở lại / Hủy / Lập lại theo quyền; còn lại theo lô; mốc thời gian; ẩn In phiếu khi không có quyền
- [x] T041 [P] [US3] Viết `frontend/tests/material-requests.mount.test.js`: thẻ đếm, lọc tổ/trạng thái/ngày/tìm trên một hàng, nhãn quá hạn, thẻ mở chi tiết

### Làm

- [x] T042 [US3] Trong `lotus_farm/issue_request.py`: `requests` (một câu SQL gộp theo `material_request_item`; đã đóng 60 ngày), `close`, `reopen`, `cancel` (trong `controls.command`), phần phiếu xuất và mốc thời gian của `detail`, thông báo đóng/mở lại/hủy
- [x] T043 [US3] Hoàn thiện `frontend/src/components/field/MaterialRequestDetail.vue` (mốc thời gian, phiếu xuất, Đóng/Mở lại/Hủy/Lập lại, In phiếu khi có `print_url`)
- [x] T044 [US3] Hoàn thiện `frontend/src/components/field/MaterialRequests.vue` (view `all`, lọc, nhãn quá hạn)

**Checkpoint**: US1–US3 chạy đủ trên VPS

---

## Phase 6: User Story 4 - Điền sẵn từ phiếu giao việc, vòng chăm sóc, lần trước (Priority: P3)

**Goal**: Bớt gõ, bớt sai liều.

**Independent Test**: spec.md US4.

- [x] T045 [P] [US4] Thêm vào `tests/integration/verify_issue_request.py`: dòng gắn phiếu giao việc; phiếu sai lô/việc/tổ hoặc đã đóng bị từ chối; chip lô đến hạn khớp `care_cycle.due`; "lần trước" ghi nguồn — viết xong, chưa chạy (cần bản sao site thật)
- [x] T046 [P] [US4] Thêm vào `frontend/tests/material-request-form.mount.test.js`: điền sẵn từ phiếu; chip phiếu mở và lô đến hạn; "Lấy như lần trước"; chip cách ly
- [x] T047 [P] [US4] Viết mount test cho mục vật tư trong `frontend/src/components/field/WorkTicket.vue` (`frontend/tests/work-ticket-materials.mount.test.js`)
- [x] T048 [US4] Trong `lotus_farm/issue_request.py`: kiểm `lotus_work_assignment`; thêm phiếu mở, lô đến hạn (gọi `care_cycle.due`) và "lần trước" vào `form_data`; lọc `assignment` trong `requests`
- [x] T049 [US4] Thêm chip và gợi ý vào `frontend/src/components/field/MaterialRequestForm.vue`
- [x] T050 [US4] Sửa `frontend/src/components/field/WorkTicket.vue`: mục "Vật tư cho phiếu này" + nút "Đề nghị cấp vật tư" điền sẵn

---

## Phase 7: User Story 5 - Kho cấp theo yêu cầu trên điện thoại (Priority: P3)

**Goal**: Thủ kho ở kho vườn cấp trên /warehouse.

**Independent Test**: spec.md US5.

- [x] T051 [P] [US5] Viết `frontend/tests/mobile-issue-from-request.mount.test.js`: chọn yêu cầu → dòng còn lại → người nhận → Lưu & ghi sổ qua `create_draft`/`submit_document`, có bước xác nhận tồn đang có; deep link `?issue_request=`
- [x] T052 [US5] Viết `frontend/src/components/MobileIssueFromRequest.vue`
- [x] T053 [US5] Sửa `frontend/src/WarehouseMobile.vue` (bản sau gộp main): một `LotusMobileAction` "Cấp theo yêu cầu (N)" và deep link; báo phiên 003 trước khi sửa

---

## Phase 8: Polish & Cross-Cutting

- [x] T054 [P] Thêm mục "Có gì mới" vào `frontend/src/release-notes.js`
- [x] T055 [P] Thêm một đoạn vào `docs/FIELD_REPORT.md`, `docs/WAREHOUSE_CONSOLE.md`, một dòng vào `docs/ACCESS_AND_SIGNERS.md` (ai lập, ai duyệt, chuỗi `issue_proposal` không dùng)
- [x] T056 Build frontend trên VPS; commit bundle; `tests/test_frontend_calls.py` và `tests/test_no_legacy_names.py` qua
- [x] T057 Chạy toàn bộ unit test Python và frontend trên VPS
- [x] T058 Chạy `tests/integration/verify_issue_request.py` và các bộ: `verify_kho_e2e`, `verify_warehouse_regressions`, `verify_warehouse_audit`, `audit_warehouse_edge_cases`, `verify_issue_uom`, `verify_lot_ledger`, `verify_care_cycle`, `verify_field_reports`, `verify_purchase_flow`, `verify_purchase_proposal`, `verify_signing`, `verify_sign_notify`, `verify_finance`, `verify_costing`
- [ ] T059 Kiểm tay `/work`, `/lotus/cong-viec`, `/lotus/kho` và (nếu có US5) `/warehouse` ở 320px, 390px, ngang trong Chromium trên VPS; không tạo/ghi sổ chứng từ thật
- [ ] T060 So số giá thành tháng, chi phí theo lô, báo cáo vườn tháng trên bản sao trước (T003) và sau: phiếu Thủ công giống hệt; ghi vào `specs/005-yeu-cau-cap-vat-tu/baseline.md`
- [x] T061 Viết `specs/005-yeu-cau-cap-vat-tu/deploy.md` (sao lưu, migrate, lệnh quay lại) — chỉ triển khai khi chủ vườn bảo

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 (MVP) → US3 → US4, US5 → Phase 8.
- US2 cần yêu cầu đã duyệt của US1 để test đầu-cuối, nhưng T028/T032 (chép chiều trong `warehouse_issue.py`) làm song song được với US1.
- US4 cần form của US1. US5 cần US2 và cần `main` đã có màn Kho điện thoại của 003 (T001).
- Trong mỗi story: test trước, rồi backend, rồi component, rồi nối vào màn.

### Parallel

- T004–T007 song song. T015–T019 song song. T021 và T022 song song. T028–T031 song song.

## Implementation Strategy

1. Phase 1–2, rồi US1 + US2: đủ để Kho xuất "Theo yêu cầu đã duyệt" từ yêu cầu lập trong Lotus. Diễn tập trên VPS, hỏi chủ vườn có triển khai không.
2. US3 ngay sau (đóng/hủy cần có trước khi dùng lâu).
3. US4, US5 khi đã có người dùng thật và đã gộp xong với 003/004.

## Notes

- Mỗi sửa vào file dùng chung là một khối riêng, không định dạng lại phần khác của file.
- Không cấp thêm quyền Material Request cho vai trò vườn.
- Chỉ commit, đẩy, triển khai khi chủ vườn bảo.
