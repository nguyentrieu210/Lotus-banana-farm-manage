# Research: Hoàn thiện mua hàng và ký điện tử

Ngày: 2026-11-10. Nguồn: đọc mã nhánh `003-mua-hang-ky-dien-tu` (từ main df7bd70, đang chạy trên VPS) và mã ERPNext 16.50 trong container thử. Đường dẫn tính từ gốc repo.

Mỗi mục ghi Quyết định, Lý do và Phương án đã loại.

## Lỗi đang có trên bản chạy thật (gom vào Phase 0)

| # | Lỗi | Chỗ | Hậu quả |
|---|---|---|---|
| B1 | Thông báo phiếu chi ném ValueError | `signing.py:29` cho link `/lotus/tai-chinh…`; `_notify` (`signing.py:216-235`) đổi app sang app có thiết bị của người nhận; `_add_alert` (`push_notifications.py:178-179`) từ chối link không thuộc app | Người nhận đã bật thông báo điện thoại thì cả thao tác lập phiếu, ký, trả lại và chuyển người ký đều lỗi, kể cả chữ ký cuối của giám đốc (lúc báo "Đã ký đủ" cho người lập, `signing.py:297`). Áp dụng cho phiếu chi NCC, tạm ứng, lương, khoản bắt buộc, chi hộ, hoàn tiền |
| B2 | "In đơn mua" lỗi | `ProcurementWorkspace.vue:428` → `/lotus/in-phieu`, nơi từ chối Purchase Order (`www/lotus_stock_print.py:29-30`) | Máy tính không in được đơn |
| B3 | Phiếu chi trong tiến độ mở nhầm loại | Dòng tiến độ thiếu doctype (`purchase_flow.py:140-141`, `procurement.py:456`); giao diện mặc định Journal Entry (`ProcurementWorkspace.vue:232`) | Bấm phiếu chi báo không tìm thấy |
| B4 | Hóa đơn ở Tài chính đưa thuế vào 1331 | `finance/payments.py:176` (`make_goods_invoice`), `:292` (`make_service_invoice`) gọi `apply_vat(..., m['input_vat'])` | Trái quy tắc hộ kinh doanh (thuế vào giá vốn); xảy ra khi kế toán chọn thuế suất khác KCT |
| B5 | Đơn mua xác nhận chỉ cần quyền | `purchasing.check_submission` (`purchasing.py:58-67`) chỉ xét vai trò; đơn không có trường Lotus bỏ qua hẳn | Người có vai trò duyệt mua xác nhận đơn qua Desk/REST mà không cần chữ ký người được chỉ định |
| B6 (tìm thấy 11/11/2026) | Hàng đợi nền đầy làm hỏng việc submit | `push_notifications.document_hook` gọi `frappe.enqueue` không bắt lỗi. Khi hàng đợi "short" vượt giới hạn, Frappe kiểm kích thước hàng đợi rồi gọi `has_permission("System Health Report")`, và hàm này ném PermissionError không nội dung với người không phải System Manager | Mọi submit có gửi thông báo đều hỏng (đề xuất, đơn mua, phiếu nhận, phiếu kho, báo cáo ngày), kể cả chữ ký cuối của giám đốc. Trên bộ thử lỗi hiện ra vì không chạy worker; trên site thật sẽ hiện khi worker dừng hoặc nghẽn |

B1, B2 và B3 sửa nhỏ, có thể tách thành bản vá riêng trước các phase khác nếu chủ vườn đồng ý. B4 và B5 nằm trong R16 và R7. B6 đã sửa: việc xếp thông báo vào hàng đợi chỉ là cố gắng, lỗi thì ghi Error Log "Lotus: thông báo chứng từ" (T128).

## R1. Điểm chốt khi ký đủ và bản PDF lưu

**Quyết định:** thêm một hàm `signing._completed(doc, key, round, effect)`. Nó chạy từ nhánh "đủ chữ ký" của `sign()` (`signing.py:291-297`), và từ `start()` khi chuỗi chỉ có một bước. Thứ tự trong cùng một giao dịch:
1. ghi chữ ký;
2. chạy `effect` do nơi gọi truyền vào (submit, đóng kỳ);
3. dựng PDF từ trang in (chế độ tin cậy, không kiểm quyền người xem);
4. lưu PDF;
5. gửi thông báo "Đã ký đủ".

Dựng PDF lỗi thì toàn bộ rollback (FR-014). PDF được lưu thành File riêng tư gắn vào chứng từ, kèm một bản ghi trong DocType mới `Lotus Signed Copy`. Tên bản ghi là hash của `doctype|name|round`, nên cơ sở dữ liệu tự chặn lưu hai lần cho cùng một vòng. QR dùng link xác minh theo vòng đã có (`signing.verify_url`, `signing.py:459-466`). `signing.verify` băm lại file đã lưu và trả "khớp bản lưu".

**Lý do:** 5 nơi gọi hiện tự xử lý bước cuối (`purchase_proposal.py:385-390`, `purchasing.py:200-207`, `finance/payments.py:405-410`, `hr_period.py:346-352`, `confirm`). Gắn một điểm chung thì không sót chứng từ nào (SC-005 yêu cầu 100%). Cách dựng PDF đã chạy thật với đơn mua (`digital_signature.archive_approved_purchase_pdf`, `digital_signature.py:414-448`; `print_kit.pdf`, `print_kit.py:191-194`).

**Đã loại:**
- Gọi `archive()` ở từng nơi gọi: dễ sót.
- Hook `on_submit`: sót đóng kỳ công và phiếu kho ký sau khi ghi sổ.
- Lưu bản PDF vào `Lotus Signature Event` với action ARCHIVE: trường `details` bị cắt ở 800 ký tự (`digital_signature.py:269`), không có index, không chặn trùng được.
- Thêm trường riêng cho từng DocType như đơn mua đang làm (`digital_signature.py:47-56`): phải sửa nhiều DocType của ERPNext. Đường `token=` cũ của đơn mua vẫn giữ để bản in cũ còn xác minh được.

## R2. Trang in chạy ở chế độ tin cậy, ký nháy ở chân trang

**Quyết định:**
- Mỗi hàm dựng trang in nhận thêm tài liệu đã nạp sẵn kèm cờ `trusted`; chỉ R1 dùng cờ này. Các hàm: `lotus_material_proposal_print.build`, `lotus_stock_print.build`, `lotus_purchase_order_print.html`, và trang phiếu chi mới.
- Người xem thường đi qua `signing.can_view` (R5).
- Chữ ký nháy của người ký bước kiểm tra nằm trong khối `#footer-html` ở `_macros.html:22-25`, khối Frappe lặp lại trên mọi trang. Ảnh nhúng dạng data URI. Lề dưới tăng từ 16 lên 22 mm. Mã nhỏ trong footer ẩn ký nháy khi tài liệu chỉ có 1 trang.
- Bước kiểm tra theo chuỗi:
  - đề xuất: bước 3 (kế toán / mua hàng);
  - đơn mua: bước 1 (người lập);
  - phiếu chi: bước 2 (kế toán trưởng);
  - phiếu nhập: không có.
- Ô chữ ký hiện chức danh lúc ký. Nếu không có ảnh, ô ghi "Đã ký điện tử: <họ tên>, <giờ>".

