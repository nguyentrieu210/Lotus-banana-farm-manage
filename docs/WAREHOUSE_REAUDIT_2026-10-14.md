# Audit lại app kho Lotus — 14/10/2026

Mã được audit: `f52b207`, nhánh `codex/lotus-work`. Phạm vi: `/lotus/kho`, API kho/danh mục/nhu cầu/mua hàng, bản in và PDF; site local `frontend`, công ty Lotus Agritech.

**Kết luận: còn 10 phát hiện — 6 mức cao (P1), 3 mức vừa (P2), 1 mức thấp (P3).** Đây là báo cáo kiểm tra, chưa phải bản sửa các phát hiện dưới đây. Các khẳng định “đã xử lý” trong báo cáo audit trước không bao phủ những trường hợp biên mới này.

## Phát hiện cần ưu tiên

### A01 · P1 · Nhầm đơn vị làm giảm số lượng khi sửa phiếu

Vị trí: `lotus_farm/warehouse.py:137` (`_simple_doc`), `:152–171` (`document`), `frontend/src/StockApp.vue:90` (`editDocument`).

`document` trả `qty=row.qty` theo đơn vị giao dịch nhưng gắn `uom=stock_uom`. Form sửa gửi lại số lượng này như đơn vị tồn, với conversion_factor=1. `_simple_doc` vẫn đánh dấu phiếu có quy đổi là sửa được.

Đã tái hiện trên bench: nhập **2 Box, hệ số 10 = 20 Kg** → app hiển thị **2 Kg**, `can_write=true`; lưu lại từ form đơn giản → `transfer_qty=2 Kg`. Bản in dùng cùng dữ liệu nên cũng ghi sai số lượng/đơn vị trước khi sửa. Có thể kéo theo sai giá trị vật tư.

Sửa: thống nhất số lượng theo đơn vị tồn (`transfer_qty`) hoặc giữ đầy đủ qty/uom/conversion_factor theo dòng. Không cho sửa bằng form đơn giản nếu chưa hỗ trợ quy đổi. Kiểm thử xem, sửa, in, ghi sổ và giá trị theo cùng một quy ước.

### A02 · P1 · Sửa phiếu nhiều kho làm dồn tất cả dòng về kho đầu tiên

Vị trí: `lotus_farm/warehouse.py:137` (`_simple_doc`), `frontend/src/StockApp.vue:90`, `lotus_farm/warehouse.py:create_draft`.

API chi tiết cho sửa phiếu ERPNext có nhiều kho nhận/xuất trong từng dòng. Form chỉ có một kho chung và lấy kho của dòng đầu tiên; máy chủ áp dụng kho chung đó cho mọi dòng.

Đã tái hiện: phiếu nhập có hai vật tư lần lượt vào **kho A và kho B**, `can_write=true`; lưu lại → cả hai dòng vào **kho A**. Đây là thay đổi âm thầm trên phiếu nháp; nếu ghi sổ sẽ nhập sai kho.

Sửa: giới hạn `_simple_doc` theo cấu trúc kho mà form thực sự hỗ trợ, hoặc cho chọn và bảo toàn kho trên từng dòng. Áp dụng tương tự cho kiểm kê nhiều kho.

### A03 · P1 · Lượng đề nghị mua chưa đặt sai khi dùng đơn vị quy đổi

Vị trí: `lotus_farm/warehouse_planning.py:118–164` (`_supply`).

`Material Request Item.ordered_qty` của ERPNext đã theo đơn vị tồn, nhưng app tiếp tục nhân conversion_factor. Lỗi có cả vòng tổng hợp tài liệu và truy vấn SQL tổng hợp.

Đã tái hiện: đề nghị **10 Box × 10 = 100 Kg**; đơn mua liên kết **3 Box = 30 Kg**. ERPNext lưu `ordered_qty=30`; phần còn chưa đặt đúng là **70 Kg**, app trả **0** vì tính `100 − 30 × 10`. Có thể tạo đề nghị bổ sung sai/trùng. Không áp dụng cùng cách sửa máy móc cho Purchase Order.received_qty vì trường đó có quy ước khác.

