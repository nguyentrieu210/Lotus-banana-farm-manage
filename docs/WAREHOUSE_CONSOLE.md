# Quản lý kho Lotus

Mở `/lotus/kho` sau khi đăng nhập. Các thao tác kho diễn ra trong Lotus, không chuyển sang giao diện quản trị ERPNext.

## Danh mục

- Thêm nhóm vật tư: tên nhóm và nhóm cha (mặc định nhóm gốc).
- Thêm vật tư: mã, tên, nhóm, đơn vị tính; ghi chú không bắt buộc. Có thể tạo nhóm mới ngay trong form vật tư.
- Thêm kho: tên kho, nhóm kho cha và công ty đang chọn. Danh mục mới không tự sinh tồn kho.

Máy chủ chỉ nhận các trường được hỗ trợ, kiểm quyền create/read của người dùng và kiểm kho cha thuộc công ty. Dữ liệu được lưu vào Item, Item Group và Warehouse chuẩn.

## Phiếu và tồn

Danh sách vật tư hiển thị 50 dòng mỗi trang, gồm vật tư có tồn bằng 0. Các chỉ số vật tư chỉ tính trang đang xem. Tồn được tổng hợp trong các kho được phân quyền, theo đơn vị tồn kho của từng vật tư.

Nhập, xuất dùng, chuyển kho tạo Stock Entry nháp. Kiểm kê tạo Stock Reconciliation nháp, chọn kiểm kê định kỳ hoặc tồn đầu kỳ. Số kiểm kê là số thực đếm, không phải chênh lệch. Giao diện không yêu cầu nhập đơn giá; định giá do hệ thống xử lý theo số đang có.

Bấm mã phiếu để xem chi tiết ngay trong Lotus. Người có quyền submit xác nhận đã kiểm tra rồi bấm Ghi sổ phiếu; máy chủ chạy submit chuẩn cùng các validation, sổ kho và kế toán của ERPNext. Chỉ các phiếu nhập, xuất, chuyển, kiểm kê thông thường được ghi sổ qua màn hình này. Phiếu đóng gói, có lô/serial và nghiệp vụ nâng cao chỉ xem, không được ghi sổ qua form đơn giản. Không ghi trực tiếp Bin, Stock Ledger Entry hoặc GL Entry.

Phiếu gần đây gồm 20 Stock Entry và 10 Stock Reconciliation của công ty, độc lập với bộ lọc kho. Chưa hỗ trợ sửa hoặc hủy phiếu tại đây.

Cần quyền đọc Company, Warehouse, Item, Bin và Stock Entry; danh mục chọn cần quyền đọc Item Group/UOM. Tạo danh mục và phiếu cần quyền create; ghi sổ cần quyền submit của loại tài liệu. Công ty dùng nhiều farm cần cấp User Permission trên Warehouse; không tự suy ra kho từ Farm.

Build: `npm ci --prefix frontend && npm run --prefix frontend build`, triển khai lại app và khởi động dịch vụ Python. Các Custom Field nguồn xuất, người nhận và khu vực/lô được cài qua warehouse_issue.install_fields hoặc migrate.

Kiểm tra: `python -m unittest discover -s tests -p test_warehouse_guards.py`; `node --test frontend/tests/*.test.js`. Kiểm tra tích hợp trên site local bằng dữ liệu tạm, rollback sau khi tạo danh mục và ghi sổ phiếu nhập.

## Ba tab xuất kho

Form Xuất dùng có Thủ công, Theo kế hoạch đã duyệt, Theo yêu cầu đã duyệt.

- Thủ công: nhập vật tư, số lượng, người nhận, lý do và khu vực/lô trên từng dòng. Cùng vật tư dùng cho nhiều lô thì tách dòng.
- Kế hoạch: Daily Work Plan đã nộp (docstatus=1), lấy Material Requirement đã nộp của kế hoạch. Kế hoạch chưa có nhu cầu vật tư đã duyệt thì chưa có dòng để xuất. Không tự suy ra lượng từ một kế hoạch thiếu định mức.
- Yêu cầu: Material Request loại Material Issue đã nộp, không đóng/dừng/hủy. Phiếu này có thể độc lập kế hoạch; không lấy đề nghị mua hay chuyển kho. Đây là phiếu yêu cầu cấp chuẩn, khác với Material Requirement liên kết định mức của kế hoạch.

Số lượng nguồn được đổi sang đơn vị tồn kho; phần còn cấp trừ các dòng Stock Entry nháp và đã nộp, bỏ phiếu đã hủy. Lưu nháp giữ phần cấp, ghi sổ mới trừ tồn. Máy chủ khóa nguồn và kiểm lại item, công ty, trạng thái, dòng nguồn, khu vực và giới hạn khi lưu/ghi sổ. Chỉ phần có qty>0 trong form được đưa vào phiếu.

Không yêu cầu người kho nhập đơn giá. Hệ thống giữ giá trị định giá đang có theo kho/mặt hàng; nếu chưa có giá trị thì dùng khả năng định giá bằng 0 của ERPNext, không tự tạo giá giả. Các trường giá trị không hiển thị trong màn hình kho đơn giản.

Triển khai cần chạy `bench --site <site> execute lotus_farm.warehouse_issue.install_fields` hoặc migrate để tạo các Custom Field liên kết nguồn, người nhận và khu vực sử dụng. Hook validate/before_submit giữ giới hạn nguồn. Nguồn đã nộp là mốc đã duyệt trong luồng hiện tại; nếu cấu hình Workflow riêng thì vẫn phải hoàn tất submit trước khi cấp kho.