**Lý do:** các hàm dựng trang in đều kiểm quyền đọc và in (`lotus_material_proposal_print.py:110-112`, `lotus_stock_print.py:32-33`, `lotus_purchase_order_print.py:15`). Người ký không có quyền đọc sẽ làm hỏng bước ký cuối. Phần header chỉ in ở trang đầu; chỉ footer lặp lại trên mọi trang.

**Đã loại:** nút ký nháy riêng, như nút đơn mua đang hỏng (`BuyingMobile.vue:384`). Ký nháy là một phần của chữ ký bước kiểm tra, không phải thao tác riêng.

## R3. Thông báo và link mở chứng từ

**Quyết định:**
- **Link đẩy cho điện thoại:** luôn có dạng gốc app + tham số, ví dụ `/buying?sign_dt=<doctype>&sign_dn=<name>`.
  - Chọn app: dùng app của chuỗi nếu người nhận có thiết bị ở đó, nếu không thì app đầu tiên họ có thiết bị.
  - Service worker (`public/lotus-push-worker.js:8-9`) nhận link có `pathname` đúng gốc app.
- **Không để thông báo làm hỏng thao tác ký:** việc gửi thông báo đẩy và email chạy trong savepoint, có try/except và `frappe.log_error` (FR-021). Thông báo đẩy đưa vào hàng đợi sau khi commit; `_send_alert` bỏ qua thông báo không còn tồn tại.
- **Link trong email:** trỏ tới trang mới `/lotus/mo?dt=&n=`. Trang này tính sẵn cả hai đích (máy tính và điện thoại), rồi chọn theo trình duyệt: màn hẹp hoặc PWA thì sang app điện thoại, còn lại sang màn máy tính. Khách chưa đăng nhập thì sang trang đăng nhập rồi quay lại. Quy tắc route phải đặt trước route bắt-tất-cả `/lotus/<path>` (`hooks.py:162`).
- **Máy tính:**
  - Mua hàng đọc `purchase_doc` và `purchase_doctype` mỗi lần điều hướng (`consumeAction`), không chỉ lúc khởi tạo (`ProcurementWorkspace.vue:171`, `:292-294`).
  - Tài chính đọc `doc` và `doctype` để mở phiếu chi (`FinanceApp.vue:55`).

**Lý do:**
- B1.
- Link đề xuất `/buying?proposal=` không được đọc.
- Thông báo trong app chỉ mở link cùng app (`LotusMobileNotifications.vue:77-87`).
- Không có app "finance" trên điện thoại.

**Đã loại:**
- Thêm app điện thoại riêng cho tài chính: tốn công, ít người dùng.
- Nới `_add_alert` cho mọi link `/lotus/`: service worker vẫn bỏ link đó.

## R4. Hộp Chờ tôi ký và tấm ký chung

**Quyết định:**
- **Máy chủ:**
  - Viết lại `signing.inbox` (`signing.py:340-357`) để mỗi dòng có: loại chứng từ, số, nhãn chuỗi, bước, người lập, số tiền, ngày chứng từ và `notified_at`. Dùng `notified_at` thay `since`, vì `since` không đổi khi chuyển bước (`update_modified=False`).
  - Hộp lọc theo `can_view` (R5) thay vì bỏ hẳn chứng từ không đọc được.
  - Truy vấn gộp theo loại chứng từ, không nạp từng chứng từ.
  - Thêm `signing.inbox_count` (một truy vấn đếm) cho số trên biểu tượng.
- **Tấm ký chung** cho mọi loại chứng từ, gồm:
  - bản xem trước trang in, nhúng trong khung;
  - lịch sử chữ ký;
  - nút Ký, Trả lại, Chuyển người ký;
  - link "Mở chứng từ" về màn nghiệp vụ, dùng khi cần sửa (ví dụ bổ sung giá ở bước mua hàng).
- **Máy tính:** nút có số đếm ở `.workspace-right` của `WorkspaceBar.vue:55`, mở trang `/lotus/cho-ky`. Trang dùng DataTable chọn nhiều để Ký nhiều; bấm dòng mở tấm ký trong WorkspaceModal.
- **Điện thoại:** biểu tượng có số đếm trong header chung (`LotusMobileShell.vue:24`), mở `LotusMobileSignInbox`; bấm dòng mở `LotusMobileSignSheet`. Trang chủ Mua hàng và Kho có thêm thẻ đếm.
- **Ngoài hộp chờ ký:** màn nghiệp vụ vẫn giữ panel ký hiện có.

**Lý do:**
- Một tấm ký dùng được cho mọi chuỗi (đề xuất, đơn mua, phiếu kho, phiếu chi, kỳ công) mà không phải sửa từng màn.
- Người ký không có quyền vào module vẫn ký được.
- Thanh điều hướng dưới đã đủ 4–5 mục, không thêm mục được.

**Đã loại:**
- Mở danh sách chờ ký trong modal từ thanh trên: không có URL riêng, khó chọn nhiều.
- Mỗi chứng từ dẫn về màn riêng của nó: người không có quyền module bị chặn, và mỗi màn lại phải tự có đủ nút ký.

## R5. Người được chỉ định ký luôn xem được chứng từ

**Quyết định:**
- Một hàm `signing.can_view(doctype, name)`: trả đúng khi người dùng có quyền đọc, hoặc có dòng ký trong vòng mới nhất (mọi trạng thái), hoặc là người lập.
- Dùng ở các chỗ:
  - `signing._doc` cho thao tác đọc;
  - `inbox`;
  - các trang in;
  - đọc file đính kèm (`stock_attachments.py:23-28`);
  - `procurement.needs`;
  - `purchase_proposal.detail`.
- Chứng từ liên quan vẫn kiểm quyền từng cái, như `proposal_progress` đang làm. Thao tác ký vẫn chỉ cho người đến lượt (`may_act`).

**Lý do:** `purchase_proposal._doc` (`purchase_proposal.py:54-64`) đã cho người ký đọc, nhưng `inbox`, trang in, file đính kèm, `procurement.needs` và `signing._doc` thì chưa.

**Đã loại:** chia sẻ chứng từ bằng DocShare. Cách này làm sai các phép kiểm quyền ở mức DocType (`purchasing.access`, `warehouse_planning.py:147-163`), và phần chia sẻ còn lại mãi nếu không thu hồi.

## R6. Ký nhiều

**Quyết định:**
- Thêm `signing.sign_many(items=[{doctype, name, modified}])`.
- Mỗi chứng từ chạy trong savepoint riêng, đặt tên `lotus_bulk_sign`, khác tên savepoint `erp_claim` đã có.
- Khóa các chứng từ theo thứ tự đã sắp xếp.
- Mỗi chứng từ đi qua đúng hàm ký của chuỗi mình, theo bảng tra `SIGN_HANDLERS`:
  - đề xuất: `purchase_proposal.sign`;
  - đơn mua: `purchasing.approve_order`;
  - phiếu chi: `payments.sign_payment`;
  - phiếu kho: `signing.confirm`;
  - kỳ công: hàm hiện có.
- Thông báo gom lại, gửi sau vòng lặp.
- Kết quả trả về theo từng chứng từ.

**Lý do:** đường ký không có commit nào bên trong. Mẫu "savepoint cho từng mục" đã chạy ở `hr_operations.py:685-698`. Mạng ở vườn yếu nên tránh gửi nhiều yêu cầu.

**Đã loại:**
- Một yêu cầu cho mỗi chứng từ: nhiều lượt gửi trên mạng yếu.
- Commit sau mỗi chứng từ: commit giữa yêu cầu, trái quy ước của repo.

