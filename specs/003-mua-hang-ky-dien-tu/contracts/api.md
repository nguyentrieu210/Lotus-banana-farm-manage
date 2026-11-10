# API Contracts

## Quy ước chung

- Mọi method là whitelisted method của Frappe, ghi theo `module.function`.
- **Ghi dữ liệu:** method ghi chỉ nhận POST và nhận `client_key` để chống gửi trùng. Hai lần gọi cùng khóa trả cùng một kết quả.
- **Phiên bản:** method sửa chứng từ nhận `modified`. Nếu lệch phiên bản, method báo "Chứng từ đã thay đổi. Tải lại trước khi thao tác."
- **Thông báo lỗi:** tiếng Việt.
- **Quyền:** máy chủ luôn kiểm lại quyền, trạng thái và phiên bản.

## Ký điện tử (`signing`)

| Method | Tham số | Kết quả | Thay đổi |
|---|---|---|---|
| `inbox` | `limit` (mặc định 100), `offset`, `chain` (tùy chọn) | `{rows, total}`. Mỗi dòng gồm:<br>• `doctype`, `name`, `chain`, `chain_label`, `step`, `step_title`<br>• `creator`, `creator_name`, `amount`, `currency`, `posting_date`, `notified_at`<br>• `desktop_url`, `mobile_url`, `print_url`, `modified` | Viết lại. Gộp mọi chuỗi; lọc theo `can_view` |
| `inbox_count` | – | `{count}` | Mới |
| `chain_status` | `doctype`, `name` | Như cũ, thêm:<br>• `designation` của từng bước<br>• `signed_copy` (`{url, pdf_sha256}` khi đã lưu bản PDF) | Đổi quyền sang `can_view` |
| `sign_many` | `items[]` (`doctype`, `name`, `modified`), `client_key` | `{results: [{doctype, name, ok, status, message}]}`. Mỗi chứng từ chạy savepoint riêng; thông báo gửi sau vòng lặp | Mới |
| `reassign` | `doctype`, `name`, `step`, `user`, `reason` | Trạng thái mới; ghi sự kiện REASSIGN | Bắt buộc lý do |
| `return_document` | `doctype`, `name`, `reason` | Trạng thái mới | Từ chối chuỗi có bước chốt (`purchase_order`, `payment_voucher`); các chuỗi này trả lại qua method riêng |
| `verify` | `dt`, `n`, `r`, `t` (công khai) | Như cũ, thêm `archive_match` (đúng hoặc sai) khi có bản PDF lưu | Băm lại file của `Lotus Signed Copy` |
| `open_targets` | `doctype`, `name` | `{desktop_url, mobile_url}` | Mới. Trang `/lotus/mo` dùng method này |

Ký từng chứng từ vẫn đi qua method của chuỗi:
- `purchase_proposal.sign`;
- `purchasing.approve_order`;
- `finance.payments.sign_payment`;
- `signing.confirm` cho phiếu kho.

Mọi method ký đều ghi nhật ký có IP, thiết bị, vai trò và chức danh. Khi ký đủ, chúng đều đi qua `signing._completed`.

**Bỏ:**
- `digital_signature.initial_purchase_order`
- `digital_signature.create_signing_challenge`
- `digital_signature.signing_challenge_details`
- tham số `sign_token` của `purchasing.approve_order`

## Chữ ký của tôi (`digital_signature`)

Giữ nguyên các method ảnh chữ ký, ký nháy và định dạng ngày (`digital_signature.py:127-234`). Màn máy tính dùng lại các method này.

`download_purchase_pdf` trả bản `Lotus Signed Copy` nếu có, nếu không thì trả bản PO đã lưu theo cách cũ.

## Đề xuất mua (`purchase_proposal`)