Sửa: tách rõ đơn vị của ordered_qty/received_qty theo từng DocType; kiểm thử hệ số khác 1, mua một phần, nhận một phần và hủy đơn.

### A04 · P1 · Mở sửa tồn đầu kỳ tự đổi sang kiểm kê định kỳ và mất giá vốn

Vị trí: `frontend/src/StockApp.vue:61` (`open`), `:90` (`editDocument`), `lotus_farm/warehouse.py:create_draft` nhánh count.

`open('count')` đặt `count_purpose='Stock Reconciliation'`; `editDocument` không khôi phục purpose của phiếu gốc. Lưu lại sẽ đi qua nhánh định giá kiểm kê thường.

Đã mô phỏng đúng payload của form trên bench: phiếu **Opening Stock, 10 Kg, giá vốn 100** → lưu sửa thành **Stock Reconciliation, giá vốn 0** do vật tư chưa có tồn ghi sổ. Chưa ghi sổ dữ liệu thử.

Sửa: khôi phục purpose khi mở sửa; máy chủ chặn đổi purpose ngoài thao tác rõ ràng, bảo toàn giá vốn tồn đầu kỳ. Khi đổi nghiệp vụ có chủ đích nên tạo phiếu mới.

### A05 · P1 · Ghi sổ không kiểm tra phiên bản mà người dùng vừa duyệt

Vị trí: `frontend/src/StockApp.vue:96` (`postDocument`), `lotus_farm/warehouse.py:176` (`submit_document`).

API ghi sổ chỉ nhận doctype/name, không nhận modified hoặc phiên bản của màn xác nhận. Nó đọc tài liệu mới nhất rồi ghi sổ; kiểm tra timestamp của ERPNext không phát hiện màn hình phía người duyệt đã cũ.

Đã tái hiện: người dùng xem phiếu nhập **5 Kg**; một thao tác khác sửa thành **9 Kg**; gọi ghi sổ theo API hiện tại → **9 Kg được ghi sổ** mà không yêu cầu xem lại. Dữ liệu thử đã rollback.

Sửa: truyền modified từ màn chi tiết, khóa tài liệu, đọc lại và so phiên bản trước khi submit. Ghi sổ cũng cần chống nhấp lại/mất phản hồi theo trạng thái thực tế.

### A06 · P1 · Lập đề nghị mua cho kỳ quá khứ có thể tạo trùng

Vị trí: `lotus_farm/warehouse_planning.py:236–254` (`create_purchase_request`), `_supply`.

Nhu cầu lấy trong khoảng ngày chọn, nhưng đề nghị mới hẹn `max(to_date, nowdate())`. Với kỳ đã kết thúc, đề nghị được hẹn ngoài kỳ và bị `_supply` bỏ khỏi phần “đã đề nghị”. Khóa Company không ngăn được lần gọi tiếp theo vì phép tính vẫn cho rằng chưa đề nghị.

Đã tái hiện: nguồn cấp đã duyệt cần 50 Kg trong **ngày hôm qua**, tồn 9 Kg; bấm lập đề nghị hai lần cùng khoảng ngày → **hai Material Request khác nhau** được tạo.

Sửa: gắn đề nghị mua với nhu cầu gốc và theo dõi phần đã đề nghị bất kể ngày hẹn; hoặc từ chối tạo mua trực tiếp cho kỳ quá khứ và yêu cầu chuyển nhu cầu còn thiếu sang kỳ hiện tại. Chọn chính sách rõ ràng trước khi sửa.

## Phát hiện mức vừa/thấp

### A07 · P2 · Nhiều phiếu nháp có thể giữ quá tồn khả dụng

Vị trí: `lotus_farm/warehouse.py:514` (`check_outbound_stock`), `warehouse_planning.py:_draft_holds`.

Kiểm tra lưu phiếu chỉ xét Bin và tồn theo ngày, chưa trừ phiếu nháp khác như bảng khả dụng. Đã tái hiện tồn **9 Kg**, lập hai phiếu xuất nháp **6 + 6 Kg** đều được lưu. Tổng giữ 12, khả dụng thành -3. **Không đồng nghĩa đã xuất âm:** ghi sổ vẫn bị chặn khi không còn tồn.

