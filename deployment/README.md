# Triển khai có HRMS

`Dockerfile` build từ ERPNext v16.50.0 và HRMS tag v16.50.0 (commit HRMS 7c037698ce57d1492f05a8b4a586a7578f722879). HRMS này yêu cầu Frappe >=16.50 và ERPNext >=16.0. Dùng tag đã kiểm tra, không lấy nhánh thay đổi tùy ý khi triển khai lại.

```sh
docker build -f deployment/Dockerfile -t lotus-erpnext:local .
```

Sao lưu database, site config, public/private files trước khi thay image. Mọi dịch vụ backend, frontend, websocket, queue và scheduler phải dùng cùng image. Với volume sites sẵn có, bảo đảm apps.txt có frappe, erpnext, lotus_farm, hrms (mỗi app một dòng, không thêm trùng), sau đó:

```sh
bench --site frontend install-app hrms
bench --site frontend migrate
bench --site frontend clear-cache
bench --site frontend list-apps
```

Chỉ chạy install-app nếu site chưa cài HRMS. Trên site mới cài các app theo quy trình bench. Migration Lotus tạo DocType đội khoán và custom fields Attendance/Work Team; không tạo nhân viên hay tài khoản thực tế.

Bản local đã kiểm tra: Frappe16.51.0, ERPNext16.50.0, HRMS16.50.0. Có backup đầy đủ trước cài ngày 14/10/2026. Cổng local 8080, site frontend; tên volume/network/compose cấu hình riêng tại máy, không đưa site credentials vào repo. Liên kết tài sản hrms và lotus_farm đã tạo trong image, build cả frontend Lotus lẫn HRMS.

Kiểm tra sau nâng cấp: kho `/lotus/kho`, chấm công `/lotus/cham-cong`, quản trị HRMS `/desk/hr-setup`, in phiếu/PDF và in công/CSV. Cổng `/hrms` yêu cầu Employee native liên kết tài khoản; không tạo Employee giả cho Administrator.
