# Lotus VIP 126 — hoàn thiện số cây A1–A13 và lịch suy ngược một vòng

## Dữ liệu thực nhập (nhưng chưa kiểm kê lại)

Người dùng cung cấp ảnh biển lô khu A ngày 18/10/2026:
- A1 = 6.830 cây; A2 = 8.568 cây; A3 = 8.060 cây; A4 = 8.743 cây.
- Người dùng xác nhận A12 = 10.148 cây.
- Tổng 5 lô bổ sung = **42.349 cây**.
- Cộng với Excel gốc A5–A11/A13 = 63.283 cây, toàn khu A **105.632 cây (13/13 lô)**.
- Toàn Vườn 222: 269.353 cây có nguồn, 35/64 lô; 29 lô C/D/E chưa có số cây.
- CSDL dùng `lotus_tree_count`, `lotus_tree_count_source`; dữ liệu đầu vào gốc `Lo_lon_lo_nho_va_so_cay_222.xlsx` không bị ghi đè. Biển lô là nguồn đọc được, chưa phải số lượng kiểm kê hiện tại.

## Suy ngược lịch với quy tắc mới
- Khu A dự kiến trổ đợt 1 01/11/2026. Trồng suy ngược **6 tháng lịch** = 01/05/2026. Khu B/C/D trồng lần lượt mỗi khu cách 1 tháng.
- A: trồng ước tính 01/05/2026; chọn chồi kiểm tra sau 90 ngày 30/07/2026; bắt đầu trổ 01/11/2026.
- B: 01/06/2026 → chọn chồi 30/08/2026 → trổ 01/12/2026.
- C: 01/07/2026 → chọn chồi 29/09/2026 → trổ 01/01/2027.
- D: 01/08/2026 → chọn chồi 30/10/2026 → trổ 01/02/2027.
- Khu E chưa có mốc thực tế hay mốc suy ngược được xác nhận. Chỉ có lịch giả lập trong chế độ thử nghiệm.
- Mỗi lô: trổ 20% tháng +6, 60% tháng +7, 20% tháng +8 tính từ trồng; cắt bắp sau trổ 17 ngày; thu sau cắt 60–70 ngày (cơ sở 65). Vụ đầu khu A sẽ thu cơ sở từ 22/01/2027 rồi thu tiếp hai đợt vào 21/02 và 24/03/2027.
- Chọn chồi sau trồng 90 ngày là lịch kiểm tra dự kiến. Khi ghi ngày chọn chồi thật, dự phóng tính trổ đợt đầu sau 6 tháng lịch từ ngày chọn chồi; *không* tự ghi thời điểm giả định thành quan sát thật.
- Phiếu Harvest Profile `HP-00002` (vẫn Draft, active=0) lưu hai hệ số ngày tham chiếu 266, nhưng lịch tính theo tháng lịch, không cộng 266 ngày cho mọi lô.

## Bảo toàn nguồn và nghiệp vụ
- Script riêng `lotus_farm.vip126_evidence.apply`: kiểm mã và diện tích, chặn ghi đè dữ liệu có giá trị xung đột, idempotent.
- Script `lotus_farm.vip126_zone_plan.apply_zone_estimates`: nâng cấp REVISION_TAG cũ sang 6 tháng, kiểm tra xung đột chỉnh tay, tạo trường `lotus_estimated_sucker_selection_date`, không ghi `planting_date`.
- `vip126_live.import_census` tránh import lại CSV cũ mà xóa số cây/ước tính mới; `forecast_import_preview.preview` hiển thị số từ Farm Block cùng nguồn.
- `vip126_trial.calendar` chỉ đọc, phân chia 20/60/20, không ghi dữ liệu mô phỏng vào DB hoặc kho; release bằng 0.
- Đây là mô hình một đợt chủ đạo/lô; để tính độc lập mẹ/chồi nhiều thế hệ chồng nhau cần thêm bảng cohort riêng trong tương lai.
