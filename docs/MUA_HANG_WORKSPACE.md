# Mua hàng nối kho và tài chính

## Hoàn thiện mua hàng và ký điện tử (spec 003, 10/11/2026)

Tài liệu đầy đủ: `specs/003-mua-hang-ky-dien-tu/` (spec, plan, research, data-model, contracts, quickstart, tasks).

Một khoản mua đi một đường: **đề xuất → đơn mua → nhập kho → hóa đơn NCC → công nợ → trả tiền**, làm được trên điện thoại và máy tính, không mở ERPNext Desk.

| Bước | Quy tắc | Mã chính |
|---|---|---|
| Đề xuất mua | Một tên giai đoạn cho mọi người xem; đóng phần chưa mua và hủy có lý do | `proposal_rules.stage`, `purchase_proposal.py` |
| Báo giá | Lựa chọn báo giá lưu trên dòng đề xuất; chọn giá không thấp nhất phải có lý do | `procurement.choose_quote` |
| Đơn mua | Giám đốc được chỉ định ký mọi đơn; lưu đơn trả ngay các dòng sẽ bị chặn | `purchasing.check_submission`, `purchase_flow.order_issues` |
| Nhập kho theo đơn | Một bước; cần người giao ký kèm họ tên hoặc ảnh phiếu giao; xác nhận là thủ kho ký; lưu PDF | `warehouse_planning.receive_order`, `purchase_flow.receipt_evidence`, `receipt_signed` |
| Hóa đơn NCC | Một lõi cho mọi đường nhập; gõ tay, file chỉ là bằng chứng; hộ kinh doanh không ghi 1331; tổng in lệch tối đa 1 đ mỗi dòng | `finance/supplier_invoice.py` |
| Công nợ | Theo ngày chốt: tuổi nợ, đến hạn 7 ngày, hàng chưa có hóa đơn, sổ chi tiết, biên bản đối chiếu | `procurement_queries.payables`, `supplier_statement`, `unbilled` |
| Phiếu chi | Một phiếu trả nhiều hóa đơn, phần vượt ghi tạm ứng; ký đủ mới ghi sổ; lưu PDF | `finance/supplier_payment.py` |

Tên trạng thái dùng chung nằm ở `lotus_farm/purchase_status.py` và `frontend/src/purchase-status.js`. Hàng mua lẻ không qua đơn gọi là **Mua nhanh** ở mọi màn.

Trang in mới: `/lotus/in-don-mua`, `/lotus/in-hoa-don`, `/lotus/in-phieu-chi`, `/lotus/in-doi-chieu`; phiếu nhập in tại `/lotus/in-phieu` có chữ ký người giao.

Thiết lập ERPNext do `procurement_setup.install` đặt: cho phép hóa đơn khác giá đơn mua (Lotus bắt buộc ghi lý do), giá vốn theo giá hóa đơn.

Giới hạn hiện tại: một hóa đơn chưa gồm được cả phiếu nhận theo đơn và phiếu Mua nhanh; nhập thành hai lần với hai phiếu khác loại sẽ bị chặn trùng số hóa đơn.

Kiểm thử: `tools/test_site_procurement.sh` dựng bộ thử dùng-rồi-bỏ `procurement.test`; các script `tests/integration/verify_procurement*.py` và `verify_purchase_flow.py` chạy trên đó.

## Luồng đề xuất mua ngày 07/11/2026

Lotus lập Đề xuất mua độc lập theo bộ phận, lý do, kho nhận, vật tư, số lượng và ngày cần. Giá dự kiến có thể để trống. Mọi đề xuất mới ký đủ Người đề xuất → Phụ trách bộ phận → Kế toán/mua hàng → Giám đốc. Bổ sung giá sau khi ký trả phiếu về người đề xuất để gửi vòng ký mới. Các cửa tạo từ Kho và API cũ cùng tạo nháp và mở quy trình ký này.

Nhu cầu cấp cho công việc là nguồn tham khảo để lập đề xuất phần thiếu. Liên kết tham khảo theo dòng được giữ riêng với nguồn cấp vật tư. Phiếu xuất kho thực tế mới ghi nhận lượng đã cấp cho công việc.

Đề xuất và đơn mua hiển thị tiến độ đặt, nhận, hóa đơn cùng các chứng từ liên quan. Nhận hàng, hóa đơn và thanh toán có trạng thái riêng. Mua nhanh được ghi rõ là không qua đề xuất/đơn, phiếu chưa có hóa đơn hiện ở Chờ hạch toán cùng lượng còn lập hóa đơn và đường mở phiếu nhận.

Chính sách được giới hạn theo `lotus_purchase_flow_company` trong cấu hình site. Dấu mốc `lotus_purchase_flow_since` cho phép đơn mua cũ xử lý tiếp. Đề xuất đã duyệt giữ lịch sử, lượt ký 2 bước chưa hoàn tất được trả lại và gửi vòng 4 bước. Site khác tiếp tục dùng chính sách hiện có.

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

