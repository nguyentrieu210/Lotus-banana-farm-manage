# Chạy thử và đưa Lotus vào dùng

## 1. Chuẩn bị trên môi trường riêng

Cài ERPNext/Frappe v16 và app, migrate, build asset. Cấu hình timezone `Asia/Ho_Chi_Minh`. Mở `/assets/lotus_farm/field/index.html` sau khi đăng nhập. HTTPS cần cho GPS/service worker trên thiết bị thật; localhost dùng cho kiểm thử trình duyệt.

Tạo các vai trò Lotus và cấp User Permission theo Farm. Quyền Stock, Sales Order, Item, Warehouse và Employee/Attendance vẫn cấp ở ERP/HR. Tài khoản nhập dữ liệu có Lotus Integration User **và** quyền tạo các DocType đích được chọn; không cấp bỏ qua quyền. Tài khoản feed riêng được giới hạn Farm và nguồn đọc. Không dùng Administrator làm tài khoản feed chạy thường xuyên.

Tạo Company/Farm/lô/thửa/vụ/đợt chồi đã xác nhận; duyệt Legacy Organization Map. Cấu hình Work Type, năng suất, Norm Basis, Item/UOM/kho và định mức có hiệu lực. Cấu hình QC, nguyên nhân hủy/lỗi, Grade/Market/Pack Specification và profile dự thu. Sau khi map sản phẩm, bật `require_pack_classification`; kiểm lại kg/thùng. Bật `require_registered_scale` và đăng ký Scale Device đúng API user/kỳ hiệu chuẩn.

## 2. Một ngày phải chạy hết

| Bước | Dữ liệu / thao tác | Kết quả cần thấy |
|---|---|---|
| Giao việc | Farm A / Lô 33 / Thửa 33.1, bao 1.250 buồng | Kế hoạch trước khi làm, đúng UOM |
| Tính nhu cầu | 4 tấm/buồng | 5.000 tấm; phiên bản định mức được giữ |
| Kiểm tồn | ERP còn 3.800 tấm | Thiếu 1.200; tạo Material Request nháp, gửi lại không thêm phiếu |
| Nhân công | Năng suất và số công theo mức đã duyệt | Need/allocated/actual hiện đủ; không bố trí nhân viên vắng hoặc quá khả năng ngày |
| Thực hiện | 1.110 buồng | Ghi kết quả và lý do 140 buồng chưa xong |
| Vật tư | Xuất 5.000, dùng 4.440, thu hồi 560 | Đúng các dòng ERP Stock Entry; dùng + thu hồi = xuất |
| Hủy | 50 buồng, reason master, đúng cohort/kỳ thu | ATP hiện tại giảm; hash dự thu đã phát hành không đổi |
| Thu hoạch | Buồng/kg đúng thửa và ngày | Nhận lô không vượt nguồn |
| QC | Khối lượng nhận đạt, lỗi và kg loại | Phiếu QC nộp trước packout; tổng kg lỗi giải thích phần loại |
| Xưởng | Nhận đủ nguồn, thành phẩm + phụ phẩm + hao hụt | Cân đối kg, tiêu chuẩn đúng ngày/Item; kho do ERP ghi |
| Truy nguồn | Mở Item/Batch và quét QR lô | Đi về Harvest Lot → cohort → vụ → thửa → lô → Farm → Company |
| Dự thu sau actual | Đủ nguồn nhận/QC/đóng gói/ghi kho | Đề xuất kg/buồng, quality và yield; tạo version nháp, không tự duyệt |
| Chốt | Không còn lỗi chặn hoặc draft chưa xử lý | Nộp được; sửa/hủy ngày đã chốt bị chặn |
| Sửa có lý do | Mở lại chốt, cancel/amend đúng phiếu | Có người, thời gian và lý do; không sửa số cũ âm thầm |

## 3. Các tình huống bắt buộc thử thêm