## R7. Chốt đơn mua theo chữ ký người được chỉ định; bỏ tự duyệt

**Quyết định:**
- Viết lại `purchasing.check_submission` (`purchasing.py:58-67`):
  - bỏ đường tắt `lotus_policy_approved` và phần chỉ kiểm vai trò;
  - áp cho mọi đơn của công ty đang bật luồng mua (đơn cũ trước `lotus_purchase_flow_since` vẫn miễn như `order_guard`);
  - bắt buộc vòng mới nhất khớp các bước của chuỗi `purchase_order`, mọi dòng đã ký, có giờ, có dấu vân tay bằng `signing.fingerprint(doc)` hiện tại;
  - người duyệt được chỉ định vẫn đủ điều kiện (`_validate_person`);
  - người bấm phải là người duyệt đó, hoặc Administrator.
- Xóa `procurement._approve_by_policy` (`procurement.py:412-427`) và nơi gọi duy nhất của nó (`:405-407`). `select_quotes` chỉ tạo đơn nháp; tham số `approver` (tùy chọn) để gửi duyệt ngay (FR-040).
- Xóa `warehouse_buying_lite.submit_order` (không màn nào gọi; nó submit mà không ký).
- Patch: đơn "Chờ duyệt" chưa có vòng ký thì trả về Nháp, kèm ghi chú.
- Ba test tích hợp đang dùng `lotus_policy_approved` chuyển sang ký đúng chuỗi.

**Lý do:** Clarification Q2 (giám đốc ký mọi đơn). Áp cùng mẫu kiểm tra đã dùng cho đề xuất (`purchase_flow.py:42-52`) và phiếu chi (`finance/native_guards.py:21-29`). `approve_order` đã ký trước khi submit (`purchasing.py:202-205`), nên đường Lotus vẫn qua được.

**Đã loại:** giữ tự duyệt có dấu vết. Chủ vườn đã từ chối ở Q2.

## R8. Gỡ đường ký không dùng (FR-022)

**Quyết định:**
- **Máy chủ:**
  - `digital_signature.py:326-411`: `initial_purchase_order`, `_assert_signer_qr`, `create_signing_challenge`, `signing_challenge_details`.
  - Tham số `sign_token` ở `purchasing.py:187`, `:196-199` và `erp_workbench.py:542`.
  - Phần ký nháy trong `lotus_purchase_order_print.py:42-44,51-59`.
  - DocType `Lotus Signing Challenge`: thư mục và một patch xóa DocType.
- **Giao diện:** `BuyingMobile.vue:43,208,224-242,384-390,422-430`.
- **Bản dịch và test:** dòng dịch tương ứng; các test `signature-v2.test.js`, `approval-self-role.test.js` sửa theo.
- **Giữ:**
  - đường xác minh `token=` cũ;
  - các endpoint ký nháy của người dùng (`digital_signature.py:206-234`), cần cho FR-018 và FR-023;
  - các trường ký nháy cũ trên Purchase Order: giữ dữ liệu, chỉ thôi dùng.

**Lý do:** cả hai tính năng đều không chạy: `can_initial` không bao giờ được trả về, `sign_token` không ai đọc. Đơn vẫn duyệt được mà không cần token, nên QR không thêm an toàn.

## R9. Nhật ký ký

**Quyết định:**
- `Lotus Signature Event` thêm trường: `ip`, `user_agent`, `roles`, `designation`, `round`, `step_key`, `content_hash`, `image_sha256`, và index trên (`document_type`, `document_name`).
- `Lotus Sign Request` thêm `signer_designation` và `initials_file`.
- Ghi tại `_record` (`signing.py:205-213`), là đường ghi duy nhất sau khi bỏ nhánh `record=False` của đơn mua. Nguồn:
  - IP lấy từ `frappe.local.request_ip`;
  - User-Agent từ `frappe.get_request_header`;
  - vai trò = vai trò của bước giao với vai trò của người dùng;
  - chức danh lấy từ Employee.
- `reassign` ghi thêm sự kiện REASSIGN: từ ai, sang ai, lý do. Hiện nó chỉ ghi đè trường `note`.
- `return_document` từ chối các chuỗi có bước chốt (đơn mua, phiếu chi), giống như `confirm` đang làm.

**Đã loại:** gom hết vào `details` JSON: bị cắt ở 800 ký tự, hỏng JSON.

## R10. Chữ ký của tôi trên máy tính; chữ ký người giao hàng

**Quyết định:**
- Tách phần không phụ thuộc Vant ra thành:
  - `use-signature-profile.js`: trạng thái, gọi API, kiểm file (`LotusMobileSignatureSettings.vue:26-81`);
  - `SignaturePad.vue`: chỉ có canvas, lấy từ `LotusSignatureDraw.vue:8-44`. Màu nét lấy từ token thay cho `#133b86`.
- Máy tính: `SignatureSettings.vue` dựng bằng `components/ui` trong WorkspaceModal, mở từ menu người dùng (`WorkspaceBar.vue:57-69`).
- Điện thoại giữ màn hiện có, chuyển sang dùng composable chung.
- Chữ ký người giao hàng: `SignaturePad` cộng ô "Họ tên người giao", đặt trong màn xác nhận nhận hàng ở Kho điện thoại và trong `WarehouseReceiving`.

**Đã loại:** đặt nguyên màn Vant vào modal máy tính. Cách này trái quy ước component máy tính (`AGENTS.md`).

## R11. Giai đoạn đề xuất

**Quyết định:**
- Một hàm thuần `proposal_rules.stage(t)` thay cho ba chỗ đang tự tính (`purchase_proposal.py:272-275`, `procurement.py:206-213`, `purchase_flow.py:149-157`).
- Đầu vào là tổng theo dòng, không phụ thuộc người xem. Mỗi dòng, tính theo đơn vị kho:
  - `ordered`, `received`, `billed`;
  - `closed` = phần chưa nhận của các đơn đã đóng, cộng phần chưa đặt nếu đề xuất đã ngừng (Stopped).
- Quy tắc:
  - Chưa submit: Nháp, Bị trả lại hoặc Đang ký.
  - Đã hủy: Đã hủy.
  - Đã submit, xét lần lượt:
    1. mọi dòng có nhận + đóng ≥ số đề xuất: "Đã xong" nếu phần đã nhận đều có hóa đơn, nếu không thì "Đã nhận đủ";
    2. có dòng đơn mua nào (kể cả đơn nháp): Đang mua;
    3. còn lại: Chờ mua.
- `purchase_proposal.proposals` trả thêm số đếm từng giai đoạn.

**Đóng phần chưa mua:**
- Đặt trạng thái native Stopped ở máy chủ, có kiểm vai trò riêng.
- Ghi `lotus_close_reason`, `lotus_closed_by`, `lotus_closed_at` (sửa được sau submit).
- Từ chối khi còn đơn nháp hoặc đơn chờ duyệt trỏ tới đề xuất.

**Hủy:**
- Cancel native, chỉ khi chưa có dòng đơn mua nào (nháp hay đã duyệt) trỏ tới đề xuất.
- Báo giá chưa dùng trỏ tới đề xuất: hệ thống hỏi rồi hủy cùng lúc.
- Ghi `lotus_cancel_reason`. Danh sách có thêm đề xuất đã hủy (hiện lọc `docstatus < 2`, `purchase_proposal.py:253`).

