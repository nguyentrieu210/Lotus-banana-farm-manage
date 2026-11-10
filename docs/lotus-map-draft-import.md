# Nạp ranh Lotus Map vào ERPNext — chỉ bản nháp

Bộ dữ liệu do repo **Lotus Map** xuất qua `scripts/export_erp_geometry.py` gồm 64 lô chăm sóc (215,16 ha theo bảng PDF 222 ha) kèm 205 mã thửa tưới. File GeoJSON dùng tọa độ WGS84 **căn tạm theo ảnh vệ tinh**, chưa kiểm tra GPS ngoài thực địa. Lô là đơn vị nhỏ nhất của vườn: chỉ ranh lô được nhập; mã thửa tưới trong gói chỉ được kiểm tra cho đúng định dạng.

## Quy trình an toàn

1. Trong ERPNext, chọn đúng **Farm**. Kiểm tra mã **Farm Block** của các lô chăm sóc A1…E13 (đủ 64 lô) và diện tích nguồn.
2. Tải JSON export lên ERPNext bằng **File riêng tư** (không đặt đường dẫn public).
3. Gọi:
   - `lotus_farm.map_import.preview_map_bundle(farm, file_url)` (GET/Desk). Trả về số lô trong gói (`care_blocks_in_source`), số ranh lô tạo được (`ready_block_geometries`), mã lô chưa có trong danh mục (`missing_block_masters`) và lô có diện tích lệch quá 30% (`area_conflicts`).
   - Sau khi kiểm tra, gọi POST `lotus_farm.map_import.stage_map_bundle` với `farm`, `file_url`, `acknowledge_unverified=1`. Chỉ tạo ranh **Draft** cho mã lô đã có và diện tích chênh không quá 30%; mọi ranh có `reason` nêu rõ nguồn PDF chưa xác minh.
4. Kiểm tra tận vườn. Chỉ người có quyền mới duyệt ranh đúng thực địa; không tự chuyển Draft sang Approved.

Kết quả: `Farm Block Geometry` lưu ranh lô theo phiên bản. Các bản `Approved` hiện có **không bị ghi đè**. Gửi lại cùng một GeoJSON thì bỏ qua nếu đã có hình giống hệt (`already_present`), không tạo phiên bản lặp.

## Điều kiện / giới hạn

- Cần vai trò Lotus Farm Manager và quyền đọc vườn.
- Không tự tạo hay sửa `Farm Block`, không đụng sổ lô, chấm công hay sản lượng. Mã lô chưa có trong danh mục chỉ được liệt kê để người quản lý tạo trước.
- Ranh nối tạm từ PDF chỉ dùng để đối chiếu, không tính diện tích nghiệm thu hay cảnh báo GPS thật.
- API mới được thêm ở **mã nguồn Frappe**, không đồng nghĩa máy chủ ERPNext đã chạy bản mới. Cần triển khai custom app và chạy migrate trên site trước khi dùng.
- Test không thay thế kiểm tra trực tiếp với dữ liệu thật trên Frappe site.
