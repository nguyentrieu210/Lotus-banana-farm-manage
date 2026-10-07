# Lotus Farm 360° — BRD Frontend Vue 3 + Frappe UI

**Baseline code:** `main@47c4efc8c2d6f08f458b0f413bd3182640da8793`  
**Backend target:** Frappe/ERPNext v16  
**Frontend target:** Vue 3 + Frappe UI + Vue Router + Pinia + Vite  
**Target route:** `/lotus`

## 1. Mục tiêu

Frontend Lotus phải biến bộ nghiệp vụ ProMax hiện đã có trong backend thành một ứng dụng điều hành dùng được hằng ngày, thay vì buộc người dùng đi qua nhiều DocType hoặc nhiều file Excel.

Chuỗi điều hành đích:

```text
Công ty
→ Nông trường
→ Lô
→ Thửa
→ Vụ / đợt chồi
→ kế hoạch
→ công việc
→ người
→ vật tư
→ actual hiện trường
→ hủy / bệnh / đo trái
→ thu hoạch
→ QC
→ xưởng / packout
→ chốt ngày
→ kết vụ
→ dự thu mới
```

Không có cấp **Xí nghiệp** trong điều hướng, phân quyền hay mô hình tổ chức đích. Các tên XN/XNC/Xí nghiệp chỉ tồn tại ở dữ liệu lịch sử và mapping migration.

## 2. Hiện trạng code và đích frontend

Repo hiện đã có:

- backend ProMax cho Farm/Block/Plot/Cycle/Cohort;
- Daily Work, labor, material norm/requirement/consumption/recovery;
- cancellation, planting, disease, bunch operation, fruit measurement;
- harvest, incoming QC, packout, secondary/loss;
- dashboard, traceability, forecast feedback, close;
- source registry, staging/import, OneDrive adapter;
- field offline capture, GPS/photo, QR, scale, GIS;
- giao diện hiện trường tại `/assets/lotus_farm/field/index.html`.

Giao diện hiện tại là HTML/JS/PWA trực tiếp. Nó là **UI vận hành tạm có giá trị** và là nguồn tham chiếu behavior, nhưng không phải kiến trúc frontend đích.

Frontend đích phải:

1. giữ nguyên semantics đã chạy ổn: quyền, idempotency, offline queue, source trace;
2. chuyển navigation/list/detail/action sang Vue 3 + Frappe UI;
3. dùng lại backend hiện có trước khi tạo API mới;
4. không bỏ UI hiện tại cho đến khi Vue đạt parity và UAT.

## 3. Người dùng chính

| Persona | Việc hằng ngày | Thiết bị chính |
|---|---|---|
| Ban điều hành | xem lệch kế hoạch, rủi ro, sản lượng, loss, close | desktop/tablet |
| Quản lý nông trường | điều hành việc/người/vật tư/chốt ngày | desktop/tablet |
| Planner | plan, forecast, ATP, revision | desktop |
| Kỹ thuật nông nghiệp | công việc, bệnh, đo trái, hủy | mobile/tablet |
| Điều phối thu hoạch | harvest, nguồn, lot | mobile/tablet |
| QC | incoming inspection, defect | tablet |
| Quản đốc xưởng | packout, recovery, loss, reconciliation | tablet/desktop |
| Kho/vật tư | requirement, request, issue/receipt | desktop |
| Data admin | source registry, staging, import, mapping | desktop |
| Auditor | trace, version, amend/reopen | desktop |

## 4. Nguyên tắc UX

- Người dùng nhìn thấy việc cần làm trước, không nhìn thấy cấu trúc DocType trước.
- Mỗi số liệu actual chỉ nhập một lần.
- Màn hình tổng phải drill-down đến transaction nguồn.
- Các list lớn dùng server-side filter/pagination.
- Action phải phụ thuộc role + scope + document state.
- Validation hiển thị ngay cạnh field; backend vẫn là nơi quyết định cuối.
- Mobile không phụ thuộc hover.
- Mất mạng phải cho biết rõ bản nào đang chờ, lỗi hay đã gửi.
- Không dùng thuật ngữ kỹ thuật nếu người vận hành không cần biết.
- Không hard-code grade, package, ribbon, norm, tolerance, hệ số forecast.

## 5. Information Architecture

### 5.1 App shell

Sidebar:

```text
Hôm nay
Nông trường
Kế hoạch & Dự thu
Công việc
Nhân lực
Vật tư
Tổn thất
Đo trái
Thu hoạch
QC đầu vào
Xưởng đóng gói
Chốt ngày
Kết vụ
Truy xuất
Báo cáo
---
Danh mục
Nhập dữ liệu
Cấu hình
```