**Lý do:**
- Đề xuất kẹt "Đang mua" vì `proposal_progress` cộng đủ số lượng dòng của đơn đã đóng (`purchase_flow.py:108-109`). Lệnh đóng đơn của ERPNext cũng không tính lại số đã đặt của đề xuất.
- ERPNext 16 không có trạng thái "Closed" cho Material Request, chỉ có "Stopped", và không đóng được từng dòng.
- Mâu thuẫn trong spec giữa "Đã nhận đủ" và "Đã xong" đã được sửa trong spec (FR-030) bằng điều kiện hóa đơn.

**Đã loại:** đóng từng dòng bằng trường `lotus_closed_qty`. Cách này linh hoạt hơn, nhưng chưa ai cần, và làm khác cách tính "còn lại" ở bốn nơi.

## R12. Một biểu mẫu đề xuất; đề xuất từ Excel thiếu lý do

**Quyết định:**
- Kho điện thoại dùng `MobilePurchaseProposal`, thay form rút gọn ở `WarehouseMobile.vue:261-279`.
- Kho máy tính (`WarehousePlanning.vue:49-50`) dùng chung form đề xuất máy tính với Mua hàng. Form này tách từ `ProcurementWorkspace`.
- `purchasing.create_request` bỏ lý do mặc định (`purchasing.py:128`) và bỏ nhánh submit không ký. Hàm còn lại làm lớp bọc cho tương thích.
- `_apply_lines` kiểm kho: cùng công ty, không phải nhóm, không bị tắt.
- `purchase_proposal.sign` nhận `reason` ở bước 0 khi đề xuất chưa có lý do (do Excel nhập vào), lưu trước khi `signing.start`. Lý do nằm trong dấu vân tay nội dung.

**Lý do:** AGENTS.md yêu cầu luồng giữa các app dùng chung component. Hiện có bốn form đề xuất khác nhau. Đề xuất nhập từ Excel bị `sign` chặn (`purchase_proposal.py:375-376`).

## R13. Lập đơn từ đề xuất giữ NCC và giá đã chọn

**Quyết định:**
- Lưu lựa chọn báo giá trên dòng đề xuất bằng các trường `lotus_selected_quote`, `lotus_selected_quote_item`, `lotus_selection_reason` (sửa được sau submit, nằm ngoài dấu vân tay; dấu vân tay chỉ gồm số lượng, giá, kho).
- So sánh giá ghi lựa chọn này khi người dùng chọn.
- `request_detail` (`warehouse_buying_lite.py:143-167`) trả dòng theo NCC đã chọn, kèm giá, thuế, phí vận chuyển và link báo giá. Dòng chưa chọn lấy giá dự kiến, không còn đặt về 0.
- `purchaseFromRequest` (`mobile-purchase.js:8-12`) giữ các trường này.

**Lý do:** hiện lựa chọn chỉ tồn tại trên trình duyệt rồi đi thẳng vào `select_quotes`. Acceptance US3-1 cần lựa chọn được lưu lại.

**Đã loại:** cho "Lập đơn từ đề xuất" đi qua màn so sánh mỗi lần. Thêm một bước, và vẫn mất giá khi không có báo giá.

## R14. Báo trước dòng sẽ bị chặn lúc duyệt

**Quyết định:**
- Tách `purchase_flow.order_issues(doc)` → `[{line, code, message}]` từ `order_guard` (`purchase_flow.py:60-84`). Hàm cộng thêm phần đã giữ chỗ bởi đơn nháp và đơn chờ duyệt khác.
- `save_order` và `request_approval` trả về danh sách này dưới dạng cảnh báo.
- `order_guard` vẫn ném lỗi dựa trên chính danh sách đó.

## R15. Trạng thái đơn mua và thao tác trên máy tính

**Quyết định:**
- Hàm thuần `purchase_status.order_state(...)`. Đầu vào: `docstatus`, trạng thái duyệt, `status` của ERPNext, `lotus_sent_at`, `lotus_supplier_confirmed_at`, số đã nhận. Đầu ra theo bộ tên chung. Quá hẹn là một cờ riêng.
- Máy tính có thêm:
  - sửa và gửi lại đơn nháp hoặc đơn bị trả lại;
  - trả lại (`reject_order`);
  - hủy có lý do;
  - xóa nháp (máy chủ kiểm người lập, không cần quyền delete);
  - in đơn bằng `digital_signature.download_purchase_pdf` / bản lưu của R1.
- Quyền hủy đơn đã duyệt: người duyệt (vai trò `Lotus Purchase Approver` được thêm quyền cancel trên Purchase Order trong `warehouse_access.py`). Chỉ hủy được khi chưa nhận hàng; ghi `lotus_cancel_reason`.
- Báo giá: thêm hủy (từ chối khi còn dòng đơn trỏ tới) và xóa nháp. Sửa báo giá đã xác nhận = hủy rồi sửa lại.

## R16. Một lõi lập hóa đơn

**Quyết định:**
- Module mới `finance/supplier_invoice.py`, hàm `create(...)`, dựng từ `procurement.invoice_receipt` (`procurement.py:484-538`). Các bước:
  1. khóa Company → `idempotent` → `_duplicate` (NCC + ký hiệu + số);
  2. dòng hàng:
     - phiếu nhận: qua `make_purchase_invoice`, gộp được nhiều phiếu;
     - Mua nhanh: ghi Nợ 3388 theo tiền hàng, không gồm chi phí phát sinh;
     - dịch vụ: nhập tay;
  3. sửa được số lượng và giá; dòng nào lệch đơn mua thì có `lotus_variance_reason`;
  4. `apply_line_taxes`: hộ kinh doanh đi 33881 "Valuation and Total", không bao giờ 1331;
  5. `_match_invoice_total` với ngưỡng 1 đồng × số dòng hàng, nêu tên dòng nghi sai;
  6. submit, gắn file, ghi link vào các phiếu Mua nhanh.
- `procurement.invoice_receipt`, `payments.make_goods_invoice` và `make_service_invoice` thành lớp bọc mỏng gọi lõi này. Việc gộp này sửa luôn B4.
- Giá vốn theo giá hóa đơn (FR-051):
  - Phiếu nhận: lúc đầu định bật Buying Settings `set_landed_cost_based_on_purchase_invoice_rate` bằng migration. Sau buổi thử trên bản sao site thật, đã đổi sang Lotus tự ghi Landed Cost Voucher theo từng hóa đơn (xem cuối mục này).
  - Mua nhanh: dùng mẫu điều chỉnh giá đã có (`finance/stock.py:155-189`).
- `stock_attachments` cho phép đính kèm file vào Purchase Invoice và Payment Entry.

**Lý do:** bốn đường lập hóa đơn đang lệch nhau ở thuế (1331 so với 33881), kiểm trùng, khóa và idempotency. Hai đường của Tài chính không có khóa nên hai người có thể cùng qua bước kiểm trùng.

**Đã loại:** giữ bốn đường và chỉ dùng chung phần kiểm tra. Phần dựng dòng vẫn tiếp tục trôi lệch như đã xảy ra.

