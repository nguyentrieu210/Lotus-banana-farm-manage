# Triển khai bản phát hành (từ 19/10/2026)

Chỉ deploy bằng `compose.release.yaml` và một image `lotus-release:<sha>` build từ một commit
(`Dockerfile.release`, xem hướng dẫn ở đầu file). Không dùng lại chuỗi `compose.*.override.yaml`
hay `lotus-runtime/compose.yaml`: chúng cho mỗi dịch vụ một image khác nhau, mở cổng ra LAN và
chứa mật khẩu mặc định.

```sh
docker compose -p lotus --env-file <file .env riêng> -f deployment/compose.release.yaml up -d
docker exec lotus-backend-1 bench --site frontend migrate
```

File env (không commit) cần `LOTUS_IMAGE`, `DB_ROOT_PASSWORD`, `LOTUS_ADMIN_PASSWORD`. Cổng 8080
chỉ bind `127.0.0.1`; truy cập công khai đi qua tunnel cloudflared `lotus.gpcds.site`.
Trước khi migrate, so DocField trong DB với JSON của commit: field có trong DB mà thiếu trong
code sẽ bị migrate gỡ khỏi DocType.

Với bản sửa chỉ ở frontend, dùng `Dockerfile.frontend-release` từ cùng git archive và
gắn một tag local cho SHA256 image đang chạy đã kiểm tra. Truyền tag đó qua `BASE_IMAGE`
và ID qua `BASE_IMAGE_ID`; kiểm tra tag vẫn trỏ đúng ID trước khi build. Nó chỉ thay nguồn frontend và
bundle đã build; backend cùng các asset cũ được giữ từ image nền. Ghi lại image nền và
commit trong biên bản phát hành, vẫn dùng một `lotus-release:<sha>` cho mọi dịch vụ qua
`compose.release.yaml`, sao lưu như thường lệ và không chạy migrate khi không đổi schema.

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