Mở `/lotus/mua-hang` trên máy tính; Kho có bốn mục Tồn kho, Nhu cầu vật tư, Phiếu kho, Sổ kho; Thiết lập kho là thao tác riêng. Mua hàng nằm ở menu riêng, không lồng trong Kho. PWA `/buying` mở các bước mới qua “Báo giá, nghiệm thu & thanh toán”. Kế toán trưởng chọn hai tài khoản chi hộ tại Thanh toán › Tài khoản chi hộ trước khoản chi hộ đầu tiên. Khoản vốn góp không được hoàn ứng. Hủy phiếu chưa ghi sổ giữ file gốc/lịch sử chi hộ và giải phóng số tiền đang giữ.


## Hoàn thiện phân hệ ngày 24/10/2026

- Menu Mua hàng riêng: đề nghị, báo giá, đơn, nhận/nghiệm thu, hóa đơn, thanh toán, công nợ, báo cáo; danh mục NCC và hàng mua. `buying_view`/`stock_view` giữ màn khi tải lại; công ty/kho được chuyển cùng thao tác. Rời biểu mẫu chưa lưu cần xác nhận.
- NCC dùng Supplier/Contact/Address/Bank Account native; nhóm, loại, MST, liên hệ, địa chỉ, điều khoản thanh toán, ngừng dùng. Chỉ kế toán cập nhật ngân hàng; tài khoản mua hàng không đọc được số tài khoản qua API. Lưu có kiểm tra phiên bản, khóa và khóa chống tạo trùng.
- Hàng mua dùng Item/Item Group/UOM/Asset Category native; bảo toàn mã, loại và đơn vị gốc đã tạo; giữ quy đổi khi đã phát sinh sổ kho. Loại mua gợi ý cho mã mới không đổi cờ Item cũ.
- Thêm nhanh NCC/hàng từ đơn/báo giá không làm mất dòng đang nhập. Nhập theo đơn trong Kho dùng WarehouseReceiving, giữ phần chi phí thực nhận của PR #54 và quyền nhận hàng độc lập với quyền quản lý mua.
- Hóa đơn và các loại thanh toán có danh sách/chi tiết, lọc và phân trang máy chủ. Lập hóa đơn lấy phần chưa lập hóa đơn; có hạn trả, liên kết phiếu nhận/đơn, VAT và vận chuyển. Phiếu chi hộ đã hủy giữ chứng từ gốc; lần chi NCC đã hủy giữ mã lịch sử riêng kể cả khi số phiếu nháp được dùng lại.
- Công nợ tại ngày chốt từ Payment Ledger Entry, tách phải trả, quá hạn và tạm ứng. Hóa đơn điều chỉnh không ghi thêm tồn; hoàn tiền NCC dùng Payment Entry Receive có chuỗi ký, khóa số còn hoàn và chống gửi trùng. Báo cáo nguyên vật liệu trừ đúng tiền NCC hoàn về.
- API bổ sung: `procurement_masters.options/listing/detail/save`; `procurement_queries.invoices/invoice/payments/payables/supplier_history`; `procurement.billing_source`; `procurement_adjustments.credit_note/refund`. Các endpoint cũ giữ tương thích.
- Kiểm chứng: 454 frontend tests; 255 Python tests (một skip cũ); 27 ca integration, gồm 25 ca chạy toàn bộ và hai ca bổ sung về cả bốn loại Item mới và lịch sử phiếu đã hủy. Ca hoàn tiền được chạy lại sau khi siết kiểm tra chữ ký native. Build và kiểm tra DOM form mua dùng chung qua.
- Browser trên site test: lưu NCC đầy đủ từ đơn vẫn giữ vật tư và số lượng 2; hủy chuyển màn giữ form; Sổ kho giữ đúng sau reload; cả ba PWA ở 320/390/844px không tràn ngang, hồ sơ NCC ở 320px cũng đạt. Dữ liệu UAT chỉ ở `procurement.test`, không ghi vào live.
- GitHub Actions từng bị chặn trước khi chạy do billing/spending limit của tài khoản; không coi đây là CI xanh. Phát hành chỉ từ commit đã merge, có backup và so sánh số chứng từ, dữ liệu danh mục và hash GL/SLE trước/sau.

## Sửa nhập không theo đơn ngày 24/10/2026

Form Kho PWA trước đây không có lý do nhập và NCC nên không gửi được hai trường này; khi tài chính đã bật, máy chủ chặn lưu để tránh ghi sai tài khoản. Máy tính và điện thoại nay dùng chung `StockReceiptReason`: mua ngoài chọn NCC, thu hồi chọn lô theo từng dòng, thừa kiểm kê không cần NCC/đơn mua. Không bỏ kiểm tra tài khoản ở máy chủ. Nếu không tải được danh mục, form báo lỗi và cho thử lại; lưu chờ tải xong và kiểm tra các trường bắt buộc.

Khóa chống gửi trùng phiếu nhập bao gồm lý do và NCC. Kiểm chứng: 458 frontend tests, 255 Python tests (một skip cũ), ba ca ERPNext lưu/ghi sổ và đối chiếu tài khoản đối ứng, UI lưu nháp mua ngoài thành công trên site test. Ba PWA ở 320/390/844px và form thu hồi ở 320px không tràn ngang. Không tạo phiếu thử trên live.
