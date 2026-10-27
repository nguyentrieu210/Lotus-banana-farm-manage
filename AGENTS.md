# Quy ước giao diện theo yêu cầu người dùng

- Giao diện bảng phải gọn. Không thêm khối tiêu đề lớn, breadcrumb, mô tả nghiệp vụ, phạm vi kho lặp lại hoặc nhóm chọn mật độ phía trên các bảng.
- Tên màn hình được thể hiện ở thanh điều hướng và mục đang chọn. Phía trên bảng chỉ giữ bộ lọc, tìm kiếm và thao tác cần thiết.
- Không thêm mô tả, chú giải hoặc câu hướng dẫn thừa để trang trí bảng. Thông báo lỗi, trạng thái trống và hướng dẫn bắt buộc để nhập liệu đúng vẫn được giữ khi cần.
- Áp dụng quy ước này cho các bảng mới và những bảng đang được chỉnh sửa; không tự thêm lại mô tả trong các lần cải tiến giao diện sau.
- Bảng dùng chung DataTable cố định header ở trên và dòng tổng ở dưới; chỉ thân dữ liệu cuộn. Container bọc bảng không được tạo thêm vùng cuộn dọc khiến header hoặc dòng tổng bị cuộn mất.
- Thanh lọc trên máy tính phải nằm trên một hàng: kho, từ ngày, đến ngày, làm mới và tìm kiếm. Không xếp hai trường ngày thành cột hoặc cho thanh lọc xuống nhiều hàng; màn hẹp được cuộn trong chính thanh lọc khi cần.

## Hệ màu chung (yêu cầu người dùng 19/10/2026)

- Màu chính duy nhất cho máy tính và PWA: Đỏ Lotus #c43224. Mọi màu, font, cỡ chữ, spacing, bo góc, bóng lấy từ frontend/src/lotus-tokens.css; không ghi mã màu hex trong CSS/`<style>` khác (trừ trắng/đen và bóng trong suốt). tests/design-tokens.test.js kiểm tra quy tắc này.

## Bộ component máy tính (từ 19/10/2026)

- Màn máy tính dùng primitive trong frontend/src/components/ui (shadcn-vue trên reka-ui): Button, Input/Select/Textarea bọc trong FormField (label, gợi ý, lỗi theo trường), Combobox (mọi ô chọn có tìm; SearchSelect/LinkPicker chỉ là lớp bọc), DatePicker/DateRangePicker (gõ được dd/mm/yyyy hoặc chọn lịch), DropdownMenu, Tooltip cho nút chỉ có icon, Popover, Sheet, Pagination, Skeleton, Toast (use-toast: thông báo thành công; lỗi chặn vẫn hiển thị cạnh biểu mẫu).
- Không tự viết lại popover/combobox/menu/date picker. Nội dung nổi trong hộp thoại modal phải render trong chính <dialog> (ui/portal-target.js).
- Xác nhận dùng useWorkspaceConfirm (máy tính) / useMobileConfirm (PWA), cùng lõi use-confirm-core.js. Bảng dùng DataTable (OpsList là lớp bọc). Icon dùng LotusIcon, không dùng ký tự.
- Hộp thoại máy tính chỉ dùng WorkspaceModal: v-model + title cho hộp thoại mới; `bare` + ref (showModal/close/open) cho form có markup riêng. Không thêm <dialog> thô (trừ quét camera).
- Component có hành vi (mở/đóng, lọc, chọn) cần test mount qua tests/support/mount.mjs (happy-dom), không chỉ kiểm tra regex mã nguồn.
- Xem trước toàn bộ component: `npm run dev` rồi mở /assets/lotus_farm/frontend/showcase.html (không build ra production).

## Chuẩn PWA điện thoại (yêu cầu người dùng 17/10/2026)

- Toàn bộ PWA điện thoại dùng Vue 3 và Vant 4. Dùng chung LotusMobileShell, LotusMobileHeader và LotusMobileBottomNav; không tạo header/bottom hoặc bộ component riêng cho từng app.
- Component chung ở frontend/src/components/LotusMobile*.vue. Màu, chữ, spacing gốc ở frontend/src/lotus-tokens.css (chung với máy tính); safe-area và bố cục PWA ở mobile-ui.css; mobile-ui-theme.js chỉ trỏ tới token. Kho, Mua hàng, Công việc và các PWA mới cùng dùng chuẩn này.
- Nút, trường nhập, lựa chọn, hộp thoại, thao tác trang chủ dùng wrapper Vant chung. Input native cần thiết cho ngày, số, file, bàn phím và validation HTML được giữ bên trong component chung.
- Header một hàng; điều hướng dưới dùng biểu tượng gọn, có tên truy cập đầy đủ, ẩn khi bàn phím mở. Không lặp tiêu đề lớn/mô tả trang trí. Không tràn ngang ở 320px; popup và nội dung không bị header/bottom che.
- Chuẩn hóa giao diện không đổi API, phân quyền, trạng thái chứng từ, chống gửi trùng, xác nhận rời form hoặc cách tách service worker giữa các PWA.

- PWA Kho, Mua hàng và Công việc có manifest/service worker độc lập. Tìm/chọn dữ liệu phải có gợi ý khi gõ, không bắt Enter; giữ IME và cuộn popup.
- Mỗi lần sửa UI điện thoại phải chạy frontend unit tests, build và kiểm tra cả ba PWA ở màn hẹp. Chi tiết: docs/MOBILE_UI_STANDARD.md.

- Header PWA dùng màu đỏ Lotus và logo đủ lớn, rõ chữ; giữ một hàng ở 320px. Không tự thu nhỏ logo về biểu tượng 30px.
- Các luồng liên quan giữa app phải dùng chung cả component và logic: tạo/sửa đơn mua, tạo nhà cung cấp, xem đơn mua của Kho và Mua hàng dùng MobilePurchaseOrderForm, MobileSupplierForm, MobilePurchaseOrderDetail và mobile-purchase.js. Không sao chép form riêng từng app.
- Named link (vật tư, nhà cung cấp, đề nghị) luôn tìm/chọn cùng một cách dù danh sách ít hay nhiều. Chỉ dùng selector native khi khai báo searchable=false cho lựa chọn ngắn như kho/công ty; lỗi, cảnh báo và xác nhận dùng component/composable chung.
