# Lotus – triển khai Cấu hình kế hoạch & định mức lên live

Ngày: 18/10/2026. Site: `frontend`. URL: `https://lotus.gpcds.site/lotus/plan-norm?farm=LOTUS-222`.

## Image và cách triển khai
- **Trước triển khai**: `lotus-vip126-complete-cycle:v1-20261018`.
- **Image mới**: `lotus-plan-norm-live:v1-20261018`, build từ `deployment/Dockerfile.plan-norm-live-v1` dựa trực tiếp trên image đang vận hành.
- **Compose**: giữ tất cả 22 tệp Compose của stack đang chạy (lấy từ label container), nối `deployment/compose.plan-norm-live-v1.override.yaml` vào cuối; không đổi Redis/DB/Websocket.
- **Cập nhật**: backend trước, `bench --site frontend reload-doc lotus_farm doctype plan_cohort`, `bench --site frontend clear-cache`, sau đó frontend + queue-short/long + scheduler.
- **Rollback image**: `powershell -NoProfile -ExecutionPolicy Bypass -File deployment/deploy-plan-norm-live.ps1 -Rollback`. Lệnh này hoàn nguyên image theo stack cũ; KHÔNG tự khôi phục dữ liệu DB.

## Sao lưu
Lệnh: `bench --site frontend backup --with-files --compress`.

Bản sao lưu lưu trong volume `lotus_sites`:
`/home/frappe/frappe-bench/sites/frontend/private/backups/20261018_150755-frontend-*`.
Bao gồm database (~1.4 MiB), public/private files và cấu hình site. Khi cần khôi phục dữ liệu, phải đánh giá thay đổi phát sinh sau backup rồi mới restore.

## Smoke live
- `Plan Cohort` DocType và bảng tồn tại sau reload-doc.
- `lotus_farm.plan_norm.board(farm='LOTUS-222')` đọc 64 lô, 8 loại công việc, 1 Harvest Profile, 0 bộ định mức vật tư, 0 Work Schedule Rule, 0 Plan Cohort thời điểm test.
- Tạo thử 1 Plan Cohort trong transaction, `frappe.db.rollback()` xóa sạch thay đổi, xác nhận không để lại dữ liệu.
- `Guest` không được xem Farm/API; HTTP 403 nếu gọi backend API chưa đăng nhập.
- Public `/lotus/plan-norm` chuyển đến đăng nhập khi chưa có phiên (HTTP 301), tương tự các màn cũ.
- Public JS mới (tên file theo Vite manifest) trả HTTP 200.
- Docker 5 thành phần ứng dụng dùng image mới, database healthy, scheduler workers online.
- Frontend trước khi triển khai: 216/216 test đạt, Vite build đạt. Python AST và DocType JSON hợp lệ.

## Giới hạn vận hành hiện tại
- Bộ cấu hình sử dụng thật cần người quản lý nhập và duyệt. Không tự điền định mức hoặc tỷ lệ chuyên môn chưa được xác nhận.
- Các đợt chỉ là kế hoạch mô phỏng, KHÔNG tự động thay mốc bằng số thực từ hiện trường hoặc trừ tồn kho thật.
- Chưa có bước phát hành kế hoạch tuần/ngày tự động, chưa tạo yêu cầu mua, phiếu kho hoặc dự thu hàng được cam kết.
- Chỉ nâng cấp Doctype mới bằng `reload-doc`, KHÔNG chạy `bench migrate` toàn bộ, không sửa dữ liệu vườn.
- Giữ nguyên trạng thái các worktree khác đang phát triển; không ghi đè mã chưa commit ở repo ứng dụng di động.
