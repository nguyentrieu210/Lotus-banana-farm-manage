# Rà giao diện spec 003 (T103)

Ngày rà: 10/11/2026. Nơi chạy: VPS, thư mục thử `/opt/lotus-003-test/app` (không phải site thật).

## Đã kiểm bằng máy

| Hạng mục | Công cụ | Kết quả |
|---|---|---|
| Toàn bộ test giao diện (có mount thật các màn mới) | `cd frontend && npm test` | 677/677 qua |
| Build | `npx vite build` | qua |
| Luồng mua trên điện thoại (Mua hàng) | `tools/verify_mobile_purchase_dom.mjs` | qua |
| Luồng Kho trên điện thoại, gồm nhận hàng một bước | `tools/verify_warehouse_mobile_dom.mjs` | qua |
| Khung máy tính (mật độ, chuyển khung nhìn, giao diện sáng/tối) | `tools/verify_desktop_workspace_dom.mjs` | qua |
| Chuẩn biểu mẫu và token màu cho `components/procurement`, `components/signing` | `form-standard.test.js`, `design-tokens.test.js` | qua |

Các màn mới có test mount riêng: Chờ tôi ký (điện thoại và máy tính), tấm ký, chi tiết đề xuất, chi tiết đơn mua, thẻ so sánh giá, người giao hàng khi nhận, chi tiết phiếu nhập (trả hàng, hủy, xác nhận), biểu mẫu nhập hóa đơn, Hóa đơn chờ nhập, chi tiết hóa đơn, Công nợ kèm biểu mẫu phiếu chi, chi tiết phiếu chi, nhập hóa đơn từ Tài chính.

## Kiểm bổ sung và phần còn lại

- **Trình duyệt thật (bổ sung cùng ngày):** Chromium không giao diện trên VPS mở bản sao site thật `mua.test` (dữ liệu thật đến 20:31 10/11) ở 1440, 844, 390 và 320 px: 10 màn máy tính (Đề xuất, Đơn mua, Phiếu nhận, Hóa đơn, Hóa đơn chờ nhập, Công nợ, Thanh toán, Chờ tôi ký, Kho nhập, Tài chính chờ hạch toán), 2 app điện thoại (Mua hàng, Kho), và các hộp Hóa đơn dịch vụ, Sổ chi tiết, Phiếu chi. 32 lượt mở: không tràn ngang, không lỗi trang. Đã xem bằng mắt ảnh chụp Công nợ, Phiếu chi, Hóa đơn dịch vụ: bố cục đúng.
- Ảnh chụp app điện thoại bị hộp "Thiết lập lần đầu" che (đúng thiết kế cho lần mở đầu); các màn mua hàng trên điện thoại được kiểm bằng `verify_mobile_purchase_dom.mjs`, `verify_warehouse_mobile_dom.mjs` và test mount.
- Chưa có test mount riêng cho Sổ chi tiết công nợ. Phần máy chủ của màn này đã có test tích hợp.
- Các bản in mới (`/lotus/in-hoa-don`, `/lotus/in-phieu-chi`, `/lotus/in-doi-chieu`, phiếu nhập có chữ ký người giao) mới được kiểm nội dung HTML và việc tạo PDF trong test tích hợp, chưa xem bằng mắt trên giấy A4.

## Kịch bản thao tác thật trên trình duyệt (10/11/2026, tối)

Kịch bản mục 3 của quickstart.md được chạy bằng Chromium trên VPS, với bản sao site thật `mua.test`:
- mỗi vai trò đăng nhập bằng tài khoản riêng;
- điện thoại 390×844, có chế độ chạm;
- máy tính 1440 px.

Ảnh chụp từng bước nằm ở `/opt/lotus-003-test/browser/uat/`. Lỗi giao diện tìm ra và đã sửa:

| Lỗi | Thấy ở | Sửa |
|---|---|---|
| Hộp "Ký bằng tài khoản đang đăng nhập?" nằm dưới tấm ký trên điện thoại: không bấm Ký được | Chờ tôi ký, điện thoại | `LotusMobileDialog` đưa hộp lên `body` (T108) |
| Biểu mẫu nhập hóa đơn báo "JSONDecodeError", không có file gốc bên cạnh | Hóa đơn chờ nhập, máy tính | Gửi danh sách phiếu nhận dạng JSON (T113) |
| Tên các file ở phiếu nhận dính liền nhau | Chi tiết hóa đơn | Tách bằng dấu "·" (T115) |
| Tải tệp hỏng hiện "PdfReadError" | Mọi chỗ tải tệp | Báo bằng tiếng Việt, gợi ý chọn hoặc chụp lại (T112) |

Đã xem bằng mắt các ảnh: biểu mẫu hóa đơn có file bên cạnh, chi tiết hóa đơn đã có phiếu chi (có dòng hướng dẫn "đảo phiếu chi trước"), Công nợ và phiếu chi.

Rà soát độc lập sau đó (11/11/2026) tìm thêm hai lỗi giao diện, đã sửa (T125):
- Hộp thoại điện thoại đưa ra `body` mất các luật biểu mẫu của `.lotus-pwa-shell`: ô nhập 14px làm iPhone phóng to khi chạm, mất viền và vòng focus. Sửa: lớp `lotus-pwa-dialog`, và mọi luật con của shell trong `mobile-ui.css` áp cả cho lớp này. Kiểm bằng `mobile-dialog-layer.test.js`.
- Thông báo lỗi tải tệp gọi mọi lỗi là "tệp hỏng", kể cả khi hết phiên đăng nhập. Sửa: chỉ lỗi đọc tệp mới báo tệp hỏng; hết phiên thì nhắc đăng nhập lại; lỗi máy chủ thì nhắc thử lại. Kiểm bằng `upload-failure.test.js`.
