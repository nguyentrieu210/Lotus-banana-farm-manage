# Lotus Mobile PWA — triển khai bộ giao diện chung, 17/10/2026

## Phạm vi đúng

Ba PWA đang vận hành độc lập: **Kho** `/warehouse`, **Mua hàng** `/buying`, **Công việc ngoài vườn** `/work`.

Nền tảng đang sử dụng **Vue 3 + Vant 4**, không dùng shadcn-vue cho các màn hình PWA này. Các màn hình hiện đã tái sử dụng `LotusMobileShell`, `LotusMobileHeader`, `LotusMobileBottomNav`, `LotusMobileInput`, `LotusMobileSelect`, `LotusMobileFeedback`, `MobileLinkField`, `MobilePurchaseOrderForm`, `MobilePurchaseOrderDetail`, `MobileSupplierForm` và `useMobileConfirm`. Giữ nguyên lớp Frappe backend/API, phân quyền, tình trạng chứng từ và hàng chờ offline.

Báo cáo nghiên cứu cũ có thông tin từ các entry desktop `StockApp.vue`, `FarmWorkApp.vue`, `WorkspaceBar.vue` và `/lotus/mobile`; đây **không phải** là ba PWA mới đang triển khai. Không tái cấu trúc ba PWA theo lớp desktop hay tạo shell thứ hai.

## Đã xử lý trên mã nguồn làm việc (chưa phát hành)

1. **Một luồng cài PWA / bật thông báo**: chỉ `LotusMobileOnboarding.vue` nghe `beforeinstallprompt` và hướng dẫn iOS/Android; các nút cài trong Kho, Mua hàng, Công việc gọi `lotus:open-setup`. Không tự động xin quyền push khi không có thao tác người dùng.
2. **Giao diện hẹp, tương tác bằng tay**: `mobile-ui.css` bổ sung spacing/touch/focus, nút quay lại 44px, logo thu nhỏ có kiểm soát trên màn hình <= 360px, popup khi màn hình ngang thấp. Giữ logo `object-fit:contain` không xén chữ.
3. **Form dùng chung**: `LotusMobileInput` và `LotusMobileSelect` hỗ trợ `hint`, `error`, `aria-invalid` và text báo lỗi bằng Vant 4 mà không thay đổi v-model/field của nghiệp vụ.
4. **Cô lập CSS của Công việc**: `work-mobile-main.js` không nhập trực tiếp `warehouse-mobile.css`. Tạm thời dùng `mobile-work-legacy.css` lấy các rule tương thích cần thiết bằng `frontend/generate-work-compat.cjs`. Đây là bước tách phụ thuộc, chưa xóa sạch CSS cũ. Khi thay layout, vẫn phải kiểm tra hai app.
5. **Icon cài đặt PWA**: thêm icon `purpose:maskable` 512×512 cho từng manifest nhưng giữ icon thường 192/512 và giữ riêng `id`, `scope`, service worker cho ba app. Script `tools/create_mobile_maskable_icons.ps1` tái tạo icon.
6. **Kiểm thử**: bổ sung `frontend/tests/mobile-shared-plan.test.js`; sửa các bài kiểm thử cũ tìm chữ **Tiếp tục** thành nút hiện có **Rời đi**; `.github/workflows/quality.yml` chạy thêm `node tools/verify_mobile_purchase_dom.mjs` với Happy DOM 21.0.3.

## Kết quả kiểm tra ở môi trường làm việc

- `npm test` trong `frontend`: **149/149 pass** theo lần chạy ngày 17/10/2026.
- `node tools/verify_mobile_purchase_dom.mjs` tại gốc repo: **24/24 pass**, kiểm tra bằng dữ liệu giả, không ghi đơn/phiếu ERP thật.
- `npx vite build --outDir frontend/temp-mobile-ui-audit --emptyOutDir` trong `frontend`: **build thành công**. Vite vẫn cảnh báo lớp Tailwind có cú pháp mơ hồ và bundle AG Grid desktop lớn.
- **Chromium thật qua Playwright trên máy phát triển: 9/9 smoke đạt** (Kho, Mua hàng, Công việc × 320 px/390 px/landscape). Có chụp ảnh PNG của 9 màn hình và kiểm tra logo tải được, header không đè chuông, đúng 4 tab, không tràn ngang và không có runtime pageerror. Dữ liệu lấy từ mock API; chưa phải UAT nghiệp vụ thực tế.
- **Chưa xác nhận trên iPhone thật/Android thật**, chưa đánh giá ảnh baseline thủ công hoặc Safari, chưa làm UAT với người làm vườn/kho/mua hàng, chưa triển khai server production. CI bổ sung cần được GitHub chạy xác nhận trên nhánh đồng bộ.

