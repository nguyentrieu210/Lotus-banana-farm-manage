# Lotus Kho — Lọc bảng kiểu Excel và giao diện tối giản

## Đã triển khai

- **Lọc từng cột kiểu Excel:** menu ở ngoài vùng AG Grid không bị cắt, ô tìm kiếm không dấu, chọn/bỏ nhiều giá trị, Chọn tất cả kết quả chỉ tác động danh sách đang tìm, trạng thái chọn một phần, Áp dụng và Xóa lọc.
- **Lọc kết hợp đúng logic:** backend cung cấp lựa chọn theo các bộ lọc của những cột khác. Nhiều giá trị cùng cột theo OR; các cột khác nhau theo AND. Các giá trị đã chọn vẫn tồn tại trong danh sách để có thể gỡ.
- **Đường phân cách cột:** có viền dọc cho header và ô dữ liệu, viền ngang cho dòng, bộ lọc nổi bật hơn.
- **Tìm kiếm tức thì:** ô tìm nằm bên trái, tự tra sau khi ngừng gõ 220 ms; không cần Enter.
- **Ẩn bộ lọc Công ty khi một công ty:** trên màn Kho, Nhân sự, Chấm công và Điều hành. Phạm vi Company thực vẫn gửi cho backend và được kiểm tra quyền. Khi có nhiều công ty được cấp quyền, vẫn phải cho chọn.
- **Vườn:** mọi nhãn Nông trường trong Vue/JS chuyển thành Vườn; nhãn từ schema Frappe và đầu cột động cũng chuyển khi render. Không thay fieldname farm, DocType Farm hay quyền truy cập.

## Kiểm thử và vận hành

- npm test: 54/54 đạt. Vite build production thành công.
- tests/integration/verify_excel_stock_filters.py: kiểm tra lọc đa lựa chọn, phối hợp hai cột và điều kiện không có kết quả.
- tests/integration/verify_stock_overhaul.py: 4 kho / 55 vật tư / 8 có tồn; phân trang, lịch sử và danh mục giữ nguyên, không trả giá vốn qua list API.
- Backup site frontend trước triển khai. Không thay dữ liệu vật tư, tồn kho, phiếu hay nhân sự.
- Hai container lotus-backend-1 và lotus-frontend-1 phải chạy cùng image/tag; backend chọn Vite manifest, frontend phục vụ bundle qua Nginx. Phải kiểm tra lại bundle đang được route trỏ tới.
- Unit và API integration không thay thế hoàn toàn nghiệm thu click trong trình duyệt đã đăng nhập.

## Bố cục thanh lọc sau nghiệm thu

- Bộ chọn **Kho** ở đầu hàng bên trái; không hiển thị chọn Công ty khi chỉ có một công ty được phép truy cập.
- Ô tìm vật tư đặt **cuối hàng bên phải**, rộng khoảng **180 px** trên desktop, tự co trên màn nhỏ; gõ để lọc sau 220 ms, không có nút Tìm.
- **Bỏ lọc** chỉ hiện khi có điều kiện; bảng nằm ngay dưới thanh lọc, không có dashboard bổ sung.
- Kiểm thử vị trí trên giao diện bằng `frontend/tests/excel-filter-ux.test.js` và xác minh backend/frontend cùng dùng bundle `stock-Bmy_D6WZ.js` trên localhost:8080.