Top bar:

- Company/Farm scope.
- Lô/Thửa khi màn hình cần.
- ngày/tuần/tháng.
- global search.
- cảnh báo.
- sync status khi có offline.
- user menu.

### 5.2 Hierarchy

Tên hiển thị nghiệp vụ:

```text
Công ty → Nông trường → Lô → Thửa → Vụ → Đợt chồi
```

Mapping code:

```text
Company → Farm → Farm Block → Farm Plot → Crop Cycle → Sucker Selection Batch
```

## 6. Route map

```text
/lotus/today

/lotus/farms
/lotus/farms/:farm
/lotus/blocks/:block
/lotus/plots/:plot
/lotus/cycles/:cycle

/lotus/plans
/lotus/forecast

/lotus/work
/lotus/labor
/lotus/materials
/lotus/losses
/lotus/measurements
/lotus/harvest

/lotus/incoming-qc
/lotus/packhouse

/lotus/daily-close
/lotus/cycle-close

/lotus/trace
/lotus/reports

/lotus/admin/masters
/lotus/admin/imports
/lotus/admin/settings
```

Filter quan trọng phải nằm trong query string để URL có thể chia sẻ:

- company;
- farm;
- block;
- plot;
- cycle;
- date;
- from/to;
- status;
- view;
- grouping.

## 7. Screen inventory

| ID | Màn hình | Persona | Nguồn backend chính | Mobile |
|---|---|---|---|---|
| FE-001 | Hôm nay | Executive, Farm Manager | `reporting.dashboard`, `field.bootstrap` | responsive |
| FE-002 | Nông trường 360 | Farm Manager | dashboard + hierarchy | responsive |
| FE-003 | Thửa/Vụ 360 | Technical, Manager | `plot_history` + resources | responsive |
| FE-004 | Kế hoạch | Planner | Production Plan / Work Plan | desktop |
| FE-005 | Dự thu | Planner, Executive | Harvest Forecast / Output Plan | desktop |
| FE-006 | Công việc ngày | Manager, Technical | `field.bootstrap`, Daily Work Plan/Result | mobile V1 |
| FE-007 | Nhân lực | Manager | `field.available_labor`, Daily Labor | tablet |
| FE-008 | Vật tư | Manager, Warehouse | Material Requirement + ERPNext stock | desktop |
| FE-009 | Hủy/tổn thất | Technical, Harvest | Bunch Cancellation | mobile |
| FE-010 | Đo trái | Technical | Fruit Measurement | mobile |
| FE-011 | Thu hoạch | Harvest | Harvest Actual/Lot | mobile |
| FE-012 | QC đầu vào | QC | Incoming Quality Inspection | tablet |
| FE-013 | Xưởng | Packhouse | `reporting.packhouse_day`, Packout Run | tablet |
| FE-014 | Chốt ngày | Farm Manager | `daily_api.preview_close`, Daily Production Close | desktop |
| FE-015 | Kết vụ | Manager, Planner | Cycle Closing Report | desktop |
| FE-016 | Truy xuất | QC, Auditor | `trace_item`, `trace_lot`, `trace_packout` | responsive |
| FE-017 | Import Center | Data Admin | Source Registry/Import APIs | desktop |
| FE-018 | Bản đồ thửa | Manager, Technical | `field.map_data`, Plot Geometry | tablet |
| FE-019 | Cảnh báo/exception | Manager | dashboard/close checks/integration task | responsive |
| FE-020 | Audit/version | Auditor | Frappe Version + amend reason | desktop |

## 8. FE-001 — Hôm nay

### Mục tiêu

Người quản lý mở app và biết ngay:

- hôm nay phải làm gì;
- việc nào chưa xong;
- thiếu người/vật tư ở đâu;
- thu hoạch so với dự kiến;
- hủy/lỗi ở đâu;
- xưởng ra bao nhiêu;
- ngày có chốt được không.

### Header

- Scope: Company/Farm.
- Date.
- Refresh.
- Quick actions theo quyền.

### KPI

- Work completion.
- Labor gap.
- Material shortage/outstanding.
- Forecast kg.
- Harvest kg.
- Cancellation qty/rate.
- Incoming defect rate.
- Packout %.
- Finished kg.
- Close status.
- Integration errors.

### Drill-down

Mọi KPI phải mở đúng màn hình và giữ filter.

### Backend

Ưu tiên reuse:

- `lotus_farm.reporting.dashboard`
- `lotus_farm.field.bootstrap`
- `lotus_farm.reporting.packhouse_day`
- `lotus_farm.daily_api.preview_close`

