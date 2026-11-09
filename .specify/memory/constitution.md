# Lotus Farm Constitution

Tổng hợp từ `AGENTS.md`, `docs/` và các quyết định của chủ vườn. Khi có mâu thuẫn, `AGENTS.md` là chuẩn cho giao diện.

## Core Principles

### I. Số thực, không suy diễn
Không tạo số liệu giả, không tự suy một con số từ nguồn không được duyệt. Số ước tính phải ghi rõ là ước tính và nêu nguồn. Thiếu dữ liệu thì cảnh báo, không điền thay.

### II. Một nguồn sự thật
Mỗi nghiệp vụ chỉ có một nơi nhập và một cách tính. Không chạy song song hai cách tính cho cùng một con số. Tính năng mới dùng lại mô hình dữ liệu và màn hình đã có trước khi tạo mới.

### III. Truy vết và kiểm soát
Số đã xác nhận chỉ sửa khi có lý do và giữ lịch sử. Tham số phải có phiên bản, ngày hiệu lực và người duyệt. Không bỏ qua bước duyệt hay ký trừ khi chủ vườn cho phép rõ ràng cho từng trường hợp.

### IV. Quy tắc tính tách riêng và có kiểm thử
Quy tắc nghiệp vụ nằm trong module thuần, không phụ thuộc framework, có unit test. Luồng ghi sổ có integration test. Component có hành vi có test mount.

### V. Giao diện theo chuẩn chung
Máy tính dùng primitive `components/ui`, `DataTable`, `WorkspaceModal`. Điện thoại dùng Vue 3, Vant 4 và các wrapper `LotusMobile*`. Màu lấy từ `lotus-tokens.css`. Bảng gọn, không thêm tiêu đề hay mô tả trang trí. Toàn bộ chữ hiển thị bằng tiếng Việt.

## Ràng buộc vận hành

- Thay đổi dữ liệu thật phải sao lưu trước, có thể chạy lại không ghi trùng, và ghi rõ nguồn.
- Nhập khẩu dữ liệu phải có xem trước và báo lỗi từng dòng.
- Thay đổi dữ liệu kế toán đi qua chứng từ, không sửa thẳng sổ.

## Quy trình phát triển

Làm trên nhánh riêng. Trước khi đưa lên VPS: unit test, test frontend và build phải qua, thử trên bản local. Chỉ commit, đẩy code hay triển khai khi chủ vườn yêu cầu.

## Governance

Tài liệu này áp dụng cho mọi đặc tả và kế hoạch trong `specs/`. Vi phạm phải được giải trình trong mục Complexity Tracking của kế hoạch. Sửa đổi nguyên tắc cần chủ vườn đồng ý.

**Version**: 1.0.0 | **Ratified**: 2026-11-09 | **Last Amended**: 2026-11-09
