# BRD ↔ code audit — 07/10/2026

Baseline: main `ece70ecc129d50d982c2025252893fdb9bae03ae`; đối chiếu `FRONTEND_BRD.md`, `FRONTEND_IMPLEMENTATION_SPEC.md`, `FRONTEND_TRACEABILITY.md` và BRD ProMax 360° được ghi trong `BRD_COVERAGE.md`.

## Kết luận

Repo có các luồng nghiệp vụ chính và kiểm thử Frappe/ERPNext thật, nhưng **chưa khớp toàn bộ BRD/spec và chưa thể đánh dấu production accepted**. Bản sửa này đóng các lỗi chức năng dưới đây; bảng traceability là bản đồ yêu cầu, không phải chứng nhận mọi acceptance đều đã đạt.

## Các lỗi được sửa

| Yêu cầu | Trước audit | Thay đổi / bằng chứng |
|---|---|---|
| FR-001/002/030, route scope | Cycle/status có trên URL nhưng chưa lọc đầy đủ; ID cha/con mâu thuẫn; company có thể bị bỏ qua | `scoping.py` suy ra Company/Farm/Block/Plot từ Cycle, kiểm quyền và quan hệ; scope picker phụ thuộc; `console.listing`, task/report/map/material/QC/loss/productivity áp dụng scope |
| FR-004, Work views | My Work/At Risk chưa thực sự lọc theo người/rủi ro | `daily_overview`: responsible=current user; blocked/thiếu công/quá hạn; Board vẫn nhóm theo trạng thái |
| FR-003, dashboard | Trung bình phần trăm giữa Farm làm sai trọng số nhiệm vụ | Trung bình theo từng task; bổ sung tỷ lệ packout và lỗi tích hợp; không biến dữ liệu không được phép đọc thành số 0 |
| Date/status/search | Một đầu khoảng ngày bị bỏ qua; search có thể ghi đè bộ lọc nguồn | Khoảng ngày một phía; canonical status validated; search là AND với scope, không thay thế danh sách nguồn |
| FR-030, action UX | Một số nút lệnh luôn hiện dù role/state không phù hợp | `console.bootstrap.commands` + create/read capabilities; router deny; nút work/close/import/reserve/repack/calibration và tạo dòng ca theo role/docstatus |
| FR-015/016/032, offline | Queue tồn tại nhưng reload mất mạng không có app shell/session/task/master cache | Worker chỉ cache bundle tĩnh; read cache IndexedDB theo user+method+scope, TTL 24h, bỏ CSRF; preload field bootstrap/schema/link masters; không fallback trên HTTP permission denial; live browser reload offline |
| FR-016/032, account/photo | Account có thể đổi sau session check; ảnh private chưa gắn chứng cứ | `expected_user` kiểm lại trong upload/capture; refresh CSRF từ session; File gắn vào Field Capture; kiểm retry giữ chứng từ gốc |
| Idempotency | Reserve/release retry có thể tạo event ID mới | Attempt ID theo payload/lệnh, giữ qua reload trong sessionStorage đến khi có phản hồi thành công; payload mới dùng ID mới |
| FR-023, trace | Dedicated Harvest Lot trace nhận string IDs như document rows | Giữ contract cũ `packout`, thêm `packout_documents` để render/open đúng chứng từ |
| Scope navigation | Phản hồi chậm của scope cũ có thể ghi lên màn hình mới | Mỗi load có generation; loại bỏ kết quả từ generation đã thay đổi |

## Kiểm chứng

- Pure Python: các quy tắc domain, schema, identity, server guards.
- Frontend unit: schema payload, labor matrix, navigation, attempt retry identity và account partition.
- Native browser: queue commit/abort, retry/photo, single-flight, account binding; read cache khác user/scope không truy cập được và không lưu CSRF.
- Mock browser: route/query, KPI drill-down, work actual, canonical select/checkbox, ERP shortage, reload/mobile và route/action của tài khoản chỉ đọc.
- Site CI: cài/migrate hai lần trên Frappe/ERPNext v16; toàn bộ `test_brd`, thêm scope/status/date/search/permission/account/photo tests.
- Browser site thật: login → task cache → reload mất mạng → actual → audit → preview/save/submit close → đọc dữ liệu đã lưu.

Kết quả CI của đúng commit được ghi trong PR. Các bước trên không thay cho kiểm tải hoặc UAT Lotus.

## Phần còn thiếu so với BRD/spec

| Nhóm | Tình trạng thực tế / việc còn lại |
|---|---|
| FE-002 Farm 360 | Route hiện là danh sách phân cấp; chưa đủ header KPI và 10 tab Tổng quan/Lô/Công việc/Nhân lực/Vật tư/Sản lượng/Tổn thất/QC/Xưởng/Lịch sử như BRD |
| FE-003 Plot/Cycle 360 | Có timeline từ transaction thật và tabs; header chưa đủ toàn bộ area/plant count/cycle type/parent/cohort và KPI theo specification |
| FE-006 task card | Board/My Work/At Risk có; chưa có material readiness chi tiết ngay trên từng card, hủy từng task cần quy tắc nghiệp vụ riêng |
| FE-007/FE-010 UX | Labor matrix và measurement child rows có; chưa phải lịch phân công drag/drop hoặc lưới nhập nhanh chuyên biệt như thiết kế đích |
| Architecture spec §3/7 | Router/session/scope/cache đã tách; App.vue vẫn chứa nhiều module; chưa đủ page/repository/store/component layout được đặc tả |
| Keyboard/accessibility | Có native inputs/buttons; chưa kiểm hoàn chỉnh focus trap, keyboard dialog/table hoặc toàn bộ 360/430/768/1280/1920 widths |
| Cache lifecycle | Cache có TTL và account partition; không có background sync hay offline toàn bộ report/ERP; phải mở đúng scope khi còn mạng; dữ liệu offline là snapshot và quyền vẫn kiểm lại lúc gửi |
| Performance | Dashboard duyệt từng ngày/Farm, trace duyệt source; chưa có bằng chứng SLA với khối lượng 700 ha |
| Real rollout | Chưa xác nhận master Farm/Lô/Thửa thật, norm/tolerance/grade/spec, archive reconciliation, OneDrive credentials, thiết bị cân/GIS, backup/restore, UAT và cutover |

Giữ UI hiện trường cũ làm fallback. Không đánh dấu F4 switch-default/UAT/production acceptance đã xong chỉ vì CI xanh.