Sửa: nếu phiếu nháp được coi là giữ hàng, kiểm tra cùng một quy tắc khả dụng khi lưu, có khóa và loại trừ phiếu đang sửa để không trừ hai lần; xử lý các nháp cũ đã giữ vượt tồn.

### A08 · P2 · Sắp xếp chỉ trong trang 50 dòng

Vị trí: `frontend/src/components/ExcelHeader.vue:17`, `components/DataTable.vue:24`, `lotus_farm/warehouse.py:280`.

Xác nhận bằng mã nguồn: AG Grid progressSort sắp xếp row-data đang tải; endpoint không nhận sort model và phân trang trước khi người dùng bấm sắp xếp. Lọc Excel đã áp dụng trên toàn bộ tập dữ liệu, nhưng sắp xếp chưa như vậy. Khi hơn 50 dòng, “Cần mua nhiều nhất” hoặc “Giá trị cao nhất” có thể bỏ sót vật tư ở trang sau.

Sửa: truyền sort model được whitelist lên máy chủ; sort sau lọc, trước phân trang, có khóa phụ ổn định.

### A09 · P2 · PDF tải xuống khác bố cục bản xem trước

Vị trí: `lotus_farm/www/lotus_stock_print.html:2`, `lotus_stock_print.py:download_pdf`.

Đã tải PDF thực tế của MAT-STE-2026-00002, trích xuất và render trang bằng pypdfium2. PDF có 1 trang, logo/chữ/số tiền đầy đủ nhưng **Số phiếu và Ngày bị dính**, các dòng **Tiền vật tư / Tổng giá trị và số tiền mất căn hai phía**. Phông đầu phiếu cũng khác trang HTML. Trang trình duyệt dùng CSS flex cho meta/totals; cần kiểm tra hỗ trợ CSS và font trong bộ tạo PDF, không chỉ kiểm tra file bắt đầu bằng `%PDF`.

Bằng chứng local: `C:\Users\ADMIN\Documents\ChatGPT\a\lotus-runtime\warehouse-audit-print.pdf` và `warehouse-audit-pdf-page.png`. Không đưa bản phiếu thực tế vào Git.

Sửa: dùng bố cục table/table-cell tương thích cho cả meta/totals, chọn font có sẵn hoặc nhúng font; render và so sánh browser/PDF. Thử thêm phiếu nhiều dòng sang trang, ghi chú dài và tên vật tư dài.

### A10 · P3 · Trạng thái trống của bảng nhu cầu bị mất trên điện thoại

Vị trí: `frontend/src/components/DataTable.vue:22–25`, `WarehousePlanning.vue:48`, `frontend/src/compact.css:249–250`.

Đã kiểm tra ở viewport **390 × 844**. Bảng nhu cầu dùng show-empty-headers; trạng thái trống chỉ nằm trong AG Grid, nhưng CSS điện thoại ẩn AG Grid. Danh sách mobile có 0 dòng, cao 0 px, không hiện “Chưa có nhu cầu vật tư đã duyệt…”. Trang không có alert/lỗi JavaScript nhưng nhìn như mất dữ liệu.

Sửa: render loading/empty/error độc lập với hai kiểu trình bày; không để thông báo chỉ tồn tại trong bảng desktop.

## Khoảng trống nghiệp vụ cần lập kế hoạch

Các mục này là phần chưa có trong Lotus, không tính vào 10 lỗi trên:

- **Chưa khép kín mua hàng:** đã có đề nghị mua và nhận theo đơn có sẵn, chưa có form tạo/duyệt Purchase Order và quản lý nhà cung cấp trong app kho. Có thể phải dùng ERPNext để tạo đơn mua.
- **Yêu cầu vật tư ngoài kế hoạch đã duyệt:** màn xuất chọn được nguồn Material Request có sẵn, nhưng app kho chưa có form đầy đủ để người dùng lập/duyệt nguồn yêu cầu cấp này.
- **Sửa sai sau ghi sổ:** chưa có luồng hủy/đảo phiếu, trả hàng/thu hồi ngay trong app kho. Hiện chỉ sửa/xóa nháp; tiêu hao/thu hồi của farm là luồng riêng.
- **Kiểm kê:** bản in chưa thể hiện sổ trước kiểm kê / thực đếm / chênh lệch / người kiểm đếm theo từng dòng.
- **Tài liệu chi phí:** chưa có đính kèm hóa đơn, chứng từ vận chuyển; nhập kho thủ công có giá/chi phí không tự tạo công nợ hay thanh toán nhà cung cấp. Cần giữ ranh giới này rõ trong giao diện quản trị chi phí.
- **Đủ hàng khi nhu cầu bằng 0:** hiện trạng thái có thể là Đủ hàng dù tồn 0, nghĩa là đủ so với nhu cầu đã duyệt bằng 0, không phải có hàng để xuất. Nên có chú thích hoặc hiển thị dấu “—” khi không có nhu cầu; cần giữ nhất quán với quy ước 3 trạng thái mà người dùng đã chọn.

