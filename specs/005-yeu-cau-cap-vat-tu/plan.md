# Implementation Plan: Yêu cầu cấp vật tư từ vườn đến Kho

**Branch**: `005-yeu-cau-cap-vat-tu` | **Date**: 2026-11-11 | **Spec**: `specs/005-yeu-cau-cap-vat-tu/spec.md`

**Input**: Feature specification from `specs/005-yeu-cau-cap-vat-tu/spec.md`

## Summary

Làm màn lập, duyệt và theo dõi **yêu cầu cấp vật tư** (Material Request loại Material Issue) trong Công việc và /work, và hàng chờ "Cấp theo yêu cầu" trong Kho. Không tạo DocType. Thêm hai module backend (`issue_request.py` có API và hook, `issue_request_rules.py` thuần), vài trường tùy biến trên Material Request, và sửa nhỏ `warehouse_issue.py` để phiếu xuất theo yêu cầu mang lô và việc của dòng yêu cầu.

Duyệt một bước theo luật của báo cáo ngày (đội trưởng duyệt cho tổ, quản lý vườn duyệt cho đội trưởng, không ai tự duyệt). Duyệt là submit, chỉ chạy trong `issue_request.approve`; hook chặn mọi đường khác. Không dùng chuỗi ký `issue_proposal` và không sửa file của spec 003.

Thiết kế này lấy từ ba đề xuất:
- Theo hướng "vườn trước": chỗ đặt màn (Công việc, /work), luật người duyệt, giảm số khi duyệt, chép chiều từ dòng yêu cầu, hàng chờ của Kho, gắn phiếu giao việc.
- Theo hướng "kiểm soát trước": chặn mọi submit/hủy/dừng/mở lại ngoài Lotus, chống gửi trùng bằng Lotus ERP Command, `controls.command` cho submit/cancel/update_status, không đóng khi Kho còn phiếu nháp, fixture chung cho test cũ.
- Theo hướng "dùng lại tối đa": không DocType, không vai trò mới, không chạm menu, sửa `push_notifications._recipients` bằng một điều kiện, giữ bản in nguyên.

Không lấy: chuỗi 4 chữ ký (sửa `signing_rules.py`/`signing.py` của 003, chậm ngoài vườn, tab thứ năm trên /work trái `docs/MOBILE_UI_STANDARD.md`); dùng vai trò "Người đề nghị xuất kho" làm cửa lập (tổ trưởng không vào được, người vườn phải mở cả Kho); dùng `lotus_proposal_state` và `lotus_procurement_key` của 003 (ràng vào trạng thái mua hàng).

## Technical Context

**Language/Version**: Python 3.14 (backend), JavaScript ES2022 với Vue 3 (frontend)

**Primary Dependencies**: Frappe/ERPNext v16, app `lotus_farm`; Vue 3, Vant 4 và `LotusMobile*` (điện thoại); `components/form` (ModalForm, LotusField, FormGrid, FormSection, ReasonDialog, LineItemsEditor), `components/ui`, `DataTable` chỉ trong hộp thoại (máy tính)

**Storage**: MariaDB 11.8 qua DocType Frappe; không DocType mới

**Testing**: unit test Python cho module thuần (`tests/test_*.py`, frappe giả); integration trong `tests/integration` chạy bằng `run_from_tmp.py` trong container backend của khu test VPS; `node --test` với happy-dom (`frontend/tests/support/mount.mjs`)

**Target Platform**: Web máy tính (`/lotus/cong-viec`, `/lotus/kho`) và PWA điện thoại (`/work`, `/warehouse`), Docker trên VPS

**Project Type**: Ứng dụng web

**Performance Goals**: danh sách yêu cầu của một đội dưới 2 giây; một yêu cầu dưới 1 giây; số đã cấp/đang giữ của cả danh sách đọc bằng **một** câu SQL gộp theo `material_request_item`; yêu cầu đã đóng chỉ liệt kê 60 ngày gần nhất mặc định.

**Constraints**:
- Không sửa file spec 003 đang đổi và file spec 004 đang đổi (danh sách ở dưới).
- Không thêm mục menu Công việc (test giữ 7 mục) và menu Kho; không thêm tab thứ năm trên /work.
- Vai trò vườn không được cấp quyền Material Request; module tự kiểm phạm vi và ghi bằng `ignore_permissions` trong cờ ghi riêng.
- Lỗi thông báo không được làm hỏng thao tác (savepoint + try/except, như `signing._notify`).
- Không chạy test, build, docker, python trên máy này.

