# Kế hoạch gộp `main` vào spec 003 (chuẩn bị ngày 11/11/2026)

## Bối cảnh

- `main` (737f686, spec 002 bản phát hành 2, đang chạy thật là b71a0b5) đã đi xa so với điểm gộp gần nhất của spec 003 (40f8330). Bản phát hành 2 xóa 79 bảng đời cũ (Material Requirement, Daily Work Plan, Lotus Farm Settings, Harvest Lot…) cùng mã dùng chúng.
- Đã chạy thử gộp bằng `git merge-tree` (không đổi nhánh, chỉ mục hay thư mục làm việc). Kết quả:
  - 13 tệp xung đột;
  - 18 tệp hai bên cùng sửa nhưng tự gộp được.
- Mỗi tệp được một người phân tích ba bản (gốc, `main`, spec 003), rồi người thứ hai kiểm lại. Cả năm nhóm tệp đều được xác nhận.
- Nguyên tắc chung: lấy bản của `main` (đã bỏ phần đời cũ), rồi thêm lại đúng các thay đổi nhỏ của spec 003.
- Không tệp nào của spec 003 gọi tới mã `main` đã xóa, ngoài các chỗ xung đột dưới đây.

## Thứ tự làm (khi chủ vườn đồng ý commit và đưa lên)

1. Commit phần chưa commit của spec 003 trên nhánh `003-mua-hang-ky-dien-tu`.
2. `git merge main`.
3. Giải 13 xung đột theo các mục dưới. Cách nhanh: chạy `node tools/merge-003-main/resolve.cjs --release-id=<ngày đưa lên, ví dụ 2026-11-12>`.
   - Script làm đúng các cách giải dưới đây, kể cả `git rm` tệp `material_requirement.js`, cùng ba sửa ở mục "Ngoài xung đột".
   - Nó dừng nếu một xung đột khác với lúc chuẩn bị.
   - Đã thử trên bản clone tạm: kết quả trùng từng byte với cây đã kiểm trên VPS (tree `7b9c420`).
4. Kiểm nhanh bằng `git grep` (mục "Kiểm sau khi gộp").
5. Đẩy lên chỗ thử trên VPS, chạy toàn bộ bộ kiểm. Không chạy trên máy này.
6. Build giao diện trên VPS, rồi commit `lotus_farm/public/frontend`. Bản build trong cây gộp là của `main`, chưa có màn nào của spec 003.
7. Đưa lên theo `deploy.md`: sao lưu, build image, migrate. Trên site thật chỉ hai patch mới của spec 003 chạy, vì `purge_legacy_doctypes` đã chạy ở b71a0b5. Sau đó smoke test, rồi làm vòng nghiệm thu `checklists/acceptance.md`.

## Các tệp xung đột

### `lotus_farm/hooks.py`: viết lại đoạn xung đột

**Nguy hiểm nhất.** Giữ bản spec 003 thì `hooks.py` báo `KeyError: 'Harvest Actual'` ngay lúc nạp, và mọi request lẫn migrate đều hỏng.

Thay cả đoạn xung đột (nằm giữa `permission_query_conditions['Packhouse Shift']` và `doc_events['Purchase Order']`) bằng:

```python
website_route_rules = [{'from_route':'/login','to_route':'lotus_login'},{'from_route':'/lotus/in-phieu','to_route':'lotus_stock_print'},{'from_route':'/lotus/in-cong','to_route':'lotus_timekeeping_print'},{'from_route':'/lotus/in-de-xuat','to_route':'lotus_material_proposal_print'},{'from_route':'/lotus/in-luong','to_route':'lotus_payroll_print'},{'from_route':'/lotus/in-phieu-ngay','to_route':'lotus_daily_form'},{'from_route':'/hr-mobile','to_route':'hr_mobile'},{'from_route':'/lotus/in-don-mua','to_route':'lotus_purchase_order_print'},{'from_route':'/lotus/in-hoa-don','to_route':'lotus_invoice_print'},{'from_route':'/lotus/in-phieu-chi','to_route':'lotus_payment_print'},{'from_route':'/lotus/in-doi-chieu','to_route':'lotus_statement_print'},{'from_route':'/lotus/mo','to_route':'lotus_open'},{'from_route':'/lotus/<path:app_path>','to_route':'lotus'}]

doc_events['Material Request']={'validate':['lotus_farm.purchase_flow.validate'],'before_submit':['lotus_farm.purchase_flow.validate']}
# Runs after ERPNext's own validate (which sets the default buying price list): a proposal keeps its typed prices.
doc_events['Material Request']['validate'].append('lotus_farm.purchase_flow.keep_proposal_prices')
```