- Giữ hàng đồng thời từ hai phiên; tổng không vượt nguồn hoặc nhu cầu đơn. Gửi lại cùng ID/payload không tạo thêm.
- Chuyển một phần allocation sang SRE, để phần còn lại là dự thu; giao từng đợt bằng Delivery Note ERP. Đối chiếu đã giao/còn giao theo đúng dòng đơn. Khi hủy phải xử lý chứng từ giao trước, rồi đối soát SRE/kho.
- Mất mạng sau khi nhập, đóng/mở lại trình duyệt, gửi lại khi có mạng. Mất phản hồi sau gửi không được tạo hai phiếu. Đổi tài khoản không gửi outbox của người cũ. Bản lỗi phải kiểm tra xem máy chủ đã nhận chưa trước khi bỏ bản nhập sai.
- Đổi quyền Farm hoặc chốt ngày trong lúc thiết bị đang offline; khi gửi, máy chủ phải từ chối dữ liệu không còn hợp lệ và giữ bản chờ.
- Cân chưa đăng ký, API user khác, hết kỳ hiệu chuẩn, tare lớn hơn gross, ID cân trùng nhưng số khác.
- User chỉ được Farm A không mở/xuất được Farm B từ dashboard, bản đồ, truy nguồn, dataset, import hoặc ID đoán được.
- Excel có header trùng, sheet sai, ô formula, linked workbook, ngày Excel serial 60, blank, số locale sai, alias chưa map. Không sửa raw/normalized trong staging để lách nguồn gốc.
- Hai bản Excel cùng nguồn: chọn ưu tiên/kỳ nghiệp vụ, không lấy “modified mới nhất” làm đúng. Không nhập trùng một dòng từ hai batch.
- Snapshot t-8/t-4/t-2/t-1: không lấy bản phát hành sau cutoff; actual chưa đóng đủ nguồn không trở thành số 0.
- Từng thửa có diện tích và mã riêng; hai thửa cùng lô có thể cùng vụ số 1. Vụ chồi không dùng nhầm vụ mẹ/đợt chồi.

## 4. OneDrive và lịch sử

System Manager cấu hình OneDrive Feed: tenant/client/secret, drive/folder ID, mẫu tên file, mapping đã duyệt, Farm, kỳ nghiệp vụ và ưu tiên. App dùng Graph application credential với scope `.default`; quyền đọc folder phải được quản trị Microsoft cấp. Feed mặc định tắt. Bấm/lệnh `onedrive.poll_feed` để kiểm trước khi bật scheduler hourly.

Inventory ghi file có và không khớp mẫu. File khớp được tính SHA-256 và tạo Source Registry/Integration Task. `auto_stage` chỉ đọc vào staging, không nhập/duyệt giao dịch. Source mới mặc định Unknown; người phụ trách phải xác nhận ưu tiên và đánh dấu Active trước khi tạo phiếu đích. Không có credential trong repo.

Tier A/B dùng mapping để tạo phiếu nháp rồi kiểm tra. Tier C/D giữ registry/manifest/đường dẫn, không biến báo cáo trình bày thành actual. Tổng nguồn, tổng đích và số dòng rejected/pending phải được đối soát; rejected có người xử lý và lý do. ≥99.5% dòng được giải quyết là điều kiện nộp batch, không phải bằng chứng số liệu đã được Lotus nghiệm thu.

Giới hạn xử lý: XLSX ≤40 MiB, sau giải nén ≤200 MiB, ≤10.000 dòng mỗi batch; báo cáo giới hạn phạm vi và không âm thầm cắt số khi vượt 10.000 bản ghi. Chia phạm vi với mapping và nguồn được duyệt nếu vượt giới hạn. Ngày file không ghi đè ngày trong sheet. Không chạy công thức Excel trong server.

## 5. Biên bản kiểm tra

Mỗi kịch bản ghi: dữ liệu đầu vào, số mong đợi, số trên ERP/Lotus, phiếu nguồn, người thực hiện, ngày, sai lệch, quyết định và người duyệt. Kiểm dashboard với lượng dữ liệu dự kiến thực tế, thống nhất thời gian phản hồi và số người dùng đồng thời rồi mới đặt mức đạt/không đạt. Dùng `reporting.dataset` cho Power BI bằng API user giới hạn Farm; không đưa token vào report công khai.

## 6. Cutover và quay lại

1. Sao lưu DB/files và thử phục hồi trên site khác. Giữ bản source Excel bất biến, hash và thời điểm freeze.
2. Kiểm kê ERP stock/batch/đơn chưa giao; đối chiếu với kho và kế toán. Lotus không tự ghi số tồn mở đầu.
3. Dry-run import theo Farm/tầng dữ liệu, xử lý rejected và chênh lệch. Kiểm lại quyền người dùng, thiết bị, profile và ranh giới.
4. Key user Farm/xưởng/kho/planner ký kết quả UAT. Chỉ sau đó quyết định ngày dừng ghi báo cáo Excel bắt buộc và ai nhập từng chứng từ.
5. Chốt mốc cutover. Giữ Excel read-only, mở app theo Farm được duyệt và kiểm đối chiếu hàng ngày.
6. Nếu sai dữ liệu/kho nghiêm trọng: dừng nhập mới, lưu danh sách phiếu sau mốc, đối soát ERP trước. Phục hồi DB chỉ theo phương án đã thử và được người phụ trách quyết định; không đơn giản reset code để bỏ giao dịch đã phát sinh.
7. Hypercare có người nhận lỗi, mức ưu tiên, thời hạn xử lý và đối chiếu cuối ngày. Chỉ đóng đợt triển khai khi số liệu thật khớp và người dùng xác nhận làm được việc.