**Kết quả thử (T081, 10/11/2026, site `procurement.test`):**
- Bật `set_landed_cost_based_on_purchase_invoice_rate` thì hóa đơn khác giá phiếu nhận được ERPNext định giá lại phiếu nhận qua job "Repost Item Valuation". Sau khi job chạy, 3388 về 0 và đơn giá nhập kho bằng giá hóa đơn (`verify_procurement.py`, ca test_21). Trước khi job chạy (job theo lịch của ERPNext), phần chênh lệch nằm tạm trên 3388.
- Phải tắt `maintain_same_rate` và nới `over_billing_allowance` (đặt 100%), nếu không ERPNext chặn giá hóa đơn cao hơn đơn mua trước khi Lotus kịp hỏi lý do. Ba thiết lập này do `procurement_setup.install` đặt; Lotus tự giữ quy tắc: số lượng không vượt phần chưa có hóa đơn, giá khác phải có lý do.
- Hộ kinh doanh: hóa đơn cho hai phiếu nhận thuế 5% và 8% có phí vận chuyển không ghi 1331, 33881 về 0 (ca test_20, test_23).
- Mua nhanh: hóa đơn ghi Nợ 3388 theo tiền hàng (`basic_amount`), 3388 về 0 (ca test_22).

**Giới hạn còn lại:** một hóa đơn chưa gồm được cả phiếu nhận theo đơn và phiếu Mua nhanh (hai cách tính thuế khác nhau); hệ thống báo rõ và yêu cầu chọn riêng từng loại.

**Thử trên bản sao site thật và đổi cách làm (10/11/2026).** Thử kịch bản US5 trên trình duyệt với `mua.test` cho thấy cách "bật thiết lập ERPNext" không đủ. Theo đúng điều kiện đã ghi ở plan.md (Complexity Tracking), phần này chuyển sang cách Lotus tự ghi điều chỉnh:
- Thiết lập `bill_for_rejected_quantity_in_purchase_invoice` của ERPNext đang bật (mặc định). Khi bật, hóa đơn lập từ phiếu nhận tính cả hàng đã trả lại. Ca thử: nhận 60 kg, trả 5 kg, hóa đơn vẫn ghi 60 kg, 3388 lệch 600.000 đ. Lotus không ghi hàng bị loại, nên thiết lập này nay tắt. Khi tắt, ERPNext trừ hàng đã trả và lại kiểm hóa đơn vượt giá trị đơn mua.
- Cơ chế `set_landed_cost_based_on_purchase_invoice_rate` có ba chỗ hụt:
  - trải phần chênh giá lên toàn bộ số đã nhận, kể cả hàng đã trả và phần chưa có hóa đơn;
  - bỏ qua phần thuế chênh của hộ kinh doanh, nên 33881 còn 189.000 đ khi hóa đơn khác giá và khác thuế suất;
  - tính "đã có hóa đơn" theo tiền, nên hóa đơn rẻ hơn phiếu nhận để phiếu nhận "chưa đủ hóa đơn" mãi.

  Thiết lập này nay tắt. `finance/invoice_cost.py` ghi theo từng hóa đơn, cho đúng số lượng trên hóa đơn (bản cuối, sau rà soát độc lập 11/11/2026):
  - **Kỳ của phiếu nhận còn mở.** Phần chênh của từng dòng (giá, cộng thuế với hộ kinh doanh) vào giá vốn bằng Landed Cost Voucher, ghi Có 3388. Mỗi chiều tăng hoặc giảm là một phiếu.
    - Chỉ dùng một tài khoản vì ERPNext bỏ qua bút toán của mọi phiếu khi tổng phiếu trên một dòng bằng 0. Hai phiếu bù trừ nhau trên 3388 và 33881 từng làm cả hai tài khoản lệch.
    - Phần thuế chênh chuyển từ 3388 sang 33881 bằng một bút toán ngày hóa đơn.
    - Bỏ qua bước chuyển này khi phiếu nhận không có bút toán nào trên các tài khoản thuế tính vào giá vốn của hóa đơn. Khi đó ERPNext đã tự ghi thuế hóa đơn vào 3388 (`purchase_invoice.make_item_gl_entries`, nhánh "negative expense").
  - **Hàng trả lại.** Sau mỗi hóa đơn, mỗi lần trả và mỗi lần hủy trả, phần chênh C của dòng được chia lại theo số đã có hóa đơn (`rebalance`, phiếu chia gắn `lotus_cost_receipt`). Ký hiệu: Q nhận, r mỗi lần trả, K còn giữ, b đã có hóa đơn (trừ hóa đơn điều chỉnh).
    - Hàng giữ lại mang C·min(b, K)/b: dòng nhận được C·min(b, K)/b·Q/K − C, mỗi dòng trả −r·C·min(b, K)/(b·K). Khi b ≤ K, đây là cách chia cũ: dòng nhận C·Q/K, dòng trả −C·r/K.
    - Hóa đơn tính cả hàng sau đó trả lại (b > K): phần chênh của hàng đó nằm trên 3388 cùng tiền hàng, thành khoản NCC phải hoàn, đến khi có hóa đơn điều chỉnh.
    - Trả hết (K = 0): phần chênh đi theo các dòng trả, dòng trả cuối nhận phần lẻ.
    - Hàng trả ra khỏi kho đúng giá vốn của nó, không ghi khoản "divisional loss" vào 632.
    - Phiếu chia ghi lần lượt từng chứng từ, phiếu nhận trước, phiếu trả sau. ERPNext tính lại phiếu trả theo đơn giá của phiếu nhận ngay lúc phiếu của nó được ghi; phần còn lại chỉ được xếp vào job định giá lại hằng giờ. Chứng từ có phép chia không đổi thì để yên.
    - Mọi hóa đơn và hóa đơn điều chỉnh, kể cả không có chênh lệch, đều chia lại các phiếu nhận của nó, vì số đã có hóa đơn đổi. Khi hủy, chứng từ đang hủy không còn được tính, dù trong `before_cancel` nó vẫn ở trạng thái đã ghi sổ.
  - **Phí vận chuyển theo từng dòng (hộ kinh doanh).** ERPNext chia dòng phí vận chuyển cho hàng kho theo giá trị dòng (`_spread_charge_over_items`). Hóa đơn và phiếu trả lại tính phí theo từng dòng. Phiếu chia chuyển phần chênh để mỗi dòng mang đúng phí của nó, trên phiếu nhận và cả phiếu trả (`_freight_shares`). Tổng phiếu chia trên 3388 bằng 0. Chứng từ có dòng tài sản giữ cách chia của ERPNext, vì tài sản chưa ghi sổ chưa nhận được Landed Cost Voucher.
  - **Kỳ của phiếu nhận đã khóa.** Gồm: ngày khóa sổ của công ty, Accounting Period khóa Purchase Receipt, kết chuyển kết quả của Lotus, Period Closing Voucher, Stock Closing Entry đã xong. Với Period Closing Voucher, ERPNext không cho ghi lại phiếu nhận, nên trước đây hóa đơn không ghi sổ được.
    - Sổ kỳ đó không đổi. Phần chênh thành chi phí kỳ hóa đơn trên tài khoản chi phí của dòng (giữ vườn/lô), bằng bút toán ngày hóa đơn.
    - Hủy hóa đơn mà phiếu điều chỉnh của nó rơi vào kỳ nay đã khóa thì bị chặn, kèm hướng dẫn lập hóa đơn điều chỉnh.
  - **Hóa đơn điều chỉnh** đi theo cách hóa đơn gốc đã ghi:
    - gốc đưa dòng đó vào giá vốn → điều chỉnh vào giá vốn;
    - gốc ghi chi phí → điều chỉnh ghi chi phí, kể cả khi kỳ đã mở lại;
    - kỳ của phiếu nhận nay đã khóa → ghi chi phí;
    - ngoại lệ: hàng đã trả sau hóa đơn, lúc kỳ còn mở, nên phần chênh của nó đang chờ trên 3388 như khoản NCC phải hoàn, và nay kỳ đã khóa. Ghi chi phí lúc này sẽ để treo khoản đó và tạo một khoản lãi giả. Ghi đúng thì phải theo dõi riêng phần đã hoàn của từng dòng, nên Lotus từ chối và hướng dẫn mở lại kỳ, ghi hóa đơn điều chỉnh, rồi khóa lại (test_42).
  - **Liên kết và chặn.** Phiếu và bút toán gắn với hóa đơn qua `lotus_purchase_invoice` và hủy trước khi hóa đơn hủy. Không hủy, sửa hay "Hủy tất cả" riêng chúng được (`guard`), và mỗi loại có thông báo riêng. Buying Settings không bật lại được hai thiết lập ERPNext đã tắt (`settings_guard`).
  - **Trường hợp riêng.**
    - Cùng giá nhưng khác tỷ giá: để ERPNext tự ghi chênh tỷ giá.
    - Dòng tài sản cố định khác giá: bị chặn, hướng dẫn điều chỉnh nguyên giá. Thuế suất chỉ đổi được sang mã thay mã đã hết hạn (8% → 10% sau 31/12/2026); phần thuế chênh ghi chi phí, nguyên giá giữ như lúc nhận.
    - Thuế suất của hóa đơn trả lại lấy theo ngày hóa đơn gốc.
    - Mã hết hạn được thay theo `then` trong `vat_vn.json` (`rules.vat_code_on`): hàng đặt 8% nhận sau 31/12/2026 ghi 10%, và hóa đơn sau ngày đó lấy 10% cho dòng phiếu nhận 8%.