Bỏ mọi thứ khác của bên spec 003 trong đoạn này:
- các vòng lặp Packout Run, Harvest Actual, Harvest Lot;
- các mục Daily Work Plan, Bunch Cancellation, Material Requirement;
- `warehouse_planning.validate_request_lineage`;
- vòng `for _proposal_event` (vòng này sẽ bọc danh sách của `main` thành danh sách lồng).

Phần đuôi 35 dòng của spec 003 (invoice_cost, Buying Settings, Payment Entry) đã tự gộp.

### `lotus_farm/patches.txt`: giữ cả bốn dòng

Giữ đúng thứ tự: hai dòng của `main` trước (đã chạy trên site thật), hai dòng của spec 003 sau. Không sửa hay đổi thứ tự các dòng cũ, vì Patch Log ghi theo đúng chữ của từng dòng.

```
lotus_farm.patches.purge_legacy_doctypes
lotus_farm.patches.work_schedule_rule_unique_per_farm
lotus_farm.patches.return_unsigned_pending_orders
lotus_farm.patches.drop_signing_challenge
```

Lưu ý: bản sao `mua.test` chưa chạy patch purge của `main`. Lần migrate tới trên bản sao sẽ chạy nó, và nó có thể dừng nếu còn dữ liệu đời cũ chưa dọn. Site thật đã chạy purge rồi.

### `lotus_farm/public/js/material_requirement.js`: xóa

Chạy `git rm lotus_farm/public/js/material_requirement.js`. `main` đã xóa DocType mà tệp này phục vụ. Spec 003 chỉ đổi hai chữ ("đề nghị" thành "đề xuất"), không có gì cần giữ.

### `lotus_farm/finance/payments.py`: viết lại

Trong `make_service_invoice`, lấy thân hàm của spec 003 (lớp bọc của `supplier_invoice.create`). Riêng dòng đầu docstring bỏ `lotus_crop_cycle`, vì `main` đã bỏ chiều "Vụ" và `test_no_legacy_names` không cho phép tên này:

```python
    """lines: [{description, amount, cost: 'production' | 'admin', lotus_farm, lotus_farm_block, lotus_work_type}].
    Lớp bọc của finance.supplier_invoice.create: hộ kinh doanh cộng thuế vào chính khoản chi phí, không ghi 1331."""
    from lotus_farm.finance import supplier_invoice
    result = supplier_invoice.create(supplier=supplier, service_lines=_json(lines), bill_no=bill_no, bill_date=bill_date, due_date=due_date,
                                     posting_date=posting_date, vat_code=vat_code)
    return dict(invoice=result['invoice'], amount=result['amount'])
```

Bỏ thân hàm cũ của `main` và hai hàm `_receipt_vat_in_cost`, `_service_vat_in_cost`. Không còn ai gọi hai hàm này.

### `lotus_farm/warehouse_issue.py`: lấy mã của `main`, giữ chữ của spec 003

Trong `approved(name, company)`:

```python
    if doc.material_request_type != 'Material Issue':
        frappe.throw('Chỉ dùng yêu cầu cấp vật tư, không dùng đề xuất mua hoặc chuyển kho.')
    if doc.get('status') in ('Stopped', 'Closed', 'Cancelled'):
```

Không giữ `if doctype == …` của bên spec 003. Biến `doctype` không còn tồn tại, nên sẽ báo NameError mỗi lần cấp vật tư.

