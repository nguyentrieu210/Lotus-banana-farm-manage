# Triển khai spec 002 lên VPS

Chỉ chạy khi chủ vườn ra lệnh. Test, build và diễn tập chạy trên VPS (khu thử riêng `/srv/lotus-test/002`, stack `lotus-002-test`, bản sao cơ sở dữ liệu thật) hoặc GitHub Actions, không chạy trên máy làm việc.

Triển khai hai lần:

1. **Lần 1 (đã lên 10/11, `lotus-release:40f8330`)**: sổ lô, báo cáo ngày theo lô, phiếu giấy và đọc ảnh, màu dây và thu hoạch, vòng chăm sóc, dự thu chốt tuần, xưởng theo nguồn buồng, báo cáo Sáng nay/Tuần/Tháng, menu 7 mục. Các bảng đời cũ vẫn còn trong cơ sở dữ liệu nhưng không còn màn hình ghi vào.
2. **Lần 2 (US7)**: xóa hẳn 76 bảng cũ cùng mã, màn hình, menu, tool và test của chúng; tài chính, lương, kho, khung ứng dụng cũ, vườn & lô và dự thu không còn đọc chúng. Các bước ở mục 8.

## 0. Trước khi build

- Đọc image đang chạy: `docker inspect lotus-vps-backend-1 --format '{{.Config.Image}}'`. Ngày 10/11 là `lotus-release:df7bd70`. Codex cũng triển khai: nếu image đã khác, gộp commit đó vào bản phát hành trước.
- Gộp bản sửa lỗi của phiên khác: `git merge --no-ff hotfix/b1-b4-phieu-chi-vat` (20b006c hoặc đầu nhánh mới hơn: B1 ký phiếu chi lỗi khi người ký có thiết bị nhận thông báo, B4 VAT hộ kinh doanh vào 1331). Ngày 10/11 gộp được sạch vào nhánh 002.
- Trên khu thử của VPS: `npm test` và `npm run build` (tài sản đã build nằm trong git: lấy thư mục `lotus_farm/public/frontend` vừa build về rồi commit), unit Python, các `tests/integration/verify_*.py` của spec 002 trên bản sao dữ liệu thật.
- Diễn tập trên bản sao dữ liệu thật: migrate, chuyển dữ liệu, so sổ sách trước và sau (số dòng và mã kiểm của sổ cái, kho, chấm công, lương), so số liệu các báo cáo tài chính, kho, nhân sự giữa mã cũ và mã mới.
- Kiểm không có kỳ lương nào đang gửi ký dở (`Lotus Timekeeping Period` trạng thái Open có `snapshot_hash`): nếu có thì ký xong hoặc trả lại trước.
- Gộp vào main rồi triển khai từ đúng SHA đó. Không có ai đang triển khai cùng lúc.

## 1. Build trên VPS

- `git -c core.autocrlf=false archive --prefix=app/ <sha>` → `/srv/lotus-build/<sha>/`, kèm `downloads/Lotus-HR-Scanner.apk` lấy từ backend đang chạy.
- `docker build -f app/deployment/Dockerfile.release --build-arg BASE_IMAGE=<image đang chạy> -t lotus-release:<sha7> .` (dùng `--flatten` của deploy_migrate.py nếu báo quá nhiều layer). Dockerfile.release xóa `lotus_farm/lotus_farm` trước khi COPY, nên DocType đã xóa (Plan Norm…) không quay lại.

## 2. Sao lưu

- `bench --site frontend backup --with-files` trong backend; ghi lại tên tệp.
- Sao chép `/opt/lotus/.env` thành `.env.bak-<image cũ>-<ngày>`.

## 3. Rollout và chuyển dữ liệu (một lượt, trong lúc bảo trì)

Chạy bằng `rollout.sh <sha mới> <sha đang chạy>` (lưu ở `/srv/lotus-build/<sha mới>/`). Dữ liệu được chuyển **trước khi tắt bảo trì**, để không ai mở ứng dụng lúc sổ lô còn trống.

