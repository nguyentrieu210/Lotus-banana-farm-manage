# Lotus Kho — Audit nhất quán giao diện các tab

## Chuẩn giao diện từ tab Tồn kho

Thanh chọn Kho, tìm kiếm tức thì, Bỏ lọc theo tab, bảng AG Grid có đầu cột Excel, đường phân cách cột, phân trang gọn và trạng thái rỗng dễ hiểu. Giữ quyền người dùng và các nút nhập/xuất/chuyển/kiểm kê.

## Các màn đã rà và sửa

- Phiếu nhập–xuất: ngày lọc trong cùng thanh Kho/Tìm, Bỏ lọc chỉ tác động tab hiện tại, bảng luôn có tiêu đề, các cột Ngày – Số phiếu – Loại phiếu – Kho liên quan – Trạng thái. Thêm nút tạo phiếu nhanh.
- Lịch sử nhập xuất: bỏ thanh lọc ngày riêng, tích hợp cùng thanh trên, bảng có lọc Excel cả khi không kết quả; Tồn trước/Tồn sau thể hiện đúng số trước/sau từng giao dịch; ngày hiển thị dd/MM/yyyy.
- Nhu cầu & mua hàng: ngày lọc gọn, tìm ngay khi gõ, Bỏ lọc, bảng nhu cầu lọc theo cột với lựa chọn faceted, hai bảng Đề nghị mua và Hàng chờ về cũng có tìm kiếm và lọc Excel; đơn vị tính dùng nhãn tiếng Việt chung.
- Thiết lập kho: thay thẻ hướng dẫn dài bằng ba nút Thêm nhóm hàng / Thêm vật tư / Thêm kho; bên dưới là hai bảng Nhóm hàng và Danh sách kho.
- Phiếu nhập, xuất, chuyển, kiểm kê: thêm hướng dẫn đơn giản và nhóm Hàng hóa trên phiếu, cải thiện trình bày, cuộn form và responsive; giữ nguyên yêu cầu dữ liệu, quyền và xử lý lưu/duyệt.

## Không thay đổi

Không chỉnh thông tin Item, Bin, Warehouse, Stock Ledger, Stock Entry, Purchase Order, Material Request. Backend chỉ chỉnh danh sách lựa chọn bộ lọc Excel ở API warehouse_planning.overview, không can thiệp phép tính nhu cầu, giá vốn hay phiếu nhận hàng. Các thay đổi chỉ nhằm thống nhất phần nhìn và bộ lọc.

## Kiểm tra

- Frontend test và Vite production build.
- API integration: tests/integration/verify_warehouse_ui_tabs.py và bài kiểm thử Kho hiện có.
- Cả backend/frontend phải chạy cùng Docker image để trang Frappe lấy đúng Vite manifest.
- E2E tương tác bằng tài khoản người vận hành vẫn cần xác nhận trên trình duyệt thực tế.