- Phần trăm "đã có hóa đơn":
  - phiếu nhận: đo trên phần còn giữ (nhận − trả). Mỗi dòng tính phần đã có hóa đơn trên phần giữ, theo giá trị dòng. Phiếu trả hết tính là xong.
  - ERPNext 16 để `returned_qty` và `per_returned` của phiếu nhận bằng 0 với các lần trả này. `get_returned_qty_map` cũng chỉ giữ một lần trả cho mỗi dòng. Lotus tự cộng các lần trả (`returned_qty_map`) và giữ `per_returned`. Trạng thái "Đã trả hết hàng" thì không còn nút lập hóa đơn.
  - đơn mua: tính theo số đã đặt;
  - tạm ứng theo đơn mua (`purchase_funding.order_advance_room`): tối đa bằng phần chưa có hóa đơn trừ phần tạm ứng chưa trừ vào hóa đơn. ERPNext 16 vẫn cộng phần tạm ứng đã trừ vào hóa đơn trong `advance_paid`.
    - Đơn đã có hóa đơn đủ hoặc đã đóng thì không tạm ứng thêm.
    - Mọi đường chi đều kiểm (`_remaining_source`), kiểm lại lúc ký cuối (`order_advance_guard`).
- Hộ kinh doanh, dòng không có giá trị kho (dịch vụ):
  - trên mọi chứng từ (đơn mua, phiếu nhận, hóa đơn, hóa đơn điều chỉnh), không mang mẫu thuế 33881;
  - thuế và phí vận chuyển vào chi phí của chính dòng đó, giữ vườn/lô (`_line_costs`).

  Lý do: phiếu nhận chỉ ghi Có 33881 và 3388 phần nó tính vào giá vốn.
- Hộ kinh doanh, phí vận chuyển của hàng kho và tài sản:
  - ghi vào 3388 (không ghi 33881), với `allocate_full_amount_to_stock_items`;
  - mỗi dòng mang phí của chính nó (xem trên). Phí của dòng dịch vụ không còn vào hàng kho (rà soát lần 2).

  Lý do không ghi 33881: ERPNext 16 dựng lại thuế suất từng dòng theo tài khoản. Phí vận chuyển chung tài khoản với thuế theo dòng thì báo "Item Wise Tax Details do not match" ngay khi có dòng 0% hoặc dòng dịch vụ. Cũng vì lẽ đó, phần làm tròn của hóa đơn khấu trừ có dòng 0% ghi vào tài khoản làm tròn, không ghi 1331.
- Số thứ tự dòng: phiếu nhận tách dòng tài sản thành từng chiếc, phiếu trả, hóa đơn điều chỉnh và hóa đơn có dòng dịch vụ được đánh số lại 1..n (`procurement.renumber`). ERPNext chia thuế và phí theo số thứ tự dòng, nên số trùng làm một dòng nhận phí hai lần.
- "Hàng đã nhận, chưa có hóa đơn" (FR-057) tính theo đúng phần phiếu nhận đã ghi vào 3388/33881:
  - tiền hàng của dòng hàng kho và tài sản;
  - với hộ kinh doanh, thuế và phí vận chuyển của chính các dòng đó;
  - cộng phiếu chia của phiếu nhận và phần chênh của các hóa đơn ghi sau ngày chốt.

  Số chờ âm khi hóa đơn tính cả hàng sau đó trả lại: đó là khoản NCC phải hoàn, chờ hóa đơn điều chỉnh. Màn Công nợ ghi rõ. Không tính dòng dịch vụ và chi phí nhận hàng. Hai số khớp nhau ở mọi ngày chốt.
- Ca kiểm (`verify_procurement.py`):
  - test_24: trả trước hóa đơn, tăng giá, giảm giá, đổi thuế suất, dòng dịch vụ, hủy;
  - test_25: phiếu nhận không thuế, hóa đơn có thuế;
  - test_26: dịch vụ trên đơn kèm phí vận chuyển (phí của dịch vụ vào chi phí dịch vụ);
  - test_27: trả sau hóa đơn (số chờ âm bằng 3388), rồi hóa đơn điều chỉnh;
  - test_28: kỳ đã khóa;
  - test_29: "đã có hóa đơn" theo giá trị và theo trả hàng;
  - test_30: tài sản khác giá;
  - test_31: khớp sổ ở mọi ngày chốt;
  - test_32: chặn hủy riêng;
  - test_33: tài sản tách chiếc, số dòng 1..n;
  - test_34: phí vận chuyển theo từng dòng, trả hết một dòng;
  - test_35: trả hết sau hóa đơn qua hai lần trả, khoản NCC phải hoàn, hóa đơn điều chỉnh;
  - test_36: hóa đơn điều chỉnh đi theo hóa đơn gốc ghi chi phí;
  - test_37: Period Closing Voucher;
  - test_38: tạm ứng theo đơn sau khi một phần có hóa đơn, kiểm lại lúc ký;
  - test_39: mã 8% hết hạn (phiếu nhận, tài sản);
  - test_40: làm tròn hóa đơn khấu trừ có dòng 0%;
  - test_41: Buying Settings;
  - test_42: hóa đơn điều chỉnh cho hàng trả sau hóa đơn khi kỳ đã khóa.

  Mỗi ca kiểm 3388 và 33881 về 0 (hoặc bằng khoản NCC phải hoàn), giá trị hàng giữ lại, và không có khoản nào vào chi phí khi trả hàng.