| Method | Tham số | Kết quả | Thay đổi |
|---|---|---|---|
| `proposals` | `stage`, `mine`, `waiting_me`, `search`, `from`, `to`, `warehouse`, `limit`, `offset` | `{rows, total, counts: {stage: n}}`. Có cả đề xuất đã hủy | Giai đoạn lấy từ `proposal_rules.stage` |
| `detail` | `name` | Như cũ, thêm:<br>• `stage`<br>• tiến độ từng dòng (`ordered`, `received`, `billed`, `paid`, `closed`)<br>• `can_close`, `can_cancel`, `can_delete`, `can_reassign`, `can_sign`<br>• `print_url`, `signed_copy` | Quyền đọc theo `can_view` |
| `save_proposal` | như cũ | như cũ | Bắt buộc lý do ở mọi đường gọi; kho phải cùng công ty, không phải nhóm, không bị tắt |
| `sign` | `name`, `modified`, `signers`, `reason` (chỉ khi chưa có lý do), `client_key` | Trạng thái chuỗi | Thêm `reason` |
| `close_remainder` | `name`, `reason`, `modified` | Giai đoạn mới | Mới. Native Stopped kèm `lotus_close_*`. Từ chối khi còn đơn nháp hoặc đơn chờ duyệt |
| `cancel_proposal` | `name`, `reason`, `modified`, `cancel_quotes` (0 hoặc 1) | Giai đoạn "Đã hủy" | Mới. Từ chối khi có dòng đơn mua trỏ tới |
| `return_proposal`, `reassign_signer`, `delete_proposal` | như cũ | như cũ | Có trên máy tính |

`purchasing.create_request` giữ lại làm lớp bọc, nhưng không còn điền lý do mặc định và không còn submit khi chưa ký.

## Báo giá (`procurement`)

| Method | Tham số | Kết quả | Thay đổi |
|---|---|---|---|
| `save_quotation` | như cũ | như cũ | Chỉ sửa được báo giá nháp |
| `cancel_quotation` | `name`, `reason`, `modified` | Đã hủy, hoặc đã xóa nếu là nháp | Mới. Từ chối khi còn dòng đơn mua trỏ tới |
| `choose_quote` | `request`, `request_item`, `quotation`, `quotation_item`, `reason` | Dòng đề xuất đã ghi lựa chọn | Mới. Bắt buộc lý do khi không chọn giá thấp nhất |
| `select_quotes` | `lines[]`, `approver` (tùy chọn), `client_key` | `{orders: [name]}`, là các đơn nháp, hoặc đơn "Chờ duyệt" nếu có `approver` | Bỏ tự duyệt; bỏ trường `approved` |
| `compare` | như cũ | Như cũ, thêm `selected` theo dòng | Giao diện điện thoại dạng thẻ dùng chung kết quả này |

## Đơn mua (`purchasing`, `warehouse_buying_lite`)

| Method | Tham số | Kết quả | Thay đổi |
|---|---|---|---|
| `warehouse_buying_lite.request_detail` | `request` | Dòng theo NCC đã chọn, kèm giá, thuế, phí vận chuyển và link báo giá; dòng chưa chọn lấy giá dự kiến | Không còn đặt giá về 0 |
| `warehouse_buying_lite.save_order` | như cũ | Như cũ, thêm `warnings[]` (`line`, `code`, `message`) lấy từ `purchase_flow.order_issues` | Báo trước dòng sẽ bị chặn |
| `warehouse_buying_lite.delete_draft` | `name`, `modified` | `{deleted}` | Máy chủ kiểm người lập; đơn phải là Nháp hoặc Bị trả lại |
| `warehouse_buying_lite.submit_order` | – | – | **Bỏ** |
| `purchasing.request_approval` | như cũ | Như cũ, thêm `warnings[]` | |
| `purchasing.approve_order` | `name`, `modified`, `client_key` | Trạng thái và `signed_copy` | Bỏ `sign_token`; ký đủ thì đi qua `_completed` |
| `purchasing.reject_order` | `name`, `reason`, `modified` | Bị trả lại | Có trên máy tính |
| `purchasing.cancel_order` | `name`, `reason`, `modified` | Đã hủy; dòng đề xuất liên quan quay lại "Chờ mua" | Ghi `lotus_cancel_reason`; vai trò duyệt mua có quyền hủy |
| `purchasing.detail` | `name` | Như cũ, thêm:<br>• `state` lấy từ `purchase_status.order_state`<br>• `overdue`<br>• chuỗi ký<br>• lý do trả lại<br>• `print_url`, `signed_copy` | |
| `purchasing.orders` | như cũ | Mỗi dòng có `state` và tiến độ hóa đơn, trả tiền | Một bộ tên trạng thái |

**Phép kiểm khi submit** (`purchasing.check_submission`): đủ chữ ký chuỗi `purchase_order` của đúng người duyệt được chỉ định, dấu vân tay khớp, người bấm là người duyệt.

## Nhận hàng (`warehouse_planning`, `procurement`)

