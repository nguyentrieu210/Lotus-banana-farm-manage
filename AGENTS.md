# Quy ước giao diện theo yêu cầu người dùng

- Giao diện bảng phải gọn. Không thêm khối tiêu đề lớn, breadcrumb, mô tả nghiệp vụ, phạm vi kho lặp lại hoặc nhóm chọn mật độ phía trên các bảng.
- Tên màn hình được thể hiện ở thanh điều hướng và mục đang chọn. Phía trên bảng chỉ giữ bộ lọc, tìm kiếm và thao tác cần thiết.
- Không thêm mô tả, chú giải hoặc câu hướng dẫn thừa để trang trí bảng. Thông báo lỗi, trạng thái trống và hướng dẫn bắt buộc để nhập liệu đúng vẫn được giữ khi cần.
- Áp dụng quy ước này cho các bảng mới và những bảng đang được chỉnh sửa; không tự thêm lại mô tả trong các lần cải tiến giao diện sau.
- Thanh lọc trên máy tính phải nằm trên một hàng: kho, từ ngày, đến ngày, làm mới và tìm kiếm. Không xếp hai trường ngày thành cột hoặc cho thanh lọc xuống nhiều hàng; màn hẹp được cuộn trong chính thanh lọc khi cần.

## Chuẩn PWA điện thoại (yêu cầu người dùng 17/10/2026)

- Toàn bộ PWA điện thoại dùng Vue 3 và Vant 4. Dùng chung LotusMobileShell, LotusMobileHeader và LotusMobileBottomNav; không tạo header/bottom hoặc bộ component riêng cho từng app.
- Component chung ở frontend/src/components/LotusMobile*.vue. Token, spacing, safe-area và bố cục chỉ định nghĩa ở frontend/src/mobile-ui.css và mobile-ui-theme.js. Kho, Mua hàng, Công việc và các PWA mới cùng dùng chuẩn này.
- Nút, trường nhập, lựa chọn, hộp thoại, thao tác trang chủ dùng wrapper Vant chung. Input native cần thiết cho ngày, số, file, bàn phím và validation HTML được giữ bên trong component chung.
- Header một hàng; điều hướng dưới dùng biểu tượng gọn, có tên truy cập đầy đủ, ẩn khi bàn phím mở. Không lặp tiêu đề lớn/mô tả trang trí. Không tràn ngang ở 320px; popup và nội dung không bị header/bottom che.
- Chuẩn hóa giao diện không đổi API, phân quyền, trạng thái chứng từ, chống gửi trùng, xác nhận rời form hoặc cách tách service worker giữa các PWA.

- PWA Kho, Mua hàng và Công việc có manifest/service worker độc lập. Tìm/chọn dữ liệu phải có gợi ý khi gõ, không bắt Enter; giữ IME và cuộn popup.
- Mỗi lần sửa UI điện thoại phải chạy frontend unit tests, build và kiểm tra cả ba PWA ở màn hẹp. Chi tiết: docs/MOBILE_UI_STANDARD.md.

- Header PWA dùng màu đỏ Lotus và logo đủ lớn, rõ chữ; giữ một hàng ở 320px. Không tự thu nhỏ logo về biểu tượng 30px.
- Các luồng liên quan giữa app phải dùng chung cả component và logic: tạo/sửa đơn mua, tạo nhà cung cấp, xem đơn mua của Kho và Mua hàng dùng MobilePurchaseOrderForm, MobileSupplierForm, MobilePurchaseOrderDetail và mobile-purchase.js. Không sao chép form riêng từng app.
- Named link (vật tư, nhà cung cấp, đề nghị) luôn tìm/chọn cùng một cách dù danh sách ít hay nhiều. Chỉ dùng selector native khi khai báo searchable=false cho lựa chọn ngắn như kho/công ty; lỗi, cảnh báo và xác nhận dùng component/composable chung.
