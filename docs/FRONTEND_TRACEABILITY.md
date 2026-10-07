# Lotus Frontend — BRD Traceability Matrix

| ID | Nhu cầu | Backend hiện có | Frontend đích | Acceptance |
|---|---|---|---|---|
| FR-001 | Công ty → Nông trường → Lô → Thửa | Company, Farm, Farm Block, Farm Plot | ScopePicker, Farm/Plot 360 | Không xuất hiện Xí nghiệp |
| FR-002 | Vụ/đợt chồi | Crop Cycle, Sucker Selection Batch | Cycle timeline | Vụ đúng Thửa, ratoon đúng cohort |
| FR-003 | Điều hành hôm nay | `reporting.dashboard`, `field.bootstrap` | Today Dashboard | KPI drill-down được |
| FR-004 | Việc ngày | Daily Work Plan/Result | Work list/board/detail | Plan→actual trace |
| FR-005 | Việc đến hạn | Work Schedule Rule, `make_suggested_plan` | Suggested Work action | Tạo draft để kiểm tra |
| FR-006 | Nhân công | Labor Allocation, Daily Labor, `available_labor` | Labor Board | Unknown Attendance không thành present |
| FR-007 | Định mức vật tư | Material Norm Profile/Line | Material detail | Version/effective date rõ |
| FR-008 | Thiếu vật tư | Material Requirement + ERP Bin | Material Requirement | Hiển thị required/available/shortage |
| FR-009 | Kho ERP | Material Request/Stock Entry | ERP link/action | Không ledger Lotus thứ hai |
| FR-010 | Hủy buồng | Reason Group/Reason/Alias, Cancellation | Loss quick entry/analytics | Canonical reason |
| FR-011 | Hủy ảnh hưởng dự thu | Forecast logic hiện có | Loss + Forecast UI | Released snapshot không đổi |
| FR-012 | Bệnh/BVTV | Disease/Observation | Field event | Trace được về Thửa/Vụ |
| FR-013 | Đo trái | Fruit Measurement | Measurement grid/mobile | Không L1…L140 fixed fields |
| FR-014 | Thu hoạch | Harvest Actual/Lot/Source | Harvest | Submitted actual không overwrite |
| FR-015 | Offline field | `field.capture`, `capture_status` | OfflineQueue | Retry không duplicate |
| FR-016 | GPS/ảnh | Field Capture/File | Field forms | Upload lỗi không mất event |
| FR-017 | QC đầu vào | Incoming Quality Inspection, `receive_quality` | QC | QC trước packout |
| FR-018 | Xưởng | Packout Run/Source/Output | Packhouse | Input/output/loss reconciliation |
| FR-019 | Grade/pack spec | Product Grade/Market/Pack Spec | Packout selector | Không hard-code |
| FR-020 | Phụ phẩm/hao hụt | Secondary Product, Production Loss | Packhouse tabs | Mass balance |
| FR-021 | Chốt ngày | Daily Production Close, `preview_close` | Daily Close | Blocking check chặn submit |
| FR-022 | Kết vụ | Cycle Closing Report | Cycle Close | Derived from actual |
| FR-023 | Trace ngược/xuôi | trace APIs | Trace | Item/Batch↔Lot↔Plot |
| FR-024 | Forecast vintages | `forecast_vintages` | Forecast accuracy | t-8/t-4/t-2/t-1 đúng cutoff |
| FR-025 | Giao nhiều đợt | `delivery_progress`, ERP Sales/Delivery | Delivery progress | Không tạo sales ledger riêng |
| FR-026 | Bản đồ | Plot Geometry, `map_data` | Plot Map | Chỉ geometry đã duyệt |
| FR-027 | Source registry | Source File Registry | Import Center | File không biến mất khỏi inventory |
| FR-028 | Staging/import | `stage_workbook`, `preview_import`, `import_rows` | Import Center | Dry-run + rejected visible |
| FR-029 | OneDrive | OneDrive Feed/Integration Task | Source status | Auto-stage không auto-approve |
| FR-030 | Quyền Farm | permission hooks/session capabilities | Route/action guard | Farm A không đọc Farm B |
| FR-031 | Audit | Version/amendment controls | Audit Drawer | Before/after/reason |
| FR-032 | Mobile account isolation | current IndexedDB behavior | offlineStore | User B không thấy queue User A |
| FR-033 | QR | lot QR API | Harvest Lot | QR mở đúng nguồn, vẫn check permission |
| FR-034 | Scale | Scale Device/Reading | Packhouse/receiving | Device/user/calibration validated server-side |
| FR-035 | Power BI/data export | `reporting.dataset` | Reports/Admin | Dataset theo quyền Farm |
