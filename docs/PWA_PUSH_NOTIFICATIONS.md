# Thông báo đẩy PWA Lotus (17/10/2026)

## Đã triển khai
- Một chuông thông báo Vant 4 dùng chung cho Kho (`/warehouse`), Mua hàng (`/buying`), Công việc ngoài Vườn (`/work`).
- Mỗi app giữ Service Worker, manifest, icon và đăng ký push riêng; dùng cùng module `lotus_farm.push_notifications`.
- Cơ sở dữ liệu: `Lotus Push Device` (gắn user/app/endpoint) và `Lotus Mobile Alert` (user/app/phiếu/đã xem).
- Chỉ đăng ký khi người dùng nhấn **Bật thông báo đẩy** và cấp quyền trên thiết bị.
- HTTPS bắt buộc trên thiết bị thật. iOS yêu cầu PWA thêm vào màn hình chính, iOS 16.4+.
- Nhấn thông báo mở trang tương ứng; đơn mua và chứng từ kho mở chi tiết bằng mã phiếu.
- Đăng xuất gỡ đăng ký push của thiết bị đó; tài khoản khác trên cùng máy không tiếp tục nhận push từ tài khoản cũ.
- VAPID private PEM trên volume site: `sites/frontend/private/files/lotus-push-vapid.pem`; tạo một lần, không lưu vào Git. Nên thiết lập `lotus_push_contact` trong site config bằng địa chỉ mailto hợp lệ.

## Sự kiện nối với nghiệp vụ hiện có
- Mua hàng: đơn gửi duyệt -> người có vai trò duyệt, đơn được duyệt/từ chối -> người lập / người yêu cầu.
- Đề nghị mua: gửi duyệt -> vai trò duyệt mua.
- Nhận hàng theo đơn: phiếu nhập được xác nhận -> người lập đơn mua.
- Xuất/nhập/chuyển kho: phiếu được xác nhận -> vai trò kiểm tra kho.
- Kế hoạch công việc: khi xác nhận -> người được phân công qua ToDo của kế hoạch.
- Kết quả công việc: khi xác nhận -> người lập kế hoạch.

Tất cả thông báo chỉ tạo nếu người nhận có quyền đọc chứng từ. Một sự kiện được loại trùng theo người nhận và phiên bản chứng từ. Push xử lý qua hàng đợi `queue-short` (giúp thao tác tạo/duyệt phiếu không phải chờ dịch vụ push). Trường hợp mất đăng ký push, thông báo vẫn còn trong mục chuông.

**Chưa triển khai**: lịch tự động nhắc đơn gần đến hạn, công việc quá hạn, cảnh báo tồn dưới mức tối thiểu. Các cảnh báo định kỳ này cần thống nhất người nhận/ngưỡng để tránh spam.

## Triển khai Docker
- Build PWA: `cd frontend && npm run build`
- Image đang chạy: `lotus-pwa-vant4-push:v4-20261017`, `deployment/Dockerfile.vant4-push-v4` (kế thừa Vant 4 v3 và thêm backend Push).
- Docker compose: file gốc + `deployment/compose.vant4-mobile.override.yaml` + `deployment/compose.mobile-push.override.yaml`.
- Dịch vụ chạy v4: `backend`, `frontend`, `queue-short`, `queue-long`.
- Migration đã chạy cho site `frontend`, hai DocType đã tạo; VAPID: `bench --site frontend execute lotus_farm.push_notifications.setup_vapid` chỉ cần lần đầu.

## Kiểm tra trên điện thoại
1. Mở HTTPS của PWA, đăng nhập, cài vào màn hình chính (đặc biệt iPhone).
2. Bấm chuông ở header > **Bật thông báo đẩy** > **Cho phép**.
3. Chọn **Gửi thử**. Đóng PWA và xem thông báo hệ thống (có thể mất vài giây, tùy mạng).
4. Bấm thông báo để mở app, mở chuông để kiểm tra đã đọc.
5. Đăng xuất, thử xác nhận ứng dụng không tiếp tục nhận push ở tài khoản đã đăng xuất.

Trình duyệt/Android chưa được thử với một thiết bị đã cấp quyền ngay trong phiên làm việc triển khai. Chức năng gửi qua hệ thống push bên ngoài cần xác nhận bước 3 thực tế trước khi xem là nghiệm thu cuối.