**Scale/Scope**: 1 vườn (LOTUS-222), 64 lô, khoảng 10 tổ; 143 vật tư, 5 kho; ước vài chục yêu cầu một tuần, mỗi yêu cầu dưới 30 dòng.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Số thực, không suy diễn | Đạt. Số đã cấp lấy từ ERPNext (`ordered_qty`) và phiếu xuất; tồn "có thể cấp" lấy từ Bin trừ giữ chỗ. Gợi ý "lần trước" ghi rõ số yêu cầu và ngày. Lô thiếu diện tích thì không chia theo diện tích, không đoán |
| II. Một nguồn sự thật | Đạt. Yêu cầu là Material Request, không bảng mới. Trạng thái suy ra từ docstatus, status của ERPNext và vài mốc thời gian; không có bảng tiến độ riêng. Lô và việc ở chiều kế toán có sẵn. Dùng lại form xuất kho, khóa cấp vượt, bản in, màn kế hoạch |
| III. Truy vết và kiểm soát | Đạt. Không ai tự duyệt. Duyệt chỉ qua Lotus, hook chặn Desk/REST. Mọi đổi trạng thái có người, giờ, lý do; giảm số giữ số trước/sau; sự kiện APPROVE. Không sửa sau khi duyệt |
| IV. Quy tắc tách riêng, có kiểm thử | Đạt. `issue_request_rules.py` thuần có unit test; luồng duyệt → xuất → ghi sổ có integration test; component có mount test |
| V. Giao diện theo chuẩn chung | Đạt. Thẻ + hộp thoại; máy tính dùng `components/form` và `components/ui`; điện thoại dùng `LotusMobile*` và `ModalForm mobile`; chữ tiếng Việt |
| Ràng buộc vận hành | Đạt. Không chuyển dữ liệu (0 yêu cầu loại này). Trường mới cài qua `install.setup` mỗi lần migrate, chạy lại không trùng. Chi phí đi qua phiếu kho, không sửa thẳng sổ |
| Quy trình phát triển | Đạt. Làm trên nhánh 005 sau khi gộp main. Test, build, diễn tập trên khu test VPS. Chỉ commit/đẩy/triển khai khi chủ vườn bảo |

Đánh giá lại sau Phase 1: một thay đổi cần chủ vườn biết — phiếu xuất theo yêu cầu sẽ mang chiều "việc" lên GL, nên báo cáo chi phí "Theo công việc" bắt đầu có chi phí vật tư. Phiếu Thủ công không đổi.

## Project Structure

### Documentation (this feature)

```text
specs/005-yeu-cau-cap-vat-tu/
├── spec.md
├── plan.md      # file này: gồm cả mô hình dữ liệu, API, chỗ đặt màn, kế hoạch test
└── tasks.md
```

### Source Code (repository root)

**Thêm mới**

```text
lotus_farm/issue_request.py                 # API whitelisted + hook Material Request/Stock Entry
lotus_farm/issue_request_rules.py           # luật thuần, không import frappe
tests/test_issue_request_rules.py           # unit test luật thuần
tests/test_issue_request_guards.py          # unit test hook với frappe giả
tests/integration/verify_issue_request.py   # integration trên bản sao site thật
tests/integration/issue_request_fixture.py  # lập + duyệt yêu cầu qua đường Lotus cho test cũ
frontend/src/issue-request-model.js         # nhãn trạng thái, màu, chia theo diện tích, payload, khóa nháp máy
frontend/src/components/field/MaterialRequests.vue        # thẻ đếm + thẻ yêu cầu, openForm/openDetail
frontend/src/components/field/MaterialRequestForm.vue     # ModalForm lập/sửa (mobile = toàn màn)
frontend/src/components/field/MaterialRequestDetail.vue   # chi tiết, tiến độ theo lô, nút theo quyền
frontend/src/components/stock/IssueRequestQueue.vue       # hộp "Cấp theo yêu cầu" của Kho
frontend/src/components/MobileIssueFromRequest.vue        # US5, Kho điện thoại
frontend/tests/issue-request-model.test.js
frontend/tests/material-requests.mount.test.js
frontend/tests/material-request-form.mount.test.js
frontend/tests/material-request-detail.mount.test.js
frontend/tests/issue-request-queue.mount.test.js
frontend/tests/work-mobile-tabs.mount.test.js
```

**Sửa nhỏ (mỗi chỗ một khối riêng để dễ gộp)**

