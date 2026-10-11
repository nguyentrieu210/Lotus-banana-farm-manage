# Lotus mobile — một app dùng chung theo vai trò

## Kết quả

Mở `/lotus/mobile` sau khi build frontend, migrate và đăng nhập vào **cùng site Frappe/ERPNext**. Trên điện thoại có bốn khu vực: **Hôm nay, Công việc, Ghi nhận, Tài khoản**. Một người có thể có nhiều vai trò; chức năng được cộng dồn, không bắt chọn thủ công một vai trò.

- **Quản lý nông trường**: xem tiến độ theo ngày, mở giao việc nhanh (`/lotus/giao-viec`), xem các mô-đun ERPNext đang được cấp, ghi nhận sâu bệnh.
- **Giám đốc nông trường**: xem tiến độ và công việc trong nông trường được cấp. Không được giao việc hoặc sửa dữ liệu chỉ vì có chức danh giám đốc.
- **Tổ trưởng**: chỉ xem dòng công việc của **tổ được gán** (hoặc dòng giao đích danh cho mình). Không xem dòng việc của tổ khác kể cả trong cùng kế hoạch.
- **Kỹ thuật vườn**: xem công việc được giao đích danh; có thể lập phiếu quan sát bệnh (chọn thửa, vụ, đợt chồi nếu có, loại bệnh, số cây, mức độ, hướng xử lý).
- **QC, xưởng đóng gói, kế hoạch bán, nhập dữ liệu, kiểm tra kho**: thấy đường tắt đến các mô-đun mình thực sự có quyền đọc trên site. Nếu chưa có quyền mô-đun, không xuất hiện đường tắt.
- **Một người có nhiều vai trò**: được dùng những chức năng có quyền thực tế, không cần hai tài khoản hay hai app.

## Cấp quyền trước khi thử

1. `bench --site <SITE> migrate`: cập nhật ba vai trò **Lotus Farm Director**, **Lotus Team Leader**, **Lotus Field Technician**, cùng trường `Work Team.lotus_team_leader`.
2. Trong tài khoản User, gán các vai trò thích hợp.
3. Vào User Permission, tạo dòng **Allow: Farm → For Value: <tên Farm>** cho từng tài khoản. Không cấp Farm thì backend chặn truy cập dù có vai trò.
4. Với tổ trưởng, mở danh mục **Work Team** để điền **Tổ trưởng phụ trách** (User). Một tổ chỉ có một người được gán ở trường này; người phụ trách nhiều tổ được gán ở nhiều dòng.
5. Với kỹ thuật vườn muốn thấy công việc, người giao việc phải điền trường **Responsible** trên dòng Daily Work Plan. Không đoán người phụ trách từ vai trò.

Lưu ý: trang giao việc nhanh hiện tại giao theo **tổ**, không tự gán người chịu trách nhiệm. Do đó danh sách cá nhân của kỹ thuật có thể trống đến khi kế hoạch được gán trực tiếp.

## Quyền trên máy chủ

- Frontend chỉ dùng feature flags để **hiện nút**. `mobile_portal.profile`, `overview`, `observation_options` và `report_observation` đều kiểm tra lại quyền và Farm đã cấp.
- `overview` lấy các kế hoạch đã gửi và chỉ trả về dòng việc được phép xem. Tổ trưởng chỉ thấy tổ có `lotus_team_leader` trùng User; kỹ thuật chỉ thấy dòng có `responsible` trùng User.
- Tài khoản tổ trưởng **không được cấp trực tiếp quyền đọc toàn bộ Daily Work Plan**; dữ liệu phần xem việc được giới hạn bằng endpoint riêng.
- Kỹ thuật được cấp quyền tạo và submit **Disease Observation**, nhưng không được quyền sửa tùy ý phiếu của người khác. Kiểm tra liên kết Farm → Thửa → Vụ → Đợt chồi trên backend.
- **Chưa có** chức năng tổ trưởng tự gửi sản lượng đã nghiệm thu trên mobile; việc xem kế hoạch không phải phiếu xác nhận hoặc tính tiền khoán.
- Không nạp dữ liệu mẫu vào production. PR giao việc #7 đã có seed test riêng: `lotus_farm.mobile_demo_seed.seed`, chỉ chạy trên test site được bật `allow_tests`.
- App còn cần thử trên điện thoại tại vườn; phiếu sâu bệnh hiện yêu cầu có mạng.

## Xây dựng và kiểm tra

```bash
npm ci --prefix frontend
npm run --prefix frontend test
npm run --prefix frontend build
python -m unittest discover -s tests -v
bench --site <SITE> migrate
```

Bản build có `mobile.html` trong Vite manifest, route Frappe `/lotus/mobile` trả về đúng entry riêng. Giao việc nhanh `/lotus/giao-viec` vẫn còn, cùng backend và phiên đăng nhập.