Chỉ thêm aggregate endpoint mới nếu frontend phải gọi quá nhiều request nhỏ hoặc response hiện tại thiếu field thật sự cần.

## 9. FE-002 — Nông trường 360

Header:

- Farm.
- Company.
- tổng diện tích.
- số Lô/Thửa đang hoạt động.
- số Vụ đang mở.
- forecast hiện tại.
- ngày close gần nhất.
- risk count.

Tabs:

- Tổng quan.
- Lô/Thửa.
- Công việc.
- Nhân lực.
- Vật tư.
- Sản lượng.
- Tổn thất.
- QC.
- Xưởng.
- Lịch sử.

Không thêm Xí nghiệp vào breadcrumb hoặc filter.

## 10. FE-003 — Thửa/Vụ 360

Header:

- Farm / Block / Plot.
- Variety.
- Cycle.
- Cycle type.
- Parent cycle nếu ratoon.
- planting/sucker selection date.
- area.
- plant count.
- status.
- forecast.

Timeline:

```text
Trồng
→ chọn chồi
→ chăm sóc / BVTV
→ trổ
→ cắt bắp
→ chăm sóc buồng
→ đo trái
→ thu hoạch
→ QC
→ đóng gói
→ kết vụ
```

Data phải lấy từ transaction thật, không tạo một bảng timeline thứ hai.

## 11. FE-006 — Công việc ngày

Views:

- List.
- Board.
- My Work.
- At Risk.

Row/card:

- work type;
- Farm/Block/Plot;
- cycle/cohort;
- planned qty + UOM;
- completed qty;
- required workdays;
- allocated workdays;
- material readiness;
- due/status;
- risk.

Actions:

- Create draft.
- Suggest due work.
- Assign labor.
- Calculate material.
- Start.
- Record result.
- Block.
- Cancel.

Backend reuse:

- `lotus_farm.field.bootstrap`
- `lotus_farm.field.make_suggested_plan`
- `lotus_farm.field.capture`
- CRUD của Daily Work Plan/Result.

## 12. FE-007 — Nhân lực

Không làm HRM thứ hai.

Hiển thị:

| Nhóm việc | Nhu cầu công | Có thể bố trí | Đã bố trí | Actual | Gap |
|---|---:|---:|---:|---:|---:|

Backend reuse:

- `lotus_farm.field.available_labor`
- Daily Labor Summary
- Labor Allocation
- ERP Employee/Attendance theo quyền ERP.

Nếu Attendance chưa xác nhận, UI phải hiển thị **Chưa xác nhận**, không tự coi là đi làm.

## 13. FE-008 — Vật tư

Flow:

```text
Work Plan
→ Material Norm Profile có hiệu lực
→ Material Requirement
→ ERP Bin khả dụng
→ thiếu / đủ
→ Material Request hoặc Issue
→ Consumption
→ Recovery
```

Table:

- Item.
- requirement.
- UOM.
- required.
- ERP available.
- shortage.
- requested.
- issued.
- consumed.
- recovered.
- variance.

Không tạo stock balance riêng của Lotus.

## 14. FE-009 — Hủy/tổn thất

Quick entry:

- date.
- Farm/Block/Plot/Cycle/Cohort.
- bunch qty.
- canonical reason.
- expected harvest date.
- source operation nếu có.
- note.
- photo/GPS.

Analytics:

- by reason.
- by activity.
- by Farm/Block/Plot.
- by week.
- avoidable/uncontrollable nếu master hỗ trợ.

Backend transaction hiện tại đã cập nhật ATP và giữ nguyên released forecast snapshot; frontend không được tự tính lại khác backend.

## 15. FE-010 — Đo trái

V0 desktop/tablet:

- header.
- sample grid.
- copy/paste nhanh.
- import khi cần.
- validation numeric/UOM.
- summary.

V1 mobile:

```text
scan/chọn Thửa
→ Vụ/đợt
→ màu dây
→ Sample 1..N
→ lưu local
→ sync
```

Không biến sample thành hàng trăm field cố định.

## 16. FE-011 — Thu hoạch

Form:

- harvest date.
- Farm/Block/Cycle/Cohort.
- bunch qty.
- gross weight.
- rejected field weight.
- receiving point/packhouse.
- team.
- source.

Sau submit:

- mở Harvest Lot.
- QR V1.
- trace to Plot/Cycle.
- không cho overwrite submitted actual.

## 17. FE-012 — QC đầu vào

Summary:

- lot.
- released raw kg.
- accepted kg.
- rejected kg.
- defect breakdown.
- defect rate.

