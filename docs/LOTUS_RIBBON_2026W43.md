# Lotus 222 – lịch màu dây 12 màu theo tuần

Nguồn: bảng màu người dùng gửi ngày 29/10/2026 (thay bảng ngày 28/10, chưa từng dùng).
Mỗi tuần ISO một màu, xoay vòng 12 tuần, bắt đầu tuần 43/2026 (thứ Hai 19/10/2026):

| Thứ tự | Màu | Tuần đầu |
|---|---|---|
| 1 | Đỏ | 43/2026 |
| 2 | Trắng | 44/2026 |
| 3 | Tím | 45/2026 |
| 4 | Cam | 46/2026 |
| 5 | Đen | 47/2026 |
| 6 | Xanh dương | 48/2026 |
| 7 | Đỏ – Xanh lá | 49/2026 |
| 8 | Trắng – Xanh lá | 50/2026 |
| 9 | Tím – Xanh lá | 51/2026 |
| 10 | Cam – Xanh lá | 52/2026 |
| 11 | Đen – Xanh lá | 53/2026 |
| 12 | Xanh lá – Xanh dương | 01/2027 |

Tuần 02/2027 quay lại Đỏ; lịch đã nạp đến hết tuần 52/2027.

- Ngoài vườn mỗi tuần buộc hai lần ("2 dây" rồi "1 dây") nhưng **cùng màu, cùng lứa**.
  Hệ thống vẫn lưu hai nửa tuần (thứ Hai–thứ Năm, thứ Sáu–Chủ nhật) vì Bunch Tag kiểm tra
  lịch Lotus theo nửa tuần; hai nửa có cùng mã màu.
- Màu dây gắn ở **cắt bắp**; chứng từ cắt bắp dùng màu đang hiệu lực tại ngày cắt.
- Lịch tham chiếu 17 màu / 5 ngày đã **xóa hẳn** ngày 29/10/2026 theo yêu cầu (440 thẻ, không thẻ nào
  có chứng từ; bản sao lưu nằm ngoài repo).
- Nạp lại: `bench --site <site> execute lotus_farm.lotus_weekly_ribbon_2026.apply` (chạy lại không tạo trùng;
  thẻ lịch tuần cũ không còn trong bảng bị xóa nếu chưa có chứng từ).
- Lịch thuần (`lotus_farm/ribbon_cycle.py`) có test `tests/test_ribbon_cycle.py`.