1. Bật bảo trì, dừng hai hàng đợi.
2. Sao lưu cơ sở dữ liệu, chép tệp sao lưu ra `/srv/lotus-build/<sha mới>/`; chụp số dòng và mã kiểm sổ sách (trước).
3. Đổi `LOTUS_IMAGE` trong `/opt/lotus/.env`; `compose up -d --no-deps backend frontend websocket` (không có scheduler).
4. `bench --site frontend migrate` (diễn tập: 168 giây). Patch `care_cycle_rules` lưu các luật lịch cũ ra `sites/frontend/private/files/work_schedule_rule_legacy_*.json` rồi xóa. So sổ sách: phải không đổi, nếu đổi thì dừng và quay lại.
5. Chuyển dữ liệu (người chạy: Administrator):
   - `lot_ledger_migrate.preview` rồi `commit`: sổ cắt bắp đầu kỳ từ Lotus Bunch Event sang sổ lô (bản thật 10/11: 38 dòng, 593 buồng). Chạy lần hai phải ra 0 dòng.
   - `field_report_seed.apply_ledger_works(commit=1)`: thêm việc Hủy buồng, Thu hoạch, Kiểm tra sâu bệnh nếu chưa có.
   - Dự thu `block_forecast.bunch_summary` trước (mã cũ, bước 2) và sau phải bằng nhau (bản thật 10/11: 7.347 buồng, 144.001,2 kg).
   - `forecast_snapshot.ensure_all`: dựng bản chốt tuần còn thiếu.
   - `legacy_purge.preview` (chỉ đọc): số dòng từng bảng cũ, trường còn trỏ bảng cũ, danh sách chặn; lưu kết quả để chuẩn bị lần 2.
   - So sổ sách lần nữa: phải không đổi.
6. Bật lại hai hàng đợi, tắt bảo trì, khởi động lại backend, `nginx -s reload` trong `lotus-domain-router` và `daiminhloc-frontend-1`.

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

`rollback.sh <sha mới> --restore-db`. Sau khi đã migrate thì **luôn khôi phục bản sao lưu ở bước 2**: cơ sở dữ liệu đã mang cấu trúc bảng mới (Lotus Work Entry bắt buộc `source_key`, chỉ mục buổi công đã đổi), mã cũ chạy trên đó sẽ lỗi khi ghi báo cáo. Chỉ đổi image mà không khôi phục khi chưa chạy migrate.

## 8. Lần 2: xóa hẳn 76 bảng cũ (US7)

Chạy bằng `rollout2.sh <sha mới> <sha đang chạy>` (lưu ở `/srv/lotus-build/<sha mới>/`), sau khi đã diễn tập đủ trên bản sao dữ liệu thật (`/srv/lotus-test/002/rehearsal2.sh`).

1. Với mã đang chạy: `legacy_purge.preview`. Danh sách chặn phải trống (không giá trị cũ nào nằm trên chứng từ đã ghi sổ, không kỳ lương đã khóa dùng Labor Allocation, sổ cắt bắp cũ đã chuyển hết sang sổ lô). Nếu không trống thì dừng, chưa đổi gì.
2. Bật bảo trì, dừng hai hàng đợi, sao lưu cơ sở dữ liệu và tệp, chép bản sao lưu ra `/srv/lotus-build/<sha mới>/`; chụp sổ sách và dự thu (trước).
3. Đổi `LOTUS_IMAGE` sang image mới; `compose up -d --no-deps backend frontend websocket`.
4. `legacy_purge.commit`: xuất từng bảng cũ ra JSON (số dòng, mã kiểm) vào `sites/frontend/private/files/legacy_purge_<giờ>/` và đọc lại để so trước khi xóa; rồi gỡ chiều kế toán và trường trỏ bảng cũ (kể cả cột), xóa DocType, xóa bảng, xóa các dòng lịch sử và quyền còn nhắc tên bảng cũ. Chép thư mục lưu trữ ra `/srv/lotus-build/<sha mới>/`.
5. `bench migrate` (patch `purge_legacy_doctypes` chạy lại `commit`, không còn gì để làm, và dừng migrate nếu còn sót tên bảng cũ).
6. `legacy_purge.verify` phải trống; sổ sách (26 bảng) không đổi; dự thu (tổng buồng, kg, thùng) không đổi.
7. Bật hàng đợi, tắt bảo trì, khởi động lại backend, `nginx -s reload`.

Quay lại bản cũ: `rollback.sh <sha mới> --restore-db` (luôn khôi phục: bảng và cột đã bị xóa). Dữ liệu của 76 bảng còn trong thư mục lưu trữ JSON và trong bản sao lưu ở bước 2.