### `lotus_farm/www/lotus_material_proposal_print.py`: viết lại hai đoạn

- **Đoạn 1**, trong `build(name)`, sau hai kiểm tra Guest và tên rỗng:

  ```python
      # People named in the signing round see what they sign even without rights on proposals (spec 003, FR-027).
      from lotus_farm.signed_copy import as_reader
      return as_reader(frappe.get_doc('Material Request', name), lambda: _build(name))


  def _build(name):
      doc = frappe.get_doc('Material Request', name)
      doc.check_permission('read')
      doc.check_permission('print')
      if doc.material_request_type not in ('Purchase', 'Material Issue'):
          frappe.throw('Chỉ in phiếu đề xuất mua hoặc cấp vật tư.', frappe.PermissionError)
      purchase = doc.material_request_type == 'Purchase'
      when = getdate(doc.get('transaction_date') or doc.creation)
      reason = strip_html(doc.get('lotus_request_note') or doc.get('remarks') or '').strip()
      warehouse = ', '.join(sorted({r.warehouse for r in doc.items if r.warehouse}))
      rows, total, priced = _request_rows(doc)
      state = 'Đã duyệt' if doc.docstatus == 1 else (doc.get('lotus_proposal_state') or pk.status_label(doc.docstatus))
  ```

  Các dòng sau (từ `proposer = _user_name(doc.owner)` đến `return p`) thành thân của `_build`.

- **Đoạn 2**, sau `@frappe.whitelist()`:

  ```python
  def download_pdf(name):
      if frappe.db.exists('Material Request', name):
          # Once signed in full, the download is the stored signed copy (spec 003, FR-014), not a new render.
          from lotus_farm import signed_copy, signing
          doc = frappe.get_doc('Material Request', name)
          copy = signed_copy.current(doc)
          if copy and signing.can_view(doc=doc):
              return signed_copy.respond(copy, 'de-xuat-mua-' + name)
      p = build(name)
  ```

  Dòng `pk.send_pdf(...)` sau đó giữ nguyên.

### `lotus_farm/www/lotus_stock_print.py`: giữ cả hai bên

`download_pdf` sau khi gộp:

```python
@frappe.whitelist()
def download_pdf(doctype, name):
    if doctype == 'Material Request':
        from lotus_farm.www.lotus_material_proposal_print import download_pdf as proposal_pdf
        return proposal_pdf(name)
    if doctype in ('Stock Entry', 'Stock Reconciliation', 'Purchase Receipt') and frappe.db.exists(doctype, name):
        from lotus_farm import signed_copy, signing
        doc = frappe.get_doc(doctype, name)
        copy = signed_copy.current(doc)
        if copy and signing.can_view(doc=doc):
            return signed_copy.respond(copy, name)
    pk.send_pdf(pk.render('stock.html', build(doctype, name)), name)
```

### `frontend/src/App.vue`: lấy mẫu giao diện của `main`, thêm một chỗ

- Lấy 9 dòng mẫu giao diện của `main`.
- Ở dòng `<p v-if="cached||session.offline" …>`, đổi `['cong-viec','mua-hang','kho']` thành `['cong-viec','mua-hang','kho','cho-ky','tai-chinh']`. Thiếu dòng này thì bấm thông báo khi đã mở sẵn trang "Chờ tôi ký" không mở được tấm ký.
- Phần script đã tự gộp, có dòng `cho-ky` của spec 003.
- Bỏ chữ "đề xuất mua phần thiếu" của spec 003: `main` đã xóa cả bảng đó.

### `frontend/src/domain.js`: lấy của `main`, thêm "Chờ tôi ký" ở hai chỗ

