"""Private Excel preview and atomic draft-only import. Images remain manual evidence."""
from io import BytesIO
import json
from zipfile import ZipFile, BadZipFile
import re
import unicodedata
import frappe
from frappe.utils import flt, getdate, nowdate
from lotus_farm.procurement import access, parse, line_fields
from lotus_farm import procurement_rules as rules
from lotus_farm.controls import lock

DT = 'Lotus Purchase Import'
# Names the farm writes in its workbook → item / supplier chosen for them once. Kept as a global default
# (no schema): {"item": {label: item_code}, "supplier": {label: supplier}} with case-folded labels.
ALIAS_KEY = 'lotus_procurement_aliases'


def text(value):
    return unicodedata.normalize('NFC', str(value or '')).strip()


def header_key(value):
    return re.sub(r'\s+', ' ', re.sub(r'\s*\([^)]*\)', '', text(value))).strip().casefold()


def load_aliases():
    try:
        data = json.loads(frappe.db.get_default(ALIAS_KEY) or '{}')
    except ValueError:
        data = {}
    return dict(item=dict(data.get('item') or {}), supplier=dict(data.get('supplier') or {}))


def remember_aliases(items=None, suppliers=None):
    """items / suppliers: {label: code}. Later imports match these labels without manual mapping."""
    data = load_aliases()
    data['item'].update({text(k).casefold(): v for k, v in (items or {}).items() if text(k) and v})
    data['supplier'].update({text(k).casefold(): v for k, v in (suppliers or {}).items() if text(k) and v})
    frappe.db.set_default(ALIAS_KEY, json.dumps(data, ensure_ascii=False, sort_keys=True))


def _file(file_url):
    f = frappe.get_doc('File', {'file_url': file_url, 'is_private': 1})
    f.check_permission('read')
    if f.owner != frappe.session.user and frappe.session.user != 'Administrator':
        frappe.throw('Chỉ nhập file gốc do tài khoản này tải lên.', frappe.PermissionError)
    content = f.get_content()
    if len(content) > 10*1024*1024:
        frappe.throw('File Excel tối đa 10 MB.')
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(r.file_size for r in archive.infolist()) > 80*1024*1024:
                frappe.throw('Nội dung giải nén Excel quá lớn.')
    except BadZipFile:
        frappe.throw('Chọn file .xlsx hợp lệ.')
    return f, content


def workbook_rows(content):
    """Recognize the farm's four-sheet workbook as well as the download template."""
    from openpyxl import load_workbook
    book = load_workbook(BytesIO(content), read_only=True, data_only=True)
    output = []
    for sheet in book.worksheets:
        if sheet.max_row > 10000 or sheet.max_column > 80:
            raise ValueError('Sheet vượt giới hạn 10.000 dòng / 80 cột.')
        rows = list(sheet.iter_rows(values_only=True))
        is_header=lambda row:any(header_key(c) in ('item','mã hàng','tên thương mại','sản phẩm ncc') for c in row)
        header = next((i for i, row in enumerate(rows[:12]) if is_header(row)), None)
        if header is None:
            # Supplier quote sheets may have grouped headings: keep every original cell visible;
            # the user supplies explicit row mappings before commit.
            for i, row in enumerate(rows):
                if any(c is not None for c in row):
                    output.append(dict(key=f'{sheet.title}:{i+1}', sheet=sheet.title, row=i+1, type='Quotation',
                        source=[text(c) for c in row], item_label='', qty=None, rate=None, uom='', month='', supplier=''))
            continue
        headers = {header_key(v): i for i, v in enumerate(rows[header]) if text(v)}
        template = 'item' in headers or 'mã hàng' in headers
        supplier_quote = 'sản phẩm ncc' in headers
        title = ' '.join(text(c) for row in rows[:header] for c in row if c)
        month_match = re.search(r'(?:tháng|thang)\s*(\d{1,2})(?:\s*/\s*(\d{4}))?', title, re.I)
        month = f'{month_match[2] or getdate(nowdate()).year}-{int(month_match[1]):02}' if month_match else ''
        def at(row, *keys):
            index = next((headers[k] for k in keys if k in headers), None)
            return row[index] if index is not None and index < len(row) else None
        context = title
        for i, row in enumerate(rows[header+1:], start=header+2):
            if is_header(row):
                headers = {header_key(v): n for n,v in enumerate(row) if text(v)}
                continue
            if not template and not supplier_quote and header_key(row[0]) in ('stt','số thứ tự'):
                break  # Subsequent farm/block calculation table is not a purchase need.
            if not template and not isinstance(row[0],(float,int)) and not text(row[0]).isdigit():
                if text(row[0]):
                    context=text(row[0])
                continue
            label = text(at(row, 'item', 'mã hàng', 'tên thương mại', 'sản phẩm ncc'))
            if label in ('','-'):
                label=text(at(row,'tên phân bón','tên thuốc','tên vật tư'))
            if not label or label.casefold() in ('tổng', 'tổng cộng'):
                continue
            qty=at(row, 'qty', 'số lượng','sl tính','sl cần mua')
            pack=at(row,'quy cách')
            if not template and not supplier_quote and isinstance(qty,(int,float)) and isinstance(pack,(int,float)):
                qty*=pack  # farm workbook quotes price per kg/litre, demand is in packs
            price_basis='Gross' if supplier_quote and re.search(r'(đã gồm|đã bao gồm).*vat',context,re.I) else 'Net'
            output.append(dict(key=f'{sheet.title}:{i}', sheet=sheet.title, row=i, source=[text(c) for c in row],
                type=text(at(row, 'type', 'loại')) or ('Quotation' if supplier_quote else 'Need'), item_label=label,
                qty=qty, price_basis=price_basis,
                rate=at(row, 'rate', 'đơn giá', 'giá tốt nhất'), uom=text(at(row, 'uom', 'đvt')),
                supplier=text(at(row, 'supplier', 'nhà cung cấp', 'ncc giá tốt nhất')),
                month=text(at(row, 'month', 'tháng')) or month, template=template,
                source_note='Giá nguồn đã gồm VAT; chọn VAT để quy về giá chưa thuế.' if price_basis=='Gross' else ''))
    book.close()
    return output