## Phần đã kiểm tra đạt

- **80 test Python** đạt khi chạy Python ở chế độ UTF-8 (`python -X utf8 -m unittest discover -s tests`). Lệnh mặc định Windows có 2 lỗi đọc mã hóa trong test_schema; đây là vấn đề runner/test đọc file, không phải 2 lỗi nghiệp vụ.
- **21 test frontend** đạt.
- Integration chuẩn: nhu cầu kế hoạch, nguồn chưa gán kho, không cộng trùng kế hoạch/yêu cầu, cấp một phần, tiêu hao không trừ lại nhu cầu, thu hồi, giữ nháp, quy đổi PO/nhận mua, nhận một phần, chống nhận quá đơn, retry nhận hàng, giữ giá vốn kiểm kê thường, lịch sử tồn đầu/cuối, lọc kho, render các loại phiếu và tạo PDF: đạt.
- Kiểm tra tồn 0: chặn lưu xuất nháp và chặn ghi sổ nháp cũ; kiểm tra gộp nhiều dòng cùng vật tư và chuyển kho: đạt.
- Tài khoản Stock User có User Permission Warehouse A: **đọc, ghi, liệt kê, in và tải PDF của kho B đều bị chặn**. Guest bị chặn. User thử không gửi mail và được rollback.
- Rà mã: API ghi dùng POST/CSRF và quyền tài liệu native; các thao tác lưu/xóa danh mục có kiểm modified và kiểm liên kết, phiếu đã ghi sổ không được sửa/xóa qua console.
- Dữ liệu sau kiểm tra: **47 vật tư, 2 bản ghi Warehouse (gồm kho nhóm), 3 Stock Entry, 1 Stock Ledger Entry; 0 Material Request/PO/PR thực tế; 0 Bin âm; allow_negative_stock=0**. Mọi dữ liệu nghiệp vụ dựng thử đều rollback, không có commit dữ liệu thử.

## Bằng chứng tái hiện và giới hạn

Script native đã chạy, được lưu cùng repo:

- `tests/integration/audit_warehouse_edge_cases.py`: A01/A03/A04/A05/A06/A07, in kết quả quan sát, rollback ở finally. Đây là script tái hiện lỗi, không phải test xác nhận phần mềm đã hết lỗi.
- `tests/integration/audit_multiwarehouse.py`: A02, rollback ở finally.
- `tests/integration/audit_warehouse_permissions.py`: các ca quyền kho và Guest, rollback ở finally.
- `tests/integration/verify_warehouse_audit.py`, `verify_zero_stock.py`: luồng chuẩn và chặn thiếu tồn.

A08 được xác nhận bằng luồng phân trang/sort trong mã; A09 bằng PDF đã render; A10 bằng DOM/CSS ở viewport điện thoại. Chưa benchmark tải lớn, chưa thử tranh chấp đồng thời nhiều tiến trình với dữ liệu thật, chưa chứng nhận toàn bộ cấu hình vai trò/farm của doanh nghiệp. Lô/serial, hàng trả, kế toán công nợ và nghiệp vụ kho nâng cao ngoài form đơn giản cần audit riêng trước khi hỗ trợ đầy đủ.

Thứ tự sửa đề xuất: **A01–A06 → A07/A08 → A09/A10 → khép kín các luồng nghiệp vụ còn thiếu**. Sau mỗi nhóm phải thêm regression test cho đúng tình huống tái hiện và chạy lại kiểm tra native.