| File | Sửa gì |
|---|---|
| `lotus_farm/warehouse_issue.py` | `install_fields` không đổi (mọi trường mới nằm trong `issue_request.install_fields`). `source_line`: trả thêm `farm`, `farm_block`, `work_type`. `validate_issue`: với dòng chế độ Request, chép 3 chiều từ dòng nguồn vào dòng phiếu. `choices`: bỏ status `Issued`, nhãn giàu hơn. `lines`: thêm `header` (kho, người nhận, người lập, đội, tổ, việc, người duyệt). Hàm mới `queue(company, warehouse=None)`. Import trong hàm như hiện nay (test mock frappe chỉ có `throw`, `flt`, `lock`) |
| `lotus_farm/warehouse.py` | Một wrapper whitelisted `issue_queue(company, warehouse=None)` cạnh `issue_sources`/`issue_lines` |
| `lotus_farm/hooks.py` | Một khối mới đặt **sau** vòng "Shared mobile PWA notification hooks": thêm `issue_request.validate`, `issue_request.before_submit`, `issue_request.before_cancel`, `issue_request.on_trash`, `issue_request.on_change` vào `Material Request`; thêm `issue_request.issue_posted` vào `Stock Entry` `on_submit`/`on_cancel`. Không sửa dòng của 003 |
| `lotus_farm/push_notifications.py` | Trong `_recipients`, nhánh `Material Request`: `if doc.material_request_type != "Purchase": return []` |
| `lotus_farm/install.py` | Gọi `issue_request.install_fields()` trong `setup()` |
| `frontend/src/field-report-navigation.js` | Một mục ẩn `{id:'materials',label:'Yêu cầu cấp vật tư',icon:'package',hidden:true}` (cơ chế giống `inspect`, `payable`) |
| `frontend/src/FieldReportApp.vue` | Giao việc: mục "Yêu cầu cấp vật tư" (MaterialRequests compact) giữa "Phiếu đã giao" và "Chờ nghiệm thu khoán lô". Hôm nay: một thẻ "N yêu cầu vật tư chờ bạn duyệt" trên LotToday (không sửa LotToday). View ẩn `materials`, đọc `?request=` |
| `frontend/src/WorkMobile.vue` | Tổ trưởng: thêm tab `materials` "Vật tư" (icon `bag-o`) → 3 tab. Đội trưởng/quản lý: giữ 4 tab; thẻ "chờ bạn duyệt" đầu tab Xác nhận; mục yêu cầu trong tab Giao việc. Deep link `?request=` |
| `frontend/src/components/field/WorkTicket.vue` | US4: mục "Vật tư cho phiếu này" + nút "Đề nghị cấp vật tư" |
| `frontend/src/components/stock/StockDocumentList.vue` | Trong `issues`, thêm nút "Cấp theo yêu cầu (N)" vào `#actions` |
| `frontend/src/components/stock/StockDocumentForm.vue` | Hàm lộ ra `openFromRequest(name)`: `openNew('issue')` → kho xuất → `changeIssueMode('Request')` → `selectIssueSource(name)` → điền người nhận từ `header`; nhãn nguồn giàu hơn |
| `frontend/src/StockApp.vue` | Mở IssueRequestQueue; đọc `?issue_request=` |
| `frontend/src/WarehouseMobile.vue` | US5: một `LotusMobileAction` "Cấp theo yêu cầu (N)" + deep link (khoảng 10 dòng, sau khi gộp main) |
| `frontend/src/release-notes.js` | Mục "Có gì mới" |
| `frontend/tests/field-navigation.test.js`, `frontend/tests/stock-issue-uom.mount.test.js`, `frontend/tests/form-standard.test.js` | Mở rộng như ở phần test |
| `tests/test_warehouse_issue.py` | Thêm ca chép chiều, `choices` bỏ Issued, `lines` có header |
| 5 integration cũ (`audit_warehouse_edge_cases.py`, `verify_issue_uom.py`, `verify_purchase_flow.py`, `verify_warehouse_audit.py`, `verify_warehouse_regressions.py`) | Đang submit thẳng Material Issue → chuyển sang `issue_request_fixture.py` |
| `docs/FIELD_REPORT.md`, `docs/WAREHOUSE_CONSOLE.md`, `docs/ACCESS_AND_SIGNERS.md` | Một đoạn mỗi file |

**Không được sửa**

- Spec 003 (mua hàng, ký điện tử): `lotus_farm/purchase_proposal.py`, `purchasing.py`, `purchase_flow.py`, `proposal_rules.py`, `purchase_status.py`, `signing.py`, `signing_rules.py` (chuỗi `issue_proposal` để nguyên, không dùng), `signed_copy.py`, `digital_signature.py` (chỉ gọi `_event`), `procurement*.py`, `warehouse_buying_lite.py`, `warehouse_planning.py`, `www/lotus_material_proposal_print.py` và template in, `lotus_stock_print.py`; frontend `ProcurementWorkspace.vue`, `MobilePurchaseProposal.vue`, `BuyingMobile.vue`, `components/procurement/*`, `WarehousePlanning.vue`, `LotusMobileShell.vue`, `LotusMobileHeader.vue`, `LotusMobileBottomNav.vue`, hộp "Chờ tôi ký".
- Spec 004 (giao diện): `components/field/CareDueList.vue`, `LotCards.vue`, `RibbonBoard.vue`, `lot-entry-model.js`, `lotus-tokens.css`, `mobile-ui.css`, `components/ui/*`, `workspace.js`, `DataTable.vue`, `App.vue`, `router.js`, `domain.js`. Component mới dùng primitive đã có trên `main`, không dùng bộ kit mới của 004.
- Khác: `field_report.py`, `lot_report.py`, `care_cycle.py` (chỉ gọi), `finance/*` (chiều đã được `_row_dims` giữ nếu dòng có sẵn lô), `warehouse_access.py` (không thêm quyền), `stock-navigation.js`.

