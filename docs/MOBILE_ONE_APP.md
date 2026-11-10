# Một app mobile chung theo quyền — Lotus Farm

## Mục tiêu

Mở **`/lotus/mobile`** trên điện thoại. Mỗi người đăng nhập bằng **tài khoản Frappe hiện có**, không cần tải một app riêng cho từng chức danh. Tài khoản kiêm nhiều nhiệm vụ thấy tổng hợp các mục được cấp quyền.

## Các mục trên trang chủ

Danh sách khai báo ở `frontend/src/mobile-menu.js`; mỗi mục chỉ hiện khi tài khoản có đúng quyền:

| Nhóm | Mục | Mở | Điều kiện |
| --- | --- | --- | --- |
| Quản trị | Người dùng & phân quyền | `/lotus/nguoi-dung` | System Manager được đọc User |
| Nhân sự và chấm công | Hồ sơ nhân sự, Chấm công | `/lotus/nhan-su`, `/lotus/cham-cong` | vai trò HR / quyền đọc chấm công |
| Công việc ngoài Vườn | Việc hôm nay | `/work` | tổ trưởng, đội trưởng, kỹ thuật, quản lý vườn có vườn được cấp |
| Công việc ngoài Vườn | Bản đồ lô | `/lotus/map` | quyền đọc Farm Block Geometry |
| Xưởng và vật tư | Quản lý kho | `/lotus/kho` | quyền đọc kho, vật tư, tồn và phiếu kho |
| Xưởng và vật tư | Xưởng đóng gói | `/lotus/cong-viec?field_view=packhouse` | quyền mở ca đóng gói |
| Điều hành và báo cáo | Vườn, Dự thu | `/lotus/farms`, `/lotus/forecast` | quyền đọc Farm / bộ thông số dự thu |
| Điều hành và báo cáo | Báo cáo | `/lotus/reports` | Lotus Farm Manager, Lotus Auditor |

Thanh điều hướng dưới màn hình có **Trang chủ** và tối đa ba mục trong Vườn, Bản đồ lô, Dự thu, Báo cáo mà tài khoản mở được.

## Luồng vận hành

1. Nhân viên đăng nhập Lotus bằng tài khoản ERPNext/Frappe.
2. Máy chủ trả về `lotus_farm.console.bootstrap`: các vườn được xem, các nhóm màn hình theo quyền đọc DocType (`modules`) và các quyền nghiệp vụ (`capabilities`).
3. Trang chủ tự tạo các nút theo **quyền thực tế**, không có lựa chọn vai trò giả trên điện thoại.
4. Máy chủ **kiểm tra lại** quyền của chứng từ, vườn, lô và lệnh ghi. Không tin vào chuyện nút đã được ẩn ở giao diện.

Mọi thao tác ghi cần mạng. Mất mạng khi gửi thì ứng dụng báo chưa gửi được và chưa rõ máy chủ đã lưu hay chưa (yêu cầu có thể đã tới máy chủ, chỉ mất phần trả lời); kiểm tra kết nối và xem dữ liệu đã lưu chưa trước khi gửi lại, để không tạo bản trùng. Khi mất mạng, các màn chỉ đọc có thể hiện dữ liệu đã đọc trước đó của chính tài khoản (thông báo "Đang dùng dữ liệu đã lưu").

## Cách thử

Trên **site test**, sau khi cập nhật và build:
```bash
npm ci --prefix frontend
npm run --prefix frontend test
npm run --prefix frontend build
bench --site lotus.test migrate
```

1. Mở `https://<host>/lotus/mobile`; đăng nhập bằng tài khoản có quyền nghiệp vụ.
2. Thử tài khoản chỉ có kho: chỉ thấy **Quản lý kho**.
3. Thử tổ trưởng: thấy **Việc hôm nay**, mở `/work`.
4. Thử tài khoản có hai nhóm quyền: thấy cả hai nhóm trong một màn hình.
5. Thu hẹp quyền trên server, làm mới trang, kiểm tra nút biến mất **và** API chặn lệnh cũ.
6. Thử điện thoại 360–390px, quay màn hình, nút phía dưới, mất mạng và tải lại.

## Về cài trên điện thoại

`/lotus/mobile` đã có web manifest và thanh điều hướng dùng được trên màn hình nhỏ. Tùy trình duyệt và điều kiện HTTPS/site, có thể dùng “Thêm vào màn hình chính”. Đây là ứng dụng web trên điện thoại, **không phải APK phát hành qua Google Play**.