def _preview(company, file_url, mappings=None):
    access(company)
    f, content = _file(file_url)
    mappings = parse(mappings) or {}
    try:
        raw = workbook_rows(content)
    except ValueError as exc:
        frappe.throw(str(exc))
    items = frappe.get_list('Item', filters={'disabled': 0}, fields=['name', 'item_name', 'stock_uom', 'is_stock_item', 'is_fixed_asset', 'modified'], limit_page_length=0)
    suppliers = frappe.get_list('Supplier', filters={'disabled': 0}, fields=['name', 'supplier_name', 'modified'], limit_page_length=0)
    item_names = {text(v).casefold(): r.name for r in items for v in (r.name, r.item_name)}
    supplier_names = {text(v).casefold(): r.name for r in suppliers for v in (r.name, r.supplier_name)}
    aliases = load_aliases()
    for label, code in aliases['item'].items():
        if code in {r.name for r in items}:
            item_names.setdefault(label, code)
    for label, code in aliases['supplier'].items():
        if code in {r.name for r in suppliers}:
            supplier_names.setdefault(label, code)
    masters, result = {}, []
    for row in raw:
        edit = mappings.get(row['key'], {})
        if edit.get('skip'):
            continue
        value = {**row, **{k: edit[k] for k in ('item', 'qty', 'rate', 'uom', 'month', 'supplier', 'warehouse', 'kind', 'type', 'date', 'vat_code', 'freight') if k in edit}}
        value['item'] = value.get('item') or item_names.get(text(value['item_label']).casefold(), '')
        value['supplier_label'] = text(row.get('supplier'))
        value['supplier'] = supplier_names.get(text(value.get('supplier')).casefold(), value.get('supplier') or '')
        errors = []
        if value.get('price_basis')=='Gross' and 'vat_code' not in edit:
            errors.append('Xác nhận VAT của giá đã gồm thuế trong báo giá gốc.')
        if value['type'] not in ('Need', 'Quotation'):
            errors.append('Chọn Need hoặc Quotation.')
        elif not frappe.has_permission('Material Request' if value['type']=='Need' else 'Supplier Quotation','create'):
            errors.append('Chưa có quyền tạo loại chứng từ của dòng này.')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', str(value.get('month') or '')):
            errors.append('Xác nhận tháng YYYY-MM của dòng gốc.')
        try:
            item = frappe.get_doc('Item', value['item'])
            item.check_permission('read')
            if item.disabled:
                raise ValueError('Mặt hàng ngừng sử dụng.')
            value['uom'] = value.get('uom') or item.stock_uom
            factor = 1 if value['uom'] == item.stock_uom else next((flt(u.conversion_factor) for u in item.uoms if u.uom == value['uom']), 0)
            if factor <= 0:
                raise ValueError('ĐVT chưa có quy đổi trong Item.')
            value['factor'] = factor
            value['qty'] = float(rules.number(value.get('qty'), 'Số lượng', True))
            value['rate'] = float(rules.number(value.get('rate'), 'Đơn giá')) if value.get('rate') not in ('', None) else None
            value['source_rate']=value['rate']
            if value.get('price_basis')=='Gross' and value['rate'] is not None and edit.get('vat_code') in ('0','5','8','10'):
                value['rate']/=1+float(edit['vat_code'])/100
            value.update(line_fields(item, value))
            masters[item.name] = [str(item.modified), [[u.uom, u.conversion_factor] for u in item.uoms]]
            from lotus_farm.warehouse import _warehouse
            if not value.get('warehouse'):
                errors.append('Chưa chọn kho nhận.')
            else:
                _warehouse(value.get('warehouse'), company)
        except (frappe.DoesNotExistError, ValueError) as exc:
            errors.append(str(exc) if isinstance(exc, ValueError) else 'Chưa ánh xạ mặt hàng/kho.')
        if value['type'] == 'Quotation' and value.get('supplier') not in {r.name for r in suppliers}:
            errors.append('Chưa ánh xạ nhà cung cấp.')
        if value.get('date'):
            try:
                if str(getdate(value['date']))[:7] != value.get('month'):
                    errors.append('Ngày cần hàng khác tháng gốc; kiểm tra lại.')
            except (ValueError, TypeError):
                errors.append('Ngày không hợp lệ.')
        value['errors'] = errors
        result.append(value)
    fingerprint = rules.digest([company, rules.digest(content.hex()), mappings, masters,
        [[r.name, str(r.modified)] for r in suppliers], result])
    previous = frappe.get_list(DT, filters={'company': company, 'file_hash': rules.digest(content.hex())}, fields=['name'], limit_page_length=0)
    return dict(rows=result, fingerprint=fingerprint, valid=bool(result) and not any(r['errors'] for r in result),
                previous=[r.name for r in previous], file=f.name, file_hash=rules.digest(content.hex()))