**Gộp nhánh**: trước khi viết mã, gộp `main` (a8a304a) vào 005 và đọc lại `hooks.py`, `push_notifications.py`, `warehouse_issue.py`, `WarehouseMobile.vue`. Nhánh 004 phải gộp `main` trước khi triển khai. Nếu 004 lên trước, các component mới đổi sang primitive của 004 ở một bước riêng sau.

## Mô hình dữ liệu

### Material Request (đầu phiếu)

Trường chuẩn: `material_request_type` = `Material Issue`; `company` = `Farm.company`; `transaction_date` = hôm nay (máy chủ); `schedule_date` = ngày cần; `set_warehouse` = kho cấp; `title` = "Phun thuốc · Tổ 3 · A12, A13"; `owner` = người lập.

Trường có sẵn, chỉ ghi vào: `lotus_request_note` (lý do; bản in "Lý do"), `lotus_department` ("Đội khu A + B · Tổ 3"; bản in "Bộ phận").

Trường mới, cài bằng `issue_request.install_fields()` (tên riêng `lotus_issue_*` để không dính trạng thái mua hàng của 003; cùng hàm cài `lotus_work_assignment` trên Material Request Item):

| fieldname | Kiểu | Ghi chú |
|---|---|---|
| `lotus_crew` | Link Work Team | Đội; read_only; có giá trị = yêu cầu lập từ Lotus |
| `lotus_work_team` | Link Work Team | Tổ nhận; trống = cả đội; read_only |
| `lotus_issue_receiver` | Link Employee | Người nhận vật tư; Kho điền sẵn vào phiếu xuất |
| `lotus_issue_approver` | Link User | Người duyệt dự kiến; trống = quản lý vườn; read_only, no_copy |
| `lotus_issue_sent_at` | Datetime | Có = đang chờ duyệt; read_only, no_copy |
| `lotus_issue_approved_by` | Link User | read_only, no_copy |
| `lotus_issue_approved_at` | Datetime | read_only, no_copy |
| `lotus_issue_return_reason` | Small Text | read_only, no_copy |
| `lotus_issue_close_reason` | Small Text | allow_on_submit, read_only, no_copy |

`lotus_proposal_state` (của 003) để mặc định, không dùng. Hệ quả nhỏ: bản in một yêu cầu chưa duyệt ghi "Nháp" ở ô trạng thái; dấu "CHƯA DUYỆT" vẫn đúng. Người vườn không in nên chấp nhận ở bản này.

### Material Request Item (dòng)

`item_code`; `qty` = `stock_qty` (đơn vị tồn kho, `uom` = `stock_uom`, `conversion_factor` 1); `warehouse` = kho cấp; `schedule_date` = ngày cần; `lotus_farm_block` = lô; `lotus_farm` = vườn của lô; `lotus_work_type` = việc; `lotus_usage_area` = `Farm Block.block_code` (chuỗi mà `validate_issue` và `finance.stock.block_from_text` đang đọc); `lotus_purpose` = tên việc lúc lập; `lotus_notes` = liều / ghi chú; mới `lotus_work_assignment` (Link Lotus Work Assignment, tùy chọn, no_copy). `ordered_qty`, `per_ordered`, `status` do ERPNext tính khi phiếu xuất ghi sổ/hủy.

### Trạng thái (suy ra, không lưu thêm)

`issue_request_rules.state(docstatus, status, sent_at, return_reason, totals, needed, today)`:

| Trạng thái | Điều kiện |
|---|---|
| Nháp | docstatus 0, không `sent_at`, không lý do trả lại |
| Chờ duyệt | docstatus 0, có `sent_at` |
| Trả lại | docstatus 0, không `sent_at`, có lý do trả lại |
| Chờ cấp | docstatus 1, status Pending, không phiếu nháp |
| Kho đang lập phiếu | docstatus 1, có phiếu nháp giữ số |
| Đã cấp một phần | status Partially Ordered |
| Đã cấp đủ | status Issued |
| Đã đóng | status Stopped |
| Đã hủy | docstatus 2 |

