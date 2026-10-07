# Đối chiếu BRD ProMax — phạm vi code và nghiệm thu

Nguồn: **Lotus Farm BRD 360° ProMax — Điều hành nông trường, dự thu, thu hoạch và đóng gói**, bản 06/10/2026 18:49 UTC. Không lấy BRD đầu tiên thay cho bản này.

**“Có trong code” khác với “Lotus đã nghiệm thu”.** Bảng dưới ghi các phần đã triển khai trong app; việc khóa tên Farm, hệ số, dữ liệu, quyền người dùng và thiết bị thật vẫn phải làm tại đơn vị. Kết quả kiểm tra được ghi trong PR của commit hiện tại.

| Nhóm yêu cầu | Code / nơi sử dụng | Phạm vi và cách kiểm tra |
|---|---|---|
| Company → Farm → Block → Plot | Farm, Farm Block, Farm Plot | Không tạo Xí nghiệp; kiểm diện tích, khóa danh tính đã dùng |
| Vụ mẹ / vụ chồi / cohort | Crop Cycle, Sucker Selection Batch | Vụ độc lập theo thửa; vụ chồi có vụ mẹ và ngày chọn chồi |
| Dữ liệu đất cũ | Legacy Organization Map, Legacy Cycle Plot Mapping | Mapping phải duyệt; giữ dữ liệu nguồn và lịch sử cũ |
| Công việc và định mức năng suất | Work Category, Work Type | Đơn vị và số lượng một công do Lotus cấu hình |
| Đề xuất việc đến hạn | Work Schedule Rule, `field.suggest_work` | Mốc trồng/chọn chồi/trổ/cắt bắp; offset, chu kỳ lặp, phiên bản; tạo kế hoạch nháp |
| Kế hoạch / kết quả ngày | Daily Work Plan/Result, màn hình Ngoài vườn | Kết quả đúng dòng kế hoạch; thiếu khối lượng phải giải thích |
| Nhân công cần / bố trí / thực tế | Labor Allocation, Daily Labor Summary | Employee và đội; giới hạn một công, nửa ngày/vắng khi có Attendance |
| ERP Employee / Attendance | `field.available_labor` | Đọc trực tiếp ERP/HR; không có Attendance thì báo chưa xác nhận, không tự coi là có mặt |
| Định mức vật tư có phiên bản | Norm Basis, Material Norm Profile/Line | Tách UOM vật tư và mẫu số; thời gian hiệu lực không chồng lấn |
| Nhu cầu / thiếu vật tư | Material Requirement, Material Request | Tính từ kế hoạch; đọc Bin ERP; đề nghị mua nháp, gửi lại không tạo thêm |
| Xuất / dùng / thu hồi | Material Consumption/Recovery | Khớp dòng Stock Entry thật; không có ledger Lotus riêng |
| Hủy buồng | Cancellation Reason Group/Reason/Alias, Bunch Cancellation | Lý do master, nguồn/cohort/kỳ thu; cập nhật ATP mà giữ nguyên snapshot đã phát hành |
| Trồng / trồng dặm | Planting Event | Ngày, cây, diện tích, thửa/vụ; dùng chung nhập hiện trường và staging |
| BVTV / bệnh | Disease, Disease Observation | Ghi số cây, mức độ và việc xử lý; thuốc/vật tư theo Work Result/Consumption |
| Chăm sóc buồng / màu dây | Bunch Operation, Bunch Tag | Mốc phát triển, tag có hiệu lực; retry được kiểm tra payload |
| Đo trái / luống | Fruit Measurement | Số mẫu, luống, chiều dài/đường kính và UOM |
| Thu hoạch và truy nguồn | Harvest Actual/Lot/Source | Không nhận quá khối lượng nguồn; nguồn vụ phải có thửa trước khi nhận lô mới |
| QC đầu vào | Incoming Quality Inspection, `packhouse.receive_quality` | Nộp QC trước đóng gói; nguyên nhân và kg lỗi giải thích toàn bộ phần loại |
| Grade / Market / quy cách | Product Grade, Market, Pack Specification | Liên kết Item, kg/thùng, phiên bản và ngày hiệu lực; bật bắt buộc phân loại khi cutover |
| Ca đóng gói / nguồn vào / đầu ra | Packout Run/Source/Output | Một phiếu tương ứng ca/đợt xử lý theo Farm, nhiều lô cùng Farm; QC, khối lượng và kho giữ luồng cũ |
| Phụ phẩm / hao hụt | Secondary Product Type/Movement, Production Loss Detail | Phụ phẩm là Item kho ERP; hao hụt có nguyên nhân; đầu ra cân đối với đầu vào |
| Bản đồ kho | Warehouse Mapping và warehouse ERP | Farm/kho/điểm giữ hàng thực; không tạo kho giả cho từng thửa |
| ERP ghi kho thành phẩm | Stock bridge Repack, Supply Reconciliation | Tồn và kế toán do ERP ghi; đảo kho phải duyệt ảnh hưởng tới dự thu/cam kết |
| Snapshot dự thu tuần/tháng | Harvest Forecast, Forecast Output Plan | Ngày kỳ, planning grain, nguồn, công thức, hash, revision; snapshot đã phát hành không bị viết lại |
| Cam kết bán / ATP | Forecast Allocation, Sales Order/SRE | Theo đúng dòng đơn/Item, khóa giao dịch, không giữ vượt nguồn hoặc nhu cầu |
| Chuyển một phần sang hàng kho | `stock_bridge.link_stock_reservation(..., qty_kg=...)` | Tách lượng đã chuyển và lượng còn dự thu; retry, kiểm tổng nhu cầu; hủy SRE có đối soát và gộp lại phần dự thu |
| Giao nhiều đợt | Delivery Note/Sales Order ERP, `reporting.delivery_progress` | ERP giữ giao hàng thật; Lotus đọc đã giao/còn giao/SRE, không tạo đơn bán thứ hai |
| Actual quay lại dự thu | `learning.propose_complete_profile`, `create_calibrated_profile`, `create_calibrated_packout` | Chỉ lấy nguồn đã nhận/QC/đóng gói/ghi kho đầy đủ; bình quân có trọng số; tạo phiên bản nháp cần duyệt |
| Độ chính xác dự thu | `reporting.forecast_vintages` | Snapshot trước thu 8/4/2/1 tuần; sai lệch tuyệt đối, bias, WAPE, thay đổi; dữ liệu chưa đủ không bị coi là actual zero |
| Dashboard Company / Farm | `reporting.dashboard`, màn hình Tổng quan | Việc tính theo từng task, không cộng khác UOM; công, hủy, kg, QC, packout và nguồn ATP |
| Drill-down / vòng đời thửa | `plot_history`, `trace_lot`, `trace_packout`, `trace_item` | Thửa → việc/nhân công/vật tư/bệnh/thu hoạch/QC/xưởng/dự thu; thành phẩm → lô/vụ/thửa/Farm/Company |
| Cảnh báo | Ngưỡng trong Lotus Farm Settings | Thiếu công; ngưỡng hủy, bệnh, packout do Lotus đặt. Vật tư trên dashboard là nhu cầu chưa ghi dùng; tồn thiếu xem riêng ERP Bin |
| Chốt ngày | Daily Production Close | Kết quả/công/vật tư/thu hồi/nhận hàng/QC/kho/lỗi tích hợp; còn lỗi chặn thì không nộp |
| Kết vụ | Cycle Closing Report | Số thực tế truy nguồn, phân bổ xưởng trộn nhiều lô theo kg đóng góp; ngày chốt đủ, lý do mở lại |
| Audit / amendment | track_changes, amendment_reason, close/reconciliation controls | Sửa phiếu đã nộp theo cancel/amend; lý do bắt buộc; dữ liệu cân và capture không xóa/sửa |
| Quyền Farm | permission/query hooks, các endpoint kiểm quyền cha | Thông tin con chỉ đọc sau khi cha được phép; không bỏ quyền ERP khi tạo stock/đơn nhập |
| Source Registry / tầng A–D | Source File Registry | ID/hash/kỳ/ưu tiên/trạng thái; A/B giao dịch, C/D archive/snapshot |
| Scan cây OneDrive | OneDrive Feed, Source Inventory Item | Graph delta theo folder; ghi mọi file, kể cả file không khớp mẫu nhập; item ID/path/size/created/modified/deleted |
| Excel extraction | `extraction.read_workbook`, Source Import Mapping | Sheet/header rõ, Unicode/locale/ngày/blank, merged header, formula, external link, named range; không chạy công thức |
| Staging / import | Source Import Batch/Row, `stage_workbook`, `preview_import`, `import_rows` | Giữ raw/hash/sheet/dòng/mapping; thử nhập rồi rollback; tạo phiếu nháp; kiểm lại file gốc khi nhập/nộp |
| Đối soát nguồn / đích | `importing.reconciliation`, control_totals_json | Tổng theo cột số, độ lệch, số rejected/pending; lệch hoặc reject phải giải thích; ≥99.5% dòng đã xử lý |
| Retry / lỗi tích hợp | Integration Task, OneDrive Feed | ID + hash, trạng thái, số thử, lỗi; chạy lại không thêm batch; lỗi chặn hiển thị trước chốt |
| Nhận file OneDrive mới | Graph feed theo lịch hourly, mặc định tắt | Tải file đúng mẫu, lưu riêng phiên bản/hash, tạo task và staging nếu cấu hình; không tự duyệt nguồn hoặc phiếu |
| Mobile / offline | `/assets/lotus_farm/field/index.html` | IndexedDB giữ task/số liệu và outbox theo user; mở lại mất mạng; gửi tuần tự, kiểm quyền/ngày lại trên máy chủ |
| GPS / ảnh | Field Capture | Thời điểm, tọa độ, độ chính xác, ảnh private, nguồn phiếu; cảnh báo ngoài ranh giới; đây là chứng cứ do thiết bị/người dùng gửi |
| QR Harvest Lot | `field.lot_qr`, nút trên Harvest Lot | QR mở phiếu nguồn; quyền đăng nhập/Farm vẫn áp dụng |
| Cân | Scale Device, Scale Reading, `api.ingest_scale` | API user gắn thiết bị/Farm, Kg và kỳ hiệu chuẩn; dữ liệu gốc và mã lần cân bất biến |
| GIS | Plot Geometry, `map_data`, `preview_kml` | GeoJSON WGS84, version duyệt, Polygon/MultiPolygon, xem thửa và nhật ký; KML preview không tự đoán mã đất |
| Power BI | `reporting.dataset` | JSON có đăng nhập và quyền Farm; đọc dữ liệu hệ thống thay Excel |
| UAT / cutover / hypercare | [UAT_CUTOVER.md](UAT_CUTOVER.md) | Kịch bản, dữ liệu đối soát, người ký, kế hoạch quay lại và xử lý lỗi; chưa thực hiện ở Lotus |

## Những gì không thể đóng bằng việc viết thêm code

- Không có bảng tên Farm/lô/thửa và dữ liệu Lotus được duyệt trong repo. Không tự suy BP1/BP2/ER1 thành Farm.
- Chưa có tài khoản/credential OneDrive, quyền Graph, ERP chạy thật, người dùng thực tế hoặc dữ liệu cân. Adapter có code, nhưng chưa kết nối những hệ thống này.
- Các hệ số dự thu, định biên, định mức, mẫu số, tolerance và tiêu chuẩn đóng gói cần bên vận hành duyệt. Không cấp các số “chuối thường là…” vào app.
- Chưa có SLA được thống nhất, bài kiểm tải trên dữ liệu 700 ha, đối soát toàn bộ archive, UAT có người ký, cutover hoặc hypercare.
- Machine learning chưa được triển khai: chính BRD yêu cầu transaction sạch trước. Phần hiệu chỉnh hiện tại dùng bình quân có trọng số và lịch sử snapshot, có người duyệt.
- Không dùng code của repo để tuyên bố đã dừng các báo cáo Excel, đã thay thế chấm công, hoặc đã đủ điều kiện chạy sản xuất.