@frappe.whitelist(methods=['POST'])
def preview(company, file_url, mappings=None):
    return _preview(company, file_url, mappings)


@frappe.whitelist(methods=['POST'])
def commit(company, file_url, mappings, fingerprint, client_key, duplicate_reason=None):
    access(company)
    lock('Company', company)
    token = rules.digest([frappe.session.user, client_key])
    old = frappe.db.get_value(DT, {'client_key': token}, ['name', 'fingerprint', 'documents_json'], as_dict=True, for_update=True)
    if old:
        from lotus_farm.procurement import document
        document(DT,old.name,company,for_update=True)
        if old.fingerprint != fingerprint:
            frappe.throw('Mã nhập đã dùng với nội dung khác.')
        return dict(name=old.name, documents=frappe.parse_json(old.documents_json))
    if not client_key:
        frappe.throw('Thiếu mã yêu cầu nhập.')
    data = _preview(company, file_url, mappings)
    if not data['valid'] or data['fingerprint'] != fingerprint:
        frappe.throw('Dữ liệu hoặc danh mục đã đổi. Xem trước và sửa lỗi trước khi nhập.')
    if data['previous'] and not str(duplicate_reason or '').strip():
        frappe.throw('File gốc đã nhập. Kiểm tra bản nhập trước; ghi lý do nếu cần tạo các nháp khác.')
    groups = {}
    for row in data['rows']:
        groups.setdefault((row['type'], row['month'], row.get('supplier') if row['type'] == 'Quotation' else ''), []).append(row)
    documents = []
    for (kind, month, supplier), rows in groups.items():
        dt = 'Material Request' if kind == 'Need' else 'Supplier Quotation'
        d = frappe.new_doc(dt)
        d.company, d.transaction_date = company, min(getdate(nowdate()),getdate(month+'-01'))
        if kind == 'Need':
            d.material_request_type = 'Purchase'
        else:
            d.supplier = supplier
        for row in rows:
            day = row.get('date') or month+'-01'
            item = frappe.get_doc('Item', row['item'])
            d.append('items', dict(item_code=item.name, qty=row['qty'], rate=row['rate'] or 0, uom=row['uom'],
                stock_uom=item.stock_uom, conversion_factor=row['factor'], warehouse=row['warehouse'], schedule_date=day,
                **{k: row[k] for k in ('lotus_purchase_kind', 'lotus_line_vat', 'lotus_line_freight', 'lotus_quote_reason')}))
        d.schedule_date = rows[0].get('date') or month+'-01'
        if kind == 'Quotation':
            d.lotus_delivery_date = d.schedule_date
            from lotus_farm.procurement import apply_line_taxes
            apply_line_taxes(d)
        d.insert()  # Never submit an imported request or quotation.
        documents.append(dict(doctype=dt, name=d.name, month=month, docstatus=d.docstatus))
    batch = frappe.get_doc(dict(doctype=DT, company=company, original_file=file_url, file_hash=data['file_hash'],
        fingerprint=fingerprint, client_key=token, duplicate_reason=duplicate_reason, documents_json=frappe.as_json(documents)))
    batch.flags.procurement_write = True
    batch.insert()
    frappe.db.set_value('File', data['file'], dict(attached_to_doctype=DT, attached_to_name=batch.name))
    # Remember how this workbook's names were matched, so next month's file needs no manual mapping.
    remember_aliases({r['item_label']: r['item'] for r in data['rows'] if r.get('item_label') and r.get('item')},
                     {r['supplier_label']: r['supplier'] for r in data['rows'] if r.get('supplier_label') and r.get('supplier')})
    return dict(name=batch.name, documents=documents)


@frappe.whitelist()
def template():
    from lotus_farm.purchasing import access
    access()
    from openpyxl import Workbook
    book = Workbook()
    book.active.append(['type', 'item', 'qty', 'uom', 'rate', 'supplier', 'month'])
    book.active.append(['Need', '', '', '', '', '', nowdate()[:7]])
    out = BytesIO()
    book.save(out)
    frappe.local.response.update(filename='mau-nhap-mua-hang.xlsx', filecontent=out.getvalue(), type='download')