| Method | Tham số | Kết quả | Thay đổi |
|---|---|---|---|
| `warehouse_planning.receive_order` | `order`, `lines[]`, `costs[]`, `files[]`, `deliverer_name`, `deliverer_signature`, `delivery_proof`, `post` (mặc định 1), `client_key` | `{receipt, state, signed_copy, remaining[]}` | Một đường cho Kho điện thoại và máy tính:<br>• gắn file trong cùng giao dịch<br>• bắt buộc người giao<br>• tự ký bước thủ kho<br>• lưu PDF<br>• khi tranh chấp: báo "Còn nhận được N" |
| `warehouse_planning.receipt_action` | `name`, `action` (`submit`, `cancel`, `delete`), `reason`, `modified` | Trạng thái mới | Hủy bắt buộc lý do; xóa nháp do máy chủ kiểm |
| `procurement.return_receipt` | `receipt`, `lines[]`, `reason`, `post` (mặc định 1), `client_key` | `{return_receipt, needs_credit_note}` | Ghi sổ ngay trong Lotus |
| `procurement.receipt` | `name` | Như cũ, thêm:<br>• `files[]`<br>• người giao<br>• `print_url`, `signed_copy`<br>• tình trạng hóa đơn<br>• nhãn "Mua nhanh" | |

**Ghi chú triển khai:** tên tham số giữ như hàm cũ để không vỡ nơi đang gọi: `receive_order(name, posting_date, quantities, client_event_id, additional_costs, post, files, deliverer_name, deliverer_signature, delivery_proof, notes)`, `return_receipt(name, posting_date, quantities, client_key, post, reason)`. Máy chủ mặc định `post=0`; giao diện mới luôn gửi `post=1`. Chữ ký thủ kho được ghi ở hook `on_submit`, nên đường nào ghi sổ phiếu nhập cũng có chữ ký.

**Hook `Purchase Receipt.before_submit`:** với phiếu theo đơn của công ty đang bật luồng mua, bắt buộc có (họ tên + chữ ký) hoặc ảnh phiếu giao.

## Hóa đơn NCC (`finance.supplier_invoice`, mới)

| Method | Tham số | Kết quả |
|---|---|---|
| `queue` | `supplier`, `from`, `to`, `has_file`, `limit`, `offset` | Hóa đơn chờ nhập, gồm phiếu nhận và phiếu Mua nhanh chưa có hóa đơn đủ. Mỗi dòng có `doctype`, `name`, `supplier`, `date`, số tiền chưa có hóa đơn, `files[]`, `mua_nhanh` |
| `source` | `receipts[]` | Dòng điền sẵn: số lượng chưa có hóa đơn, đơn giá theo đơn, thuế suất, chi phí, đơn giá nhập kho; `files[]` của các phiếu |
| `create` | `supplier`, `receipts[]`, `lines[]` (`source_doctype`, `source_name`, `source_item`, `qty`, `rate`, `vat_code`, `variance_reason`), `service_lines[]`, `bill_no`, `series`, `tax_code`, `bill_date`, `due_date`, `posting_date`, `printed_total`, `printed_vat`, `files[]`, `client_key` | `{invoice, rounding_adjustment, warnings[]}`. Thuế theo quy tắc hộ kinh doanh, không bao giờ 1331 khi `vat_in_cost` bật |
| `detail` | `name` | Đầu hóa đơn, các dòng, thuế, tổng in, phần lệch làm tròn, `files[]`, phiếu nhận và phiếu Mua nhanh liên quan, thanh toán, `print_url` |
| `cancel` | `name`, `reason`, `modified` | Đã hủy. Bị chặn khi có thanh toán, phiếu chi nháp, khoản chi hộ, trả hàng hoặc tạm ứng đã cấn trừ |
| `invoices` | `supplier`, `status`, `as_of`, `from`, `to`, `limit`, `offset` | Danh sách, có trạng thái tính tại ngày chốt |

**Lớp bọc gọi `create`** (giữ tương thích):
- `procurement.invoice_receipt`
- `procurement.billing_source`
- `finance.payments.make_goods_invoice`
- `finance.payments.make_service_invoice`

**Hook `Purchase Invoice.before_cancel`:** chạy cùng phép chặn với `cancel`.

`procurement_adjustments.credit_note`: giữ nguyên, thêm `files[]`.

## Công nợ và phiếu chi (`procurement_queries`, `finance.supplier_payment`)

