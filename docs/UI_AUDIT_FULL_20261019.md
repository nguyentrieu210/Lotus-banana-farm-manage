# Audit giao diện Lotus — đồng bộ & chuyên nghiệp (19/10/2026)

Phạm vi: giao diện máy tính `/lotus/*` và bốn PWA `/warehouse`, `/buying`, `/work`, `/hr-mobile` chạy tại cổng 8080. Bổ sung cho `UI_AUDIT_2026-10-19.md` (đợt đó đã gộp khung `App.vue`, toolbar/modal HR & Người dùng). Đợt này xử lý gốc rễ thiếu đồng bộ: hệ màu, chữ, component và trạng thái.

Quyết định: màu chính duy nhất **Đỏ Lotus `#c43224`** cho máy tính và PWA; chuẩn hóa cả desktop và PWA; được xóa phần thừa sau khi xác minh.

Cách kiểm tra: đọc mã nguồn, chạy test/build, chụp ảnh trước/sau bằng Playwright trên bản build (dữ liệu giả lập, không đăng nhập vào hệ thống thật) và các màn không cần đăng nhập trên 8080.

## Tóm tắt

| Nhóm | Trước | Sau giai đoạn 1 |
|---|---|---|
| Màu chính | 5 màu cạnh tranh: đất nung `#b8401b`, đỏ `#c43224`, cam PWA `#ed633c` (+6 sắc cam khác), indigo `#5262ce`, xanh lá `#173e2e` | 1 màu: Đỏ Lotus `#c43224` |
| Nguồn token | 8 file tự định nghĩa lại `--lotus-*`/`--primary`, màu cuối phụ thuộc thứ tự import | 1 file `lotus-tokens.css` |
| Mã màu cứng | ~1.010 mã hex khác nhau trong CSS/`<style>` | 0 (trừ trắng/đen và bóng trong suốt), có test chặn |
| Font | 5 font stack; PWA không tải Inter | 1 stack Inter cho cả máy tính và PWA |
| Dark mode | Tailwind `dark:` và token frappe-ui không bao giờ bật (preset dùng `[data-theme=dark]`, app dùng `.dark`) | Đồng bộ `.dark` + `data-theme` |

## Danh sách vấn đề

Mức độ: **Cao** = thấy rõ/ảnh hưởng nhận diện hoặc khả năng dùng; **TB** = thiếu nhất quán; **Thấp** = trau chuốt.

| # | Khu vực | Vấn đề | Mức | Vị trí | Đề xuất | Trạng thái |
|---|---|---|---|---|---|---|
| 1 | Toàn hệ thống | 5 màu thương hiệu khác nhau giữa desktop, Kho, PWA | Cao | `desktop-system.css`, `compact.css`, `mobile-ui.css`, `attio.css`, `style.css` | Một token `--lotus-primary` | Đã xử lý (GĐ1) |
| 2 | Toàn hệ thống | Token định nghĩa lại ở 8 file, màu phụ thuộc thứ tự CSS | Cao | `src/main.js` nạp 18 stylesheet | `lotus-tokens.css` duy nhất, nạp đầu tiên | Đã xử lý (GĐ1) |
| 3 | Toàn hệ thống | ~1.010 mã hex cứng, nhiều sắc gần giống nhau | Cao | CSS + `<style>` của 6 component | Thang màu `--lotus-<nhóm>-<bậc>` | Đã xử lý (GĐ1) |
| 4 | PWA | Font hệ thống thay vì Inter, khác desktop | TB | `*-mobile.css` | `--lotus-font` + nạp Inter | Đã xử lý (GĐ1) |
| 5 | Desktop | Dark mode Tailwind/frappe-ui không kích hoạt | TB | `tailwind.config.js`, `workspace.js` | `darkMode:['selector','.dark']`, set `data-theme` | Đã xử lý (GĐ1) |
| 6 | Desktop | Biểu đồ Dự thu dùng màu cứng, không theo theme | TB | `DesktopForecastChart.vue` | Đọc token lúc vẽ | Đã xử lý (GĐ1) |
| 7 | PWA Nhân sự | `window.alert/confirm`, Vant trực tiếp, loading/empty riêng | Cao | `HrMobile.vue` | `useMobileConfirm`, `LotusMobileButton`, `LotusMobileFeedback` | Đã xử lý (GĐ1) |
| 8 | PWA | 23 trường không có tên truy cập (label rời không gắn) | Cao | Kho, Công việc, Mua hàng, form đơn mua | `aria-label` | Đã xử lý (GĐ1) |
| 9 | PWA | Vùng chạm 28–36px; quy tắc 28px và 44px mâu thuẫn | TB | `mobile-ui.css`, `warehouse-mobile.css`, `CccdQrScanner.vue` | 44px qua `--lotus-touch` | Đã xử lý (GĐ1) |
| 10 | PWA | Hộp thoại xác nhận không có tên truy cập | TB | `LotusMobileDialog.vue` | Tự gắn `aria-labelledby` theo h2 | Đã xử lý (GĐ1) |
| 11 | PWA | 4 kiểu trạng thái trống khác nhau | TB | `.buy-empty`, `.mobile-empty`, `<p>` trơn | `.mobile-empty` chung | Đã xử lý (GĐ1) |
| 12 | PWA Nhân sự | Trạng thái ứng viên hiện mã tiếng Anh (New, Interview…) | TB | `HrMobile.vue` | Từ điển trạng thái | Đã xử lý (GĐ1) |
| 13 | Desktop | Chữ lẫn Anh–Việt: "Lưu offline", "Tạo staging", "Mapping…", "Hash…", "Sheet nguồn", "UI hiện trường" | TB | `App.vue`, `labels.js`, `www/lotus.py` | Việt hóa | Đã xử lý (GĐ1) |
| 14 | Desktop | 4 kiểu hộp thoại: `WorkspaceModal`, `<dialog class="stock-dialog">`, div `.modal-backdrop`, `window.confirm` | Cao | StockApp, TimekeepingApp, WarehouseBuyingLite, WarehousePlanning, FarmWorkApp, App.vue, HrOperations | Chuẩn `WorkspaceModal` + `useConfirm` | GĐ2 |
| 15 | Desktop | Không có hệ thông báo chung (`.notice`, `.hr-ops-notice`, `.error`, `.stock-error`) | TB | nhiều file | `WorkspaceNotice` | GĐ2 |
| 16 | Desktop | Nút/select/ngày native song song shadcn | TB | PlanNormSettings, Vip126RollingForecast, FarmWorkApp, ExcelHeader, ForecastPlanner | `UiButton`, `UiSelect`, `UiInput` | GĐ2 |
| 17 | Desktop | Bảng HTML thô song song AG Grid | TB | HrApp, HrOperations, PlanNormSettings, FarmWorkApp, ForecastWorkspace | `DataTable` hoặc class bảng chung | GĐ2 |
| 18 | Toàn hệ thống | Icon là ký tự chữ (↗ ↻ ◌ › ⟳ ☀ ×) trộn với icon | Thấp | WarehouseMobile, BuyingMobile, MobileLiveSearch, CccdQrScanner, sidebar | Bộ icon thống nhất | GĐ2 |
| 19 | PWA | Logic `openSetup/confirmLeave/logout/swipe` chép 3–4 lần | TB | Buying, Warehouse, Work, Hr | composable dùng chung | GĐ2 |
| 20 | Desktop | Liên kết cuối sidebar giãn cách bất thường | Thấp | sidebar `App.vue` | Gom nhóm liên kết | GĐ2 |
| 21 | Mã thừa | 5 entry HTML không URL nào phục vụ (`assign/stock/timekeeping/farm-work/hr.html`) + shell `stock-shell` cũ | TB | `vite.config.js`, `*-main.js`, `stock.css` | Xóa sau xác minh | GĐ3 |
| 22 | Mã thừa | CSS header/bottom PWA cũ (v1/v2/v3) không còn dùng | Thấp | `warehouse-mobile.css`, `buying-mobile.css` | Xóa | GĐ3 |
| 23 | Tài liệu | `UI_STACK.md` mô tả theme indigo, không khớp mã | Thấp | `docs/UI_STACK.md` | Cập nhật | GĐ3 |
| 24 | Toàn hệ thống | Trang `/login` và Desk `/app` là giao diện Frappe gốc tiếng Anh, logo Frappe, nút đen | Cao | `hooks.py` | Theme Desk/login theo token | GĐ4 (cần duyệt riêng) |
| 25 | Desktop | `App.vue` 72 KB chứa mọi trang bằng `v-if` | TB | `App.vue`, `router.js` | Tách component theo route | GĐ4 (cần duyệt riêng) |
| 26 | Kiểm thử | Test chủ yếu đọc mã nguồn bằng regex, chưa mount component | TB | `frontend/tests` | Playwright visual regression | GĐ4 |