## Gate nghiệm thu trước khi phát hành

| Nhóm | Điều kiện bắt buộc |
| --- | --- |
| Phạm vi | 3 PWA độc lập, icon/tên/manifest riêng, không đổi quy trình nghiệp vụ |
| Tự động | `npm test` và `node tools/verify_mobile_purchase_dom.mjs` qua, CI build xanh |
| Điện thoại | 320px, 390px, Android Chrome và iPhone Safari; chiều dọc/ngang; không bị tràn màn hình |
| Bàn phím và popup | Dòng đang nhập còn thấy được; tìm trực tiếp; IME tiếng Việt; cuộn popup không bấm nhầm; bottom nav không đè nút khi keyboard hiện |
| Header | Logo Lotus không mất chữ; nút back, thông báo, tiêu đề rõ ở 320px |
| Luồng Kho | Nhập theo đơn, nhập không theo đơn, xuất, chuyển, in phiếu, tìm kiếm, lọc |
| Luồng Mua hàng | Tạo đơn nháp, chọn NCC, duyệt đúng quyền, báo giá, nhận một phần/đủ, trạng thái và in/tải |
| Luồng Công việc | Giao việc, duyệt giá, báo công, chụp ảnh, offline queue, đồng bộ không ghi trùng |
| Cài/PWA | Cài độc lập ba icon, mở từ màn hình chính, iPhone Add to Home Screen, quyền push theo người dùng, logout hủy đăng ký đúng app |
| Phiên đăng nhập | Giữ hành vi guest riêng của `/buying` để không thoát khỏi phạm vi PWA sau khi hết phiên; Kho/Work hiện redirect login |
| An toàn dữ liệu | Không test giao dịch ghi sổ trên production; role Kho/Buyer/Tổ trưởng/Đội trưởng không vượt quyền |

## Quy trình phát hành và quay lại

1. **Không ghi đè worktree hiện tại**: đang có nhiều thay đổi chưa commit của nhiều tính năng, bao gồm file PWA untracked. Kiểm tra/dọn sạch và thống nhất nhánh nguồn trước khi stage/commit; tuyệt đối không `git add -A`, `reset --hard` hay force push trong nhánh làm chung.
2. Chụp màn hình baseline trên thiết bị thật và chạy QA ở site staging với từng vai trò. Kiểm tra trang độc lập `/warehouse`, `/buying`, `/work` cả sau khi cài PWA.
3. Tách PR theo nhóm giao diện chung, Kho/Mua, Work/CSS và test/PWA. Không trộn cập nhật backend giao dịch hay phát sinh chứng từ vào PR UI.
4. Release tuần tự, giữ bản build/manifest/assets trước đó để quay lại. Nếu gặp lỗi P0/P1, hoàn nguyên đúng bản build, kiểm tra cache của mỗi service worker và mở lại ba PWA để xác nhận.
5. Đối chiếu người dùng thực tế sau phát hành: logo, nút, keyboard, nháp, quyền duyệt, in, offline; quan sát lỗi, thời gian hoàn thành thao tác và gửi nhầm/trùng.

## Điểm còn phải làm sau khi code đã qua unit/DOM test

- Browser automation có mock server riêng cho cả ba PWA, ảnh baseline tại 320/390px; chạy với browser thực không thay thế bằng Happy DOM.
- Kiểm tra thủ công trên Android và iOS thật, cả trạng thái lần đầu cài, phiên hết hạn, push, service worker update và mạng chập chờn.
- Dọn các CSS legacy chỉ sau khi ảnh/luồng đã được kiểm chứng; tránh đổi nền Tailwind desktop trong cùng đợt.
- Giữ mã trên nhánh đồng bộ riêng, chỉ phát hành production sau khi CI và UAT thiết bị thật qua; cần lưu manifest/asset cũ và xác nhận không làm mất PWA người đang dùng.