| Method | Tham số | Kết quả |
|---|---|---|
| `procurement_queries.payables` | `as_of`, `supplier`, `limit`, `offset` | Mỗi NCC có:<br>• `invoiced`, `advance`, `net`<br>• `aging` (`current`, `d1_30`, `d31_60`, `d61_90`, `d90_plus`, `no_due`)<br>• `due_7d`<br>• `unbilled` (hàng đã nhận chưa có hóa đơn, tạm tính)<br><br>Kèm dòng tổng và phép đối chiếu với sổ cái 331 và 3388 + 33881 |
| `procurement_queries.due_soon` | `as_of`, `days` (mặc định 7) | Các hóa đơn đến hạn |
| `procurement_queries.supplier_statement` | `supplier`, `from`, `to` | `{opening, lines[], closing}`. Mỗi dòng có `doctype`, `name`, `kind`, `debit`, `credit`, `balance`. Loại dòng: hóa đơn, điều chỉnh, phiếu chi, tạm ứng, hoàn tiền, chi hộ |
| `finance.supplier_payment.prepare` | `supplier`, `allocations[]` (`doctype`: Purchase Invoice hoặc Purchase Order, `name`, `amount`), `advance_amount`, `mode` (`bank` hoặc `cash`), `reference_no`, `reference_date`, `files[]`, `signers`, `client_key` | `{voucher, chain_status}`. Bắt đầu chuỗi ký phiếu chi. Không chi vượt số còn nợ, trừ phần ghi là tạm ứng |
| `finance.payments.sign_payment`, `return_payment`, `cancel_draft` | như cũ | như cũ |
| `finance.posting.reverse` | như cũ | Gọi được từ màn Mua hàng (chỉ kế toán trưởng) |

**Lớp bọc gọi `finance.supplier_payment.prepare`:**
- `procurement.supplier_payment`
- `finance.payments.prepare_supplier_payment`

Dòng tiến độ trả về từ `purchase_flow.proposal_progress` và `procurement.chain` luôn có `doctype`.

## Trang web

| Đường dẫn | Mục đích |
|---|---|
| `/lotus/mo?dt=&n=` | Mới. Chưa đăng nhập: chuyển sang đăng nhập. Đã đăng nhập: chuyển tới link điện thoại (màn hẹp hoặc PWA) hoặc link máy tính. Route đặt trước route bắt-tất-cả `/lotus/<path>` |
| `/lotus/in-de-xuat?name=` | Như cũ; người ký được xem; ký nháy ở chân trang; chức danh trong ô ký |
| `/lotus/in-don-mua?name=` | Mới. Trả bản PDF đã lưu nếu có, nếu không thì trang in đơn |
| `/lotus/in-phieu?doctype=Purchase Receipt&name=` | Như cũ, thêm chữ ký hoặc ảnh phiếu giao của người giao hàng |
| `/lotus/in-phieu-chi?doctype=&name=` | Mới. Phiếu chi tiền mặt, hoặc giấy đề nghị chi khi chuyển khoản |
| `/lotus/in-hoa-don?name=` | Mới. Hóa đơn đã ghi sổ, kèm danh sách file gốc |
| `/lotus/in-doi-chieu?supplier=&from=&to=` | Mới. Biên bản đối chiếu công nợ |
| `/lotus/cho-ky` | Mới. Trang Chờ tôi ký trên máy tính |
| `/verify/lotus` | Như cũ, thêm kết quả so với bản PDF lưu |

## Thông báo

- **Thông báo đẩy:** link luôn có dạng `/<app>?sign_dt=&sign_dn=`, và chỉ trỏ tới app mà người nhận có thiết bị.
- **Email:** link trỏ tới `/lotus/mo?dt=&n=`.
- **Khi gửi lỗi:** lỗi gửi thông báo không bao giờ làm hỏng thao tác chính; chỉ ghi vào Error Log.

## Tham số link sâu trên PWA (`mobile-deep-link.js`)

| Tham số | Mở |
|---|---|
| `sign_dt`, `sign_dn` | Tấm ký của chứng từ |
| `doctype`, `doc` | Chi tiết chứng từ theo bảng hàm mở của từng app |
| `proposal` (cũ) | Chi tiết đề xuất |
| `doc` (cũ, không có `doctype`) ở `/buying` | Chi tiết đơn mua |
| `request`, `tab` (cũ) | Như cũ |
