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

## Chưa kiểm

- **Chưa mở bằng trình duyệt thật ở 320, 390, 844 và 1440 px.** Các công cụ trên chạy bằng Happy DOM, không có máy dựng bố cục, nên không phát hiện được tràn ngang hay chữ bị cắt. Cần một lượt mở tay hoặc Playwright trên site thử cho các màn mới:
  - Hóa đơn chờ nhập, biểu mẫu nhập hóa đơn (khung xem file cạnh biểu mẫu trên máy tính);
  - Công nợ (thẻ tổng, tuổi nợ, danh sách nhà cung cấp), sổ chi tiết, biểu mẫu phiếu chi, chi tiết phiếu chi;
  - khối người giao hàng và chi tiết phiếu nhập trên điện thoại.
- Chưa có test mount riêng cho Sổ chi tiết công nợ. Phần máy chủ của màn này đã có test tích hợp.
- Các bản in mới (`/lotus/in-hoa-don`, `/lotus/in-phieu-chi`, `/lotus/in-doi-chieu`, phiếu nhập có chữ ký người giao) mới được kiểm nội dung HTML và việc tạo PDF trong test tích hợp, chưa xem bằng mắt trên giấy A4.
