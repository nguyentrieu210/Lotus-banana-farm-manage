# Bản đồ chăm sóc và Tổng quan

- Nguồn LOTUS-222: `nguyentrieu210/lotus-map`, commit `404f43a`,
  `v2/data/farms/farm222/care.geojson`, sinh từ KML chuẩn của repo Map.
- Bản chụp nguồn: `data/farm222-care-boundaries.geojson`, SHA256
  `ebbf822b555e0672787931bd8fb4b07f2564ab1a0aeacadcfb2494965a0b76ed`.
- 64 mã lô, 65 polygon (D2 có hai phần); giữ nguyên mọi tọa độ và diện tích nguồn.
- `tools/import_care_map.py` xem trước mặc định. `--commit` sao lưu tất cả ranh
  bị tác động ra file JSON trước khi thay 64 ranh chăm sóc nháp và xóa 200 ranh
  thửa nháp của LOTUS-222. Không xóa danh mục thửa hay các chứng từ lịch sử.
  Dừng nếu có ranh đã duyệt; không tự duyệt dữ liệu nhập.
- Bản đồ dùng `field.map_block_data(..., include_draft=1)`; nhãn nêu rõ ranh nháp.
  Lớp khu là hợp hình học các lô trong khu, không phải ranh khảo sát độc lập.
- Ảnh XYZ flycam dùng trực tiếp máy chủ Map, cùng phép căn hiển thị trong
  `v2/data/imagery.json`. Không thay tọa độ KML. Ngoài vùng ảnh có nền vệ tinh.
- Bộ lọc dùng Vườn → Khu → Lô chăm sóc. Backend kiểm tra lô thuộc khu và
  áp dụng danh sách lô vào công việc, báo cáo, dự thu và danh sách chứng từ.
  Các số liệu công ty chưa phân bổ xuống khu/lô hiển thị giới hạn thay vì
  đưa tổng công ty vào kết quả khu. Dữ liệu thửa cũ chỉ giữ để truy nguyên.
- `/lotus/reports` là Tổng quan duy nhất; `/lotus/mobile` chuyển về đây cho
  người có quyền Tổng quan, còn giữ trang chức năng cho tài khoản hiện trường.
  `/lotus/today` chuyển về Tổng quan. Mỗi phần báo cáo tôn trọng quyền đọc.
- Đăng nhập `/login` dùng shell Lotus mới, kế thừa toàn bộ xác thực, MFA,
  khôi phục mật khẩu và SSO của Frappe. Không có API xác thực riêng.
- Mọi modal desktop dùng WorkspaceModal; bộ quét camera và tìm nhanh dùng
  chế độ bare của cùng component. Màn điện thoại tiếp tục dùng wrapper Vant.

Kiểm tra: `npm --prefix frontend test`, `npm --prefix frontend run build`,
và `tools/verify_care_scope.py` trong bench/site (chỉ đọc).
