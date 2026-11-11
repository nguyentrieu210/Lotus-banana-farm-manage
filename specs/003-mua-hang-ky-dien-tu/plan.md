# Implementation Plan: Hoàn thiện mua hàng: đề xuất, đơn mua, nhập kho, hóa đơn NCC, công nợ và ký điện tử

**Branch**: `003-mua-hang-ky-dien-tu` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-mua-hang-ky-dien-tu/spec.md`

## Summary

Luồng mua hàng đang chạy thật từ 07/11/2026. Spec này không làm lại luồng, chỉ lấp chỗ thiếu, sửa chỗ hỏng và đưa điện thoại với máy tính về ngang nhau.

**Ký điện tử:**
- Một hộp Chờ tôi ký và một tấm ký dùng chung cho mọi chứng từ, trên cả điện thoại và máy tính.
- Một điểm chốt khi ký đủ: chạy việc của chứng từ, rồi lưu bản PDF cố định (`Lotus Signed Copy`) trong cùng giao dịch.
- Nhật ký ký ghi đủ IP, thiết bị, vai trò, chức danh.
- Ký nhiều chứng từ một lượt; mỗi chứng từ chạy trong savepoint riêng.
- Gửi thông báo không bao giờ làm hỏng thao tác ký.
- Gỡ đường ký bằng QR và nút ký nháy không chạy.

**Đề xuất:**
- Giai đoạn tính bằng một hàm thuần duy nhất.
- Đóng phần chưa mua, hủy có lý do.
- Người được chỉ định ký luôn xem được chứng từ.
- Một biểu mẫu dùng chung cho Kho và Mua hàng.

**Đơn mua:**
- Bỏ tự duyệt; giám đốc ký mọi đơn.
- Khi submit, máy chủ kiểm đủ chữ ký của đúng người được chỉ định.
- Giữ NCC và giá của báo giá đã chọn.
- Báo trước dòng sẽ bị chặn lúc duyệt.
- Máy tính có sửa, trả lại, hủy và in.

**Nhập kho:**
- Một đường nhận hàng chung cho Kho và Mua hàng: ghi sổ một bước, có ảnh và chi phí.
- Bắt buộc có xác nhận của người giao hàng. Xác nhận nhập kho cũng là chữ ký của thủ kho.
- Trả hàng, hủy và xóa nháp làm ngay trong Lotus.

**Hóa đơn NCC:**
- Một lõi lập hóa đơn dùng chung, thuế luôn theo quy tắc hộ kinh doanh. Việc này sửa luôn lỗi đưa thuế vào 1331.
- Danh sách Hóa đơn chờ nhập; file gốc hiện cạnh biểu mẫu.
- Hủy có chặn khi đã phát sinh thanh toán.

**Công nợ:**
- Tuổi nợ theo ngày chốt, danh sách đến hạn, hàng đã nhận chưa có hóa đơn.
- Sổ chi tiết và biên bản đối chiếu.
- Một lõi lập phiếu chi trả được nhiều hóa đơn; có mẫu in phiếu chi.

**Phase 0** gom 3 lỗi đang làm hỏng việc trên bản thật. Phase này tách được thành bản vá riêng.

Chi tiết từng quyết định ở [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (backend), JavaScript ES2022 với Vue 3.5 (frontend)

**Primary Dependencies**:
- Frappe 16.51, ERPNext 16.50, HRMS 16.50; app `lotus_farm`.
- Vue 3.5, Vant 4.10 (điện thoại); shadcn-vue trên reka-ui 2.11, `DataTable` AG Grid 36 (máy tính).
- Vite 8.
- wkhtmltopdf qua `frappe.utils.pdf.get_pdf` (đang dùng cho PDF đơn mua).

**Storage**: MariaDB 11.8 (REPEATABLE-READ, snapshot isolation), qua DocType Frappe; file PDF và ảnh lưu riêng tư trong `private/files`.

**Testing**:
- `python -m unittest` cho module thuần trong `tests/`.
- Script tích hợp `tests/integration/*.py` chạy trên site thử `mua.test`.
- `node --test` với happy-dom (`tests/support/mount.mjs`) cho frontend.
- `tools/verify_mobile_purchase_dom.mjs` cho màn hẹp.

**Target Platform**:
- Web máy tính `/lotus/*`.
- Bốn PWA điện thoại: `/buying`, `/warehouse`, `/work`, `/hr-mobile`.
- Docker trên VPS.

**Project Type**: Ứng dụng web (backend app Frappe + frontend Vue nhiều entry)

**Performance Goals**:
- Số đếm Chờ tôi ký dưới 300 ms.
- Danh sách 100 dòng chờ ký dưới 1 giây.
- Ký bước cuối, kể cả dựng và lưu PDF, dưới 4 giây.
- Ký nhiều 20 chứng từ dưới 30 giây.
- Công nợ có tuổi nợ cho dưới 200 NCC dưới 2 giây.
- Lưu nhận hàng 10 dòng kèm 3 ảnh dưới 3 giây trên mạng 4G yếu.

**Constraints**:
- VPS không có container lịch, nên không việc nào dựa vào cron. Đến hạn và tuổi nợ tính khi xem.
- Codex dùng chung repo, nên làm trong worktree riêng. Không chạm cây của spec 002.
- Chứng từ kế toán chỉ thay đổi qua chứng từ, không sửa thẳng sổ.
- Hộ kinh doanh: thuế đầu vào vào giá vốn, không dùng 1331.
- Mạng ở vườn yếu: mọi thao tác ghi có khóa chống gửi trùng và chịu được thử lại.
- Giao diện:
  - Máy tính dùng `components/ui`, `DataTable`, `WorkspaceModal`.
  - Điện thoại dùng Vant và `LotusMobile*`.
  - Màu lấy từ `lotus-tokens.css`.
  - Toàn bộ chữ tiếng Việt.
  - Không có `<table>` thô.

**Scale/Scope**:
- Một trang trại, vài chục chứng từ mua mỗi tuần, khoảng 10–20 người ký, dưới 200 NCC.
- Khoảng 25 file backend và 35 file frontend phải sửa hoặc tạo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Số thực, không suy diễn | **Đạt.**<br>• Công nợ, tuổi nợ và tiến độ đều tính từ sổ và chứng từ.<br>• "Hàng đã nhận chưa có hóa đơn" ghi rõ là tạm tính theo giá phiếu nhận, và đối chiếu với 3388 + 33881.<br>• Hóa đơn nhập tay; không có số nào do máy đọc. |
| II. Một nguồn sự thật | **Đạt, có một ngoại lệ** ghi ở Complexity Tracking (DocType mới `Lotus Signed Copy`).<br>• Bốn đường lập hóa đơn và hai đường lập phiếu chi gom về một lõi mỗi loại.<br>• Ba chỗ tính giai đoạn đề xuất và khoảng 15 bảng nhãn gom về một module.<br>• Bốn form đề xuất còn một.<br>• Không có sổ song song. |
| III. Truy vết và kiểm soát | **Đạt.**<br>• Bỏ tự duyệt đơn; máy chủ kiểm đúng người được chỉ định ở mọi đường submit.<br>• Đóng, hủy, lệch giá và chuyển người ký đều phải có lý do.<br>• Nhật ký ký có IP, thiết bị, vai trò, chức danh; có bản PDF cố định.<br>• Mua nhanh không ký là do chủ vườn quyết định rõ (Clarification Q5). |
| IV. Quy tắc tách riêng, có kiểm thử | **Đạt.**<br>• Quy tắc nằm ở module thuần có unit test: giai đoạn, trạng thái, tuổi nợ, ngưỡng tổng in, chuỗi ký, chọn app thông báo.<br>• Luồng ghi sổ có test tích hợp: ký, lưu PDF, nhận hàng, hóa đơn, phiếu chi, hủy.<br>• Mỗi component mới có mount test. |
| V. Giao diện theo chuẩn chung | **Đạt.**<br>• Máy tính dùng primitive `components/ui`, `DataTable`, `WorkspaceModal`.<br>• Điện thoại dùng Vant và wrapper `LotusMobile*`. Hộp chờ ký nằm trong shell chung.<br>• Màu nét chữ ký chuyển sang token.<br>• Toàn bộ chữ tiếng Việt. |
| Ràng buộc vận hành | **Đạt.**<br>• Patch chạy lại không ghi trùng: trả đơn chờ duyệt chưa ký về Nháp, xóa DocType thử thách QR, bật thiết lập giá vốn theo hóa đơn.<br>• Có sao lưu trước khi migrate trên VPS.<br>• Không sửa thẳng sổ. |
| Quy trình phát triển | **Đạt.**<br>• Làm trên nhánh 003 trong worktree riêng.<br>• Test, build và kiểm DOM phải qua trên site thử `mua.test` trước.<br>• Chỉ commit, đẩy và triển khai khi chủ vườn yêu cầu. |

**Đánh giá lại sau Phase 1:** không có vi phạm mới. Hai thay đổi chủ vườn cần biết khi duyệt tasks:
1. Đơn đang "Chờ duyệt" mà chưa có vòng ký sẽ bị trả về Nháp khi phát hành.
2. Bật giá vốn theo giá hóa đơn sẽ khiến ERPNext tính lại giá trị kho khi hóa đơn lệch giá đơn.

## Project Structure

### Documentation (this feature)

```text
specs/003-mua-hang-ky-dien-tu/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks tạo
```

### Source Code (repository root)

```text
lotus_farm/
├── signing.py                    # inbox/inbox_count/sign_many/can_view/_completed/open_targets; thông báo an toàn; REASSIGN; verify bản lưu
├── signing_rules.py              # chuỗi purchase_receipt; bước kiểm tra; chọn app thông báo
├── signed_copy.py                # MỚI: dựng PDF tin cậy, lưu, băm, xác minh
├── purchase_status.py            # MỚI (thuần): giai đoạn, trạng thái đơn/phiếu/hóa đơn/phiếu chi, nhãn
├── proposal_rules.py             # stage() theo tổng từng dòng
├── purchase_flow.py              # tổng theo dòng không phụ thuộc người xem; order_issues; doctype ở dòng tiến độ
├── purchase_proposal.py          # proposals + counts; close_remainder; cancel_proposal; sign(reason)
├── procurement.py                # choose_quote; cancel_quotation; select_quotes không tự duyệt; receipt chi tiết; nhãn Mua nhanh
├── purchasing.py                 # check_submission mới; approve_order bỏ token; cancel_order lý do; detail/orders state
├── warehouse_buying_lite.py      # request_detail giữ NCC/giá; save_order cảnh báo; delete_draft; bỏ submit_order
├── warehouse_planning.py         # receive_order một bước + file + người giao + tự ký; receipt_action hủy/xóa
├── procurement_adjustments.py    # return_receipt post=1; credit_note files
├── procurement_queries.py        # payables tuổi nợ/unbilled/đối chiếu; due_soon; supplier_statement
├── push_notifications.py         # link gốc app + query; bỏ alert mất
├── digital_signature.py          # gỡ QR/ký nháy đơn; download_purchase_pdf đọc Lotus Signed Copy
├── stock_attachments.py          # cho phép Purchase Invoice, Payment Entry
├── warehouse_access.py           # quyền hủy đơn của người duyệt
├── hooks.py                      # PR before_submit, PI before_cancel, route /lotus/mo và trang in mới
├── finance/
│   ├── supplier_invoice.py       # MỚI: queue/source/create/detail/cancel/invoices
│   ├── supplier_payment.py       # MỚI: prepare (nhiều hóa đơn, tạm ứng, hình thức, tham chiếu, file)
│   ├── payments.py               # lớp bọc; _voucher_info bổ sung
│   ├── reports.py                # đối chiếu 3388 + 33881
│   └── native_guards.py          # chặn hủy hóa đơn
├── lotus_farm/doctype/
│   ├── lotus_signed_copy/        # MỚI
│   ├── lotus_signature_event/    # thêm trường + index
│   ├── lotus_sign_request/       # thêm trường
│   └── lotus_signing_challenge/  # XÓA
├── www/
│   ├── lotus_open.py             # MỚI /lotus/mo
│   ├── lotus_payment_print.py    # MỚI phiếu chi / đề nghị chi
│   ├── lotus_invoice_print.py    # MỚI
│   ├── lotus_statement_print.py  # MỚI biên bản đối chiếu
│   ├── lotus_purchase_order_print.py, lotus_material_proposal_print.py, lotus_stock_print.py  # chế độ tin cậy, chức danh, ký nháy, người giao
│   └── verify/lotus.py
├── templates/print/…             # _macros.html footer ký nháy; mẫu phiếu chi, hóa đơn, đối chiếu
├── patches/                      # trả đơn chưa ký về Nháp; xóa Signing Challenge; bật giá vốn theo hóa đơn
└── translations/vi.csv

frontend/src/
├── purchase-status.js            # MỚI: nhãn, tông màu
├── use-signing.js                # MỚI: inbox, count, sign, signMany, return, reassign, xác nhận
├── mobile-deep-link.js           # MỚI
├── use-signature-profile.js      # MỚI (tách từ LotusMobileSignatureSettings)
├── components/
│   ├── signing/                  # MỚI: SigningInboxPage, SignSheet, SignatureSettings, SignaturePad
│   ├── LotusMobileSignInbox.vue, LotusMobileSignSheet.vue   # MỚI
│   ├── LotusMobileShell.vue      # biểu tượng chờ ký có số
│   ├── WorkspaceBar.vue          # nút chờ ký, menu Chữ ký của tôi
│   ├── procurement/              # MỚI, tách từ ProcurementWorkspace: NeedDetail, NeedForm, QuoteDetail,
│   │                             #   CompareCards, OrderDetail, ReceiptDetail, InvoiceQueue, InvoiceForm,
│   │                             #   InvoiceDetail, PayablesView, SupplierStatement, PaymentForm, VoucherDetail,
│   │                             #   use-procurement.js
│   ├── ProcurementWorkspace.vue  # còn là khung
│   ├── ProcurementCompare.vue, PurchaseProgress.vue, WarehouseReceiving.vue, WarehousePlanning.vue
│   ├── MobilePurchaseProposal.vue, MobilePurchaseOrderDetail.vue
│   └── LotusMobileSignatureSettings.vue, LotusSignatureDraw.vue
├── BuyingMobile.vue, WarehouseMobile.vue, WorkMobile.vue, HrMobile.vue, FinanceApp.vue, App.vue
├── domain.js, router.js, workspace-routes.js, procurement-navigation.js
└── release-notes.js

tests/                            # thuần: test_purchase_status, test_proposal_rules, test_signing_rules, test_procurement_rules
tests/integration/                # verify_signing_inbox, verify_signed_copy (mới) + mở rộng các script mua hàng/tài chính
frontend/tests/                   # mount test cho mọi component mới; cập nhật guard lists; bỏ test QR
docs/MUA_HANG_WORKSPACE.md, docs/LOTUS_SIGNATURE_V2.md   # cập nhật trạng thái
```

**Structure Decision**: giữ nguyên bố cục app Frappe và frontend nhiều entry. Mã mới đặt cạnh mã cùng nghiệp vụ. `ProcurementWorkspace.vue` được tách vì đã quá dài (R22). Không thêm app, không thêm PWA.

## Thứ tự triển khai

Mỗi phase thử được độc lập, và đưa lên VPS được từng phase theo yêu cầu của chủ vườn.

| Phase | Nội dung | Story | Ghi chú |
|---|---|---|---|
| 0 | Bản vá:<br>• thông báo phiếu chi (B1)<br>• link in đơn mua (B2)<br>• loại chứng từ ở tiến độ (B3) | US1, US3, US6 | Nhỏ; có thể tách thành bản vá trên main |
| 1 | Nền tảng chung:<br>• `purchase_status` thuần + `purchase-status.js`<br>• `signing.can_view`<br>• trường mới của các DocType ký<br>• `Lotus Signed Copy`<br>• tách `use-procurement.js` | Tất cả | Làm trước mọi story |
| 2 | Ký điện tử:<br>• hộp Chờ tôi ký, tấm ký, ký nhiều<br>• điểm chốt + PDF lưu<br>• nhật ký<br>• link `/lotus/mo` và link sâu<br>• Chữ ký của tôi trên máy tính<br>• gỡ QR, ký nháy ở chân trang<br>• gate đơn mua, bỏ tự duyệt | US1 (P1) | MVP |
| 3 | Bảng đề xuất:<br>• giai đoạn, số đếm<br>• đóng, hủy<br>• form chung cho Kho<br>• in, chuyển người ký, xóa nháp trên máy tính<br>• hỏi lý do khi ký | US2 (P1) | |
| 4 | Đơn mua:<br>• chọn báo giá, so sánh dạng thẻ<br>• giữ giá; cảnh báo khi lưu<br>• sửa, trả lại, hủy, xóa, in trên máy tính<br>• Kho gửi duyệt<br>• hủy báo giá | US3 (P2) | |
| 5 | Nhập kho:<br>• một đường nhận hàng có ảnh, chi phí, người giao<br>• chuỗi `purchase_receipt`<br>• trả hàng, hủy, xóa, in, đính kèm<br>• tranh chấp nhận cùng lúc | US4 (P2) | |
| 6 | Hóa đơn NCC:<br>• lõi lập hóa đơn (sửa B4)<br>• Hóa đơn chờ nhập, form có file gốc<br>• hủy<br>• in | US5 (P3) | Thử thiết lập giá vốn theo hóa đơn trước |
| 7 | Công nợ và phiếu chi:<br>• tuổi nợ, đến hạn, hàng chưa có hóa đơn<br>• sổ chi tiết, biên bản đối chiếu<br>• lõi phiếu chi nhiều hóa đơn<br>• in phiếu chi<br>• đảo phiếu từ Mua hàng | US6 (P3) | |
| 8 | Hoàn thiện:<br>• rà ma trận thao tác ở 320 px và máy tính<br>• bỏ link Desk<br>• chữ "Đề xuất"<br>• tài liệu, ghi chú phát hành | Tất cả | |

## Complexity Tracking

| Vi phạm | Vì sao cần | Phương án đơn giản hơn bị loại vì |
|---|---|---|
| DocType mới `Lotus Signed Copy` (Nguyên tắc II: dùng lại mô hình đã có trước) | Cần một bản ghi mỗi vòng ký, có file, có băm, và có ràng buộc duy nhất để không lưu hai lần (SC-005) | Ghi vào `Lotus Signature Event` với action ARCHIVE: trường `details` bị cắt ở 800 ký tự, không có index, không chặn trùng. Thêm trường vào từng DocType ERPNext như đơn mua đang làm: phải sửa 5 DocType và mất cách xác minh chung |
| Lotus tự ghi chứng từ phụ theo từng hóa đơn khác giá hoặc khác thuế suất (`finance/invoice_cost.py`): Landed Cost Voucher trên 3388, bút toán chuyển thuế sang 33881, phiếu chia lại khi có hàng trả, bút toán chi phí khi kỳ phiếu nhận đã khóa. Tắt `set_landed_cost_based_on_purchase_invoice_rate` và `bill_for_rejected_quantity_in_purchase_invoice` của ERPNext | FR-051 yêu cầu giá vốn theo giá hóa đơn. Thử trên bản sao site thật (10/11/2026), thiết lập của ERPNext để lại 3388 và 33881 khác 0 khi có hàng trả hoặc thuế suất khác, và tính lại cả hàng đã trả vào hóa đơn. Rà soát độc lập (11/11/2026) tìm thêm các trường hợp hàng trả, kỳ đã khóa, dòng dịch vụ (R16) | Chỉ bật thiết lập ERPNext: đây là cách ban đầu. Đã thay đúng theo điều kiện ghi ở đây ("nếu 33881 không được xóa sạch thì quay về tự điều chỉnh"). Chứng từ phụ là chứng từ chuẩn của ERPNext, gắn với hóa đơn, hủy cùng hóa đơn và không hủy riêng được |
