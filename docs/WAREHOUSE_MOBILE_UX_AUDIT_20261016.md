# Audit trải nghiệm Kho trên điện thoại — 16/10/2026

Phạm vi: `/warehouse`, trang chính, tạo đơn mua, nhận theo đơn, nhập ngoài đơn, xuất, chuyển kho, lịch sử, xuất nhập tồn và tài khoản. Đã sửa trong source và triển khai vào backend/frontend local bằng image `lotus-warehouse-mobile-v6:20261016`.

## Các lỗi và thay đổi

| Vấn đề | Cách sửa |
|---|---|
| Trường kho ít lựa chọn vẫn bật bàn phím | Kho/công ty luôn dùng select của hệ điều hành; danh mục khác có tối đa 8 lựa chọn cũng dùng select. |
| Danh sách bị dòng dưới hoặc thanh dưới che | Teleport danh sách ra body, fixed overlay, tách khỏi stacking context của dòng. |
| Popup đứng sai khi cuộn, xoay máy, bật bàn phím | Theo dõi scroll/resize/visualViewport, đo lại bằng requestAnimationFrame; giới hạn vùng nhìn thấy, header và thanh điều hướng. |
| Chặn thao tác cuộn trên lựa chọn | Không preventDefault pointerdown touch; chỉ giữ focus cho chuột; phân biệt kéo và chọn. |
| Gõ tìm làm xóa link đang chọn và đơn vị | Gõ là tìm tạm, chỉ cập nhật dữ liệu khi chọn một kết quả. |
| IME tiếng Việt có thể chọn sớm khi Enter | Bỏ qua phím trong lúc isComposing, giữ hỗ trợ Arrow/Enter/Escape và cuộn tới kết quả đang chọn. |
| Nhiều popup cùng mở | Chỉ một picker hoạt động; đóng bằng chạm ngoài, đổi focus, Escape hoặc Back. |
| Thanh điều hướng chiếm chỗ khi bàn phím mở | Theo dõi visualViewport, ẩn thanh dưới khi bàn phím thu nhỏ vùng nhìn. |
| iPhone hẹp, tai thỏ, nằm ngang | Safe-area trên/dưới/trái/phải, font nhập tối thiểu 16px, ngày không ép tràn ngang, grid một cột ở màn rất hẹp và header ngắn khi nằm ngang. |
| Thiếu đường quay lại rõ ràng | Thanh quay lại theo màn hình, giữ header logo và thanh icon dưới. |
| Quay lại mất vị trí cuộn | Lưu vị trí vào history entry, phục hồi khi Back. |
| Phản hồi detail chậm kéo người dùng về màn cũ | Kiểm tra request, màn hình và công ty trước khi áp dụng phản hồi. Hủy hiệu lực truy vấn danh sách khi rời màn. |
| Có thể bấm phân trang khi đang tải | Khóa theo trạng thái tải của từng danh sách. Bấm lại tab hiện tại không tải lại và không reset danh sách. |
| Xác nhận rời form dùng window.confirm gây chặn trình duyệt | Dialog trong trang, lựa chọn Ở lại/Tiếp tục; Back đóng dialog; vẫn bảo vệ đóng/reload trang bằng beforeunload. |
| Dễ sửa dữ liệu lúc đang gửi | Khóa fieldset khi lưu; giữ chặn gửi lặp và chặn điều hướng lúc ghi. |
| Lỗi ở đầu trang không được thấy khi đang ở cuối form | Cuộn tới thông báo lỗi. Loader nổi không đẩy danh sách nhảy khi tìm kiếm. |
| Nhận hàng có thể bỏ trống ngày vì không nằm trong form native | Kiểm tra ngày trước khi gọi API tạo phiếu. |
| Thiếu cử chỉ chuyển tab | Vuốt ngang rõ ràng giữa 4 tab gốc; không áp dụng trên trường nhập, popup, dialog; bỏ qua cuộn dọc, vuốt chéo, chạm ngắn và mép 24px dành cho cử chỉ hệ điều hành. |

## Bằng chứng kiểm tra

- `node --test tests/*.test.js`: **92/92 pass**. Có thêm kiểm tra hình học popup khi bàn phím thu nhỏ/pan viewport và phân loại cử chỉ vuốt.
- `node tools/verify_warehouse_mobile_dom.mjs`: **15/15 pass**, mount Vue thực trong Happy DOM với API giả. Bao gồm native select, portal, tìm không dấu, không xóa link khi tìm, IME, touch không bị preventDefault, Escape, nhiều dòng hàng, keyboard viewport, dialog giữ/rời form, tránh tải lại tab, phản hồi detail muộn, vuốt/edge, ba form kho và kiểm tra ngày nhận.
- `node node_modules/vite/bin/vite.js build`: thành công. Cảnh báo Tailwind utility và chunk desktop lớn đã tồn tại; không phải lỗi build. Bundle Kho riêng không kéo AG Grid vào điện thoại.
- Trình duyệt Chromium: trang chính tại **320×568, 360×800, 375×812, 390×844, 430×932, 844×390**, không tràn ngang; thanh dưới bám đúng đáy; không có button/select hiển thị nhỏ hơn 44px.
- Form mua ở 390px: chọn vật tư không dấu, chọn kết quả, thêm dòng; popup là con trực tiếp body, z-index 200; hit-test ba kết quả thấy đúng option ở lớp trên.
- Sau khi phiên cũ được đóng: kiểm tra lại trực tiếp trên Chromium bản cuối, chọn kho nhận KHO 2, tìm/chọn vật tư, xác nhận **Ở lại** giữ nguyên vật tư, **Tiếp tục** rời form và mở Lịch sử/Xuất nhập tồn. Cả 4 form mua/xuất/chuyển/nhập ngoài đơn đều không tràn ngang và không có control hiển thị thấp hơn 44px tại 320×568, 375×812, 430×932, 844×390 (**16 tổ hợp**). Không gửi/lưu phiếu thật.
- Log ở `lotus-runtime/mobile-ux-unit-results.log` và `lotus-runtime/mobile-ux-dom-results.log` trong workspace chat.

Chạy kiểm tra DOM mà không thay dependency dự án: cài `happy-dom@21.0.1` vào thư mục runtime riêng, đặt biến `MOBILE_UX_HAPPY_DOM` thành file URL tới `happy-dom/lib/index.js`, rồi chạy tool ở trên. Tool chỉ dùng API giả, không tạo hay ghi sổ chứng từ thật. Mã biên dịch tạm nằm trong `frontend/node_modules/.mobile-ux-audit`.

## Giới hạn nghiệm thu

Chưa có kiểm tra trên Safari/iPhone hoặc Android vật lý, bàn phím thật, thanh địa chỉ động và quán tính vuốt của hệ điều hành. Không xem mô phỏng Chromium/Happy DOM là bằng chứng đạt cảm giác native trên mọi điện thoại. Phiên browser cũ từng bị window.confirm chặn input tự động; sau khi được đóng, dialog mới và luồng giữ/rời form đã kiểm tra lại thành công cả bằng mounted DOM và trình duyệt. Chưa thử giao dịch thật hay thay đổi số tồn trong audit này.

Compose trước thay đổi lưu tại `lotus-runtime/compose.pre-mobile-ux-v6.yaml`; image v5 vẫn còn để rollback giao diện. Các sửa đổi đã có sẵn trong checkout được giữ nguyên; không commit hoặc reset chúng.