Cờ thêm: `overdue` = ngày cần < hôm nay và còn số, ở các trạng thái sau duyệt chưa xong.

### Bằng chứng và lịch sử

- Lotus Signature Event `APPROVE` (người, giờ, `signature_type='NAME'`) qua `digital_signature._event` — bản in đã đọc sự kiện này để ghi người duyệt.
- Bình luận trên chứng từ cho: gửi, rút lại, trả lại, giảm số (số trước → sau), duyệt, đóng, mở lại, hủy, xóa; Version log cho sửa nháp; Deleted Document cho nháp bị xóa.
- Lotus ERP Command cho mỗi lệnh ghi (`erp_workbench._command`, khóa = sha256(user + client_event_id)).

### Đường truy vết

Phiếu giao việc ← `Material Request Item.lotus_work_assignment`; dòng yêu cầu ← `Stock Entry Detail.material_request_item`; phiếu xuất ← `Lotus Work Entry Material.stock_entry` (sổ lô, đã có). Thẻ tháng "Vật tư xuất và báo dùng lệch" đọc phiếu xuất theo lô như hiện nay.

## API (lotus_farm/issue_request.py)

Đọc là GET (`@frappe.whitelist()`), ghi là POST (`@frappe.whitelist(methods=['POST'])`). Mọi lời gọi: đăng nhập; `field_report.require_farm(farm)`; `field_report.access(farm, crew)` (với lời gọi theo tên, lấy farm/crew từ `lotus_crew` của chứng từ). Phạm vi đọc: quản lý vườn và kỹ thuật vườn thấy mọi đội của vườn được cấp; đội trưởng thấy đội mình; tổ trưởng thấy tổ mình.

Ghi: đặt ContextVar `_writing` và `doc.flags.ignore_permissions` (như `field_report._store`); mỗi lệnh `controls.lock('Material Request', name)`, kiểm `modified`, đi qua `erp_workbench._command(client_event_id, payload, operation)`; submit/cancel/update_status gọi trong `controls.command(doc, action)` trên cùng đối tượng.

**Đọc**
- `form_data(farm, crew)` → tổ được lập cho; lô (mã, khu, ha, số cây, cách ly); việc của vườn (`field_report._works`, việc `lotus_requires_material` lên đầu); kho lá đang bật của công ty, kho gợi ý (Warehouse Mapping vai trò Input/Field Store, không có thì để trống); người nhận (nhân viên đang làm của các tổ trong đội, mặc định nhân viên của người lập); nhãn người duyệt; chip phiếu đang mở và lô đến hạn (`care_cycle.due`) và "lần trước" theo việc (US4).
- `item_options(search)` → `field_report.item_options` + đơn vị đóng gói; bỏ vật tư có lô/serial.
- `stock(farm, items, warehouse)` → mỗi vật tư: có thể cấp = Bin.actual_qty − giữ chỗ − phiếu nháp (cách đọc của `check_outbound_stock`), và số đã duyệt chưa cấp của yêu cầu khác. Chỉ số lượng.
- `requests(farm, crew=None, team=None, view='open'|'approve'|'mine'|'all', assignment=None, from_date=None, to_date=None)` → thẻ yêu cầu và số đếm theo trạng thái; tiến độ từ một câu SQL gộp.
- `detail(name)` → đầu phiếu, dòng theo vật tư × lô (đề nghị, đã cấp, đang giữ, còn), phiếu xuất (số, ngày, số lượng, người nhận), tồn ở kho, lịch sử, cảnh báo, `actions` {edit, send, withdraw, approve, lower, return, close, reopen, cancel, copy, delete, print}, `print_url` (chỉ khi user có quyền in Material Request).

**Ghi**
- `save(farm, crew, values, name=None, modified=None, client_event_id, send=0)`; `values = {team, work_type, needed, warehouse, receiver, note, lines:[{item_code, farm_block, qty, notes, assignment}]}` → trả `detail` + `warnings`.
- `send(name, modified, client_event_id)` → Nháp/Trả lại → Chờ duyệt; đặt `lotus_issue_approver`, `lotus_issue_sent_at`, xóa lý do trả lại; báo người duyệt.
- `withdraw(name, modified, client_event_id)` → người lập; về Nháp.
- `approve(name, modified, client_event_id, lines=None, reason=None)` → `rules.may_approve`; nếu có `lines` thì `rules.lowered` (chỉ giảm/bỏ) và bắt buộc `reason`; ghi duyệt, `_event('APPROVE')`, `doc.flags.lotus_issue_approval = True`, `doc.submit()`; báo người lập và Kho.
- `return_request(name, modified, reason, client_event_id)` → Trả lại.
- `close(name, modified, reason, client_event_id)` → `doc.update_status('Stopped')`; chặn khi `allocation_totals` còn nháp.
- `reopen(name, modified, reason, client_event_id)` → `doc.update_status('Submitted')`.
- `cancel(name, modified, reason, client_event_id)` → chặn khi có nháp hoặc đã ghi sổ; `doc.cancel()`.
- `delete_draft(name, modified, client_event_id)` → người lập; Nháp hoặc Trả lại.

