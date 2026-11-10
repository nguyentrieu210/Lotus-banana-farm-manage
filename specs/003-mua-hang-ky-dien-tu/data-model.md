# Data Model: Hoàn thiện mua hàng và ký điện tử

Nguyên tắc: chứng từ ERPNext vẫn là nguồn số duy nhất (Material Request, Supplier Quotation, Purchase Order, Purchase Receipt, Stock Entry Mua nhanh, Purchase Invoice, Payment Entry, Journal Entry). Spec này chỉ:
- thêm trường vào DocType của Lotus;
- thêm custom field cộng thêm vào DocType của ERPNext;
- thêm một DocType mới (`Lotus Signed Copy`);
- xóa một DocType không dùng (`Lotus Signing Challenge`).

Không có sổ song song. Công nợ, tuổi nợ, tiến độ và giai đoạn đều được tính ra, không lưu.

## 1. DocType của Lotus

### Lotus Signed Copy (mới)

Bản PDF cố định lưu khi một vòng ký hoàn tất (R1).

| Trường | Kiểu | Ghi chú |
|---|---|---|
| name | Data | `sha1(document_type|document_name|round)` |
| document_type | Link DocType | bắt buộc, index |
| document_name | Dynamic Link | bắt buộc, index |
| round | Int | vòng ký |
| chain | Data | `purchase_proposal`, `purchase_order`, `purchase_receipt`, `payment_voucher`… |
| file | Attach | File riêng tư gắn vào chứng từ gốc |
| pdf_sha256 | Data | băm của đúng file đã lưu |
| content_hash | Data | dấu vân tay nội dung lúc hoàn tất, bằng `signing.fingerprint` |
| pages | Int | số trang |
| created_by | Link User | người ký bước cuối |
| created_at | Datetime | giờ máy chủ |

Quy tắc:
- Tên bản ghi chặn lưu hai lần cho cùng một vòng.
- Không có quyền ghi qua API. Chỉ `signing._completed` tạo bản ghi.
- Quyền đọc: System Manager, Lotus Auditor, và người qua `signing.can_view`.

### Lotus Signature Event (thêm trường)

| Trường mới | Kiểu | Nguồn |
|---|---|---|
| ip | Data | `frappe.local.request_ip` |
| user_agent | Small Text | header `User-Agent`, cắt 500 ký tự |
| roles | Small Text | vai trò của bước giao với vai trò của người dùng |
| designation | Data | chức danh trên Employee lúc ký |
| round | Int | vòng ký |
| step_key | Data | khóa bước |
| content_hash | Data | dấu vân tay nội dung |
| image_sha256 | Data | băm ảnh chữ ký đã chụp |

Action có thêm giá trị `REASSIGN` (chuyển người ký, `details` ghi người cũ, người mới, lý do) và `ARCHIVED` (đã lưu bản PDF).

Thêm index trên (`document_type`, `document_name`).

### Lotus Sign Request (thêm trường)

| Trường mới | Kiểu | Ghi chú |
|---|---|---|
| signer_designation | Data | chức danh lúc ký, để in ở ô chữ ký |
| initials_file | Attach | bản chụp ảnh ký nháy lúc ký, riêng tư; chỉ có ở bước kiểm tra |

Trạng thái giữ nguyên: Chưa đến lượt · Chờ ký · Đã ký · Trả lại.

### Lotus Signing Challenge (xóa)

Bỏ cùng đường ký bằng QR (R8). Một patch xóa DocType. Các dòng cũ chỉ là token hết hạn.

## 2. Custom field cộng thêm trên DocType ERPNext

Tạo trong `install`/setup như các trường `lotus_*` hiện có. Cột "Sau submit" đánh dấu trường có `allow_on_submit`.