```js
export const pages=[['nguoi-dung','Người dùng & phân quyền'],['tai-chinh','Tài chính – Kế toán'],['nhan-su','Hồ sơ nhân sự'],['cham-cong','Chấm công'],['kho','Quản lý kho'],['cong-viec','Công việc ngoài vườn'],['farms','Vườn & lô'],['forecast','Dự thu'],['mau-day','Danh mục màu dây'],['map','Bản đồ chăm sóc'],['reports','Tổng quan'],['admin/masters','Danh mục']]
pages.push(['cho-ky','Chờ tôi ký'],['mua-hang','Mua hàng'])
export const titles=Object.fromEntries(pages)
// Sidebar grouping of `pages`: [path, LotusIcon name, optional shorter sidebar label]. Every page belongs to exactly one group.
export const navGroups=[
 {label:'Tổng quan',icon:'chart',items:[['reports','chart','Tổng quan'],['cho-ky','edit','Chờ tôi ký']]},
```

Phần còn lại của tệp là của `main`. `pages` và `navGroups` phải cùng có `cho-ky`. Nếu không:
- `workspace-sidebar.mount.test.js` hỏng;
- `/lotus/cho-ky` đưa người dùng tới trang "không có quyền".

### `frontend/src/labels.js`: lấy của `main`, thêm một nhãn

Lấy ba dòng của `main`. Trong `documentNames`, thay `'Lotus Signing Challenge':'Phiên QR ký chứng từ'` bằng `'Lotus Signed Copy':'Bản PDF đã ký'`.

### `frontend/src/api.js`: giữ hàm báo lỗi tải tệp của spec 003, bỏ tham số `expectedUser`

`upload(file,doctype,name)` mang thân hàm của spec 003 (`uploadFailure`) nhưng không có nhánh `expectedUser` / `lotus_farm.field.save_uploaded_photo`, vì `main` đã xóa hàng đợi ngoại tuyến. Giữ nguyên khối `FILE_ERRORS`, `SESSION_ERRORS`, `uploadFailure` của spec 003, và câu báo mất mạng mới của `main` ở dòng 13.

### `frontend/src/components/finance/FinanceGuide.vue`: lấy của `main`, đổi chữ

Lấy bản của `main`, đổi hai chỗ "Mua ngoài" thành "Mua nhanh":
- dòng Mua hàng trong `ROLES`;
- dòng Kho trong `DAILY`.

Bỏ dòng "Kho / xưởng — chuối thu hoạch". `main` đã bỏ Lô thu hoạch, và thay bằng "Ca đóng gói đã đóng, chưa nhập kho".

### `frontend/src/release-notes.js`: giữ cả hai mục, đổi ngày mục spec 003

Giữ cả hai mục: mục spec 003 ở trên cùng, mục '2026-11-11' của `main` ở dưới. Đổi id của mục spec 003 thành ngày thực sự đưa lên, ví dụ `'2026-11-12'` hoặc `'2026-11-11b'`, và id đó phải lớn hơn '2026-11-11'. Đổi cả ngày trong tiêu đề.

Lý do: ai đã đóng thông báo ngày 11/11 sẽ không thấy mục nào có id nhỏ hơn. Mục '2026-11-10b' hiện tại sẽ không hiện cho ai cả.

Khi gỡ dấu xung đột, nhớ đóng mục spec 003 bằng ` ]},`. Nếu không, mục của `main` sẽ lồng vào trong, gây lỗi cú pháp.

## Ngoài xung đột: ba sửa tìm ra khi chạy mã đã gộp trên VPS

1. **`frontend/src/App.vue`: đường link thẳng mở sai màn hình (lỗi của `main`, đang có trên site thật b71a0b5).**
   - Khi mở thẳng một đường link trong tab mới (`/lotus/kho`, `/lotus/mua-hang`, `/lotus/cho-ky?sign_dt=…`, link trong thông báo hay email), ứng dụng đọc trang trước khi bộ định tuyến xử lý xong địa chỉ. Nó thấy "/" và chuyển sang trang đầu của menu: Chấm công, Tài chính, …
   - Spec 003 trước đây không gặp vì `await refreshOutbox()` vô tình làm chậm. `main` đã bỏ hàng đợi ngoại tuyến cùng dòng đó.
   - Sửa: thêm `await router.isReady();` đầu khối `onMounted`.
   - Đã kiểm: trước khi sửa, cả ba đường link đều sang trang đầu menu với giám đốc, mua hàng và thủ kho. Sau khi sửa thì mở đúng.
