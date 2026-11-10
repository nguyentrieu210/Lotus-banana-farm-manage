# Danh mục màu dây cắt bắp — ngày áp dụng

Mở **Việc hằng ngày → Thiết lập → Màu dây cắt bắp** (đường dẫn `/lotus/mau-day`).
Chọn vườn ở thanh phía trên, xem màu đã dùng, ngày bắt đầu và ngày kết thúc.
Dòng đã lưu là chứng từ thật, không phải mặc định cho toàn bộ tương lai.

## Hai cách có lịch

1. **Lịch Lotus theo tuần** (Vườn 222): mỗi tuần ISO một màu, xoay vòng 12 màu từ tuần 43/2026, lưu thành hai nửa tuần cùng màu (thứ Hai–thứ Năm, thứ Sáu–Chủ nhật). Bảng màu và cách nạp: [LOTUS_RIBBON_2026W43.md](LOTUS_RIBBON_2026W43.md); bảng màu nằm ở `lotus_farm/ribbon_cycle.py`. Vườn đã có lịch tuần thì không thêm kỳ thủ công.
2. **Lịch thủ công** (vườn chưa có lịch tuần): quản lý chọn một màu trong bảng 12 màu và khoảng ngày không trùng kỳ đã có. Hệ thống tạo Bunch Tag mới; không sửa thẻ cũ. Ngày kết thúc không được trước ngày bắt đầu.

## Kiểm soát dữ liệu

- Ngày bắt đầu / kết thúc là kỳ **cắt bắp**, không phải ngày thu.
- Cùng một vườn không được trùng kỳ hai màu.
- Màu đã có dòng sổ lô (`Lotus Work Entry`) không được sửa mã, màu, ngày hoặc xóa; muốn đổi thì tạo kỳ mới.
- Xem và tạo phụ thuộc quyền Frappe + phạm vi vườn; không dùng giao diện để thay thế kiểm tra quyền ở máy chủ.
- Báo cáo ngày tự gắn màu đang hiệu lực vào dòng cắt bắp.

Kiểm tra thuần Python: `python -m unittest tests.test_bunch_tag_rules tests.test_ribbon_cycle`. Nghiệm thu
thao tác tạo lịch trên site thử trước khi đưa lên live.