Pattern:

- DefectMatrix cho nhiều defect.
- quick form khi chỉ có một defect.
- idempotency khi retry.

Reuse:

- `lotus_farm.packhouse.receive_quality`

## 18. FE-013 — Xưởng

Tabs:

- Tổng quan.
- Nguồn vào.
- QC.
- Packout.
- Phụ phẩm.
- Hao hụt.
- Thu hồi vật tư.
- Reconciliation.
- Ghi kho ERP.

Reuse:

- `lotus_farm.reporting.packhouse_day`
- Packout Run/Source/Output.
- Secondary Product Movement.
- Production Loss Detail.
- stock bridge hiện có.

Grade/Market/Pack Specification luôn lấy master có hiệu lực.

## 19. FE-014 — Chốt ngày

Bước 1: Preview.

Checks:

- work plan/result.
- unfinished reason.
- labor allocation/actual.
- material issue/consumption/recovery.
- harvest/receiving/QC.
- packout/mass balance.
- ERP stock output.
- integration errors.

Reuse:

- `lotus_farm.daily_api.preview_close`

Rule:

- blocking check chưa xử lý → không Submit.
- reopen/cancel/amend cần reason.
- UI chỉ phản ánh rule; backend quyết định.

## 20. FE-015 — Kết vụ

Hiển thị derived metrics:

- plant/area.
- bunch operations.
- harvest bunch/kg.
- processed.
- finished.
- grade mix.
- secondary/waste.
- yield t/ha/cycle.
- forecast accuracy.

Không nhập lại số tổng đã có transaction.

## 21. FE-016 — Truy xuất

Ba entry points:

- Harvest Lot.
- Packout.
- Item/Batch.

Cho trace xuôi/ngược:

```text
Company
→ Farm
→ Block
→ Plot
→ Cycle/Cohort
→ Harvest
→ Harvest Lot
→ Incoming QC
→ Packout
→ Item/Batch
```

Reuse:

- `reporting.trace_item`
- `reporting.trace_lot`
- `reporting.trace_packout`
- `reporting.plot_history`

## 22. FE-017 — Import Center

Tabs:

- Source Inventory.
- Source Registry.
- Mapping.
- Staging.
- Batch.
- Reconciliation.
- Integration Errors.

Reuse:

- `importing.stage_workbook`
- `importing.preview_import`
- `importing.import_rows`
- OneDrive Feed / Integration Task.

Không tự coi file mới nhất là đúng.

## 23. FE-018 — Bản đồ thửa

V0/V1:

- Polygon/MultiPolygon đã duyệt.
- click Plot → history.
- filter Farm/Block/status.
- show GPS capture warning nếu ngoài ranh.

Reuse:

- `field.map_data`
- `reporting.plot_history`

Không tự đoán CRS hoặc mapping từ KML chưa duyệt.

## 24. Permission UX

Frontend cần capability summary từ:

- `field.session_info`
- Frappe Role Permission.
- User Permission theo Farm.

Rule:

- hide action không có quyền rõ ràng;
- disable action khi state không hợp lệ;
- backend vẫn kiểm tra;
- route guard không thay permission backend;
- ID đoán được vẫn không đọc được dữ liệu ngoài scope.

## 25. Design system

### Dùng trực tiếp từ Frappe UI khi phù hợp

- Button.
- Input/FormControl.
- Select/Autocomplete.
- Dialog.
- Popover/Dropdown.
- Tabs.
- Tooltip.
- Badge.
- Toast.
- List/Table primitives.
- File upload integration.
- Skeleton/empty/error primitives nếu phiên bản đang dùng hỗ trợ.

### Shared Lotus components

- AppSidebar.
- ScopePicker.
- PeriodPicker.
- OpsViewControls.
- OpsDataTable.
- KpiCard.
- ExceptionBanner.
- WorkStatusBadge.
- LaborGapCell.
- MaterialReadiness.
- DefectMatrix.
- TraceTimeline.
- SyncStatus.
- OfflineQueueDrawer.
- AuditDrawer.
- ApprovalBar.
- PlotMap.

## 26. Frontend architecture

```text
frontend/
  src/
    app/
      router/
      layouts/
    modules/
      dashboard/
      farms/
      planning/
      forecast/
      work/
      labor/
      materials/
      losses/
      measurements/
      harvest/
      qc/
      packhouse/
      close/
      trace/
      reports/
      admin/
    components/
      common/
      domain/
    composables/
    repositories/
    stores/
    offline/
    types/
    utils/
```

### Rule