- **Rà soát lần 3 (11/11/2026, 25 phát hiện: 24 xác nhận, 1 bác bỏ), đã sửa:**
  - Đơn mua đã đóng phần còn lại (Đóng đơn): ERPNext không cho ghi lại phiếu nhận của đơn đã đóng, mà Landed Cost Voucher nào cũng ghi lại phiếu nhận. Trước đây hóa đơn khác giá, hóa đơn điều chỉnh và việc hủy đều bị chặn. Nay Lotus coi đơn là mở trong lúc ghi hoặc hủy phiếu (`_orders_open`), đóng lại ngay, rồi tính lại số đặt mua của kho.
  - Tạm ứng trả trong tháng đã kết chuyển: ERPNext gắn tạm ứng vào hóa đơn mới bằng cách lưu lại phiếu chi cũ, và bước kiểm tháng đã kết chuyển chặn cả hóa đơn. Lần lưu đó không đổi bút toán nào, nên nay được cho qua (cờ `ignore_reposting_on_reconciliation` của ERPNext).
  - Khoản NCC phải hoàn trên 3388 được đo đúng: tổng phiếu chia của dòng và các dòng trả, trừ phần phí vận chuyển (`_parked_claim`). Lotus kiểm mọi dòng của hóa đơn điều chỉnh và của hóa đơn bị hủy, kể cả dòng không có chênh lệch.
  - "Đã có hóa đơn" chỉ thành 100 khi mọi dòng có giá trị đã có hóa đơn đủ (trước đây 99,99% bị coi là xong). "Đã trả hết hàng" chỉ khi không còn giữ dòng nào. Cả hai áp dụng cho đơn mua.
  - Tài chính › Đối chiếu và ô "Hàng về chưa có hóa đơn" dùng 3388 + 33881 và cùng cách tính với Công nợ (`procurement_queries.unbilled`). T082 trước đây đánh dấu xong nhưng chưa làm.
  - Công nợ tách khoản NCC phải hoàn khỏi hàng chưa có hóa đơn. Hàng chưa có hóa đơn tính cả phiếu bổ sung giá Mua nhanh.
  - "Còn phải lập hóa đơn" của phiếu nhận và phần còn tạm ứng được của đơn tính theo từng dòng, gồm thuế và phí vận chuyển của chính dòng.
  - Thuế 8% hết hạn: biểu mẫu hóa đơn tự chuyển dòng sang 10% theo ngày hóa đơn. Báo giá được so sánh và đặt hàng theo thuế suất đang áp dụng. Tài sản có hóa đơn 8% trước ngày hết hạn được giữ 8%. Đường nhập một thuế suất cho cả hóa đơn so theo thuế suất tại ngày hóa đơn.
  - Bảng kê thuế GTGT mua vào: tách theo thuế suất từng dòng và chỉ lấy dòng thuế. Hộ kinh doanh không đối chiếu với TK 1331.
  - Ca kiểm test_43–test_51 và sổ sách ở test_29.
- **Chi phí nhận hàng của hàng trả lại:** chi phí bốc xếp và các chi phí nhận hàng khác (dòng Actual 'Valuation') được phân bổ vào giá vốn khi nhận. Khi trả hàng, ERPNext ghi phần chi phí của số hàng trả vào chi phí (divisional loss). Chi phí này đã phát sinh và NCC không hoàn lại, nên Lotus giữ cách ghi đó (rà soát lần 3, phát hiện mức thấp).
- **Giới hạn còn lại: phần lẻ đồng.** Thuế chênh được tính và làm tròn theo từng dòng của từng hóa đơn. Phí vận chuyển và tiền hàng của hóa đơn từng phần chia theo số lượng (ví dụ phí 50.000 đ của 3 đơn vị, lập 3 hóa đơn thì mỗi hóa đơn 16.667 đ). Vì vậy, với số lượng lẻ, mỗi dòng có thể còn ±1 đồng trên 3388/33881 sau khi có hóa đơn đủ (rà soát lần 2). Màn Công nợ khi đó báo lệch vài đồng so với sổ cái. Kế toán xử lý bằng một bút toán làm tròn. Nếu sau này lệch nhiều, thêm bước "khi dòng có hóa đơn đủ thì lần cuối lấy phần còn lại".
- **Trước khi đưa lên site thật:** phiếu nhận do bản cũ ghi (phí vận chuyển của hộ kinh doanh trên 33881, dòng Actual không có `allocate_full_amount_to_stock_items`) sẽ lệch số chờ. Bản sao site thật ngày 10/11/2026 không có phiếu nào như vậy (17 phiếu nhận). Chạy lại truy vấn ở quickstart §5 trên site thật ngay trước khi nâng cấp.

## R17. Hủy hóa đơn

**Quyết định:**
- Endpoint mới `supplier_invoice.cancel(name, reason, modified)`:
  - bắt buộc lý do; khóa Company và hóa đơn;
  - chặn khi có: dòng sổ thanh toán từ chứng từ khác, phiếu chi nháp, khoản chi hộ, hóa đơn trả hàng, tạm ứng đã cấn trừ. Thông báo chỉ hướng "đảo phiếu chi trước hoặc lập hóa đơn điều chỉnh";
  - kiểm kỳ còn mở; hủy qua phần lõi của `posting.reverse`;
  - xóa `lotus_purchase_invoice` trên các phiếu Mua nhanh, giữ file.
- Hook `before_cancel` của Purchase Invoice chạy cùng phép chặn, để Desk không đi vòng được.

**Lý do:** hiện không có phép chặn nào của Lotus khi hủy hóa đơn đã có thanh toán. ERPNext có thể lặng lẽ biến khoản đã cấn trừ thành tạm ứng.

## R18. Công nợ: tuổi nợ, đến hạn, hàng chưa có hóa đơn, sổ chi tiết

**Quyết định:**
- **Tuổi nợ:** đọc Payment Ledger Entry trên TK 331 đến ngày chốt, gộp theo NCC và hóa đơn, lấy `max(due_date)`.
  - Số dương chia nhóm theo số ngày từ hạn trả đến ngày chốt.
  - Số âm là tạm ứng.
  - Số dư đầu kỳ không có hạn trả vào nhóm riêng.
- **Đến hạn trong 7 ngày:** hạn trả trong khoảng ngày chốt + 1 đến ngày chốt + 7.
- **Hàng đã nhận chưa có hóa đơn:**
  - Phiếu nhận: (đã nhận − đã trả − đã có hóa đơn đến ngày chốt) × đơn giá nhập kho của dòng.
  - Mua nhanh: theo mẫu đã có ở `finance/reports.py:296-303`.
  - Tổng phải khớp −(3388 + 33881). Sửa luôn phép đối chiếu hiện chỉ lấy 3388 (`finance/reports.py:305-306`).
- **Sổ chi tiết:** dùng `statements.general_ledger(331, from, to, party)` và `party_summary` (`finance/statements.py:162-224`). Dòng được phân loại: hóa đơn, điều chỉnh, phiếu chi, tạm ứng, hoàn tiền, chi hộ, số đầu kỳ.
- **In biên bản đối chiếu:** trang in mới.
- **Tính toán:** các phép chia nhóm, cộng dồn, ngưỡng nằm ở module thuần.

**Lý do:** tuổi nợ hiện tính theo ngày hôm nay, không theo ngày chốt (`finance/payments.py:315-319`). `invoices` cũng chỉ trả số dư hôm nay.

## R19. Một lõi lập phiếu chi; in phiếu chi

**Quyết định:**
- Tách lõi từ `payments.prepare_supplier_payment` (`finance/payments.py:327-374`). Lõi nhận:
  - phân bổ cho nhiều hóa đơn, hoặc tạm ứng theo đơn mua;
  - hình thức chi; số tham chiếu và ngày chứng từ ngân hàng;
  - file đính kèm;
  - phần chi vượt ghi rõ là tạm ứng;
  - khóa idempotency.

  Lõi kiểm số còn nợ, đã trừ phiếu nháp, rồi bắt đầu ký.