Người được làm gì (tính trong `rules.actions`):

| Thao tác | Ai |
|---|---|
| Sửa, gửi, xóa nháp | Người lập; Nháp hoặc Trả lại |
| Rút lại | Người lập; Chờ duyệt |
| Duyệt, giảm số, trả lại | Người duyệt hợp lệ (FR-010), khác người lập; Chờ duyệt |
| Đóng phần còn lại | Người lập, người duyệt, quản lý vườn, Lotus Warehouse Manager đọc được kho đó; sau duyệt, chưa cấp đủ, không nháp |
| Mở lại | Người đã duyệt hoặc quản lý vườn; Đã đóng |
| Hủy | Người lập hoặc người đã duyệt; sau duyệt, chưa có phiếu xuất |
| Lập lại từ yêu cầu này | Ai lập được cho đội đó |

**Hook (không whitelisted), chỉ với `material_request_type == 'Material Issue'`**
- `validate`: chứng từ có `lotus_crew` chỉ ghi được khi `_writing` bật; khi đang chờ duyệt hoặc đã duyệt thì không đổi dòng; kiểm lại `rules.line_issues`.
- `before_submit`: bắt buộc `doc.flags.lotus_issue_approval` và `controls.command_allowed(doc, 'issue-approve')`; người duyệt ≠ người lập.
- `before_cancel`: bắt buộc `command_allowed(doc, 'issue-cancel')`.
- `on_trash`: chỉ qua `delete_draft`.
- `on_change`: đổi sang/ra Stopped chỉ khi `command_allowed(doc, 'issue-close'|'issue-reopen')`, trừ đổi status do ERPNext tự tính khi phiếu xuất ghi sổ/hủy (Pending/Partially Ordered/Issued). Phải thử kỹ trên bản sao (rủi ro chặn nhầm).
- `issue_posted` (Stock Entry on_submit/on_cancel): báo người lập và người duyệt "Kho đã cấp …"; trong savepoint, không chặn ghi sổ.

**Luật thuần `lotus_farm/issue_request_rules.py`**: `STATES`; `state(...)`; `approver_for(requester, crew_leader, team_leader_of_requester)`; `may_request(...)`; `may_approve(user, requester, crew_leader, is_manager)`; `line_issues(lines, zone_blocks, today, max_lines=100)`; `lowered(old, new)`; `split_by_area(total, areas, whole)`; `progress(required, posted, draft)`; `duplicates(lines, open_lines)`; `actions(...)`; `title(...)`.

**Kho (`warehouse_issue.py`)**: `queue(company, warehouse=None)` → yêu cầu đã duyệt (kể cả nháp Desk cũ nếu có), chưa đóng, còn số, xếp theo ngày cần, kèm đội/tổ/lô/việc/người duyệt. Quyền: `warehouse._access()` + Material Request read.

## Chỗ đặt màn

**Máy tính, `/lotus/cong-viec` (FieldReportApp.vue)**
- Menu giữ 7 mục. Thêm mục ẩn `materials` (vào được bằng link, `?field_view=materials&request=…`).
- Giao việc: mục "Yêu cầu cấp vật tư" — thẻ đếm (Chờ bạn duyệt · Chờ duyệt · Trả lại · Chờ cấp · Đang cấp · Đã cấp 7 ngày), nút "Đề nghị cấp vật tư", link "Xem tất cả".
- Hôm nay (đội trưởng, quản lý vườn): thẻ "N yêu cầu vật tư chờ bạn duyệt" → hộp danh sách → hộp chi tiết.
- View `materials`: lưới thẻ; lọc cùng một hàng: tổ, trạng thái, khoảng ngày cần, tìm.
- WorkTicket (US4): mục "Vật tư cho phiếu này".

**Điện thoại, `/work` (WorkMobile.vue)** — tối đa 4 tab theo `docs/MOBILE_UI_STANDARD.md`
- Tổ trưởng: Hôm nay · Vật tư · Tôi.
- Đội trưởng, quản lý vườn: giữ Hôm nay · Xác nhận · Giao việc · Tôi; thẻ "chờ bạn duyệt" đầu tab Xác nhận; mục yêu cầu trong Giao việc.
- Kỹ thuật vườn: xem trong Giao việc (đang có tab đó).