2. **`tests/integration/verify_kho_e2e.py`:** kiểm tra của `main` còn chờ chữ "Mua ngoài". Đổi thành "Mua nhanh", theo quyết định 10/11.
3. **`tests/integration/verify_warehouse_audit.py`:** test ghi sổ thẳng một đơn mua. Spec 003 không còn duyệt theo chính sách, nên đơn phải ở "Chờ duyệt" trước khi xác nhận. Lỗi này có cả trên nhánh 003 trước khi gộp, vì test này chưa nằm trong bộ chạy của spec 003.

## Đã kiểm bản gộp trên VPS (11/11/2026)

Gộp thật trên một bản clone tạm, không commit gì vào kho mã và không đổi nhánh nào. Đẩy cây đã gộp lên chỗ thử `lotus-003-proc`. Migrate hai site thử: patch dọn bảng cũ của `main` chạy và lưu trữ như ở site thật. Build giao diện từ mã gộp. Kết quả:

| Bộ | Kết quả |
|---|---|
| `verify_procurement` / `verify_procurement_complete` / `verify_purchase_flow` / concurrency | 51/51 · 62/62 · 23/23 · 4/4 |
| `verify_vat_in_cost`, `verify_signing`, `verify_purchase_proposal`, `verify_sign_notify` (bản sao site thật) | qua (24/24 với bộ thuế) |
| Test đơn vị Python (gồm `test_no_legacy_names`, `test_frontend_calls` của `main`) | 292/292 |
| Test giao diện | 586/586 |
| Bộ của `main` trên bản sao site thật: `verify_warehouse_audit`, `verify_kho_e2e`, `verify_costing`, `verify_master_guards`, `verify_field_reports` | qua (Kho 61/61), sau hai sửa test ở mục trên |
| Kịch bản trình duyệt uat-1, 3, 4, 5 | 16/16, 11/11, 7/7, 11/11 |

Lần chạy kịch bản đầu tiên trên bản gộp tìm ra lỗi đường link thẳng (sửa 1 ở mục trên). Ở lần chạy lại, bước "đổi ảnh chữ ký" của uat-1 lỗi một lần do lỗi thoáng qua. Chạy lại uat-1 qua 16/16; mã chữ ký giống hệt bản trước khi gộp.

## Kiểm sau khi gộp

**Tại chỗ** (chỉ `git`, không chạy test trên máy này):
- `git diff --check`, và tìm `^(<<<<<<<|=======|>>>>>>>)`: không còn dấu xung đột.
- `git grep -nE "expectedUser|save_uploaded_photo|daily_api|stock_bridge|validate_request_lineage|Material Requirement|lotus_crop_cycle" -- lotus_farm frontend/src`: chỉ còn trong tài liệu và patch.
- `git diff main -- frontend/src/App.vue`: chỉ có dòng `cho-ky` và danh sách `navigation-key`.

**Trên VPS** (chỗ thử riêng):
- `tests/test_no_legacy_names.py` và `tests/test_frontend_calls.py` (sau khi build và commit bản build mới);
- `verify_procurement.py`, `verify_procurement_complete.py`, `verify_purchase_flow.py`, `verify_procurement_concurrency.py`;
- trên bản sao site thật: `verify_vat_in_cost.py`, `verify_signing.py`, `verify_purchase_proposal.py`, `verify_sign_notify.py`;
- toàn bộ test giao diện.

**Bằng tay trên site thử:**
- `/lotus/cho-ky` mở được;
- bấm link ký khi trang đã mở sẵn thì mở đúng tấm ký;
- in đề xuất, in phiếu nhận và in đơn mua đều mở được bản PDF đã ký;
- tải tệp hỏng thì báo "Không đọc được tệp…".

**Cuối cùng:** build giao diện trên VPS, commit `lotus_farm/public/frontend` (`.vite/manifest.json` và `assets`), rồi mới đưa lên.
