# Lotus Manage UI: shadcn-vue + Attio-inspired CSS + AG Grid

## Thành phần
- Vue 3 + Frappe/ERPNext: giữ nguyên API, quyền, CSRF, và nghiệp vụ.
- **shadcn-vue (cấu hình Tailwind v3)**: đã thêm `frontend/components.json`, `jsconfig.json`, alias `@/`, `src/shadcn.css`, `src/lib/utils.js`, các dependency và phiên bản khóa trong npm.
- Các component dưới `frontend/src/components/ui/`: `button`, `input`, `textarea`, `card`, `badge`, `skeleton`, `separator`. Các file component thuộc repo để Lotus chỉnh trực tiếp theo cách hoạt động của shadcn-vue.
- **Button** thực sự được dùng tại `App.vue`, `SchemaForm.vue` và `AssignApp.vue`, thay thế nút tự viết phiên bản trước.
- **Frappe UI** vẫn được giữ cho các phần tích hợp Frappe.
- **AG Grid Community** giữ nhiệm vụ bảng trên máy tính; điện thoại dùng danh sách nút theo dòng.
- Attio chỉ là phong cách thiết kế, không dùng SDK hoặc sao chép tài sản từ Attio.

## Vì sao không nâng thẳng Tailwind 4?
Repo đang dùng Tailwind 3.4 với preset từ Frappe UI. Tài liệu shadcn-vue chính thức hướng dẫn dùng CLI **1.0.3** cho Tailwind v3. Giữ v3 nhằm tránh thay đổi quá nhiều hệ thống một lúc.

## Cách thêm component về sau
Trong thư mục `frontend/`:
```bash
npm ci
npm run ui:add -- dialog
npm run ui:add -- select
```
Các lệnh dùng CLI `shadcn-vue@1.0.3` để giữ tương thích v3. Với các tên đã có, hãy so sánh thay đổi trước khi ghi đè code Lotus. **shadcn-vue không phải một npm package chứa sẵn toàn bộ component**: mỗi component được lưu dưới dạng source ở `src/components/ui/` khi thêm vào dự án. Các file nêu trên được đưa vào branch với cấu trúc tương thích; do môi trường hiện tại không truy cập được npm registry, chưa chạy CLI trực tiếp.

## Quy tắc
- Màn hình văn phòng nhiều cột: AG Grid, không dùng bảng HTML tràn lan.
- Điện thoại: form và các dòng bấm lớn, không ép bảng nhiều cột.
- Không bật sửa ô AG Grid trước khi có API kiểm tra quyền, chống lưu nhầm và đối soát.
- Không đụng vào ERPNext Desk hay giao diện hiện trường HTML dự phòng trong đợt này.

## Kiểm tra
```bash
npm ci --prefix frontend
npm run --prefix frontend build
npm run --prefix frontend test
```
Workflow `.github/workflows/ui-build.yml` chạy ba bước này trên GitHub Actions. Sau đó kiểm tra trên một Frappe site thử nghiệm: `/lotus/today`, `/lotus/mobile`, `/lotus/giao-viec`, mở phiếu, lọc/sắp xếp, quyền, offline.

**Trạng thái (13/10/2026):** Đã cập nhật mã nguồn, dependencies, lockfile, cấu hình; rà soát tĩnh 44 điều kiện đạt. GitHub Actions hiện trả failure ngay trước khi runner nhận job (`steps: []/null`, chưa chạy `npm ci`), vì vậy đây **không phải** bằng chứng code lỗi hay build đạt. Mở tab Actions trong PR để xem cảnh báo phía GitHub/tài khoản (có thể liên quan hạn mức hoặc runner). Khi Actions hoạt động, chạy ba lệnh bên trên và kiểm tra trên Frappe site thử nghiệm. PR phải giữ Draft cho tới khi build và UAT đạt.
