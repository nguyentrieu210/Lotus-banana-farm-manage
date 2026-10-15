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

## Bổ sung nghiệm thu: popup, Can, thao tác nhanh và thứ tự cột

- Popup Excel neo **sang bên phải** nút lọc (khoảng cách 8px), tự giới hạn trong khung nhìn khi cột ở gần cạnh phải hoặc trên di động.
- UOM chuẩn **Can** được tạo idempotent qua `lotus_farm.warehouse_masters.install_fields` cùng với Bao. Can dùng được làm **đơn vị tồn kho gốc** hoặc **đơn vị phụ** cho từng Item; hệ số quy đổi vẫn khai báo trên Item.uoms, không hardcode quy cách của Can.
- Trên bảng tồn kho có bốn nút nhanh: **Nhập kho / Xuất kho / Chuyển kho / Kiểm kê kho**. Các nút gọi form chuẩn đã tồn tại, chỉ hiện khi quyền `Stock Entry` hoặc `Stock Reconciliation` cho phép. Không lập phiếu ngoài luồng duyệt.
- Cột theo trình tự: **Tên hàng, Nhóm hàng, ĐVT, Tồn kho, Tồn quy đổi, Tối thiểu chung, Thiếu tối thiểu, Cảnh báo tồn, Cần dùng, Có thể dùng, Thiếu theo nhu cầu, Sắp về, Cần mua, Tình trạng nhu cầu**.
- Thay đổi trên là cách **trình bày**, không thay ý nghĩa các trường `actual_qty`, `minimum_stock`, `demand_qty`, `incoming_qty`, `to_buy_qty`.
- Frontend 58/58 test đạt và Vite build thành công. Integration Frappe `tests/integration/verify_can_stock_uom.py` tạo thử Item với `stock_uom='Can'`, mức tồn tối thiểu chung, rồi rollback. `tests/integration/verify_stock_overhaul.py` xác minh 4 kho / 55 Item / 8 có tồn.
- Đã backup site `frontend` trước khi tạo UOM Can và triển khai image `lotus-stock-quick:20261015` cho **cả backend/frontend**; đã xác nhận đúng JS bundle, HTTP 200 trên 8080.