**Form `MaterialRequestForm.vue`** (ModalForm 860px; điện thoại toàn màn): (1) Việc · Tổ · Ngày cần · Kho cấp (mỗi kho ghi "có thể cấp" cho vật tư đã chọn); (2) Lô theo khu, "Chọn cả khu", chip phiếu mở / lô đến hạn (US4); (3) Vật tư: tìm, "Mỗi lô" hoặc "Tổng — chia theo diện tích", liều, chip cách ly, tồn ở kho, "Lấy như lần trước" (US4); (4) Người nhận · Lý do. Nút: Lưu nháp / Gửi duyệt.

**Chi tiết `MaterialRequestDetail.vue`**: dòng tóm tắt + nhãn trạng thái; mốc thời gian (lập · gửi · duyệt/trả lại · Kho lập phiếu · ghi sổ · đóng); mỗi vật tư một thẻ với từng lô: Đề nghị / Đã cấp / Kho đang lập phiếu / Còn; phiếu xuất; với người duyệt: "Kho còn 12 lít · đã duyệt chờ cấp cho yêu cầu khác 5 lít"; nút theo `actions`; lý do qua ReasonDialog.

**Kho máy tính, `/lotus/kho`**: Xuất kho có thêm nút "Cấp theo yêu cầu (N)" → `IssueRequestQueue.vue` (hộp thoại, thẻ) → "Lập phiếu xuất" → `StockDocumentForm.openFromRequest(name)`. "Nhu cầu cấp cho công việc" không đổi (dòng đã duyệt luôn có kho).

**Kho điện thoại (US5)**: `LotusMobileAction` "Cấp theo yêu cầu (N)" → `MobileIssueFromRequest.vue` → `create_draft` (issue_mode Request) + `submit_document`, có bước xác nhận tồn kho đang có.

**Bản in**: `/lotus/in-de-xuat?name=` như hiện nay, chỉ hiện cho người có quyền in Material Request.

## Kế hoạch test

Không chạy gì trên máy này. Python, frontend và build chạy ở khu test VPS (`/srv/lotus-test/…`: `stack.sh up` với image đang chạy, site nạp từ bản sao lưu mới nhất của site thật, `agent_check.sh py|front|build`) hoặc GitHub Actions.

**Unit (thuần)**: `tests/test_issue_request_rules.py` — trạng thái mọi tổ hợp; `approver_for`/`may_approve` (tổ trưởng → đội trưởng; đội trưởng → quản lý; quản lý → quản lý khác; không tự duyệt; quản lý duyệt thay); `may_request`; `line_issues` (lô ngoài khu, trùng, qty ≤ 0, >100 dòng, ngày quá khứ, hai việc); `lowered`; `split_by_area` (giữ tổng, đơn vị nguyên, lô thiếu diện tích); `actions`; `duplicates`.

**Unit (frappe giả)**: `tests/test_warehouse_issue.py` thêm: dòng Request nhận 3 chiều từ nguồn; lệch vật tư/lô vẫn bị chặn; `choices` bỏ Issued; `lines` có header; module vẫn nạp được với mock hiện có. `tests/test_issue_request_guards.py`: before_submit từ chối khi thiếu cờ; validate từ chối ghi ngoài API; before_cancel; on_change chặn Stopped ngoài lệnh nhưng để ERPNext tự đổi Pending/Partially Ordered/Issued; `push_notifications._recipients` trả [] cho Material Issue. Các test chặn có sẵn tự bắt: `tests/test_frontend_calls.py` (mọi lời gọi `lotus_farm.*` mới phải whitelisted; bundle build lại trên VPS), `tests/test_no_legacy_names.py`.

