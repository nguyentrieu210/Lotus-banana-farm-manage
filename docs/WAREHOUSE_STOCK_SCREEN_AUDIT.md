# Audit và dựng lại màn Tồn kho Lotus — 15/10/2026

## Phạm vi
Audit dữ liệu thực site `frontend`, API Tồn kho, filter/Excel Header, tìm kiếm, kỳ nhu cầu, thống kê, phân trang Tồn kho/Phiếu/Lịch sử, trạng thái rỗng, quyền hiển thị giá vốn; smoke test API Mua hàng và quy trình phiếu nhập vật tư. Không tạo hoặc xóa dữ liệu kho thật.

## Kết quả xác minh trước sửa
- Cùng công ty Lotus Agritech có **4 kho hoạt động**, **55 Item có tồn kho**, **8 Item có tổng tồn thực tế dương**; có **12 chứng từ lịch sử** và **12 dòng sổ kho** được trả về dưới quyền kiểm thử.
- Hai bộ lọc đồng thời `stock_status = Dưới tối thiểu` và `coverage_status in (Cần mua, Chờ nhập)` trả **0 kết quả**, mặc dù Item và Bin còn đầy đủ. Đây là kết quả lọc, không phải mất dữ liệu.
- Giao diện dùng `total_count` và `stocked_count` sau lọc để hiển thị KPI khiến thành 0 vật tư, 0 có tồn. Khi bảng không có dòng, banner “Bắt đầu cho farm mới” bị hiển thị sai.
- ExcelHeader “chọn tất cả” vẫn ghi một bộ lọc đang bật; hai nút lọc nhanh có thể chồng điều kiện không mong muốn.
- Tìm kiếm sử dụng ngay giá trị người dùng đang gõ khi kích hoạt một thao tác tải lại khác; không phân biệt bản nháp tìm kiếm với từ khóa đã áp dụng.
- Lịch sử chứng từ và biến động kho dùng chung biến phân trang `movementStart`.
- Kỳ nhu cầu mặc định chỉ có ngày hiện tại, dễ hiểu lầm các cột thiếu hàng là luôn đầy đủ cho tuần.
- API danh sách vẫn trả `stock_value`, `valuation_rate` và sổ biến động `stock_value_difference` dù UI đã ẩn cột.

## Thiết kế đã thực hiện
| Vấn đề | Thay đổi |
|---|---|
| KPI sai sau khi lọc | API trả `catalogue_count`, `stocked_count` độc lập với tìm kiếm và filter; `total_count` dành riêng kết quả hiện tại |
| 0 kết quả ≠ 0 dữ liệu | Các trạng thái riêng: chưa chọn công ty, chưa có kho, chưa có Item, không khớp bộ lọc, đang tải, có kết quả |
| Bỏ lọc khó | Hiện chip từng cột và điều kiện tìm kiếm/kho; xóa từng chip hoặc xóa toàn bộ; giữ đầu cột khi lọc ra 0 dòng |
| ExcelHeader | Chọn tất cả = không áp bộ lọc. Bỏ lựa chọn cột không tác động cột khác |
| Nút lọc nhanh | Dưới tối thiểu và Thiếu theo nhu cầu là hai nút bật/tắt, chuyển nhóm nhanh không giữ trạng thái nhanh xung đột |
| Tìm kiếm | Nội dung gõ (draft) và tìm kiếm đã gửi tách nhau; nhấn Tìm hoặc Enter mới áp dụng |
| Kỳ nhu cầu | 7 ngày mặc định; chọn Hôm nay / 7 ngày / 30 ngày; ghi rõ tác động cột nhu cầu và mua hàng, không làm biến mất tồn kho |
| Phân trang | Sổ nhập–xuất và danh sách chứng từ có trạng thái phân trang độc lập; dòng hiển thị `từ–đến / tổng` |
| Quyền về giá | API tổng quan và lịch sử kho không gửi giá vốn/giá trị biến động. API phiếu nhập và hạch toán nội bộ giữ đơn giá hợp lệ |
| Tải lại thất bại | Không xóa dữ liệu cuối đã xác thực; báo lỗi; khoảng ngày không hợp lệ không ghi đè bảng |

**Nguyên tắc:** Không thay đổi dữ liệu Item, Bin, Stock Entry, Purchase Order hoặc Stock Ledger. Các ngưỡng tồn tối thiểu và công thức quy đổi UOM từ PR #15 được giữ nguyên.

## UAT / kiểm chứng
- Frontend: `npm test`, `npm run build`; bộ test `frontend/tests/stock-filter-overhaul.test.js`.
- Site thực `frontend`: `tests/integration/verify_stock_overhaul.py` kiểm tra 4 kho, 55 Item, 8 có tồn, phân trang 50+5, lọc hai điều kiện ra 0 nhưng giữ KPI, tìm kiếm không khớp, xem một kho, API chứng từ và lịch sử, không gửi dữ liệu giá vốn.
- `tests/integration/verify_item_uom_global.py`: tạo vật tư giả, nhập 4.000 Bao × 25 kg, ghi sổ 100.000 kg đúng và rollback.
- Mua hàng & nhu cầu vật tư: API `warehouse_planning.overview` trả schema hợp lệ; thời điểm kiểm tra không có dòng nhu cầu được duyệt và không báo thiếu quyền/dữ liệu.
- Site `frontend` đã được sao lưu trước khi thay image Docker.
- Docker `localhost:8080` phục vụ tài nguyên mới HTTP 200.

## Giới hạn / theo dõi
- Bộ lọc chỉ áp dụng trong phiên màn hình; chưa có lưu bộ lọc cá nhân theo tài khoản.
- Các cột số trong Excel Header vẫn lọc theo giá trị chính xác; có thể bổ sung lọc khoảng số nếu nghiệp vụ yêu cầu.
- Vite cảnh báo bundle DataTable/AG Grid lớn và Tailwind utility mơ hồ tồn tại từ trước, không cản build nhưng nên tách chunk trong sprint tối ưu tiếp theo.
- Đợt này sửa luồng tổng quan Kho và shared Excel Header, **không tuyên bố viết lại toàn bộ chức năng mua hàng, kế toán, kho vận**. Các luồng đó chỉ smoke/regression test để tránh phá vỡ.
- UI đã build và API tích hợp chạy, kiểm thử tương tác thủ công bằng phiên nhân viên ở trình duyệt vẫn nên nghiệm thu tại farm.

## Triển khai
Dockerfile: `deployment/Dockerfile.stock-audit` kế thừa image `lotus-stock-uom-vietnamese:20261015`; copy frontend và backend `warehouse.py`. Không có migration schema.