- `procurement.supplier_payment` và `prepare_supplier_payment` thành lớp bọc.
- Mua hàng mở được "Đảo phiếu chi" cho kế toán trưởng, gọi `posting.reverse`.
- Trang in mới `lotus_payment_print`:
  - phiếu chi tiền mặt có ô trống cho Thủ quỹ và Người nhận tiền; giấy đề nghị chi khi chuyển khoản;
  - số tiền bằng chữ qua `print_kit.amount_in_words_vi`;
  - chữ ký chuỗi phiếu chi; QR.
  - Dữ liệu lấy từ `_voucher_info` (`finance/payments.py:457-480`), bổ sung ký hiệu và số hóa đơn, mã số thuế và tài khoản ngân hàng của NCC.

**Lý do:** Mua hàng hiện chỉ trả một hóa đơn mỗi phiếu (`ProcurementWorkspace.vue:263-273`). Tài chính trả nhiều hóa đơn nhưng thiếu idempotency, thiếu tạm ứng theo đơn và không có hình thức chi. Chưa có mẫu in phiếu chi.

## R20. Nhận hàng một đường, xác nhận là thủ kho ký

**Quyết định:**
- Kho điện thoại và `WarehouseReceiving` cùng gọi `warehouse_planning.receive_order` ở chế độ ghi sổ một bước, kèm:
  - chi phí phát sinh;
  - danh sách file đã tải lên, gắn vào phiếu trong cùng giao dịch;
  - người giao hàng: `lotus_deliverer_name` và `lotus_deliverer_signature` (ảnh riêng tư), hoặc `lotus_delivery_proof` (ảnh phiếu giao có chữ ký).
- Hook `before_submit` của Purchase Receipt bắt buộc "họ tên + chữ ký" hoặc "ảnh phiếu giao" với phiếu theo đơn của công ty đang bật luồng mua.
- Chuỗi mới `purchase_receipt`: một bước, có bước chốt. Ngay sau submit, `signing.start` ghi chữ ký của người xác nhận, rồi R1 lưu PDF. Lỗi thì rollback cả việc ghi sổ.
- `chain_for` giữ các vòng `stock_document` cũ trên chuỗi cũ.
- Hai người nhận cùng lúc:
  - Phép chặn nhận vượt (khóa `FOR UPDATE`, `controls.py:17-21`) giữ nguyên.
  - Lỗi "record changed" hoặc deadlock của MariaDB được bắt, rollback, đọc lại rồi báo "Còn nhận được N" (US4-3).
- **Trả hàng:** `return_receipt` thêm `post=1` để ghi sổ ngay. Nếu phiếu gốc đã có hóa đơn, hệ thống nhắc lập hóa đơn điều chỉnh.
- **Hủy phiếu:** có lý do (`lotus_cancel_reason`), quyền quản lý kho.
- **Xóa nháp:** máy chủ kiểm người lập hoặc vai trò nhận hàng.
- **Ở Mua hàng:** chi tiết phiếu nhận có in và đính kèm.
- **Nhãn:** thống nhất "Mua nhanh" (hiện Kho ghi "Mua ngoài", `warehouse.py:330`).

**Lý do:**
- Clarification Q3.
- Chuỗi `stock_document` có bước "người giao" cần tài khoản Lotus, mà người giao của NCC không có.
- Kho điện thoại hiện đi hai bước, không có ảnh và chi phí (`WarehouseMobile.vue:422-446`).

## R21. Tên trạng thái chung

**Quyết định:**
- Máy chủ: module thuần `lotus_farm/purchase_status.py`, gồm giai đoạn đề xuất (R11), trạng thái đơn (R15), phiếu nhận, hóa đơn và phiếu chi, kèm nhãn tiếng Việt.
- Giao diện: `frontend/src/purchase-status.js` giữ nhãn và tông màu.
- Thay khoảng 15 bảng nhãn đang rải rác, trong đó có:
  - `buying-order-status.js`, `MobilePurchaseOrderDetail.vue:11`, `BuyingMobile.vue:75-79`;
  - `MobilePurchaseProposal.vue:27-38`, `ProcurementWorkspace.vue:68-414`, `PurchaseProgress.vue:25`;
  - `WarehouseReceiving.vue:63,76`, `WarehouseMobile.vue:456,661,674`, `stock-columns.js:6`;
  - `FinanceApp.vue:358,442,530`;
  - phía máy chủ: `purchasing.py:10,246,266`, `warehouse_buying_lite.py:304-305`, `procurement.py:206-210`.
- Đổi tên:
  - Từ chối → Bị trả lại;
  - Hoàn tất → Đã xong;
  - Đã duyệt chờ mua → Chờ mua;
  - Đã ghi sổ / Đã xác nhận (phiếu nhận) → Đã nhập kho.

## R22. Cấu trúc giao diện

**Quyết định:**
- Tách `ProcurementWorkspace.vue` (69,8 KB, 26 dòng dài trên 400 ký tự) thành `components/procurement/*` theo từng màn, cộng `use-procurement.js` chung (công ty, danh mục, run, ask, act, open). Mỗi màn giữ hai chế độ máy tính / điện thoại qua prop `mobile` như hiện nay.
- Bỏ hai link sang Desk (`ProcurementWorkspace.vue:424`, `:438`).
- Màn so sánh giá có chế độ điện thoại: mỗi mặt hàng một thẻ, mỗi báo giá một dòng chọn (FR-033).
- Kho điện thoại:
  - dùng form đề xuất chung;
  - nhận hàng một bước, có ảnh và người giao;
  - gửi duyệt đơn bằng `MobilePurchaseOrderDetail` như app Mua hàng.
- Đọc link sâu thống nhất bằng `mobile-deep-link.js`:
  - tham số đọc được: `sign_dt`/`sign_dn`, `doctype`/`doc`, và các tham số cũ `proposal`, `request`, `tab`;
  - mỗi app tự khai bảng hàm mở chứng từ của mình;
  - đọc xong thì xóa tham số bằng `history.replaceState`.

**Lý do:** file hiện quá dài. Muốn thêm thao tác cho từng loại chứng từ mà không phình thêm thì phải tách, và mỗi màn tách ra có test mount riêng.

## R23. Kiểm thử và môi trường thử

**Quyết định:**
- Frontend: chạy trong worktree `C:\code\lotus-003-mua-hang\frontend` (cần `npm ci` trước): `npm test`, `npm run build`. Kiểm DOM điện thoại bằng `tools/verify_mobile_purchase_dom.mjs` ở 320, 390 và 844 px.
- Python thuần: `python -m unittest discover -s tests -v`, chạy trong container vì máy này không có Python.
- Tích hợp:
  - Một container từ image `lotus-local-test:20261104`, mount worktree này vào `apps/lotus_farm`, nối vào mạng `lotus-vps-test`.
  - Site riêng `mua.test`, khôi phục từ bản sao lưu site `frontend`. Không đụng site `frontend` mà phiên spec 002 đang dùng.
  - Chạy `tests/integration/*.py` với `SITE=mua.test`, `LOTUS_PROCUREMENT_TEST_ONLY=1`. Thông báo đẩy và email tắt trong tiến trình thử.
- GitHub Actions chạy `ui-build` khi có PR. Chỉ tạo PR hoặc commit khi chủ vườn yêu cầu.
