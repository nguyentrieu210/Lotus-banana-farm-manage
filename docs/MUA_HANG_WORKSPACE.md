# Mua hàng nối kho và tài chính

Phạm vi được chốt: nguyên vật liệu, công cụ, tài sản và dịch vụ. Chứng từ ERPNext là nguồn gốc duy nhất; không tạo sổ kho hoặc sổ công nợ song song.

## Luồng

Đề nghị (Material Request) → báo giá (Supplier Quotation) → duyệt đơn (Purchase Order, giữ chuỗi người ký) → nhận hàng/nghiệm thu (Purchase Receipt) → hóa đơn (Purchase Invoice) → thanh toán (Payment Entry / Journal Entry).

Tiền cá nhân chi hộ được ghi từng giao dịch trong Lotus Purchase Funding. Kế toán phân loại khoản phải hoàn hoặc vốn góp, chọn tài khoản đã cấu hình, trình kế toán trưởng và giám đốc ký. Hoàn ứng là dòng tiền công ty, không cộng lần nữa vào tiền trả nhà cung cấp.

## Điều kiện nghiệm thu

- [x] Cả bốn loại mua, nhận/nghiệm thu từng phần, tài sản từng chiếc.
- [x] Báo giá quy về ĐVT kho, có thuế, vận chuyển, hạn giao và lý do chọn theo dòng.
- [x] Import Excel xem trước, ánh xạ danh mục/ĐVT, lỗi từng dòng, fingerprint và chống gửi trùng; chỉ tạo nháp.
- [x] Chi hộ, vốn góp, tạm ứng NCC và hoàn từng phần có giới hạn, khóa, bằng chứng và chữ ký.
- [x] API/Desk không vượt quyền hoặc thay nội dung đã ký.
- [x] Báo cáo theo ngày từng giai đoạn, công nợ tại ngày chốt từ sổ, xuất đủ dữ liệu đã lọc.
- [x] Giao diện desktop /lotus/mua-hang, Kho dùng chung; PWA giữ điều hướng hiện hành.
- [x] Unit, integration trên site riêng, build, kiểm tra PWA 320px.
- [ ] Merge, backup, kiểm tra schema, migrate, live smoke và ảnh xác nhận.

## Dữ liệu nghiệm thu

Thư mục nguồn `Downloads/New folder (3)` chỉ dùng xem trước/UAT, không nhập lại giao dịch lịch sử vào live. Phân bón/thuốc tháng 10; vật tư tháng 11. Hai ảnh hóa đơn máy tính là một chứng từ; báo giá máy chấm công không phải thanh toán; canxi có phí vận chuyển; máy in ghi đã trả 0; mỡ bò chưa giao không nhập kho.

Triển khai cộng thêm trường/DocType, không sửa cờ Item, không ghi lại chứng từ cũ. Tài khoản tiền chi hộ/vốn góp do kế toán trưởng cấu hình, không mặc định số tài khoản. Khi thiếu cấu hình, chặn duyệt giao dịch tương ứng.

ERPNext cần bật `Buying Settings.allow_multiple_items` để cùng một tài sản xuất hiện theo từng chiếc trên phiếu nhận và hóa đơn. Migration bật thiết lập native này; lượng nhận vẫn kiểm tra tổng theo dòng đơn gốc, không sinh thêm Stock Entry. Người thu mua chỉ được chọn tài khoản phục vụ chứng từ native; quyền ghi sổ và duyệt chi giữ riêng cho kế toán/người ký.

## Kiểm chứng trước phát hành

- Frontend: 448 test qua, build Vite qua; kiểm tra DOM form mua chung của Kho/Mua hàng qua. Thao tác Tạo đơn / Nhập theo đơn từ thanh Kho chờ catalogue sẵn sàng, rồi mở cùng form hoặc lọc các đơn chờ nhận.
- Python: 255 test, một test không áp dụng được bỏ qua theo bộ kiểm tra hiện hữu.
- ERPNext thật trên `procurement.test`: 16 ca qua, có bốn loại mua, VAT trộn, vận chuyển, dịch vụ, tài sản từng chiếc, tạm ứng tiền công ty/chi hộ, công nợ quá khứ, hoàn ứng, trả/hủy, chứng từ native cũ và Excel đầy đủ.
- Ba ca đồng thời qua: khóa trùng yêu cầu, giữ chỗ công nợ, giữ chỗ hoàn ứng. MariaDB 11.8 có snapshot conflict; client thử lại toàn bộ request với cùng idempotency key.
- File gốc được đọc thử: 18 dòng phân bón + 31 dòng thuốc tháng 10, 23 dòng vật tư tháng 11, 192 dòng báo giá. Loại bảng tính số cây/lô ra khỏi dòng cần mua; quy đổi 33 can × 20 lít thành 660 lít. Giá báo đã gồm VAT cần xác nhận thuế trước khi nhập.
- PWA Mua hàng/Kho/Công việc: 320px, 390px và 844px, không tràn ngang; gợi ý mặt hàng, thêm dòng và cảnh báo rời form hoạt động.

## Vận hành

Mở `/lotus/mua-hang` trên máy tính; tab Mua hàng trong Kho dùng cùng component. PWA `/buying` mở các bước mới qua “Báo giá, nghiệm thu & thanh toán”. Kế toán trưởng chọn hai tài khoản chi hộ tại Thanh toán › Tài khoản chi hộ trước khoản chi hộ đầu tiên. Khoản vốn góp không được hoàn ứng. Hủy phiếu chưa ghi sổ giữ file gốc/lịch sử chi hộ và giải phóng số tiền đang giữ.