**Integration** `tests/integration/verify_issue_request.py` (bản sao site thật, LOTUS-222, đội/vật tư/kho thật, user tạm trong giao dịch, rollback cuối):
1. Tổ trưởng lưu + gửi 2 vật tư × 2 lô → Chờ duyệt, người duyệt dự kiến = đội trưởng, có alert.
2. Cùng `client_event_id` → cùng tên; khác nội dung → từ chối.
3. Từ chối: tổ trưởng duyệt; đội trưởng đội khác; `doc.submit()`/`doc.save()`/`frappe.client.submit`/`update_status` ngoài API (kể cả với Stock Manager).
4. Đội trưởng giảm một dòng có lý do + duyệt → docstatus 1, Pending, sự kiện APPROVE, bình luận; alert cho người lập và Kho; KHÔNG có "Có đề xuất mua mới".
5. Kho: `issue_queue` có yêu cầu; `issue_lines` có header; `create_draft` Request một phần → "Kho đang lập phiếu"; `submit_document` → Stock Entry Detail có lô và việc (kể cả khi client gửi lô khác), GL 621 mang hai chiều, Partially Ordered, alert "Kho đã cấp".
6. Cấp vượt bị chặn; cấp nốt → Issued; `choices` không còn.
7. Yêu cầu 2: duyệt, Kho nháp, đóng bị chặn; Kho xóa nháp; đóng được; Kho không chọn được; mở lại; hủy bị chặn khi có phiếu; yêu cầu 3 chưa cấp hủy được.
8. Yêu cầu của đội trưởng: đội trưởng không duyệt được; quản lý vườn duyệt được.
9. Kho hủy phiếu đã ghi sổ → phần còn lại quay lại, người lập được báo.
10. `warehouse_planning.snapshot` liệt kê dòng với kho, không có "chưa xác định kho".
11. `field_reports.month`: thẻ vật tư đếm phiếu xuất cho lô.
12. Bản in render cho user Kho, ô người duyệt có tên.

Rồi chạy lại: `verify_kho_e2e`, `verify_warehouse_regressions`, `verify_warehouse_audit`, `audit_warehouse_edge_cases`, `verify_issue_uom`, `verify_lot_ledger`, `verify_care_cycle`, `verify_field_reports`, `verify_purchase_flow`, `verify_purchase_proposal`, `verify_signing`, `verify_sign_notify`, `verify_finance`, `verify_costing`. So sánh số giá thành tháng và chi phí theo lô trên bản sao trước/sau (SC-004).

**Mount (happy-dom)**: `material-requests.mount.test.js` (thẻ đếm, lọc, thẻ chờ duyệt chỉ cho người duyệt, mở chi tiết); `material-request-form.mount.test.js` (chọn cả khu, chia theo diện tích, làm tròn đơn vị nguyên, thông báo lỗi, cảnh báo trùng, khôi phục số đang gõ, bấm hai lần gửi một lần với một `client_event_id`; US4: điền sẵn từ phiếu, chip); `material-request-detail.mount.test.js` (nút đúng quyền và trạng thái, ReasonDialog, còn lại theo lô, ẩn In phiếu khi không có quyền); `issue-request-queue.mount.test.js` (thẻ, "Lập phiếu xuất" gọi `openFromRequest`); mở rộng `stock-issue-uom.mount.test.js` (`openFromRequest` đặt chế độ Request, kho xuất, người nhận); mở rộng `field-navigation.test.js` (`materials` ẩn nhưng vào được, menu không đổi); `work-mobile-tabs.mount.test.js` (tổ trưởng: Hôm nay · Vật tư · Tôi; đội trưởng 4 tab, thẻ duyệt trong Xác nhận); thêm form mới vào `form-standard.test.js`; `issue-request-model.test.js`.

**Kiểm tay** theo `docs/MOBILE_UI_STANDARD.md`: `/work` và `/warehouse` ở 320px, 390px và ngang trong Chromium trên VPS (form, chip, popup, bàn phím che thanh dưới, quay lại khi có thay đổi). Không tạo hay ghi sổ chứng từ thật.

## Triển khai

1. Gộp `main` vào 005; build frontend trên VPS (bundle commit trong repo phải build lại, `test_frontend_calls.py` kiểm).
2. Diễn tập trên khu test VPS với bản sao site thật: migrate (cài trường), toàn bộ test, kiểm tay.
3. Chỉ khi chủ vườn bảo: sao lưu (CSDL + tệp), triển khai, migrate, ghi lệnh quay lại. Không cần chuyển dữ liệu.
4. Sau triển khai: tạo 1 yêu cầu thật cùng đội trưởng một đội, Kho cấp, kiểm GL. Gửi chủ vườn danh sách việc cần làm thêm về tài khoản (tổ trưởng, quyền vườn cho quản lý vườn).

## Complexity Tracking

| Điểm | Vì sao cần | Cách đơn giản hơn bị bỏ vì |
|---|---|---|
| Hook chặn submit/cancel/stop ngoài Lotus | Không chặn thì người lập tự submit trong Desk = bỏ duyệt (nguyên tắc III) | Chỉ ẩn nút trong Lotus: Desk và REST vẫn mở |
| 9 trường mới trên Material Request | Phạm vi đội/tổ, người nhận, người duyệt, mốc thời gian, lý do phải lưu trên chứng từ để truy vết | Dùng `lotus_proposal_state`/`lotus_return_reason` của 003: ràng vào trạng thái mua hàng đang đổi |
| Sửa 5 integration test cũ sang fixture | Chúng submit thẳng Material Issue, sẽ bị hook chặn | Miễn chặn cho Administrator: mở lại đường bỏ duyệt |
