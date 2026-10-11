# Nạp ranh Lotus Map vào ERPNext — chỉ bản nháp

Bộ dữ liệu do repo **Lotus Map** xuất qua `scripts/export_erp_geometry.py` gồm 64 lô chăm sóc, 205 mã thửa tưới và 209 liên kết theo bảng PDF 222 ha. File GeoJSON dùng tọa độ WGS84 **căn tạm theo ảnh vệ tinh**, chưa kiểm tra GPS ngoài thực địa.

## Quy trình an toàn

1. Trong ERPNext, chọn đúng **Farm**. Kiểm tra mã **Farm Block** tương ứng lô chăm sóc A1…E13 (đủ 64 lô), diện tích nguồn; mã **Farm Plot** nằm trong đúng Farm Block.
2. Với mã xuất hiện trong nhiều lô chăm sóc (A35, C17, C24, E7), cần người quản lý xác nhận phần ranh và danh mục riêng. E6 có ghi chú liên quan E5 dù bảng mã đang xếp ở E4; không tự giải quyết. Bản nhập **không tạo** các mã thiếu danh mục.
3. Tải JSON export lên ERPNext bằng **File riêng tư** (không đặt đường dẫn public).
4. Gọi:
   - `lotus_farm.map_import.preview_map_bundle(farm, file_url)` (GET/Desk). Trả về số ranh có thể tạo nháp, danh mục thiếu, diện tích lệch và 5 mã cần kiểm tra.
   - Sau khi kiểm tra, gọi POST `lotus_farm.map_import.stage_map_bundle` với `farm`, `file_url`, `acknowledge_unverified=1`. Chỉ tạo ranh **Draft** cho các mã hiện có và diện tích chênh không quá 30%; mọi ranh có `reason` nêu rõ nguồn PDF chưa xác minh.
5. Kiểm tra tận vườn. Chỉ người có quyền mới duyệt ranh đúng thực địa; không tự chuyển Draft sang Approved.

Kết quả: `Farm Block Geometry` lưu ranh lô chăm sóc theo phiên bản; `Plot Geometry` lưu ranh thửa theo phiên bản. Các bản `Approved` hiện có **không bị ghi đè**. Gửi lại cùng một GeoJSON thì bỏ qua nếu đã tồn tại hình giống hệt, không tạo phiên bản lặp.

## Điều kiện / giới hạn

- Không tự tạo `Farm Block`, `Farm Plot`, không đụng dữ liệu chấm công, kế hoạch việc, sản lượng, hoặc dữ liệu chu kỳ trồng.
- Mã thửa lặp chưa thể lưu vào mô hình `Farm Plot` một-cha-một-thửa khi chưa thống nhất quy tắc chia thửa. Phải xử lý nghiệp vụ trước khi nhập.
- Ranh nối tạm từ PDF chỉ dùng để đối chiếu, không tính diện tích nghiệm thu hay cảnh báo GPS thật.
- API mới được thêm ở **mã nguồn Frappe**, không đồng nghĩa máy chủ ERPNext đã chạy bản mới. Cần triển khai custom app và chạy migrate trên site trước khi dùng.
- Test không thay thế kiểm tra trực tiếp với dữ liệu thật trên Frappe site.