```text
Page/Component
→ composable
→ repository
→ Frappe UI resource/call
→ backend
```

Component không gọi endpoint tùy ý.

## 27. State management

Pinia chỉ giữ state dùng chung:

- sessionStore.
- scopeStore.
- masterStore.
- alertStore.
- offlineStore.

List/detail transaction dùng resource/composable cache, tránh copy toàn bộ server state vào Pinia.

## 28. API/resource strategy

### Reuse custom methods hiện có

- `lotus_farm.field.session_info`
- `lotus_farm.field.bootstrap`
- `lotus_farm.field.capture`
- `lotus_farm.field.capture_status`
- `lotus_farm.field.map_data`
- `lotus_farm.field.make_suggested_plan`
- `lotus_farm.field.available_labor`
- `lotus_farm.reporting.dashboard`
- `lotus_farm.reporting.packhouse_day`
- `lotus_farm.reporting.plot_history`
- `lotus_farm.reporting.forecast_vintages`
- `lotus_farm.reporting.trace_item`
- `lotus_farm.reporting.delivery_progress`
- `lotus_farm.daily_api.preview_close`
- `lotus_farm.packhouse.receive_quality`
- `lotus_farm.importing.stage_workbook`
- `lotus_farm.importing.preview_import`
- `lotus_farm.importing.import_rows`

CRUD đơn giản dùng Frappe resource API/DocType resource của frontend toolkit nếu phù hợp.

### Chỉ thêm API mới khi

- action cần atomic transaction nhiều DocType;
- cần aggregate server-side;
- cần permission check riêng;
- payload hiện có không đủ cho UX mới.

## 29. Upload

Ảnh/file:

- private by default.
- cùng session.
- attach/link về transaction.
- lỗi upload không làm mất bản ghi local.
- mobile queue cho phép upload lại.

## 30. Offline/mobile

Giữ semantics của UI hiện tại:

- IndexedDB queue theo user.
- client_event_id.
- payload hash/idempotency server-side.
- Sent/Error/Pending/Discarded.
- account isolation.
- server re-check permission/date/state khi sync.

Vue không được làm mất các guarantee này.

Preload tối thiểu:

- permitted farms.
- today's tasks.
- cycles/cohorts.
- cancellation reasons.
- diseases.
- UOM/master cần thiết.

Không offline toàn ERP.

## 31. Conflict rule

| Data | Rule |
|---|---|
| Master | server wins |
| Draft do chính user tạo | merge khi an toàn |
| Submitted actual | không auto-merge |
| Closed date | require reopen |
| Photo | append |
| Harvest/Cancellation | append transaction, không overwrite |

## 32. Migration UI tạm → Vue

### Phase F0 — nền

- tạo `frontend/`.
- pin versions.
- app shell.
- auth/session.
- ScopePicker.
- router.
- repository layer.
- Frappe UI baseline.

### Phase F1 — parity read-only

- Today.
- Farm/Plot 360.
- work list.
- dashboard.
- trace.
- map.

### Phase F2 — parity write online

- work result.
- cancellation.
- measurement.
- harvest.
- QC.
- import actions.

### Phase F3 — offline parity

- IndexedDB queue.
- photo upload.
- capture_status reconcile.
- account isolation.
- retry.

### Phase F4 — switch default

Chỉ chuyển người dùng sang `/lotus` khi toàn bộ parity/UAT đạt. UI cũ giữ làm fallback trong giai đoạn pilot.

## 33. Frontend acceptance

- Route chia sẻ mở đúng scope/filter.
- Farm A không xem Farm B.
- Action đúng role/state.
- List lớn server paging/filter.
- Dashboard drill-down đến transaction.
- Submit retry không tạo duplicate.
- Offline reload không mất queue.
- Đổi account không thấy/gửi queue account cũ.
- Close blocking error chặn submit.
- Trace hai chiều hoạt động.
- Không hard-code grade/spec/norm/tolerance.
- Mobile 360–430px không overflow ngang ngoài data table có scroll chủ động.
- Keyboard usable trên desktop cho filter/list/dialog quan trọng.
- Loading/empty/error/no-permission rõ ràng.

## 34. Những gì chưa được coi là đã nghiệm thu

- mapping Farm/Lô/Thửa thật;
- official coefficients/norm/tolerance;
- product/grade/pack master thật;
- OneDrive credential thật;
- thiết bị/cân thật;
- real-volume SLA;
- user UAT;
- cutover.

Frontend BRD này là baseline để code UI chuẩn; nó không biến code hiện có thành “production accepted” nếu các mục trên chưa được Lotus xác nhận.
