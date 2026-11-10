# Dọn sạch đồ cũ: kiểm kê

Kiểm ngày 10/11/2026 trên mã nhánh tách từ main `df7bd70`. Số dòng dữ liệu trên bản thật phải đếm lại ngay trước khi xóa (mục 5).

**Kết quả**: mảng vườn đi từ 99 bảng xuống 25 bảng (23 bảng giữ, 2 bảng mới). Xóa hẳn 76 bảng, trong đó 18 bảng con.

## 1. Bảng xóa hẳn (76)

### A. Ghi chép vườn đời cũ, thay bằng sổ lô (22)

Bunch Operation, Bunch Cancellation, Sucker Selection Batch, Planting Event, Crop Cycle, Cycle Closing Report, Field Capture, Field Todo, Daily Work Plan, Daily Work Plan Line, Daily Work Result, Work Actual Labor, Labor Allocation, Daily Labor Summary, Daily Production Close, Daily Close Check, Disease Observation, Farm Plot, Plot Geometry, Legacy Cycle Plot Mapping, Work Category, Lotus Bunch Event (xóa sau khi chuyển dữ liệu sang sổ lô).

### B. Thu hoạch, chất lượng, đóng gói đời cũ, thay bằng dòng thu hoạch và ca đóng gói (25)

Harvest Actual, Harvest Lot, Harvest Lot Source, Harvest Profile, Incoming Quality Inspection, Defect Inspection, Defect Inspection Line, Defect Reason, Quality Defect Group, Quality Standard, Quality Standard Parameter, Quality Measurement, Production Loss Detail, Fruit Measurement, Fruit Measurement Sample, Product Grade, Pack Specification, Packout Run, Packout Run Source, Packout Output, Packout Profile, Secondary Product Type, Secondary Product Movement, Scale Device, Scale Reading.

### C. Dự thu, kế hoạch, định mức đời cũ, thay bằng dự thu của spec 001 đọc sổ lô (17)

Harvest Forecast, Forecast Allocation, Forecast Output Plan, Forecast Source Claim, Supply Reconciliation, Lotus Cut Forecast Profile, Lotus Cut Journal Entry, Lotus Cut Journal Import, Plan Cohort, Lotus Handover Cohort, Material Norm Profile, Material Norm Line, Norm Basis, Material Requirement, Material Requirement Line, Material Consumption, Material Recovery.

### D. Nhập từ OneDrive, chuyển đổi từ hệ thống cũ (12)

OneDrive Feed, Source File Registry, Source Import Batch, Source Import Mapping, Source Import Row, Source Inventory Item, Source Mapping Field, Integration Event, Integration Task, Lotus Process Adoption, Legacy Organization Map, Cancellation Reason Alias.

### E. Khung ứng dụng cũ chỉ còn phục vụ các luồng trên (3, thêm khi rà soát ngày 10/11)

Lotus Alert (trang Cảnh báo và việc chạy mỗi giờ, mọi loại cảnh báo đều đọc bảng ở nhóm A–C), Lotus Farm Settings (trang Cấu hình: 13 ngưỡng và hệ số chỉ các luồng đã xóa đọc), Market (danh mục thị trường, chỉ Packout Output trỏ tới). Trên bản thật: Lotus Alert 0 dòng, Market 0 dòng, Lotus Farm Settings chỉ có giá trị mặc định 0 và một ghi chú. Phần "Sáng nay" của báo cáo mới (spec 002, US5) thay cho cảnh báo.

Ngoài các bảng, lần dọn gỡ thêm các cột của luồng cũ trên bảng giữ: chiều kế toán "Vụ" `lotus_crop_cycle` (60 bảng), `lotus_work_plan`, `lotus_harvest_lot`, `lotus_packout_run`, `lotus_forecast_impacts_json` (Stock Entry), `lotus_requirement`, `lotus_requirement_line` (Stock Entry Detail, Material Request Item), `process_adoption`, `source_version` (Bunch Tag), `category` (Work Type, 168 việc đang mang nhóm việc cũ; giá trị được lưu trong tệp lưu trữ), `posted_event` (Lotus Work Entry), `harvest_lot` (Packhouse Preprocessing), `norm_profile` (Work Schedule Rule). Không cột nào có giá trị trên chứng từ đã ghi sổ.

## 2. Bảng giữ (23) và bảng mới (2)

