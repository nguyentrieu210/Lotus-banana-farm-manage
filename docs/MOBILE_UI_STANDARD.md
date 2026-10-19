# Chuẩn PWA điện thoại Lotus

Vant 4 (hiện pin 4.10.2), Vue 3. Áp dụng cho `/warehouse`, `/buying`, `/work`, `/hr-mobile` và các PWA mới theo yêu cầu người dùng 17/10/2026.

## Khung và component

- `LotusMobileShell`: ConfigProvider, theme chung, header, safe-area và bottom; truyền title, tabs, activeTab, back, disabled, keyboardOpen. Đặt nội dung trong main, không tự tạo thanh điều hướng.
- `LotusMobileHeader`, `LotusMobileBottomNav`: một hàng tiêu đề/logo rõ chữ trên nền đỏ Lotus và bốn tab icon có tên truy cập. Tiêu đề chỉ xuất hiện một lần.
- `LotusMobileAction`: thao tác trang chủ, Vant Button/Icon, sự kiện select; disabled chặn cả thao tác và callback.
- `LotusMobileButton`: type là HTML button/submit; variant là loại Vant. Giữ nút lưu và nút điều hướng tách biệt để tránh submit ngoài ý muốn.
- `LotusMobileInput`, `LotusMobileSelect`: Vant Field, giữ input/select native bên trong để không mất required/min/max/step, bàn phím số, chọn ngày và lựa chọn hệ điều hành.
- `MobileLinkField`, `MobileLiveSearch`: Vant Field, CellGroup và Button với gợi ý trực tiếp. Tìm không dấu; IME Enter không chọn sớm; gõ tìm không xóa liên kết đã chọn; popup tôn trọng viewport/header/bottom, kéo để cuộn không chọn nhầm.
- `LotusMobileDialog`: Vant Dialog với showModal/close, dùng cho mọi xác nhận (rời form, bỏ hàng chờ, xác nhận nghiệp vụ). Tự gắn tên hộp thoại theo tiêu đề h2 đầu tiên. Không dùng `window.alert/confirm`.
- Trạng thái trống dùng `<p class="mobile-empty">`, đang tải dùng `LotusMobileFeedback kind="loading"` ở cả bốn PWA.
- Trường có nhãn rời (`<label>` bên cạnh) phải truyền `aria-label` cùng nội dung cho component; vùng chạm tối thiểu `var(--lotus-touch)` (44px).

## Quy tắc bố cục

Nguồn token gốc: `frontend/src/lotus-tokens.css` (dùng chung với máy tính; màu chính Đỏ Lotus `#c43224`), nhập đầu tiên ở mỗi entrypoint sau CSS Vant. `mobile-ui-theme.js` (Vant) và các biến `--lotus-pwa-*` trong `mobile-ui.css` chỉ trỏ tới token, không ghi mã màu. CSS cuối cùng: `mobile-ui.css`, nhập sau CSS nghiệp vụ ở mỗi entrypoint. Không sao chép stylesheet để có một chuẩn khác cho từng app. Header 54px, bottom 60px cộng safe-area; content tối đa 600px, lề 12px ở màn 320px và 16px bình thường; field 16px để tránh iOS tự zoom. Grid trang chủ hai cột, thao tác chính một hàng. Ẩn bottom khi bàn phím mở. Bỏ tiêu đề lặp và mô tả trang trí; giữ hướng dẫn nhập đúng, trạng thái và lỗi cần thiết.

## Kiểm tra khi thay đổi

Chạy toàn bộ unit test frontend, build Vite và `tools/verify_mobile_purchase_dom.mjs` (bao gồm kiểm tra kho) (Happy DOM runtime riêng). Kiểm tra ba PWA trong Chromium: 320px, 390px và ngang; mở form, chọn vật tư, thêm dòng, quay lại khi có thay đổi, chuyển tab và popup. Không tạo/ghi sổ chứng từ thật để thử giao diện. API, quyền, chống gửi trùng và offline queue được giữ nguyên. Worker/manifest mỗi app tiếp tục độc lập; hash build tự cập nhật cache giao diện.

## Luồng dùng chung giữa các app

- `MobilePurchaseOrderForm` và `mobile-purchase.js`: cùng trường nhập, chọn đề nghị, mặt hàng, đơn vị, ngày giao, báo giá, validation, lưu đơn nháp, nhận diện đơn đã lưu và thử lại báo giá.
- `MobileSupplierForm`: cùng tên, người liên hệ, điện thoại, ghi chú; quay lại đơn đang nhập giữ các dòng và chọn NCC vừa lưu.
- `MobilePurchaseOrderDetail`: cùng thông tin/giá trị/dòng hàng/tệp đính kèm; nút duyệt, sửa, nhận hàng vẫn do quyền từng caller quyết định.
- `LotusMobileFeedback` và `useMobileConfirm`: thông báo và xác nhận của Kho, Mua hàng, Công việc và Nhân sự.
- Named link luôn searchable; searchable=false chỉ dành cho lựa chọn ngắn rõ ràng. Nút wrapper ánh xạ type sang Vant native-type; phải kiểm tra DOM type=submit của nút lưu, tránh chỉ kiểm tra source.
