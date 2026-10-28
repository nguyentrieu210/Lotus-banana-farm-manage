# Danh mục màu dây cắt bắp — ngày áp dụng

Mở **Dự thu → Danh mục màu dây** (đường dẫn `/lotus/mau-day`).
Chọn vườn ở thanh phía trên, xem màu đã dùng, ngày bắt đầu và ngày kết thúc.
Dòng đã lưu là chứng từ thật, không phải mặc định cho toàn bộ tương lai.

## Hai cách tạo lịch

1. **Lịch thủ công**: quản lý chọn màu và khoảng ngày không trùng kỳ đã có. Hệ thống tạo Bunch Tag mới; không sửa thẻ cũ. Ngày kết thúc không được trước ngày bắt đầu.
2. **Quy trình nguồn đã duyệt**: nếu vườn đã có Lotus Process Adoption, chỉ dùng chức năng **Tạo kỳ từ lịch đã duyệt**. Kỳ mới dùng hàm `generate_tags` sẵn có, giữ nguyên kỳ nguồn và phiên bản. Không chèn kỳ thủ công vào khoảng lịch đã duyệt.

Dữ liệu tham chiếu `lotus_farm/data/onedrive_protocol_v1.json` hiện gồm **17 màu**,
mỗi kỳ **5 ngày** theo lịch nguồn. Đây không phải xác nhận Lotus chỉ có 17 hay
phải áp dụng 5 ngày. Chưa được phép tự cắt xuống 12 màu hoặc đổi lịch nguồn.
Khi có danh sách 12 màu chính thức và ngày hiệu lực, cần cấu hình một phiên bản
lịch mới được duyệt (không sửa hồi tố chương trình đã phát hành).

## Kiểm soát dữ liệu

- Ngày bắt đầu / kết thúc là kỳ **cắt bắp**, không phải ngày thu.
- Cùng một vườn không được trùng kỳ hai màu trong lịch thủ công.
- Màu đã liên kết chứng từ cắt bắp không được sửa ngày/màu hoặc xóa.
- Kỳ đã dùng giữ liên kết Bunch Operation, không cập nhật ngược khi quay vòng màu.
- Xem và tạo phụ thuộc quyền Frappe + phạm vi vườn; không dùng giao diện để thay thế kiểm tra quyền ở máy chủ.
- Chưa tự đưa màu vào `Work Daily Journal` hoặc `ReportsWorkspace`; đó là bước nối nghiệp vụ riêng.

Kiểm tra thuần Python: `python -m unittest tests.test_bunch_tag_rules`. Nghiệm thu
thao tác tạo lịch trên site thử trước khi đưa lên live.