**Giữ**: Farm, Farm Block, Farm Block Geometry, Banana Variety, Work Type, Work Team, Work Schedule Rule (rút gọn thành vòng chăm sóc), Lotus Work Assignment, Lotus Work Entry, Lotus Work Entry Person, Lotus Work Entry Material, Lotus Work Session, Lotus Work Inspection, Lotus Piece Rate, Bunch Tag, Cancellation Reason, Cancellation Reason Group, Disease, Packhouse Shift, Packhouse Shift Labor, Packhouse Preprocessing, Lotus Block Forecast Profile, Lotus Forecast Snapshot.

**Mới**: Lotus Daily Report, Packhouse Shift Source.

Bốn bảng lúc đầu nằm trong diện nghi là đồ cũ nhưng được giữ:

| Bảng | Lý do giữ |
|---|---|
| Lotus Crew Attendance | Đang dùng ở chấm công và bảng lương; không thuộc mảng vườn |
| Banana Variety | Giống chuối của lô |
| Cancellation Reason Group | Nhóm của lý do hủy buồng |
| Disease | Danh mục bệnh, dùng cho dòng kiểm tra sâu bệnh trong sổ lô |

## 3. Chỗ phải sửa ngoài mảng vườn

| Phần | Đang dùng đồ cũ | Xử lý |
|---|---|---|
| Giá thành (`finance/costing.py`, `finance/rules.py`) | `Crop Cycle` làm chiều kế toán "Vụ"; `Harvest Lot`, `Harvest Actual` để nhập kho thu hoạch; `Harvest Forecast` để tính sản lượng dở dang | Bỏ chiều Vụ: chi phí tập theo lô, số vụ ghi kèm. Nhập kho thành phẩm theo ca đóng gói (research R15). Sản lượng dự kiến lấy từ dự thu chung |
| Tài sản (`finance/assets.py`, bảng con `Lotus Asset Allocation Row`) | Trường trỏ `Crop Cycle` | Bỏ trường vụ; phân bổ theo lô |
| Bảng giá thành (`Lotus Costing Row`) | Trường trỏ `Crop Cycle` | Đổi thành số vụ (số nguyên) |
| Kế hoạch tài chính (`finance/planning.py`) | `Harvest Forecast` | Đọc API dự thu chung |
| Lương và chi phí công theo lô (`finance/payroll.py`, `hr_period.py`) | `Daily Work Result`, `Work Actual Labor`, `Labor Allocation`, `Daily Work Plan Line` | Chỉ đọc buổi công của sổ lô (có trọng số). Bỏ `Labor Allocation` khỏi danh sách khóa kỳ |
| Kho, phiếu xuất (`warehouse_issue.py`, `warehouse.py`, form xuất kho) | Chế độ xuất "Theo kế hoạch đã duyệt" (`Daily Work Plan`), `Material Requirement`, `Material Consumption`, `Material Recovery` | Bỏ chế độ theo kế hoạch; còn "Thủ công" và "Theo yêu cầu đã duyệt" |
| Kho, "Nhu cầu cấp cho công việc" (`warehouse_planning.py`) | `Material Requirement` cùng `Material Request` | Chỉ còn `Material Request`. Phần nhận hàng mua giữ nguyên |
| Kho, cầu nối (`stock_bridge.py`, `finance/stock.py`, `finance/setup.py`, `install.py`) | `Packout Run`, `Harvest Lot`, `Forecast Allocation`; các trường `lotus_harvest_lot`, `lotus_work_plan` trên phiếu kho và trường trỏ `Packout Run` | Gỡ phần cầu nối cũ và các trường này; giữ các kiểm tra phiếu kho khác |
| In phiếu (`www/lotus_stock_print.py`, `www/lotus_material_proposal_print.py`) | `Material Requirement`, `Daily Work Plan` | Bỏ phần tham chiếu |
| Thông báo, người dùng, duyệt đơn giá (`push_notifications.py`, `user_admin.py`, `rate_approval.py`) | `Daily Work Plan`, `Daily Work Result` | Bỏ thông báo và quyền liên quan. Xóa `rate_approval.py` vì đơn giá lấy từ bảng giá khoán |
| Bảng giữ nhưng có trường trỏ bảng cũ | `Bunch Tag` (trỏ `Bunch Operation`, `Lotus Process Adoption`), `Work Type` (`Work Category`), `Work Schedule Rule` (`Material Norm Profile`), `Packhouse Preprocessing` (`Harvest Lot`), `Lotus Work Entry` (`posted_event`) | Bỏ các trường đó |
| Vườn & lô, bản đồ (`farm_land.py`, `field.py`, `scoping.py`, `map_import.py`) | `Farm Plot`, `Plot Geometry` và các bảng ghi chép cũ | Bỏ lớp thửa. Phần việc và sản lượng của lô đọc sổ lô |
| Tổng quan (`reporting.py`) | Nhiều bảng cũ | Đọc sổ lô và dự thu chung |
| Khung ứng dụng (`hooks.py`, `install.py`, `permissions.py`, `console.py`, `controls.py`, `api.py`, `App.vue`, `router.js`, `mobile-menu.js`, `preload.js`) | Đăng ký quyền, sự kiện, màn và mục menu cho bảng cũ | Gỡ hết các đăng ký đó |