| DocType | Trường | Kiểu | Sau submit | Dùng cho |
|---|---|---|---|---|
| Material Request | lotus_close_reason | Small Text | có | Đóng phần chưa mua (R11) |
| Material Request | lotus_closed_by | Link User | có | |
| Material Request | lotus_closed_at | Datetime | có | |
| Material Request | lotus_cancel_reason | Small Text | có | Hủy đề xuất |
| Material Request Item | lotus_selected_quote | Link Supplier Quotation | có | Báo giá đã chọn (R13) |
| Material Request Item | lotus_selected_quote_item | Data | có | Dòng báo giá |
| Material Request Item | lotus_selection_reason | Small Text | có | Bắt buộc khi không chọn giá thấp nhất |
| Purchase Order | lotus_cancel_reason | Small Text | có | Hủy đơn |
| Purchase Receipt | lotus_deliverer_name | Data | không | Họ tên người giao |
| Purchase Receipt | lotus_deliverer_signature | Attach Image | không | Chữ ký tay người giao (riêng tư) |
| Purchase Receipt | lotus_delivery_proof | Attach | không | Ảnh phiếu giao có chữ ký |
| Purchase Receipt | lotus_cancel_reason | Small Text | có | Hủy phiếu |
| Purchase Invoice | lotus_cancel_reason | Small Text | có | Hủy hóa đơn |
| Purchase Invoice Item | lotus_variance_reason | Small Text | không | Lý do lệch giá hoặc lượng so với đơn và phiếu nhận |

Các trường đang có và vẫn dùng:
- Purchase Order: `lotus_approval_status`, `lotus_sent_at`, `lotus_supplier_confirmed_at`, ngày giao đã đổi, các trường PDF đơn đã ký. Bản cũ vẫn xác minh được.
- Purchase Invoice: `lotus_einvoice_series`, mã cơ quan thuế.
- Stock Entry Mua nhanh: `lotus_receipt_reason`, `lotus_supplier`, `lotus_purchase_invoice`, `lotus_einvoice_*`, `lotus_vat_in_cost`.
- Trường ký nháy cũ trên Purchase Order: giữ dữ liệu, thôi dùng.

Thiết lập ERPNext: Buying Settings `set_landed_cost_based_on_purchase_invoice_rate = 1`. Bật bằng patch, sau khi đã thử trên site test (R16).

## 3. Chuỗi ký

| Chuỗi | Chứng từ | Bước | Bước chốt | Bước kiểm tra (ký nháy) |
|---|---|---|---|---|
| purchase_proposal | Material Request (Purchase) | người đề xuất → trưởng bộ phận → mua hàng/kế toán → giám đốc | submit | bước 3 |
| purchase_order | Purchase Order (mọi đơn) | người lập → người duyệt được chỉ định | submit | bước 1 |
| **purchase_receipt** (mới) | Purchase Receipt theo đơn, không phải trả hàng | thủ kho (người xác nhận), tự ký lúc submit | đã submit trước khi ký | không |
| stock_document | Stock Entry, Stock Reconciliation, phiếu trả hàng, vòng cũ của Purchase Receipt | không đổi | không | không |
| payment_voucher | Payment Entry, Journal Entry đang ký | kế toán → kế toán trưởng → giám đốc | submit và ghi sổ | bước 2 |

Quy tắc chung:
- Ký tuần tự; chỉ người đến lượt được ký.
- Mỗi lần ký đều có bước xác nhận. Không có mã ký hay token.
- Sửa nội dung thì mở vòng mới.
- Ký đủ thì lưu một `Lotus Signed Copy`.

## 4. Trạng thái và chuyển trạng thái

Tất cả là hàm thuần trong `purchase_status.py` và `proposal_rules.py`, tính từ chứng từ, không lưu.

### Đề xuất mua

```text
Nháp ──ký gửi──▶ Đang ký ──ký đủ (submit)──▶ Chờ mua ──có dòng đơn mua──▶ Đang mua
  ▲                │                                                     │
  └──trả lại──── Bị trả lại                                               ▼
                                     mọi dòng: nhận + đóng ≥ số đề xuất ─▶ Đã nhận đủ ──đủ hóa đơn──▶ Đã xong
Hủy (chưa có dòng đơn mua) ─▶ Đã hủy
```

Đầu vào tính theo từng dòng, quy về đơn vị kho:
- `qty`: số đề xuất;
- `ordered`: tổng các dòng đơn mua, kể cả nháp;
- `received`;
- `returned`;
- `billed`;
- `closed`: phần chưa nhận của các đơn đã đóng, cộng phần chưa đặt khi đề xuất đã ngừng.

