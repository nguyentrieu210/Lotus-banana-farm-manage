# Triển khai spec 002 lên VPS

Chỉ chạy khi chủ vườn ra lệnh và đưa mật khẩu SSH tại lúc triển khai. Mật khẩu không được lưu.

Triển khai hai lần:

1. **Lần 1 (bản này)**: sổ lô, báo cáo ngày theo lô, phiếu giấy và đọc ảnh, màu dây và thu hoạch, vòng chăm sóc, dự thu chốt tuần, xưởng theo nguồn buồng, báo cáo Sáng nay/Tuần/Tháng, menu 7 mục. Các bảng đời cũ vẫn còn trong cơ sở dữ liệu nhưng không còn màn hình ghi vào.
2. **Lần 2 (US7)**: dọn 76 bảng cũ (`legacy_purge.preview`, chủ vườn xem, rồi `commit`). Làm sau khi lần 1 chạy ổn.

## 0. Trước khi build

- Đọc image đang chạy: `docker inspect lotus-vps-backend-1 --format '{{.Config.Image}}'`. Ngày 10/11 là `lotus-release:df7bd70`. Codex cũng triển khai: nếu image đã khác, gộp commit đó vào bản phát hành trước.
- Gộp bản sửa lỗi của phiên khác: `git merge --no-ff hotfix/b1-b4-phieu-chi-vat` (20b006c hoặc đầu nhánh mới hơn: B1 ký phiếu chi lỗi khi người ký có thiết bị nhận thông báo, B4 VAT hộ kinh doanh vào 1331). Ngày 10/11 gộp được sạch vào nhánh 002.
- Chạy lại: `npm run build` (tài sản đã build nằm trong git), `node --test`, unit Python và các `tests/integration/verify_*.py` của spec 002 trên bản local.
- Gộp vào main rồi triển khai từ đúng SHA đó. Không có ai đang triển khai cùng lúc.

## 1. Build trên VPS

- `git -c core.autocrlf=false archive --prefix=app/ <sha>` → `/srv/lotus-build/<sha>/`, kèm `downloads/Lotus-HR-Scanner.apk` lấy từ backend đang chạy.
- `docker build -f app/deployment/Dockerfile.release --build-arg BASE_IMAGE=<image đang chạy> -t lotus-release:<sha7> .` (dùng `--flatten` của deploy_migrate.py nếu báo quá nhiều layer). Dockerfile.release xóa `lotus_farm/lotus_farm` trước khi COPY, nên DocType đã xóa (Plan Norm…) không quay lại.

## 2. Sao lưu

- `bench --site frontend backup --with-files` trong backend; ghi lại tên tệp.
- Sao chép `/opt/lotus/.env` thành `.env.bak-<image cũ>-<ngày>`.

## 3. Rollout

1. Bật bảo trì: `bench --site frontend set-maintenance-mode on`.
2. Đổi `LOTUS_IMAGE` trong `/opt/lotus/.env` sang `lotus-release:<sha7>`.
3. `docker compose -p lotus-vps --env-file /opt/lotus/.env -f /opt/lotus/compose.yaml up -d --no-deps backend frontend websocket queue-short queue-long` (không có scheduler, giữ nguyên).
4. `bench --site frontend migrate` (khoảng 3 đến 7 phút). Patch `care_cycle_rules` lưu các luật lịch cũ có mốc trồng/chọn chồi ra `sites/frontend/private/files/work_schedule_rule_legacy_*.json` rồi xóa.
5. Tắt bảo trì; `nginx -s reload` trong `lotus-domain-router` và `daiminhloc-frontend-1`. Nếu còn 503 thì `docker restart lotus-vps-backend-1`.

## 4. Chuyển dữ liệu (bench execute trong backend, người chạy: Administrator)

1. `lotus_farm.lot_ledger_migrate.preview`: xem số dòng sẽ chuyển từ Lotus Bunch Event sang sổ lô (sổ cắt bắp đầu kỳ 593 buồng), số dòng thử bị hủy, số phiếu Round thử bị hủy. Không có lỗi mới chạy tiếp.
2. `lotus_farm.lot_ledger_migrate.commit`. Chạy lại lần hai phải ra 0 dòng chuyển thêm.
3. `lotus_farm.field_report_seed.apply_ledger_works` với `commit=1`: thêm việc Hủy buồng, Thu hoạch, Kiểm tra sâu bệnh nếu chưa có.
4. Kiểm dự thu trước và sau bằng `lotus_farm.block_forecast.bunch_summary('LOTUS-222')`: tổng buồng phải bằng nhau (local: 7.347 buồng).
5. `lotus_farm.forecast_snapshot.ensure_all`: dựng bản chốt tuần (cũng tự chạy khi có người mở ứng dụng).

## 5. Việc của chủ vườn sau khi lên

- Danh sách tổ trưởng Đội khu A + B (họ tên, số điện thoại) để tạo tài khoản, gán vai trò Lotus Team Leader và quyền vườn.
- Quản lý vườn đặt vòng chăm sóc cho các việc vườn (Thiết lập › Vòng chăm sóc) và duyệt.
- Kế toán chọn Chuối thành phẩm, Chuối phụ phẩm, Kho thành phẩm (Tài chính – Kế toán › Thiết lập) trước lứa thu đầu.
- Chụp 10 phiếu giấy thật đã ghi để đo tỷ lệ đọc đúng (T083) trước khi cho các tổ dùng phiếu giấy.

## 6. Kiểm sau khi lên

- Mở `/lotus/cong-viec` (Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Báo cáo) và `/work` trên điện thoại: không lỗi.
- Một tổ thử nhập một lô, gửi; đội trưởng xác nhận; số hiện trên bảng màu dây.
- Error Log không có lỗi mới ngoài "Session Stopped" lúc vừa tắt bảo trì.

## 7. Quay lại bản cũ

- Đổi `LOTUS_IMAGE` về image cũ theo `.env.bak-*`, compose up như bước 3.
- Nếu bước 4 đã chạy và cần bỏ: khôi phục bản sao lưu cơ sở dữ liệu ở bước 2 (`bench --site frontend restore`).
