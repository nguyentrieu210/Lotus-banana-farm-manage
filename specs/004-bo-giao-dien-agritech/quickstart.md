# Quickstart: kiểm chứng bộ giao diện Lotus

Mọi kiểm tra, bản dựng và ảnh chụp chạy trên **máy chủ thử** (thư mục `/opt/lotus-004-test` trên VPS, không phải bản thật) hoặc GitHub Actions. Không chạy trên máy làm việc.

## Chuẩn bị (một lần)

1. Trên VPS có sẵn Node 24 và Chromium (`/usr/bin/chromium`).
2. Thư mục thử:
   - `/opt/lotus-004-test/app`: bản sao của worktree `C:\code\lotus-004-giao-dien` (không có `.git`, `node_modules`).
   - `/opt/lotus-004-test/node_modules`: thư viện frontend (cùng `package-lock.json` với nhánh 002 và 003); `app/frontend/node_modules` là liên kết tới đây.
   - `/opt/lotus-004-test/www`: thư mục phục vụ nội bộ ở `127.0.0.1:8704` (`python3 -m http.server`), chứa bản dựng trang mẫu và phông chữ.
3. Đồng bộ mã từ máy làm việc lên: nén worktree, gửi qua SSH, giải nén vào `app.new`, rồi đổi tên thành `app`.

## Kịch bản 1: không làm vỡ gì (SC-004)

```bash
cd /opt/lotus-004-test/app/frontend
nice -n 10 node --test --test-concurrency=2 tests/*.test.js
```

Kết quả mong đợi: không có kiểm tra nào lỗi. Mốc trước khi làm là 611 đạt, 0 lỗi (xem [baseline.md](baseline.md)); số kiểm tra chỉ tăng thêm.

## Kịch bản 2: bản dựng thật vẫn dựng được (SC-004, SC-008)

```bash
cd /opt/lotus-004-test/app/frontend
nice -n 10 npx vite build --outDir /opt/lotus-004-test/build-check --emptyOutDir
```

Kết quả mong đợi: dựng xong không lỗi. So dung lượng kiểu sau nén của từng ứng dụng với bảng trong [baseline.md](baseline.md); không ứng dụng nào vượt ngưỡng 15%. Bản dựng thử ghi ra thư mục riêng, không ghi vào `lotus_farm/public/frontend`.

## Kịch bản 3: trang mẫu (User Story 6, SC-003)

```bash
cd /opt/lotus-004-test/app/frontend
LOTUS_SHOWCASE_OUT=/opt/lotus-004-test/www/showcase LOTUS_SHOWCASE_BASE=/showcase/ \
  nice -n 10 npx vite build --config vite.showcase.config.js
```

Mở `http://127.0.0.1:8704/showcase/showcase.html` bằng Chromium không giao diện và chụp:

```bash
chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=1440,2400 --virtual-time-budget=8000 \
  --screenshot=/opt/lotus-004-test/shots/<tên>.png \
  'http://127.0.0.1:8704/showcase/showcase.html?section=<phần>&mode=<light|dark|outdoor>&density=<compact|comfortable>' \
  > /opt/lotus-004-test/shots/chromium.log 2>&1 </dev/null
```

Kết quả mong đợi:

- Sáu phần của trang mẫu đều hiện: Nền, Thành phần, Bảng, Điện thoại, Nông nghiệp, Mẫu màn hình.
- Đổi `mode` và `density` thì cả trang đổi theo.
- Mọi số liệu có ghi "Dữ liệu mẫu".
- Phần Điện thoại ở khung 320px không tràn ngang.

## Kịch bản 4: tương phản và giữ chuẩn (SC-001, FR-041)

Các kiểm tra mới nằm trong `frontend/tests/` và chạy cùng kịch bản 1: tương phản của bộ màu ở ba chế độ, không ghi màu ngoài `lotus-tokens.css`, mọi thành phần của bộ có mặt trên trang mẫu, hành vi của các thành phần có đóng mở, chọn, lọc.

## Kịch bản 5: các màn vườn dùng bộ nông nghiệp (User Story 5, SC-007)

Trong trang mẫu, phần Mẫu màn hình dựng lại các màn Hôm nay, Màu dây và thu hoạch, Vòng chăm sóc bằng chính các component thật với dữ liệu mẫu. So thẻ của cùng một lô ở ba màn: cùng bố cục, cùng màu trạng thái.

## Không làm trong lúc kiểm chứng

- Không ghi chứng từ thật, không đổi dữ liệu trên bản thật.
- Không chạy `vite build` mặc định vào `lotus_farm/public/frontend` trừ khi đang đóng gói bản phát hành.
- Không đưa lên máy chủ thật khi chủ vườn chưa yêu cầu.