Ràng buộc:
- Đóng phần chưa mua: từ chối khi còn đơn nháp hoặc đơn chờ duyệt trỏ tới đề xuất.
- Hủy: từ chối khi có dòng đơn mua trỏ tới.

### Đơn mua

```text
Nháp ──gửi duyệt──▶ Chờ duyệt ──giám đốc ký (submit)──▶ Đã duyệt ──▶ Đã gửi NCC ──▶ NCC đã xác nhận
  ▲                    │                                   │
  └──sửa── Bị trả lại ◀┘                                   ├─ có phiếu nhận ─▶ Đang nhận ─▶ Đã nhận đủ
                                                            ├─ đóng phần chưa giao ─▶ Đã đóng
                                                            └─ hủy (chưa nhận hàng, có lý do) ─▶ Đã hủy
```

Thứ tự xét khi đã submit:
1. Đã đóng
2. Đã nhận đủ
3. Đang nhận
4. NCC đã xác nhận
5. Đã gửi NCC
6. Đã duyệt

Quá hẹn giao là cờ riêng, không phải trạng thái.

### Phiếu nhận hàng

- Trạng thái phiếu: Nháp → Đã nhập kho → Đã hủy.
- Tình trạng hóa đơn, tính từ `per_billed` hoặc `lotus_purchase_invoice`: Chưa có hóa đơn, Có hóa đơn một phần, Đã có hóa đơn.
- Phiếu theo đơn chỉ submit được khi có `lotus_deliverer_name` + `lotus_deliverer_signature`, hoặc có `lotus_delivery_proof`.
- Phiếu Mua nhanh luôn mang nhãn "Mua nhanh".

### Hóa đơn NCC

Trạng thái:
- Chưa trả;
- Trả một phần;
- Đã trả;
- Quá hạn (khi còn nợ và đã quá hạn trả);
- Đã hủy.

Hóa đơn điều chỉnh là chứng từ trả hàng gắn với hóa đơn gốc.

Ràng buộc:
- Không trùng cặp NCC + ký hiệu + số.
- Tổng ghi sổ bằng tổng in. Lệch tối đa 1 đồng nhân số dòng hàng; phần lệch hiện rõ trên chi tiết.
- Chỉ hủy được khi không có thanh toán, phiếu chi nháp, khoản chi hộ, trả hàng hay tạm ứng đã cấn trừ.

### Phiếu chi

Nháp → Đang ký → (Bị trả lại → sửa → Đang ký) → Đã chi → Đã đảo.

Ràng buộc:
- Không chi vượt số còn nợ, đã trừ các phiếu nháp, trừ khi phần vượt ghi rõ là tạm ứng.
- Chỉ kế toán trưởng được đảo phiếu đã ghi sổ.

## 5. Dữ liệu tính ra (không lưu)

| Tên | Nguồn | Cột chính |
|---|---|---|
| Dòng Chờ tôi ký | Lotus Sign Request (Chờ ký, assignee = tôi, vòng mới nhất) và chứng từ | loại, số, nhãn chuỗi, bước, người lập, số tiền, ngày chứng từ, notified_at, link máy tính, link điện thoại |
| Công nợ theo NCC tại ngày chốt | Payment Ledger Entry TK 331 đến ngày chốt | phải trả theo hóa đơn, tạm ứng, còn phải trả, 5 nhóm tuổi nợ, đến hạn 7 ngày |
| Hàng đã nhận chưa có hóa đơn | Purchase Receipt Item (đã nhận − đã trả − đã có hóa đơn) × đơn giá nhập kho; Stock Entry Mua nhanh chưa có hóa đơn | số theo NCC; tổng khớp −(3388 + 33881) |
| Sổ chi tiết NCC | GL TK 331 theo khoảng ngày và party | đầu kỳ, hóa đơn, điều chỉnh, phiếu chi, tạm ứng, hoàn tiền, chi hộ, cuối kỳ |
| Tiến độ đề xuất và đơn | các chứng từ liên quan | đặt, nhận, hóa đơn, trả tiền, mỗi dòng có `doctype` và `name` |
