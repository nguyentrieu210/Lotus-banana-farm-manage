# Mốc trước khi làm: bộ giao diện Lotus

Đo ngày 10/11/2026 trên nhánh `004-bo-giao-dien-agritech`, tách từ `002-cham-soc-thu-hoach-du-thu` tại `40f8330`.

## Nhánh và nơi làm

- Worktree: `C:\code\lotus-004-giao-dien`.
- Bản đang chạy trên máy chủ thật: `lotus-release:df7bd70` (nhánh `main`). Nhánh 002 chưa lên máy chủ thật.
- Các nhánh đang sửa cùng tệp giao diện:
  - `002` phần dọn đồ cũ (US7, đang làm ở các worktree `lotus-us7-*`): sẽ xóa `FarmWorkApp.vue`, `ForecastWorkspace.vue`, `ForecastPlanner.vue`, `ForecastForm.vue`, `ForecastCloseAction.vue`, `ZonePlantingSchedule.vue`, `Vip126RollingForecast.vue`, `PlotMap.vue`, `OneDriveSupplyDialog.vue`, `OneDriveProcessWorkspace.vue`, `HarvestProfileSettings.vue`, `WorkMaterialSettings.vue`, `LotusImportPreview.vue`, `forecast-workspace.css`, `forecast-calendar.css`, `field-todo.css`, `farm-work.css`, `document-action.css`, `preload.js`, `offline.js`, `attempts.js`, `forecast-sample.js`, `forecast-planning.js`; và sửa `main.js`, `App.vue`, `router.js`, `store.js`, `domain.js`, `WorkspaceSidebar.vue`, `WorkspaceScopeBar.vue`, `MobileHome.vue`. Bộ giao diện mới không đầu tư vào các tệp sắp bị xóa.
  - `003` (mua hàng và ký điện tử, chưa commit): sửa `lotus-tokens.css` (thêm `--lotus-signature-ink`), `tests/design-tokens.test.js`, `buying-mobile.css`, `LotusMobileShell.vue`, `WorkspaceBar.vue`, `App.vue`, `router.js` và các màn mua hàng.

## Kiểm tra tự động

- Chạy trên máy chủ thử `/opt/lotus-004-test` (thư mục riêng, không phải bản thật), Node 24.22.
- `node --test tests/*.test.js` trong `frontend/`: **611 kiểm tra, 611 đạt, 0 lỗi**, 164 giây (chạy hai luồng).

## Dung lượng bản dựng (từ `lotus_farm/public/frontend/.vite/manifest.json` của `40f8330`)

| Ứng dụng | Kiểu (CSS) | Kiểu sau nén | Số tệp kiểu |
|---|---|---|---|
| Máy tính (`index.html`) | 296 KB | 57 KB | 5 |
| Kho (`warehouse.html`) | 315 KB | 75 KB | 10 |
| Mua hàng (`buying.html`) | 323 KB | 78 KB | 16 |
| Công việc (`work-mobile.html`) | 336 KB | 79 KB | 11 |
| Nhân sự (`hr-mobile.html`) | 280 KB | 68 KB | 6 |

Ngưỡng của SC-008 (không tăng quá 15% sau nén): máy tính 66 KB, Kho 86 KB, Mua hàng 90 KB, Công việc 91 KB, Nhân sự 78 KB.

## Tương phản của bộ màu hiện tại (chế độ sáng)

Đo bằng `frontend/tests/support/css-tokens.mjs`:

| Cặp chữ trên nền | Tỉ lệ | Đạt 4,5:1 |
|---|---|---|
| `--lotus-text` trên `--lotus-surface` | 13,26 | đạt |
| `--lotus-muted` trên `--lotus-surface` | 5,36 | đạt |
| `--lotus-subtle` trên `--lotus-page` | 3,70 | không |
| `--lotus-primary` trên `--lotus-surface` | 5,48 | đạt |
| `--lotus-success` trên `--lotus-success-soft` | 4,40 | không |
| `--lotus-warning` trên `--lotus-warning-soft` | 4,16 | không |
| `--lotus-danger` trên `--lotus-danger-soft` | 5,96 | đạt |
| `--lotus-info` trên `--lotus-info-soft` | 6,08 | đạt |

Ở chế độ tối, mọi cặp trên đều đạt (5,86 đến 13,10).

## Ảnh chụp trước khi làm

- Trang mẫu hiện tại (dựng trên máy chủ thử bằng `vite.showcase.config.js`): nút "Lưu" và nút "Xóa" cùng màu đỏ; cột số trong bảng mẫu canh trái.
- Ảnh các màn Hôm nay, Màu dây và thu hoạch, Giao việc theo vòng, Báo cáo tuần, Xưởng, Kho (máy tính) và Báo cáo hôm nay, hộp nhập lô (điện thoại) lấy từ lần kiểm tra của spec 002.

## Cách chụp ảnh thử

Trang mẫu được dựng trên máy chủ thử, phục vụ nội bộ ở cổng 8704 (chỉ trong máy chủ), chụp bằng Chromium không giao diện rồi tải ảnh về để xem. Không chạy trình duyệt hay bản dựng trên máy làm việc.

## Kết quả sau đợt 1 (10/11/2026, 21:45)

- Toàn bộ test frontend trên `/opt/lotus-004-test`: **663 kiểm tra, 663 đạt, 0 lỗi** (611 test cũ vẫn đạt; 52 kiểm tra mới).
- Hai test cũ được sửa cho đúng thay đổi có chủ đích, giữ nguyên ý kiểm tra:
  - `lot-entry-model.test.js`: màu dây giờ là token, không còn mã hex.
  - `ribbon-board.mount.test.js`: thẻ đợt màu có bố cục mới.
- Hai test đổi chỗ đọc bảng biểu tượng sang `icon-paths.js`: `ui-status.test.js`, `workspace-sidebar.mount.test.js`.
- Bản dựng thật (`vite build` ra thư mục riêng) chạy không lỗi. Kiểu sau nén so với mốc:

  | Ứng dụng | Trước (byte) | Sau (byte) | Tăng | Ngưỡng 15% |
  |---|---|---|---|---|
  | Máy tính | 58.526 | 67.168 | 14,8% | đạt |
  | Kho | 76.766 | 85.825 | 11,8% | đạt |
  | Mua hàng | 80.321 | 89.435 | 11,3% | đạt |
  | Công việc | 80.437 | 89.514 | 11,3% | đạt |
  | Nhân sự | 69.411 | 78.481 | 13,1% | đạt |

- Tương phản: 60 cặp ở ba chế độ đều đạt ngưỡng (`design-tokens-contrast.test.js`). Ba cặp cũ không đạt (chữ gợi ý 3,70; đạt 4,40; cảnh báo 4,16) nay đạt (5,14; 6,05; 6,62).
