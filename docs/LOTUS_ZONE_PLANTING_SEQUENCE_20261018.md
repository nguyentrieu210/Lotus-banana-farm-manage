# Vườn 222 VIP 126 — thứ tự trồng A → B → C → D, mỗi khu cách 1 tháng

Quy tắc người quản lý xác nhận 18/10/2026: khu A trồng trước; khu B, C, D lần lượt trồng sau khu trước **một tháng lịch**. Khu E chưa được xác nhận thời điểm trồng.

## Cơ sở suy ngược
- Mốc trổ khu A **dự kiến** 01/11/2026 do người quản lý nêu.
- Mốc trồng A **suy ngược** 255 ngày trước = 19/02/2026, không có bằng chứng đã trồng hôm đó.
- Cộng theo tháng lịch, bảo toàn ngày 19:
  - A: trồng 19/02/2026, trổ dự kiến 01/11/2026, 13 lô.
  - B: trồng 19/03/2026, trổ dự kiến 01/12/2026, 12 lô.
  - C: trồng 19/04/2026, trổ dự kiến 01/01/2027, 14 lô.
  - D: trồng 19/05/2026, trổ dự kiến 01/02/2027, 12 lô.
  - E: 13 lô vẫn **không có** ngày trồng/trổ dự kiến lưu trong DB; thử nghiệm có thể dùng mốc giả lập.
- Mỗi vụ trổ trải 3 tháng 20% – 60% – 20% theo thiết lập thử nghiệm; mỗi đợt tự có ngày thu và chuỗi vụ chồi về sau.

## CSDL
- Đã áp dụng cho **51 Farm Block** A-D, bằng trường hiện có `lotus_inferred_planting_date` và `lotus_estimated_flowering_date`.
- `lotus_estimation_basis` ghi nguồn/độ tin cậy, revision key `LOTUS-ZONE-SEQUENCE-20261018`. Hàm `lotus_farm.vip126_zone_plan.apply_zone_estimates` là idempotent, kiểm tra mã và diện tích đối chiếu với 64 mã Excel.
- Không chạm `planting_date` (ngày thực tế), `planting_density`, `Crop Cycle`, `Planting Event`, phiếu thực tế, kho, bán và duyệt.
- 30 lô có đếm cây từ Excel, 34 lô thiếu chỉ giả lập số cây trong API thử nghiệm; dữ liệu Excel private, không nằm trên GitHub.
- API chỉ đọc `lotus_farm.vip126_zone_plan.status` cần quyền Farm Block và Harvest Forecast, tuân theo `land_filters`/`land_scope`, hiển thị bảng tiến độ đã lưu theo khu.
- `vip126_trial.calendar` ưu tiên mốc cây/sự kiện đã ghi nhận; nếu chưa có dùng ngày trồng suy ngược + trổ dự kiến lưu theo khu; riêng E dùng ngày trổ giả lập **không ghi DB**. Quy tắc 20-60-20 và 36 tháng không đổi.

## Đã kiểm chứng
- 64 lô tồn tại, trong đó 51 lô được lưu lịch A-D, 13 lô E chưa lưu, đúng phân bổ 13/12/14/12/13.
- Chạy lại migration không cập nhật thêm (idempotent).
- Lô B1 dự phóng trổ 12/2026–02/2027 theo 20/60/20 và thu dự kiến 23/02, 26/03, 26/04/2027 trong kịch bản cơ sở.
- Kế hoạch chỉ thử nghiệm; hệ số kg/buồng, tỷ lệ buồng và nhịp chồi chưa có kiểm chứng tại Lotus. Sản lượng được phép cam kết bán = 0.
