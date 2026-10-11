# Một app mobile chung theo quyền — Lotus Farm

## Mục tiêu

Mở **`/lotus/mobile`** trên điện thoại. Mỗi người đăng nhập bằng **tài khoản Frappe hiện có**, không cần tải một app riêng cho từng chức danh. Tài khoản kiêm nhiều nhiệm vụ sẽ thấy tổng hợp các mục được cấp quyền.

Từ trang chủ có thể mở công việc, báo kết quả, nông trường, sâu bệnh, hủy buồng, đo trái, thu hoạch, chất lượng, xưởng, vật tư, chốt ngày, dự thu và báo cáo **nếu tài khoản được phép**. Màn giao việc nhanh vẫn ở `/lotus/giao-viec`, cùng tên miền, cùng phiên đăng nhập và cùng cơ sở dữ liệu.

## Luồng vận hành

1. Nhân viên đăng nhập Lotus bằng tài khoản ERPNext/Frappe.
2. Máy chủ trả về `console.bootstrap`: danh sách nông trường được xem, danh sách nghiệp vụ được xem, quyền tạo phiếu, các lệnh phù hợp vai trò.
3. Mobile tự tạo các nút theo **quyền thực tế**, không có lựa chọn vai trò giả trên điện thoại. Có nhiều vai trò thì thấy thêm việc.
4. Khi bấm nút, app mở phần nghiệp vụ Vue đang có hoặc màn giao việc nhanh đã có.
5. Máy chủ **kiểm tra lại** quyền của chứng từ, nông trường, lô/thửa và lệnh ghi. Không tin vào chuyện nút đã được ẩn ở giao diện.

Ví dụ:
- Người có quyền xem Daily Work Plan thấy **Xem công việc**.
- Người có thêm quyền tạo Daily Work Result thấy **Báo kết quả**.
- Người được gán vai trò **Lotus Farm Manager** (và có quyền xem việc) thấy **Giao việc cho tổ**.
- Người có quyền QC chỉ thấy **Kiểm tra chất lượng** trong nhóm xưởng; không tự động được giao việc.
- Người vừa có quyền công việc vừa có quyền QC nhìn thấy cả hai phần, không cần chuyển tài khoản.

## Quyền và giới hạn hiện tại

**Chưa tự tạo role Tổ trưởng, Đội trưởng, Kỹ thuật mới.** Hệ thống đang có các vai trò như Lotus Farm Manager, Lotus QC Manager, Lotus Packing Supervisor, Lotus Sales Planner, Lotus Integration User, Lotus Auditor, Lotus Stock Reviewer. Cần cùng Lotus xác định ai được ghi, duyệt và xem farm nào trước khi cấp quyền cho từng chức danh thực tế. Không gán quyền quản lý toàn farm cho tổ trưởng chỉ để hiện nút.

App sử dụng trực tiếp các kiểm tra của backend Frappe:
- `frappe.has_permission` cho các nhóm DocType;
- `User Permission` hạn chế theo Farm;
- kiểm tra role và dữ liệu trong `mobile_assignment` và API chứng từ.

**Không thay thế quy trình bảo vệ dữ liệu bằng cách ẩn nút**. Giao việc nhanh hiện cần online, còn báo kết quả hiện trường có hàng chờ offline đang có sẵn. Đây không phải tuyên bố rằng mọi nghiệp vụ đều hoạt động offline.

## Cách thử

Trên **site test**, sau khi cập nhật và build:
```bash
npm ci --prefix frontend
npm run --prefix frontend test
npm run --prefix frontend build
bench --site lotus.test migrate
```

1. Mở `https://<host>/lotus/mobile`; đăng nhập bằng tài khoản có quyền nghiệp vụ.
2. Thử tài khoản chỉ được xem việc: phải có **Xem công việc** nhưng không có **Giao việc**, **Báo kết quả** nếu không có quyền tương ứng.
3. Thử tài khoản manager: giao việc nhanh theo nông trường được phép, kiểm tra preview và kết quả từ API gốc.
4. Thử tài khoản QC: phải có **Kiểm tra chất lượng**; kiểm tra không đọc được farm ngoài quyền.
5. Thử tài khoản có hai nhóm quyền: thấy cả hai nhóm trong một màn hình.
6. Thu hẹp quyền trên server, làm mới trang, kiểm tra nút biến mất **và** API chặn lệnh cũ.
7. Thử điện thoại 360–390px, quay màn hình, nút phía dưới, mất mạng và tải lại.

`/lotus/today` vẫn là bảng điều hành chuyên sâu. Giao diện hiện trường cũ `/assets/lotus_farm/field/index.html` vẫn giữ làm phương án dự phòng. Bản này **chưa có UAT ngoài farm**, chưa cấp quyền thực tế theo nhân sự Lotus, chưa đóng gói Android APK và chưa triển khai lên máy chủ làm việc thật.

## Về cài trên điện thoại

`/lotus/mobile` đã có web manifest và thanh điều hướng dùng được trên màn hình nhỏ. Tùy trình duyệt và điều kiện HTTPS/site, có thể dùng “Thêm vào màn hình chính”. Đây là ứng dụng web trên điện thoại, **không phải APK phát hành qua Google Play**.
