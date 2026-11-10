---

description: "Task list: hoàn thiện mua hàng và ký điện tử (spec 003)"
---

# Tasks: Hoàn thiện mua hàng: đề xuất, đơn mua, nhập kho, hóa đơn NCC, công nợ và ký điện tử

**Input**: Tài liệu thiết kế trong `specs/003-mua-hang-ky-dien-tu/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Có. Hiến chương mục IV yêu cầu: quy tắc nghiệp vụ có unit test, luồng ghi sổ có integration test, component có hành vi có mount test.

**Organization**: chia theo user story; mỗi story thử được độc lập.

## Format: `[ID] [P?] [Story] Mô tả`

- **[P]**: chạy song song được (khác file, không phụ thuộc việc chưa xong).
- **[Story]**: US1–US6 theo spec.md.
- Đường dẫn tính từ gốc worktree `C:\code\lotus-003-mua-hang`.

---

## Phase 1: Setup

**Purpose**: môi trường thử riêng, không đụng site `frontend` và cây của spec 002.

- [x] T001 Cài thư viện frontend trong worktree: `npm ci` ở `frontend/`
- [x] T002 Viết `tools/test_site_mua.sh`. Script làm:
  - chạy container `lotus-003-test` từ image `lotus-local-test:20261104`, mount worktree vào `apps/lotus_farm`, nối mạng `lotus-vps-test_frappe_network`, volume `lotus-vps-test_sites`;
  - tạo site `mua.test` từ bản sao lưu mới nhất của site `frontend`;
  - đặt `mute_emails=1` và tắt thông báo đẩy;
  - chạy `bench --site mua.test migrate`.

  Không chạy `bench build`.
- [x] T003 Chạy mốc ban đầu trên `mua.test`:
  - unit test (`python -m unittest discover -s tests -v` trong container);
  - `tests/integration/verify_signing.py` và `verify_purchase_flow.py`;
  - `npm test` và `npm run build`.

  Ghi lỗi có sẵn vào `specs/003-mua-hang-ky-dien-tu/baseline.md`.

---

## Phase 2: Foundational (chặn mọi story)

**Purpose**: vá 3 lỗi đang chạy thật (tách được thành bản vá trên main), cùng phần nền mà mọi story dùng chung.

**⚠️ CRITICAL**: chưa xong phase này thì chưa làm story nào.

### Bản vá B1–B3 (research.md, mục "Lỗi đang có")

- [x] T004 Sửa thông báo ký, trong `lotus_farm/signing.py`, `lotus_farm/signing_rules.py` và `lotus_farm/push_notifications.py`:
  - link đẩy luôn là gốc app + `?sign_dt=&sign_dn=`;
  - chọn app bằng hàm thuần `signing_rules.notify_app(chain_app, device_apps)`: app của chuỗi nếu người nhận có thiết bị ở đó, nếu không thì app đầu tiên;
  - gửi đẩy và email trong savepoint, có try/except và `frappe.log_error`;
  - `_send_alert` bỏ qua thông báo không còn tồn tại.
- [x] T005 [P] Unit test cho `notify_app` và hàm dựng link trong `tests/test_signing_rules.py`
- [x] T006 Integration test trong `tests/integration/verify_signing.py`: người ký phiếu chi có `Lotus Push Device` đang bật, các thao tác lập phiếu, ký bước 2, ký bước cuối và trả lại đều thành công; thông báo nằm trong app `buying`.
- [x] T007 [P] Sửa "In đơn mua":
  - thêm route `/lotus/in-don-mua` trả bản PDF đã lưu, nếu chưa có thì dựng trang in: `lotus_farm/www/lotus_purchase_order_print.py` và `lotus_farm/hooks.py`;
  - `frontend/src/components/ProcurementWorkspace.vue:428` dùng `purchasePdfUrl` trong `frontend/src/purchase-document.js`.
- [x] T008 [P] Dòng tiến độ luôn có `doctype`:
  - máy chủ: `lotus_farm/purchase_flow.py` (khoảng dòng 140) và `lotus_farm/procurement.py` (khoảng dòng 456);
  - giao diện: `frontend/src/components/PurchaseProgress.vue` và `ProcurementWorkspace.vue` (`open()`, tham số URL `purchase_doctype`);
  - kiểm `doctype` trong `tests/integration/verify_purchase_flow.py`.

### Nền tảng chung

- [x] T009 [P] Module thuần `lotus_farm/purchase_status.py` (data-model mục 4). Gồm:
  - `order_state`, xét theo thứ tự "Đã đóng → Đã nhận đủ → Đang nhận → NCC đã xác nhận → Đã gửi NCC → Đã duyệt"; nháp có Nháp, Chờ duyệt, Bị trả lại; hủy là Đã hủy; quá hẹn là cờ riêng;
  - `receipt_state`, kèm tình trạng hóa đơn;
  - `invoice_state`: Chưa trả, Trả một phần, Đã trả, Quá hạn, Đã hủy;
  - `voucher_state`: Nháp, Đang ký, Bị trả lại, Đã chi, Đã đảo;
  - bảng nhãn tiếng Việt.
- [x] T010 [P] Unit test `tests/test_purchase_status.py` cho mọi nhánh của T009
- [x] T011 [P] `proposal_rules.stage(lines, docstatus, round_state, stopped, cancelled)` trong `lotus_farm/proposal_rules.py`:
  - mỗi dòng có `qty`, `ordered` (kể cả đơn nháp), `received`, `returned`, `billed`, `closed`;
  - "Đã nhận đủ": mọi dòng nhận + đóng ≥ `qty`, còn phần chưa có hóa đơn;
  - "Đã xong": như trên và đủ hóa đơn.

  Test trong `tests/test_proposal_rules.py`, gồm ca đơn đóng phần còn lại và ca đề xuất Stopped.
- [x] T012 [P] `frontend/src/purchase-status.js` (nhãn và tông màu cho mọi trạng thái), test ở `frontend/tests/purchase-status.test.js`
- [x] T013 Thêm trường vào DocType ký:
  - `lotus_farm/lotus_farm/doctype/lotus_signature_event/lotus_signature_event.json`: `ip`, `user_agent` ("cắt 500 ký tự"), `roles`, `designation`, `round`, `step_key`, `content_hash`, `image_sha256`, và index (`document_type`, `document_name`);
  - `lotus_farm/lotus_farm/doctype/lotus_sign_request/lotus_sign_request.json`: `signer_designation`, `initials_file`.
- [x] T014 DocType mới `lotus_farm/lotus_farm/doctype/lotus_signed_copy/` (json + py):
  - các trường theo data-model;
  - tên = `sha1(document_type|document_name|round)`, đặt bằng autoname trong controller;
  - System Manager và Lotus Auditor chỉ đọc; không tạo qua API.
- [x] T015 Custom field trong `lotus_farm/procurement_setup.py` (data-model mục 2):
  - Material Request: `lotus_close_reason`, `lotus_closed_by`, `lotus_closed_at`, `lotus_cancel_reason` (allow_on_submit);
  - Material Request Item: `lotus_selected_quote`, `lotus_selected_quote_item`, `lotus_selection_reason` (allow_on_submit);
  - Purchase Order: `lotus_cancel_reason`;
  - Purchase Receipt: `lotus_deliverer_name`, `lotus_deliverer_signature` (riêng tư), `lotus_delivery_proof`, `lotus_cancel_reason`;
  - Purchase Invoice: `lotus_cancel_reason`;
  - Purchase Invoice Item: `lotus_variance_reason`.
- [x] T016 `signing.can_view(doctype, name)` trong `lotus_farm/signing.py`: có quyền đọc, hoặc có dòng ký trong vòng mới nhất, hoặc là người lập. Dùng cho phần đọc của `signing._doc` và `chain_status`. Test trong `tests/integration/verify_signing.py`.
- [x] T017 Tách `frontend/src/components/procurement/use-procurement.js` (công ty, danh mục, `run`, `ask`, `act`, `open`) ra khỏi `ProcurementWorkspace.vue`. Không đổi hành vi; các test `frontend/tests/procurement-*.test.js` vẫn qua.
- [x] T018 [P] `frontend/src/mobile-deep-link.js`:
  - đọc `sign_dt`/`sign_dn`, `doctype`/`doc`, và các tham số cũ `proposal`, `request`, `tab`;
  - gọi bảng hàm mở chứng từ của từng app;
  - xóa tham số bằng `replaceState`.

  Test ở `frontend/tests/mobile-deep-link.test.js`.

**Checkpoint**: 3 lỗi đã vá; trạng thái, quyền xem và DocType sẵn sàng.

---

## Phase 3: User Story 1 - Ký điện tử (Priority: P1) 🎯 MVP

**Goal**: một hộp Chờ tôi ký và một tấm ký dùng chung trên điện thoại và máy tính; bản PDF lưu khi ký đủ; nhật ký đủ; ký nhiều; giám đốc ký mọi đơn mua.

**Independent Test**: quickstart.md mục US1 (kịch bản 1–7).

### Tests cho User Story 1

- [x] T019 [P] [US1] (Làm trong `tests/integration/verify_signing.py`, không tách file riêng.) Các ca:
  - inbox gộp mọi chuỗi, mỗi dòng đủ cột như contract;
  - `inbox_count`;
  - người được chỉ định nhưng không có quyền đọc vẫn thấy;
  - `sign_many`: một chứng từ lỗi thì các chứng từ khác vẫn ký;
  - `reassign` ghi sự kiện REASSIGN và bắt buộc lý do.
- [x] T020 [P] [US1] (Làm trong `tests/integration/verify_signing.py` cho phiếu kho và đơn mua; đề xuất kiểm ở T045, phiếu chi ở T091 khi có mẫu in.) Các ca:
  - mỗi vòng ký đủ của đề xuất, đơn mua và phiếu chi tạo đúng 1 `Lotus Signed Copy`;
  - lỗi dựng PDF thì rollback chữ ký cuối;
  - `verify` trả `archive_match`;
  - đổi ảnh chữ ký không đổi PDF đã lưu.
- [x] T021 [P] [US1] `tests/test_signing_rules.py`: bước kiểm tra của từng chuỗi (đề xuất bước 3, đơn bước 1, phiếu chi bước 2).

### Implementation cho User Story 1 (máy chủ)

- [x] T022 [US1] `lotus_farm/signed_copy.py`:
  - `render(doc, chain, round)` dựng HTML từ trang in ở chế độ tin cậy, rồi PDF qua `print_kit.pdf`;
  - lưu File riêng tư gắn vào chứng từ; tính sha256; tạo `Lotus Signed Copy`;
  - `verify(doc, round)` trả `archive_match`.
- [x] T023 [US1] Thêm chế độ `trusted` cho các trang in:
  - `lotus_farm/www/lotus_material_proposal_print.py` (`build`);
  - `lotus_farm/www/lotus_stock_print.py` (`build`);
  - `lotus_farm/www/lotus_purchase_order_print.py` (`html`).

  Người xem thường đi qua `signing.can_view`.
- [x] T024 [US1] `signing._completed(doc, key, round, effect)` trong `lotus_farm/signing.py`:
  - chạy từ nhánh "đủ chữ ký" của `sign()` và từ `start()` của chuỗi một bước;
  - thứ tự: ghi chữ ký → `effect` → dựng PDF → `Lotus Signed Copy` → thông báo.

  Sửa các nơi gọi truyền `effect` vào:
  - `lotus_farm/purchase_proposal.py:385-390`;
  - `lotus_farm/purchasing.py:200-207`, bỏ nhánh `record=False`;
  - `lotus_farm/finance/payments.py:405-410`;
  - `lotus_farm/hr_period.py:346-352`.

  Đơn mua lưu PDF qua `signed_copy`; đường `token=` cũ vẫn giữ.
- [x] T025 [US1] Nhật ký ký trong `signing._record` (`lotus_farm/signing.py`): ghi `ip`, `user_agent`, `roles`, `designation`, `round`, `step_key`, `content_hash`, `image_sha256`. Ghi thêm `signer_designation` và `initials_file` (chỉ ở bước kiểm tra) lên `Lotus Sign Request`.
- [x] T026 [US1] Trong `lotus_farm/signing.py`:
  - `reassign` bắt buộc lý do và ghi sự kiện REASSIGN;
  - `return_document` từ chối chuỗi `purchase_order` và `payment_voucher`.
- [x] T027 [US1] Viết lại `inbox`, thêm `inbox_count` và `open_targets` trong `lotus_farm/signing.py`:
  - các cột theo contracts;
  - truy vấn gộp theo loại chứng từ để lấy người lập, số tiền, ngày;
  - lọc theo `can_view`;
  - dùng `notified_at`.
- [x] T028 [US1] `sign_many` trong `lotus_farm/signing.py`:
  - bảng tra `SIGN_HANDLERS` theo chuỗi: `purchase_proposal.sign`, `purchasing.approve_order`, `finance.payments.sign_payment`, `signing.confirm`, hàm ký kỳ công;
  - mỗi chứng từ một savepoint `lotus_bulk_sign`;
  - khóa theo thứ tự đã sắp xếp;
  - thông báo gửi sau vòng lặp;
  - kết quả trả theo từng chứng từ.
- [x] T029 [US1] `lotus_farm/www/verify/lotus.py` và `signing.verify` trả thêm kết quả so với bản lưu (`archive_match`).
- [x] T030 [US1] Trang `/lotus/mo` trong `lotus_farm/www/lotus_open.py` (+ `.html`):
  - chưa đăng nhập thì sang trang đăng nhập;
  - chọn link điện thoại hay máy tính theo trình duyệt;
  - route đặt trước `/lotus/<path>` trong `lotus_farm/hooks.py`.

  Link email trong `signing._notify` trỏ tới trang này.
- [x] T031 [US1] Ô chữ ký trên bản in, trong `lotus_farm/templates/print/_macros.html` và `lotus_farm/print_kit.py`:
  - hiện chức danh;
  - không có ảnh thì ghi "Đã ký điện tử: <họ tên>, <giờ>";
  - footer có ký nháy của bước kiểm tra (data URI), ẩn khi tài liệu chỉ có 1 trang;
  - lề dưới 22 mm.
- [x] T032 [US1] Viết lại `purchasing.check_submission` (`lotus_farm/purchasing.py`) theo research R7:
  - đủ chữ ký đúng người được chỉ định, dấu vân tay khớp, người bấm là người duyệt;
  - áp mọi đơn của công ty đang bật luồng mua, miễn đơn trước `lotus_purchase_flow_since`.

  Kèm theo:
  - xóa `procurement._approve_by_policy`, nơi gọi của nó trong `select_quotes` và `lotus_policy_approved` (`lotus_farm/procurement.py`);
  - xóa `warehouse_buying_lite.submit_order`;
  - sửa `tests/integration/verify_warehouse_regressions.py`, `verify_warehouse_audit.py`, `audit_warehouse_edge_cases.py` để ký đúng chuỗi.
- [x] T033 [US1] Patch `lotus_farm/patches/return_unsigned_pending_orders.py` (thêm vào `lotus_farm/patches.txt`): đơn "Chờ duyệt" chưa có vòng ký trả về Nháp, kèm ghi chú. Chạy lại không ghi trùng; in ra số đơn.
- [x] T034 [US1] Gỡ ký bằng QR và nút ký nháy đơn mua:
  - máy chủ: `lotus_farm/digital_signature.py:326-411`, tham số `sign_token` trong `lotus_farm/purchasing.py` và `lotus_farm/erp_workbench.py:542`, phần ký nháy trong `lotus_farm/www/lotus_purchase_order_print.py`;
  - xóa thư mục DocType `lotus_signing_challenge`, thêm patch `lotus_farm/patches/drop_signing_challenge.py`;
  - dòng dịch trong `lotus_farm/translations/vi.csv`;
  - giao diện: `frontend/src/BuyingMobile.vue:43,208,224-242,384-390,422-430`;
  - test: sửa `frontend/tests/signature-v2.test.js` và `frontend/tests/approval-self-role.test.js`.

### Implementation cho User Story 1 (giao diện)

- [x] T035 [P] [US1] `frontend/src/use-signing.js`:
  - `inbox`, `count`, `sign` (gọi hàm của chuỗi), `signMany`, `returnDoc`, `reassign`;
  - câu xác nhận nêu loại chứng từ, số, số tiền, bước.

  Test ở `frontend/tests/use-signing.test.js`.
- [x] T036 [P] [US1] `frontend/src/components/signing/SignaturePad.vue`: chỉ có canvas, màu nét lấy từ token. Tách `frontend/src/use-signature-profile.js` từ `LotusMobileSignatureSettings.vue:26-81`. Test mount cho cả hai.
- [x] T037 [US1] `frontend/src/components/signing/SignSheet.vue`: WorkspaceModal gồm khung xem trang in, `LotusSignatureTimeline`, nút Ký / Trả lại / Chuyển người ký (xác nhận qua `useWorkspaceConfirm`) và link "Mở chứng từ". Test mount.
- [x] T038 [US1] `frontend/src/components/signing/SigningInboxPage.vue` (`/lotus/cho-ky`):
  - DataTable chọn nhiều; Ký nhiều xác nhận một lần, kết quả hiện theo từng dòng;
  - route trong `frontend/src/domain.js`, `router.js`, `workspace-routes.js`, `App.vue`;
  - nút có số đếm ở `.workspace-right` của `frontend/src/components/WorkspaceBar.vue`.

  Test mount.
- [x] T039 [US1] `frontend/src/components/signing/SignatureSettings.vue` (components/ui + WorkspaceModal), mở từ menu người dùng của `WorkspaceBar.vue`. Test mount.
- [x] T040 [US1] `frontend/src/components/LotusMobileSignInbox.vue` và `LotusMobileSignSheet.vue`:
  - dùng Vant; xác nhận qua `useMobileConfirm`; chọn nhiều;
  - biểu tượng có số đếm ở header của `frontend/src/components/LotusMobileShell.vue`, vừa một hàng ở 320 px.

  Test mount; cập nhật `frontend/tests/mobile-shared-plan.test.js`.
- [x] T041 [US1] Gắn `mobile-deep-link.js` vào:
  - `frontend/src/BuyingMobile.vue` (`proposal`, `doc`, `sign_dt`);
  - `frontend/src/WarehouseMobile.vue`, `WorkMobile.vue`, `HrMobile.vue`.

  `LotusMobileNotifications.vue` mở tấm ký mà không tải lại trang. `lotus_farm/public/lotus-push-worker.js` nhận link có pathname đúng gốc app, kèm query.
- [x] T042 [US1] `frontend/src/components/LotusMobileSignatureSettings.vue` và `LotusSignatureDraw.vue` chuyển sang dùng `use-signature-profile.js` và `SignaturePad.vue`. Hành vi trên điện thoại không đổi.
- [x] T043 [US1] Màn máy tính mở chứng từ từ URL ở mỗi lần điều hướng:
  - `ProcurementWorkspace.vue` (`consumeAction` đọc `purchase_doc`/`purchase_doctype`);
  - `frontend/src/FinanceApp.vue` đọc `doc`/`doctype` để mở phiếu chi.
- [x] T044 [US1] Thẻ "Chờ tôi ký" có số đếm ở trang chủ `BuyingMobile.vue` và `WarehouseMobile.vue`.

**Checkpoint**: US1 chạy trọn quickstart US1 và đưa lên VPS được như một bản riêng.

---

## Phase 4: User Story 2 - Bảng đề xuất mua (Priority: P1)

**Goal**: giai đoạn và số đếm đúng; đóng và hủy có lý do; một biểu mẫu chung; đủ thao tác trên hai giao diện.

**Independent Test**: quickstart.md mục US2.

### Tests cho User Story 2

- [x] T045 [P] [US2] `tests/integration/verify_purchase_proposal.py`, các ca:
  - giai đoạn và số đếm;
  - `close_remainder`: chuyển Stopped kèm lý do; từ chối khi còn đơn nháp hoặc đơn chờ duyệt;
  - `cancel_proposal`: từ chối khi có dòng đơn; nhánh `cancel_quotes=1`;
  - `sign` kèm lý do cho đề xuất nhập từ Excel;
  - người được chỉ định không có quyền đọc vẫn xem chi tiết và in được;
  - kiểm kho;
  - đơn đóng phần còn lại → "Đã nhận đủ"; có hóa đơn → "Đã xong".
- [x] T046 [P] [US2] `frontend/tests/purchase-proposal.mount.test.js`: tab giai đoạn có số đếm; hộp đóng và hủy bắt lý do; hộp ký hỏi lý do.

### Implementation cho User Story 2

- [x] T047 [US2] `purchase_flow.proposal_totals(names)` trong `lotus_farm/purchase_flow.py`:
  - tổng theo dòng `ordered` (kể cả đơn nháp), `received`, `returned`, `billed`, `closed` (phần chưa nhận của đơn đã đóng + phần chưa đặt khi Stopped);
  - không phụ thuộc người xem;
  - `proposal_progress` dùng hàm này.
- [x] T048 [US2] `purchase_proposal.proposals`: giai đoạn lấy từ `proposal_rules.stage`; có `counts`, các bộ lọc theo contracts, gồm cả đề xuất đã hủy. `procurement.needs` dùng cùng cách tính. Sửa `lotus_farm/purchase_proposal.py` và `lotus_farm/procurement.py`.
- [x] T049 [US2] Trong `lotus_farm/purchase_proposal.py`:
  - `close_remainder`: native Stopped, ghi `lotus_close_*`;
  - `cancel_proposal`: có lý do, kèm hủy báo giá chưa dùng nếu chọn;
  - `detail` trả thêm `stage`, các cờ `can_*`, `print_url`, `signed_copy`.
- [x] T050 [US2] Trong `lotus_farm/purchase_proposal.py` và `lotus_farm/purchasing.py`:
  - `purchase_proposal.sign` nhận `reason` ở bước 0;
  - `_apply_lines` kiểm kho: cùng công ty, không phải nhóm, không bị tắt;
  - `purchasing.create_request` bỏ lý do mặc định và bỏ nhánh submit chưa ký.
- [x] T051 [US2] `lotus_farm/www/lotus_material_proposal_print.py`:
  - người xem qua `can_view`;
  - trả bản đã lưu nếu có.
- [x] T052 [US2] `frontend/src/components/procurement/NeedDetail.vue` và `NeedForm.vue`, tách từ `ProcurementWorkspace.vue`:
  - hiện giai đoạn và tiến độ từng dòng có link;
  - thao tác: sửa, ký gửi, trả lại, chuyển người ký, xóa nháp, in, hủy, đóng phần chưa mua;
  - danh sách có tab giai đoạn kèm số đếm.
- [x] T053 [US2] `frontend/src/components/WarehousePlanning.vue` dùng `NeedForm` và mở chi tiết ngay trên máy tính.
- [x] T054 [US2] Điện thoại:
  - `frontend/src/components/MobilePurchaseProposal.vue`: tab giai đoạn có số đếm, đóng/hủy, chia sẻ PDF (`navigator.share`), link tiến độ mở ngay trong app;
  - `frontend/src/WarehouseMobile.vue` dùng `MobilePurchaseProposal`, bỏ form rút gọn ở dòng 261-279 và template 637-650.
- [x] T055 [P] [US2] Thống nhất chữ "Đề xuất" ở:
  - `lotus_farm/procurement_reports.py:9`;
  - `frontend/src/components/StockReceiptReason.vue:44`;
  - `frontend/src/components/ProcurementCompare.vue:52,56`;
  - `lotus_farm/procurement.py:361,397`.

**Checkpoint**: US1 và US2 chạy độc lập.

---

## Phase 5: User Story 3 - Đơn mua (Priority: P2)

**Goal**: giữ NCC và giá của báo giá đã chọn; cảnh báo ngay khi lưu; giám đốc ký mọi đơn; máy tính đủ thao tác; so sánh giá dạng thẻ trên điện thoại.

**Independent Test**: quickstart.md mục US3.

### Tests cho User Story 3

- [x] T056 [P] [US3] `tests/integration/verify_purchase_flow.py`, các ca:
  - `choose_quote` rồi `request_detail` giữ NCC và giá;
  - cảnh báo khi `save_order`;
  - `select_quotes` không tự duyệt;
  - submit qua REST bởi người duyệt không được chỉ định bị chặn;
  - trả lại và hủy có lý do; dòng đề xuất quay lại "Chờ mua";
  - `delete_draft` kiểm người lập;
  - tài khoản chỉ có vai trò mua hàng chạy được `select_quotes`;
  - `state` theo bộ tên chung.
- [x] T057 [P] [US3] Mount test cho `CompareCards` (chọn báo giá, lý do) và `OrderDetail` (thao tác máy tính, hiện cảnh báo) trong `frontend/tests/`.

### Implementation cho User Story 3

- [x] T058 [US3] Trong `lotus_farm/procurement.py`:
  - `choose_quote` ghi `lotus_selected_*`; bắt buộc lý do khi không chọn giá thấp nhất;
  - `compare` trả `selected`;
  - `cancel_quotation`: từ chối khi còn dòng đơn trỏ tới; báo giá nháp thì xóa.
- [x] T059 [US3] `select_quotes` chỉ tạo đơn nháp; có `approver` thì gửi duyệt luôn (`lotus_farm/procurement.py`).
- [x] T060 [US3] `warehouse_buying_lite.request_detail` trả NCC, giá, thuế, phí vận chuyển, link báo giá đã chọn; dòng chưa chọn lấy giá dự kiến. `frontend/src/mobile-purchase.js` (`purchaseFromRequest`) giữ các trường này. Sửa thêm `lotus_farm/warehouse_buying_lite.py`.
- [x] T061 [US3] `purchase_flow.order_issues(doc)`:
  - tính cả phần đã giữ chỗ bởi đơn nháp và đơn chờ duyệt khác;
  - `order_guard` ném lỗi dựa trên hàm này;
  - `save_order` và `request_approval` trả `warnings[]`.

  Sửa `lotus_farm/purchase_flow.py`, `lotus_farm/warehouse_buying_lite.py`, `lotus_farm/purchasing.py`.
- [x] T062 [US3] Đơn mua:
  - `cancel_order` có lý do; vai trò Lotus Purchase Approver có quyền cancel Purchase Order (`lotus_farm/warehouse_access.py`);
  - `delete_draft` kiểm người lập; đơn phải Nháp hoặc Bị trả lại;
  - `detail` và `orders` trả `purchase_status.order_state`, `overdue`, chuỗi ký, lý do trả lại, `print_url`, `signed_copy`.

  Sửa `lotus_farm/purchasing.py` và `lotus_farm/warehouse_buying_lite.py`.
- [x] T063 [US3] `frontend/src/components/procurement/OrderDetail.vue` (hai chế độ):
  - hiện tiến độ duyệt và lý do trả lại;
  - thao tác: sửa, gửi, trả lại, duyệt, hủy, xóa, in, đã gửi NCC, NCC xác nhận, đổi hẹn, đóng phần chưa giao.

  `MobilePurchaseOrderDetail.vue` dùng nhãn của `purchase-status.js`.
- [x] T064 [US3] `frontend/src/components/procurement/CompareCards.vue`; `ProcurementCompare.vue` ở chế độ điện thoại dùng component này và ghi lựa chọn qua `choose_quote`.
- [x] T065 [US3] `frontend/src/WarehouseMobile.vue`: sửa đơn nháp và gửi duyệt (chọn người duyệt) bằng `MobilePurchaseOrderDetail`, như app Mua hàng.
- [x] T066 [US3] Danh sách đơn hiện trạng thái chung và cột tiến độ hóa đơn, trả tiền: `ProcurementWorkspace.vue` và `BuyingMobile.vue`. `frontend/src/buying-order-status.js` chuyển sang dùng `purchase-status.js`.

**Checkpoint**: US1–US3 chạy độc lập.

---

## Phase 6: User Story 4 - Nhập kho (Priority: P2)

**Goal**: một đường nhận hàng có ảnh, chi phí và xác nhận của người giao; xác nhận nhập là thủ kho ký; trả hàng, hủy, xóa, in và đính kèm ngay trong Lotus.

**Independent Test**: quickstart.md mục US4.

### Tests cho User Story 4

- [x] T067 [P] [US4] `tests/integration/verify_procurement.py` và `verify_procurement_concurrency.py`, các ca:
  - nhận một bước có file và người giao;
  - `before_submit` chặn khi thiếu cả chữ ký lẫn ảnh phiếu giao;
  - chuỗi `purchase_receipt` tự ký và tạo `Lotus Signed Copy`;
  - hai người nhận cùng lúc → "Còn nhận được N";
  - `return_receipt` với `post=1` trả `needs_credit_note`;
  - hủy có lý do; quy tắc xóa nháp;
  - nhãn "Mua nhanh".
- [x] T068 [P] [US4] Chuỗi `purchase_receipt` trong `tests/test_signing_rules.py`; mount test form nhận hàng: bắt buộc chữ ký hoặc ảnh phiếu giao.

### Implementation cho User Story 4

- [x] T069 [US4] Hook `Purchase Receipt.before_submit`: phiếu theo đơn của công ty đang bật luồng mua phải có `lotus_deliverer_name` + `lotus_deliverer_signature`, hoặc `lotus_delivery_proof`. Sửa `lotus_farm/purchase_flow.py` và `lotus_farm/hooks.py`.
- [x] T070 [US4] Chuỗi `purchase_receipt` trong `lotus_farm/signing_rules.py`: một bước, có bước chốt, vai trò thủ kho. `signing.chain_for` giữ các vòng `stock_document` cũ trên chuỗi cũ.
- [x] T071 [US4] `warehouse_planning.receive_order` (`lotus_farm/warehouse_planning.py`) ghi sổ một bước:
  - file gắn trong cùng giao dịch; người giao; chi phí; `client_key`;
  - `signing.start` chuỗi `purchase_receipt` + `_completed` (lưu PDF);
  - bắt lỗi "record changed" và deadlock → rollback → báo "Còn nhận được N".
- [x] T072 [US4] `receipt_action`: hủy có lý do (`lotus_cancel_reason`); xóa nháp kiểm người lập hoặc vai trò nhận hàng. Sửa `lotus_farm/warehouse_planning.py` và `lotus_farm/warehouse_access.py`.
- [x] T073 [US4] Trả hàng và chi tiết phiếu:
  - `procurement.return_receipt` có `post=1`, trả `needs_credit_note`;
  - `procurement.receipt` trả thêm `files`, người giao, `print_url`, `signed_copy`, tình trạng hóa đơn;
  - đổi nhãn "Mua ngoài" thành "Mua nhanh" ở `lotus_farm/warehouse.py:330`.

  Sửa `lotus_farm/procurement.py` và `lotus_farm/procurement_adjustments.py`.
- [x] T074 [US4] Bản in phiếu nhận có chữ ký hoặc ảnh phiếu giao của người giao, và chữ ký thủ kho: `lotus_farm/www/lotus_stock_print.py` và mẫu in.
- [x] T075 [US4] `frontend/src/components/WarehouseReceiving.vue`:
  - khối người giao: `SignaturePad` + họ tên, hoặc ảnh phiếu giao;
  - chụp ảnh trước khi ghi sổ; chi phí;
  - gọi đường nhận một bước.
- [x] T076 [US4] `frontend/src/WarehouseMobile.vue`: luồng nhận hàng chuyển sang một bước, có ảnh, chi phí, người giao (`SignaturePad` trong popup Vant) và thông báo số còn nhận được.
- [x] T077 [US4] `frontend/src/components/procurement/ReceiptDetail.vue` (hai chế độ):
  - thao tác: in, đính kèm, trả hàng (ghi sổ ngay), hủy có lý do, xóa nháp, link hóa đơn;
  - nhãn lấy từ `purchase-status.js`;
  - bỏ link Desk ở `ProcurementWorkspace.vue:438`.

**Checkpoint**: US1–US4 chạy độc lập.

---

## Phase 7: User Story 5 - Hóa đơn NCC (Priority: P3)

**Goal**: một lõi lập hóa đơn (không còn 1331 khi bật thuế vào giá vốn); Hóa đơn chờ nhập; file gốc cạnh biểu mẫu; chặn hủy khi đã có thanh toán; in.

**Independent Test**: quickstart.md mục US5.

### Tests cho User Story 5

- [x] T078 [P] [US5] `tests/test_procurement_rules.py`: ngưỡng tổng in "1 đồng × số dòng hàng" và chỉ ra dòng nghi sai.
- [x] T079 [P] [US5] `tests/integration/verify_finance.py` và `verify_vat_in_cost.py`, các ca:
  - 2 phiếu nhận, thuế 5% và 8% xen nhau, phí vận chuyển, hộ kinh doanh: không có 1331, 33881 về 0;
  - hóa đơn cho phiếu Mua nhanh; hóa đơn dịch vụ;
  - trùng hóa đơn giữa các đường lập;
  - lệch giá bắt buộc có lý do;
  - hủy bị chặn khi đã có thanh toán;
  - hủy hóa đơn chưa trả xóa `lotus_purchase_invoice` trên phiếu Mua nhanh;
  - `make_goods_invoice` và `make_service_invoice` không ghi 1331.

### Implementation cho User Story 5

- [x] T080 [US5] `lotus_farm/finance/supplier_invoice.py`: `queue`, `source`, `create` (lõi theo research R16), `detail`, `invoices` (theo ngày chốt), `cancel`. Các lớp bọc gọi `create`:
  - `procurement.invoice_receipt` và `billing_source` (`lotus_farm/procurement.py`);
  - `payments.make_goods_invoice` và `make_service_invoice` (`lotus_farm/finance/payments.py`). Việc này sửa lỗi B4.
- [x] T081 [US5] Trên `mua.test`, thử bật Buying Settings `set_landed_cost_based_on_purchase_invoice_rate` với hộ kinh doanh.
  - Nếu 33881 về 0: thêm patch `lotus_farm/patches/enable_landed_cost_invoice_rate.py`.
  - Nếu không: điều chỉnh giá theo mẫu ở `lotus_farm/finance/stock.py:155-189`.

  Ghi kết quả vào research.md R16.
- [x] T082 [US5] Hóa đơn cho phiếu Mua nhanh có chi phí phát sinh ghi Nợ 3388 theo tiền hàng, không gồm chi phí (`lotus_farm/finance/supplier_invoice.py`). Phép đối chiếu trong `lotus_farm/finance/reports.py` dùng 3388 + 33881.
- [x] T083 [US5] Hook `Purchase Invoice.before_cancel` chạy cùng phép chặn với `cancel`: `lotus_farm/finance/native_guards.py` và `lotus_farm/hooks.py`.
- [x] T084 [P] [US5] `lotus_farm/stock_attachments.py` cho phép đính kèm vào Purchase Invoice và Payment Entry.
- [x] T085 [P] [US5] Trang `/lotus/in-hoa-don` (`lotus_farm/www/lotus_invoice_print.py`), kèm mẫu in và route trong `hooks.py`.
- [x] T086 [US5] `frontend/src/components/procurement/InvoiceQueue.vue` (phiếu nhận và Mua nhanh chưa có hóa đơn, cờ có file); thêm mục vào `frontend/src/procurement-navigation.js`.
- [x] T087 [US5] `frontend/src/components/procurement/InvoiceForm.vue`:
  - chọn phiếu nhận; dòng điền sẵn;
  - đầu hóa đơn, thuế theo từng dòng, lý do khi lệch giá, tổng in và thuế in;
  - file gốc hiện cạnh biểu mẫu (máy tính) hoặc mở bằng một chạm (điện thoại); đính kèm;
  - gọi `supplier_invoice.create`.
- [x] T088 [US5] `frontend/src/components/procurement/InvoiceDetail.vue`: chi tiết, file, thanh toán, hủy có lý do, hóa đơn điều chỉnh, in.
- [x] T089 [US5] Màn "Chờ hạch toán" của `frontend/src/FinanceApp.vue` dùng `InvoiceForm` và lõi chung, bỏ đường thuế riêng.

**Checkpoint**: US1–US5 chạy độc lập.

---

## Phase 8: User Story 6 - Công nợ và trả tiền (Priority: P3)

**Goal**: tuổi nợ theo ngày chốt, đến hạn, hàng chưa có hóa đơn, sổ chi tiết, biên bản đối chiếu; phiếu chi trả nhiều hóa đơn; in phiếu chi; đảo phiếu.

**Independent Test**: quickstart.md mục US6.

### Tests cho User Story 6

- [x] T090 [P] [US6] `tests/test_procurement_rules.py`: nhóm tuổi nợ (chưa đến hạn, 1–30, 31–60, 61–90, trên 90 ngày, không có hạn) và khoảng "đến hạn 7 ngày".
- [x] T091 [P] [US6] `tests/integration/verify_procurement_complete.py`, các ca:
  - `payables` theo ngày chốt có tuổi nợ;
  - `unbilled` khớp 3388 + 33881; `due_soon`;
  - `supplier_statement`: đầu kỳ, các dòng, cuối kỳ khớp sổ cái;
  - `supplier_payment.prepare` trả nhiều hóa đơn, phần vượt ghi tạm ứng, idempotent;
  - đảo phiếu chỉ kế toán trưởng làm được;
  - trang in phiếu chi dựng được.

### Implementation cho User Story 6

- [x] T092 [US6] `procurement_queries.payables` (tuổi nợ, `due_7d`, `unbilled`, phép đối chiếu), `due_soon`, `supplier_statement` trong `lotus_farm/procurement_queries.py`. Phần tính thuần đặt ở `lotus_farm/procurement_rules.py`.
- [x] T093 [US6] Lõi `prepare` trong `lotus_farm/finance/supplier_payment.py`; `procurement.supplier_payment` và `payments.prepare_supplier_payment` thành lớp bọc. File đính kèm vào Payment Entry.
- [x] T094 [US6] Trang `/lotus/in-phieu-chi` (`lotus_farm/www/lotus_payment_print.py`, mẫu in, route trong `hooks.py`):
  - phiếu chi tiền mặt có ô Thủ quỹ và Người nhận tiền; giấy đề nghị chi khi chuyển khoản;
  - số tiền bằng chữ; chữ ký chuỗi; QR.

  `_voucher_info` trong `lotus_farm/finance/payments.py` bổ sung dữ liệu. Bản lưu PDF của chuỗi phiếu chi dùng trang này.
- [x] T095 [P] [US6] Trang `/lotus/in-doi-chieu` (`lotus_farm/www/lotus_statement_print.py`) kèm mẫu in.
- [x] T096 [US6] `frontend/src/components/procurement/PayablesView.vue` (hai chế độ): ngày chốt, tuổi nợ, đến hạn 7 ngày, hàng chưa có hóa đơn, từng NCC, mở sổ chi tiết.
- [x] T097 [US6] `frontend/src/components/procurement/SupplierStatement.vue`: chọn kỳ, mở từng chứng từ, in.
- [x] T098 [US6] `frontend/src/components/procurement/PaymentForm.vue`: chọn hóa đơn của một NCC từ màn công nợ; số tiền; phần vượt ghi tạm ứng; hình thức chi; tham chiếu; file; người ký.
- [x] T099 [US6] `frontend/src/components/procurement/VoucherDetail.vue` (hai chế độ): ký, trả lại, hủy nháp, đảo phiếu (kế toán trưởng), in.

**Checkpoint**: cả 6 story chạy độc lập.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [x] T100 Bỏ mọi link Desk còn lại trong luồng mua (`ProcurementWorkspace.vue:424`; tìm `/app/` trong `frontend/src/components/procurement/`)
- [x] T101 Thay các bảng nhãn trạng thái còn lại (danh sách ở research.md R21) bằng `purchase-status.js` (giao diện) và `purchase_status.py` (máy chủ)
- [x] T102 [P] Thêm component mới vào danh sách kiểm của `frontend/tests/form-standard.test.js`. Mở `frontend/tests/design-tokens.test.js` cho thư mục con `components/procurement` và `components/signing`.
- [x] T103 Rà ma trận thao tác ở 320, 390, 844 và 1440 px bằng `tools/verify_mobile_purchase_dom.mjs` và `tools/verify_desktop_workspace_dom.mjs`. Ghi kết quả vào `specs/003-mua-hang-ky-dien-tu/checklists/ui-audit.md`.
- [x] T104 [P] Cập nhật `docs/MUA_HANG_WORKSPACE.md`, `docs/LOTUS_SIGNATURE_V2.md` và bản dịch mới trong `lotus_farm/translations/vi.csv`
- [x] T105 [P] Thêm mục mới ở đầu `frontend/src/release-notes.js`
- [x] T106 Chạy toàn bộ quickstart.md trên `mua.test` và ghi kết quả

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc gì.
- **Foundational (Phase 2)**: sau Setup; chặn mọi story. T004–T008 tách được thành bản vá trên main.
- **US1 (Phase 3)**: sau Phase 2. Là MVP.
- **US2 (Phase 4)**: sau Phase 2. Tấm ký và hộp chờ ký của US1 là cách ký đề xuất thuận nhất, nhưng màn đề xuất vẫn thử được với panel ký sẵn có.
- **US3 (Phase 5)**: sau Phase 2. Phần chốt đơn mua (T032) nằm ở US1.
- **US4 (Phase 6)**: sau Phase 2. Lưu PDF phiếu nhận dùng `_completed` của US1 (T024).
- **US5 (Phase 7)**: sau Phase 2. Không phụ thuộc story khác.
- **US6 (Phase 8)**: sau Phase 2. Đọc hóa đơn từ US5; phiếu chi dùng chuỗi ký sẵn có.
- **Polish (Phase 9)**: sau các story đã chọn làm.

### Trong mỗi story

- Viết test trước và để test hỏng trước khi làm.
- Trạng thái và quy tắc → máy chủ → giao diện.
- Xong story mới sang story kế.

### Parallel Opportunities

- **Phase 2**: T005, T007, T008, T009, T010, T011, T012, T018 chạy song song.
- **US1**: T019–T021 song song. T035 và T036 làm song song với T022–T034.
- **Giữa các story**: sau Phase 2, US5 (máy chủ: T078–T085) làm song song được với US2–US4 vì khác file.

---

## Parallel Example: User Story 1

```text
Task: "T019 verify_signing_inbox.py"
Task: "T020 verify_signed_copy.py"
Task: "T021 test_signing_rules.py bước kiểm tra"
Task: "T035 use-signing.js"
Task: "T036 SignaturePad.vue + use-signature-profile.js"
```

## Parallel Example: User Story 5

```text
Task: "T078 test ngưỡng tổng in"
Task: "T079 verify_finance.py / verify_vat_in_cost.py"
Task: "T084 stock_attachments cho Purchase Invoice"
Task: "T085 trang in hóa đơn"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 và Phase 2. Có thể đưa T004–T008 lên VPS ngay thành bản vá nếu chủ vườn đồng ý.
2. Phase 3 (US1).
3. **Dừng và thử** theo quickstart US1. Đưa lên VPS khi chủ vườn yêu cầu.

### Incremental Delivery

US1 → US2 → US3 → US4 → US5 → US6. Mỗi story thử riêng và đưa lên riêng.

Trước bản có Phase 3 (T032–T033), báo chủ vườn hai điều:
- các đơn "Chờ duyệt" chưa có vòng ký sẽ bị trả về Nháp;
- từ bản này giám đốc ký mọi đơn.

### Ghi chú

- Mỗi task xong thì đánh dấu `[x]` trong file này.
- Chỉ commit, đẩy và triển khai khi chủ vườn yêu cầu (hiến chương).
- Không chạy migrate trên site `frontend` của bản local và không chạm cây spec 002.
