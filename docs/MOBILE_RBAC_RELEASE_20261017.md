# Lotus Mobile RBAC – phát hành 17/10/2026

## Phạm vi
Ba PWA vẫn là /work, /warehouse, /buying, dùng Vue 3 + Vant 4 và cùng ERPNext/Frappe v16.
Phần này bổ sung quyền Team Leader (Tổ trưởng) và Field Supervisor (Đội trưởng), không viết lại app.
Bảo mật bắt buộc ở server; giao diện chỉ ẩn các nút không có quyền để dễ dùng.

## Gán quyền trước khi đưa nhân sự sử dụng
- Tạo tài khoản thực tế trong ERPNext User và kích hoạt có kiểm soát.
- Gán Role **Lotus Team Leader** cho tổ trưởng và Role **Lotus Field Supervisor** cho đội trưởng.
- Mỗi người bắt buộc có **User Permission: Farm** và **User Permission: Work Team**.
- Mỗi Work Team phải có Farm đúng, còn active.
- Nếu thiếu Work Team grant, tài khoản không xem được dòng việc của tổ nào.
- Không cấp **Lotus Farm Manager** cho Tổ trưởng: vai trò này xem hết các tổ thuộc vườn.
- Tổ trưởng: xem việc và báo kết quả/vướng mắc; không tạo kế hoạch hoặc duyệt giá.
- Đội trưởng: xem và giao việc cho tổ được cấp; không được giao sang tổ/vườn khác.
- Giám đốc vườn: dùng Lotus Farm Manager + Farm User Permission.
- Người duyệt giá: Lotus Price Approver, giữ cơ chế không duyệt phiếu do chính mình lập.
- Warehouse/Purchase duy trì vai trò cũ và kiểm tra backend ERPNext.

## Backend kiểm tra quyền
- lotus_farm/mobile_access.py: ability, grant Farm/Team, định danh công việc thực tế.
- lotus_farm/work_mobile.py: lọc **dòng việc** theo Team. Một Daily Work Plan có thể chứa nhiều Team.
- lotus_farm/field.py: chỉ cho tổ trưởng gửi Daily Work Result liên quan; kiểm tra Team, Farm, plan-line, ngày, lô, số công và chống bản ghi trùng theo event ID gốc.
- lotus_farm/mobile_assignment.py: supervisor chỉ được giao việc cho Team mình được phân công.
- lotus_farm/permissions.py + controls.py: kiểm tra Work Team cả danh sách và từng bản ghi.
- Không cấp quyền đọc nguyên Daily Work Plan cho Team Leader/Field Supervisor.
- Offline: dùng hàng chờ cùng client_event_id, kiểm tra quyền lần nữa khi gửi lại.
- Tất cả quyền mới là bổ sung, không tự động gán cho bất cứ nhân sự nào.

## Kiểm thử
- `npm test` — 149/149 (lúc kiểm thử RBAC).
- `npm run build` — đạt.
- `python tests/test_mobile_roles_mock.py` trong image Frappe — 6/6.
- Các API bị kiểm tra thử payload giả mạo, Farm sai và Team sai trước khi tạo.
- Trước khi gán tài khoản thật vẫn phải UAT với 2 tổ cùng một phiếu để xác nhận quyền thật trong DB.

## Triển khai
1. Git nhánh sync/lotus-mobile-20261017; commit riêng thay đổi RBAC.
2. Sao lưu database + files của site `frontend`.
3. Image `lotus-mobile-rbac:v1-20261017` kế thừa `lotus-pwa-buying:v3-20261017`.
4. Chồng `deployment/compose.mobile-rbac-v1.override.yaml` **cuối danh sách** docker compose, chỉ nâng backend/frontend.
5. Chạy `bench --site frontend migrate`, tạo vai trò và cập nhật quyền; kiểm tra 3 URL.
6. Cấp quyền người dùng thử nghiệm, chạy UAT, rồi mới cấp rộng.

## Quay về nếu phát sinh lỗi
Quay backend/frontend về image đã chụp lại trước triển khai (`lotus-pwa-buying:v3-20261017` nếu chưa thay đổi). Để nguyên quyền mới khi rollback mã lành tính. Tuyệt đối không xóa database hay chứng từ.
