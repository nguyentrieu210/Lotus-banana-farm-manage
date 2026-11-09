# Quickstart: kiểm chứng tính năng

Chạy trên bản local (cổng 8097, Vite 5173), dữ liệu thử. Tham khảo [contracts/api.md](contracts/api.md) và [data-model.md](data-model.md).

## Chuẩn bị

1. Build bản local bằng `rebuild-local.cmd` (có migrate).
2. Chạy `bunch_setup` để có danh mục lý do loại buồng.

## Kịch bản

| # | Làm | Kết quả mong đợi |
|---|---|---|
| 2 | Nhập sổ cắt bắp, xem trước | 593 buồng, lô A1 đến A13: Đỏ 113, Trắng 182, Tím 298 |
| 3 | Nhập lần hai cùng file | Không tăng số |
| 4 | Tổ nhập cắt bắp 120 buồng ở lô A5, chưa xác nhận | Dự thu chính thức chưa đổi; hiện ở phần chưa xác nhận |
| 5 | Đội trưởng xác nhận ngày | Có dòng trong sổ buồng; dự thu thêm 120 buồng ở cửa sổ 60 đến 70 ngày |
| 6 | Nhập bao buồng vượt số đã cắt | Bị chặn |
| 7 | Loại 5 buồng màu đó | Dự thu giảm tương ứng |
| 8 | Lô chỉ có chích bắp | Dự thu tầng "khá", không tính trùng phần theo số cây |
| 8b | Tổ báo chọn chồi 2 ha của lô 4 ha, 8.000 cây | Vụ sau có mốc thật cho khoảng 4.000 chồi, ghi là ước tính |
| 9 | Bấm một số trên màn dự thu | Thấy các dòng sổ buồng gốc và bộ tham số |
| 10 | Thu hoạch một màu rồi xem sai số | Thấy tỷ lệ thu, kg/buồng, số ngày thực tế |
| 11 | Đề xuất tham số | Chưa áp dụng cho tới khi duyệt |

## Kiểm thử

- `cd frontend && node --test tests/*.test.js`
- Unit test `bunch_flow_rules` và `bunch_forecast_engine`
- `tests/integration/verify_bunch_forecast.py` qua bench
- Tổng kiểm: tổng buồng dự thu không vượt số buồng tính theo số cây của từng lô