## 4. Mã và màn hình xóa hẳn

Dấu * nghĩa là phải kiểm lần cuối lúc làm: chỉ xóa nếu file đó chỉ phục vụ đồ cũ.

**Backend**:
- **Ghi chép và phiếu đời cũ:** `daily_operations.py` (kèm báo cáo `daily_operations`), `daily_api.py`, `work_review.py`, `mobile_assignment.py`, `mobile_demo_seed.py`, `field_todo.py`, `productivity.py`, `farm_workspace.py`.
- **Thu hoạch, cung ứng, đóng gói đời cũ:** `harvest_matching.py`, `allocations.py`, `reconciliation.py`, `learning.py`, `packhouse.py`, báo cáo `harvest_availability`.
- **Dự thu đời cũ:** `forecast_workspace.py`, `forecast_setup.py`, `forecast_import_preview.py`, `forecast_calendar.py`, `vip126_live.py`, `vip126_profile.py`, `vip126_zone_plan.py`, `vip126_timeline.py`, `vip126_trial.py`.
- **OneDrive:** `onedrive.py`, `onedrive_protocol.py`, `onedrive_workspace.py`, `onedrive_supply.py`.
- **Kế hoạch và định mức:** `plan_norm.py`, `plan_book2_reference.py`, `rate_approval.py`.
- **Nhập liệu và kiểm soát cũ:** `importing.py`*, `promax_controls.py`*, `inheritance.py`*.
- **Ứng dụng tĩnh cũ:** `public/field/app.js`.
- **Thay bằng module mới của spec này:** `bunch_posting.py`, `bunch_report.py`, `work_report.py`.

**Frontend**:
- **Màn cũ:** `FarmWorkApp.vue`, `OneDriveProcessWorkspace.vue`, `OneDriveSupplyDialog.vue`, `Vip126RollingForecast.vue`, `PlanNormSettings.vue`, `WorkMaterialSettings.vue`, `SchemaForm.vue`*.
- **Dự thu:** các component dự thu cũ mà trang Dự thu mới không dùng*.
- **Menu:** các mục cũ trong `mobile-menu.js` và `preload.js`.
- **Logic và kiểu dáng:** `plan-norm-engine.js`, `field-todo.css`, `mobile-work-legacy.css`*.

**Tool và test**:
- Các tool nhập OneDrive, ProMax và Farm 222 đời cũ.
- Các test tương ứng: `test_onedrive_*`, `forecast-source-form`, `source-cut-form`, `onedrive-process`, `plan-norm-safety`, `harvest-profile-settings`, `work-result-review`, `verify_field_todo`.
- Phần bảng cũ trong `test_brd.py` và `test_inheritance.py`.

## 5. Kiểm và lưu trữ trên bản thật trước khi xóa

1. Sao lưu toàn bộ cơ sở dữ liệu và tệp.
2. Đếm số dòng của từng bảng ở mục 1.
3. Đếm các giá trị khác rỗng sau:
   - chiều Vụ (`lotus_crop_cycle`) trên GL Entry, Journal Entry Account, Stock Entry Detail và các chứng từ mua bán;
   - `lotus_work_plan` và `lotus_harvest_lot` trên Stock Entry;
   - trường trỏ `Material Requirement` trên Material Request Item;
   - các kỳ lương đã hạch toán có dùng `Labor Allocation`.
4. Xuất toàn bộ dòng của mọi bảng sẽ xóa ra tệp JSON lưu trữ, mỗi bảng một tệp, kèm số dòng và mã kiểm.
5. Nếu bước 3 thấy giá trị nằm trên chứng từ kế toán đã ghi sổ thì dừng và báo chủ vườn trước khi gỡ trường. Không sửa thẳng sổ.
6. Xóa theo thứ tự: dữ liệu → trường tùy chỉnh và chiều kế toán → DocType → file mã. Sau đó migrate, rồi quét lại để chắc không còn tên bảng cũ trong mã, cơ sở dữ liệu và menu.

Công cụ: `lotus_farm/legacy_purge.py`, gồm `preview` (chỉ đọc: đếm, kiểm, ước lượng tệp lưu trữ) và `commit` (lưu trữ rồi xóa, chạy lại không lỗi). Kèm một test quét mã để chặn tên bảng cũ quay lại.