## Token chuẩn (`frontend/src/lotus-tokens.css`)

| Nhóm | Giá trị |
|---|---|
| Màu chính | `--lotus-primary` = `#c43224` (hover `#a3291d`, nhạt `#fef3f1`, chữ trên nền chính trắng — tương phản 5,5:1) |
| Thang màu | `primary`, `neutral`, `success`, `warning`, `info`; bậc 50–900 (neutral 0–950). Giá trị cố định, không đổi theo theme |
| Ngữ nghĩa | `--lotus-page`, `--lotus-surface`, `--lotus-text`, `--lotus-muted`, `--lotus-border`, `--lotus-success/warning/danger/info` (+`-soft`) — đổi theo `.dark` |
| Chữ | Inter; 11 / 12 / 13 / 14 / 16 / 20 / 24px |
| Khoảng cách | 4 / 8 / 12 / 16 / 24 / 32px |
| Bo góc | 6 / 8 / 10 / 12 / 16px |
| Bóng | `sm`, `md`, `lg` |
| Kích thước | điều khiển desktop 36px, vùng chạm PWA 44px |

Lưu ý: màu "nguy hiểm" (`--lotus-danger` `#b42318`) cùng họ đỏ với màu chính; luôn đi kèm nhãn/biểu tượng rõ nghĩa, không chỉ dựa vào màu.

## Lộ trình

1. **GĐ1 — Quick wins** (xong): một nguồn token, màu/chữ thống nhất, dark mode, a11y PWA, Nhân sự PWA theo chuẩn, Việt hóa, test chặn tái phát.
2. **GĐ2 — Hợp nhất component**: hộp thoại, thông báo, nút/chọn/ngày, bảng, trạng thái trống/tải desktop, icon, logic PWA dùng chung.
3. **GĐ3 — Dọn dẹp**: xóa entry/CSS thừa, cập nhật tài liệu, mở rộng test.
4. **GĐ4 — Dài hạn (duyệt riêng)**: theme Desk/login, tách `App.vue`, visual regression.

## Kiểm tra GĐ1

- `npm test`: 241/241 đạt (thêm `design-tokens.test.js`: một màu chính, token nạp đầu tiên, không định nghĩa lại token, không mã hex mới, một font, PWA không dùng alert/confirm). Test đã được thử bằng cách chèn màu lạ: báo lỗi đúng.
- `npm run build` thành công.
- Ảnh trước/sau (bản build, dữ liệu giả lập) Hôm nay, Kho, Nhân sự, Công việc @1440/1024 sáng/tối; bốn PWA @320/390: bố cục không đổi, không tràn ngang, màu chính đồng nhất.
