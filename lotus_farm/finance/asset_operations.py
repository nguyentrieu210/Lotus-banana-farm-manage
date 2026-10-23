"""Lifecycle adapters. All financial writes use standard ERPNext documents, in one approval transaction."""
import frappe
from frappe.utils import cint, flt, get_last_day, getdate, now_datetime, nowdate

from lotus_farm.finance import asset_rules as ar, assets as a, setup


def _category(name):
    doc = frappe.get_doc('Asset Category', name)
    accounts = next((r for r in doc.accounts if r.company_name == setup.company()), None)
    if not accounts:
        frappe.throw('Nhóm tài sản chưa cấu hình tài khoản cho công ty.')
    for field, root in [('fixed_asset_account', 'Asset'), ('accumulated_depreciation_account', 'Asset'),
                        ('depreciation_expense_account', 'Expense'), ('capital_work_in_progress_account', 'Asset')]:
        a._account(accounts.get(field), root)
    return doc, accounts


def _invoice_ref(values):
    for field, dt in [('purchase_invoice', 'Purchase Invoice'), ('purchase_receipt', 'Purchase Receipt')]:
        if values.get(field):
            doc = frappe.get_doc(dt, values[field])
            if doc.company != setup.company() or doc.docstatus != 1 or doc.get('is_return'):
                frappe.throw('Chứng từ mua phải được ghi sổ, đúng công ty và không phải hàng trả lại.')
            if doc.currency != 'VND':
                frappe.throw('Chứng từ tài sản trong đợt này phải dùng VND.')
            return field, doc
    return None, None


def _profile_check(v, existing_asset=None):
    v = dict(v, non_depreciable=bool(frappe.db.get_value('Asset Category', v.get('asset_category'), 'non_depreciable_category')))
    clean, errors = ar.profile(v)
    if errors:
        frappe.throw('<br>'.join(errors.values()))
    clean.update(a._dimensions(clean))
    _category(clean['asset_category'])
    if not frappe.db.exists('Location', clean['location']):
        frappe.throw('Vị trí tài sản không tồn tại.')
    for field, value in [('lotus_asset_code', clean['code']), ('lotus_serial_no', clean.get('serial_no'))]:
        if value and frappe.db.exists('Asset', {field: value, 'name': ['!=', existing_asset or '']}):
            frappe.throw('Mã tài sản hoặc serial đã được sử dụng.')
    if clean.get('custodian') and frappe.db.get_value('Employee', clean['custodian'], 'company') != setup.company():
        frappe.throw('Người quản lý tài sản không thuộc công ty.')
    if clean.get('existing'):
        cutover = setup.settings().cutover_date
        if cutover and getdate(clean['available_for_use_date']) >= getdate(cutover):
            frappe.throw('Tài sản đầu kỳ phải đã đưa vào sử dụng trước ngày bắt đầu ghi sổ.')
    else:
        field, source = _invoice_ref(clean)
        if source:
            matching = [r for r in source.items if r.item_code == clean.get('item_code') and
                        (not clean.get('purchase_row') or r.name == clean['purchase_row'])]
            if len(matching) != 1 or flt(matching[0].qty) != 1:
                frappe.throw('Chọn đúng một dòng mua tài sản, số lượng 1, để giữ liên kết nguyên giá.')
            if not frappe.db.get_value('Item', matching[0].item_code, 'is_fixed_asset'):
                frappe.throw('Dòng chứng từ mua chưa được đánh dấu tài sản cố định.')
            if ar.money(matching[0].base_net_amount) != clean['amount']:
                frappe.throw('Nguyên giá phải khớp giá trị dòng mua chưa thuế được khấu trừ.')
            if frappe.db.exists('Asset', {field: source.name, field+'_item': matching[0].name, 'docstatus': ['<', 2], 'name': ['!=', existing_asset or '']}):
                frappe.throw('Dòng mua này đã có hồ sơ tài sản. Không tạo thêm hồ sơ trùng.')
            clean['purchase_row'] = matching[0].name
            if field == 'purchase_invoice' and not source.update_stock:
                receipt = matching[0].purchase_receipt
                receipt_row = matching[0].pr_detail
                if not receipt or not receipt_row:
                    frappe.throw('Hóa đơn tài sản cần cập nhật tài sản trực tiếp hoặc liên kết phiếu nhận hàng đã duyệt.')
                if frappe.db.get_value('Purchase Receipt', receipt, ['company', 'docstatus']) != (setup.company(), 1):
                    frappe.throw('Phiếu nhận tài sản chưa duyệt hoặc không thuộc công ty.')
                clean['linked_receipt'], clean['linked_receipt_row'] = receipt, receipt_row
    return clean


def _documents_hash(doc, asset):
    versions = dict(operation=doc.modified, payload=doc.payload, state=doc.state,
                    asset=asset.as_dict() if asset else None)
    v = a._json(doc.payload, {})
    for field, dt in [('purchase_invoice', 'Purchase Invoice'), ('purchase_receipt', 'Purchase Receipt')]:
        if v.get(field):
            versions[field] = frappe.get_doc(dt, v[field]).as_dict()
    category = v.get('asset_category') or (asset.asset_category if asset else None)
    if category:
        versions['category'] = frappe.get_doc('Asset Category', category).as_dict()
    if asset:
        versions['schedules'] = [frappe.get_doc('Asset Depreciation Schedule', name).as_dict() for name in frappe.get_all(
            'Asset Depreciation Schedule', filters={'asset': asset.name, 'docstatus': 1}, pluck='name')]
        allocations, allocation_doc = a.allocation_for(asset.name, str(doc.posting_date)[:7])
        versions['allocation'] = allocations
        versions['allocation_version'] = allocation_doc.modified if allocation_doc else None
    versions['settings'] = setup.settings().modified
    versions['company'] = frappe.db.get_value('Company', setup.company(), 'modified')
    return versions


def preview(name):
    op = frappe.get_doc(a.OP, name, for_update=True)
    if op.company != setup.company():
        frappe.throw('Nghiệp vụ không thuộc công ty.', frappe.PermissionError)
    asset = a.asset_doc(op.asset) if op.asset else None
    v = a._json(op.payload, {})
    errors, warnings = [], []
    summary = dict(kind=op.kind, date=str(op.posting_date), asset=op.asset, values=v)
    if op.state != 'Pending':
        return dict(name=op.name, kind=op.kind, state=op.state, asset=op.asset, posting_date=str(op.posting_date),
                    summary=v.get('_preview', summary), errors=[], warnings=[], documents=a._json(op.documents, []), fingerprint=op.preview_hash)
    try:
        a.check_period(op.posting_date)
        if op.state != 'Pending':
            frappe.throw('Nghiệp vụ đã được xử lý.')
        if op.kind in ('Create', 'Profile'):
            v = _profile_check(v, op.asset)
            summary['values'] = v
            if op.kind == 'Profile' and asset:
                latest = frappe.db.sql("""select max(j.posting_date) from `tabJournal Entry` j join `tabJournal Entry Account` r on r.parent=j.name
                    where j.docstatus=1 and j.voucher_type='Depreciation Entry' and r.reference_type='Asset' and r.reference_name=%s""", asset.name)[0][0]
                if latest and getdate(op.posting_date) < getdate(latest):
                    frappe.throw('Không đổi hồ sơ ngược trước kỳ khấu hao đã ghi. Đảo kỳ liên quan trước.')
            if v.get('existing'):
                warnings.append('Hồ sơ đầu kỳ không ghi thêm bút toán; phải đối chiếu với số dư đầu kỳ trước khi duyệt khấu hao.')
        elif not asset or asset.docstatus != 1:
            frappe.throw('Tài sản phải được duyệt trước khi thực hiện nghiệp vụ.')
        if asset and op.kind not in ('Restore', 'Profile') and asset.status in ('Sold', 'Scrapped'):
            frappe.throw('Tài sản đã bán/thanh lý. Phục hồi đúng chứng từ trước.')
        if asset and getdate(op.posting_date) < getdate(asset.available_for_use_date or asset.purchase_date):
            frappe.throw('Ngày nghiệp vụ không được trước ngày đưa tài sản vào sử dụng.')
        if op.kind == 'Move':
            if not v.get('location') or not frappe.db.exists('Location', v['location']):
                frappe.throw('Chọn vị trí nhận tài sản.')
            a._dimensions(v)
            if v.get('custodian') and frappe.db.get_value('Employee', v['custodian'], 'company') != setup.company():
                frappe.throw('Người nhận tài sản không thuộc công ty.')
            warnings.append('Điều chuyển vị trí không tự thay tỷ lệ phân bổ tháng. Kiểm tra phân bổ khi duyệt khấu hao.')
        if op.kind in ('Repair', 'Upgrade'):
            if ar.money(v.get('amount')) <= 0:
                frappe.throw('Chi phí sửa chữa/nâng cấp phải lớn hơn 0.')
            a._account(v.get('expense_account'), 'Expense')
            if not (v.get('purchase_invoice') or v.get('supplier')):
                frappe.throw('Chọn hóa đơn sửa chữa đã duyệt hoặc nhà cung cấp để lập hóa đơn.')
            if cint(v.get('increase_months')) < 0:
                frappe.throw('Số tháng tăng thêm không được âm.')
            if v.get('purchase_invoice'):
                _invoice_ref(v)
                from erpnext.assets.doctype.asset_repair.asset_repair import get_unallocated_repair_cost
                if flt(get_unallocated_repair_cost(v['purchase_invoice'], v['expense_account'])) < ar.money(v['amount']):
                    frappe.throw('Chi phí vượt phần hóa đơn sửa chữa chưa phân bổ.')
            if op.kind == 'Upgrade' and asset.status == 'Fully Depreciated':
                frappe.throw('ERPNext không vốn hóa sửa chữa trên tài sản đã khấu hao hết. Lập hồ sơ ghi tăng cho phần đầu tư mới.')
        if (op.kind == 'Create' and not v.get('existing') or op.kind in ('Repair', 'Upgrade')) and not v.get('purchase_invoice') and not v.get('purchase_receipt'):
            from lotus_farm.finance import rules
            rate = rules.vat_rate(v.get('vat_code') or 'KCT', str(op.posting_date))
            if rate:
                a._account(v.get('input_vat_account'), 'Asset')
            summary['vat'] = flt(ar.money(v.get('amount')) * rate, 2)
        if op.kind in ('Suspend', 'Resume') and not str(op.reason or '').strip():
            frappe.throw('Ghi lý do thay đổi tình trạng sử dụng.')
        if op.kind == 'Suspend':
            warnings.append('Tạm ngừng sử dụng vẫn giữ lịch khấu hao hiện có.')
        if op.kind in ('Sell', 'Scrap'):
            if getdate(op.posting_date) > getdate(nowdate()):
                frappe.throw('Chỉ xử lý giảm tài sản đến ngày hiện tại.')
            future = frappe.db.sql("""select j.name from `tabJournal Entry` j join `tabJournal Entry Account` r on r.parent=j.name
                where j.docstatus=1 and j.voucher_type='Depreciation Entry' and r.reference_type='Asset'
                and r.reference_name=%s and j.posting_date>%s limit 1""", (asset.name, op.posting_date))
            if future:
                frappe.throw('Có khấu hao sau ngày giảm tài sản. Đảo các kỳ sau trước.')
            from erpnext.assets.doctype.asset.depreciation import get_value_after_depreciation_on_disposal_date
            value = flt(get_value_after_depreciation_on_disposal_date(asset.name, str(op.posting_date))) if asset.calculate_depreciation else flt(asset.net_purchase_amount)
            summary.update(remaining=value, original=flt(asset.total_asset_cost or asset.net_purchase_amount),
                           depreciation_to_date=max(0, flt(asset.value_after_depreciation)-value), proceeds=ar.money(v.get('amount')),
                           gain_loss=ar.money(v.get('amount'))-value)
            if op.kind == 'Sell':
                if summary['proceeds'] <= 0 or not frappe.db.exists('Customer', v.get('customer')):
                    frappe.throw('Chọn khách hàng và nhập giá bán chưa thuế lớn hơn 0.')
                a._account(v.get('income_account'), 'Income')
                from lotus_farm.finance.sales import vat_options
                rates = {r['code']: r for r in vat_options(str(op.posting_date))['rates']}
                if v.get('vat_code', 'KCT') not in rates:
                    frappe.throw('Thuế suất không hợp lệ tại ngày bán.')
                summary['vat'] = flt(summary['proceeds'] * flt(rates[v.get('vat_code', 'KCT')]['rate']), 2)
            if not str(op.reason or '').strip():
                frappe.throw('Ghi lý do bán/thanh lý tài sản.')
        if op.kind == 'Restore' and (not asset or asset.status != 'Scrapped'):
            frappe.throw('Phục hồi áp dụng cho tài sản đã thanh lý. Bán tài sản phải hủy hóa đơn liên quan qua nghiệp vụ gốc.')
    except (frappe.ValidationError, ValueError) as exc:
        errors.append(str(exc))
    result = dict(name=op.name, kind=op.kind, state=op.state, asset=op.asset, posting_date=str(op.posting_date),
                  summary=summary, errors=errors, warnings=warnings, documents=a._json(op.documents, []))
    result['fingerprint'] = ar.fingerprint(dict(result=result, versions=_documents_hash(op, asset)))
    return result


def _item(v, service=False):
    if v.get('item_code') and not service:
        item = frappe.get_doc('Item', v['item_code'])
        if not item.is_fixed_asset or item.is_stock_item or item.asset_category != v['asset_category']:
            frappe.throw('Mặt hàng phải là tài sản cố định, không quản lý tồn kho và đúng nhóm tài sản.')
        return item
    code = ('LOTUS-ASSET-SERVICE' if service else 'TS-' + v['code'])
    if frappe.db.exists('Item', code):
        item = frappe.get_doc('Item', code)
        if bool(item.is_fixed_asset) == (not service) and not item.is_stock_item:
            return item
        frappe.throw('Mã mặt hàng đã dùng cho mục đích khác: '+code)
    groups = frappe.get_all('Item Group', filters={'is_group': 0}, pluck='name', limit_page_length=1)
    if not groups:
        group = frappe.get_doc(dict(doctype='Item Group', item_group_name='Tài sản Lotus', parent_item_group='All Item Groups', is_group=0))
        group.flags.ignore_permissions = True
        group.insert()
        groups = [group.name]
    item = frappe.get_doc(dict(doctype='Item', item_code=code, item_name='Dịch vụ tài sản Lotus' if service else v['asset_name'],
                              item_group=groups[0], stock_uom='Nos', is_stock_item=0, is_fixed_asset=0 if service else 1,
                              auto_create_assets=0, asset_category=None if service else v['asset_category']))
    item.flags.ignore_permissions = True
    item.insert()
    return item


def _purchase(v, on_date, item, expense_account, dimensions):
    # Existing submitted invoices remain external references and must never be cancelled with this operation.
    doc = frappe.get_doc(dict(doctype='Purchase Invoice', supplier=v['supplier'], company=setup.company(), posting_date=on_date, set_posting_time=1, currency='VND', conversion_rate=1,
                             bill_no=v.get('bill_no'), bill_date=v.get('bill_date') or on_date, update_stock=int(bool(item.is_fixed_asset)),
                             due_date=on_date, items=[dict(item_code=item.name, qty=1, rate=v['amount'], expense_account=expense_account,
                             cost_center=frappe.get_cached_value('Company', setup.company(), 'cost_center'), **dimensions)]))
    doc.flags.ignore_permissions = True
    doc.set_missing_values()
    doc.calculate_taxes_and_totals()
    # The VAT rule is shared with supplier invoices; asset input VAT may be chosen explicitly.
    code = v.get('vat_code') or 'KCT'
    if code != 'KCT':
        from lotus_farm.finance import sales
        rate = next((r for r in sales.vat_options(on_date)['rates'] if r['code'] == code), None)
        if not rate:
            frappe.throw('Thuế suất không hợp lệ.')
        account = a._account(v.get('input_vat_account'), 'Asset')
        doc.append('taxes', dict(charge_type='On Net Total', account_head=account, rate=flt(rate['rate'])*100,
                                 description='Thuế GTGT tài sản', cost_center=doc.items[0].cost_center))
        doc.calculate_taxes_and_totals()
    doc.lotus_vat_code = code
    doc.insert()
    doc.submit()
    return doc


def _create(op, v, documents):
    v = _profile_check(v)
    category, accounts = _category(v['asset_category'])
    item = _item(v)
    field, purchase = _invoice_ref(v)
    if not v.get('existing') and not purchase:
        purchase = _purchase(v, op.posting_date, item, accounts.capital_work_in_progress_account, a._dimensions(v))
        documents.append(dict(doctype=purchase.doctype, name=purchase.name))
        field = 'purchase_invoice'
        v['purchase_row'] = purchase.items[0].name
    doc = frappe.new_doc('Asset')
    doc.update(dict(company=setup.company(), item_code=item.name, asset_name=v['asset_name'], asset_category=v['asset_category'],
                    location=v['location'], custodian=v.get('custodian'), department=v.get('department'),
                    purchase_date=v['purchase_date'], available_for_use_date=v['available_for_use_date'], asset_quantity=1,
                    net_purchase_amount=v['amount'], gross_purchase_amount=v['amount'],
                    opening_accumulated_depreciation=v['opening_depreciation'], opening_number_of_booked_depreciations=v['booked_months'],
                    is_fully_depreciated=int(v['amount']-v['opening_depreciation'] <= v['salvage_value']),
                    calculate_depreciation=int(not category.non_depreciable_category and v['amount']-v['opening_depreciation'] > v['salvage_value']),
                    lotus_asset_code=v['code'], lotus_serial_no=v.get('serial_no') or None, lotus_managed_asset=1,
                    cost_center=v.get('cost_center') or frappe.get_cached_value('Company', setup.company(), 'cost_center'), **a._dimensions(v)))
    if doc.meta.has_field('asset_type'):
        doc.asset_type = 'Existing Asset' if v.get('existing') else None
    else:
        doc.is_existing_asset = cint(v.get('existing'))
    if purchase:
        doc.set(field, purchase.name)
        doc.set(field+'_item', v['purchase_row'])
        if v.get('linked_receipt'):
            doc.purchase_receipt = v['linked_receipt']
            doc.purchase_receipt_item = v['linked_receipt_row']
    if doc.calculate_depreciation:
        start = v.get('depreciation_start_date') or str(get_last_day(setup.settings().cutover_date if v.get('existing') else v['available_for_use_date']))
        doc.append('finance_books', dict(depreciation_method=v['method'], frequency_of_depreciation=1,
                                        total_number_of_depreciations=v['months'], depreciation_start_date=start,
                                        expected_value_after_useful_life=v['salvage_value'], daily_prorata_based=1))
    doc.flags.ignore_permissions = True
    doc.insert()
    doc.submit()
    op.asset = doc.name
    documents.append(dict(doctype='Asset', name=doc.name))
    return doc


def _repair(op, doc, v, documents):
    expense = a._account(v['expense_account'], 'Expense')
    if v.get('purchase_invoice'):
        _, invoice = _invoice_ref(v)
    else:
        item = _item(v, service=True)
        invoice = _purchase(v, op.posting_date, item, expense, {k: doc.get(k) for k in ar.DIMENSIONS})
        documents.append(dict(doctype=invoice.doctype, name=invoice.name))
    repair = frappe.get_doc(dict(doctype='Asset Repair', company=doc.company, asset=doc.name,
                                 failure_date=v.get('failure_date') or str(op.posting_date)+' 00:00:00',
                                 completion_date=str(op.posting_date)+' 00:00:00', repair_status='Completed',
                                 description=op.reason or 'Sửa chữa/nâng cấp từ Lotus', actions_performed=v.get('description'),
                                 capitalize_repair_cost=int(op.kind == 'Upgrade'), increase_in_asset_life=cint(v.get('increase_months')),
                                 cost_center=doc.cost_center, invoices=[dict(purchase_invoice=invoice.name, expense_account=expense, repair_cost=v['amount'])],
                                 **{k: doc.get(k) for k in ar.DIMENSIONS}))
    repair.flags.ignore_permissions = True
    repair.insert()
    repair.submit()
    documents.append(dict(doctype=repair.doctype, name=repair.name))


def _sell(op, doc, v, documents):
    from erpnext.assets.doctype.asset.asset import make_sales_invoice
    invoice = make_sales_invoice(doc.name, doc.item_code, doc.company, 1)
    invoice.customer = v['customer']
    invoice.currency = 'VND'
    invoice.conversion_rate = 1
    invoice.set_posting_time = 1
    invoice.posting_date = op.posting_date
    invoice.due_date = v.get('due_date') or op.posting_date
    invoice.update_stock = 0
    invoice.lotus_vat_code = v.get('vat_code') or 'KCT'
    invoice.lotus_einvoice_no = v.get('einvoice_no')
    invoice.lotus_einvoice_series = v.get('einvoice_series')
    invoice.items[0].rate = v['amount']
    invoice.items[0].income_account = v['income_account']
    invoice.flags.ignore_permissions = True
    invoice.set_missing_values()
    code = v.get('vat_code') or 'KCT'
    if code != 'KCT':
        from lotus_farm.finance import sales
        rate = next(r for r in sales.vat_options(str(op.posting_date))['rates'] if r['code'] == code)
        invoice.set('taxes', [dict(charge_type='On Net Total', account_head=setup.mapping()['output_vat'],
                                  rate=flt(rate['rate'])*100, description='Thuế GTGT bán tài sản', cost_center=doc.cost_center)])
    invoice.calculate_taxes_and_totals()
    invoice.insert()
    invoice.submit()
    documents.append(dict(doctype='Sales Invoice', name=invoice.name))
    # Native disposal posts net gain/loss. Split the sale proceeds and carrying expense for Lotus reports.
    disposal = frappe.get_cached_value('Company', doc.company, 'disposal_account')
    a._account(disposal, 'Expense')
    center = doc.cost_center or frappe.get_cached_value('Company', doc.company, 'cost_center')
    dims = {k: doc.get(k) for k in ar.DIMENSIONS}
    reclass = a._journal(op.posting_date, [dict(account=disposal, debit_in_account_currency=v['amount'], cost_center=center, **dims),
                                          dict(account=v['income_account'], credit_in_account_currency=v['amount'], cost_center=center, **dims)],
                         'Tách thu nhập và giá trị còn lại bán tài sản '+doc.name, operation=op.name)
    documents.append(dict(doctype='Journal Entry', name=reclass.name))


def _profile(op, doc, v):
    v = _profile_check(v, doc.name)
    # Financial changes apply through the native asset controller; it retains booked schedule rows.
    for field, key in [('asset_name','asset_name'), ('location','location'), ('custodian','custodian'),
                       ('department','department'), ('lotus_asset_code','code'), ('lotus_serial_no','serial_no')]:
        if field in ('location', 'custodian') and (v.get(key) or None) != (doc.get(field) or None):
            frappe.throw('Đổi vị trí/người quản lý bằng nghiệp vụ Điều chuyển để giữ lịch sử bàn giao.')
        doc.set(field, v.get(key) or None)
    if ar.money(v['amount']) != ar.money(doc.net_purchase_amount) or v['asset_category'] != doc.asset_category:
        frappe.throw('Nguyên giá và nhóm đã duyệt không được sửa trực tiếp; dùng nghiệp vụ nâng cấp/điều chỉnh phù hợp.')
    for field in ('purchase_date', 'available_for_use_date'):
        if str(getdate(v[field])) != str(getdate(doc.get(field))):
            frappe.throw('Ngày gốc đã duyệt không được sửa trực tiếp.')
    if any((doc.get(k) or None) != (v.get(k) or None) for k in ar.DIMENSIONS):
        frappe.throw('Đổi vườn/lô bằng nghiệp vụ điều chuyển; phân bổ chi phí sửa ở bảng phân bổ tháng.')
    policy_changed = False
    if doc.calculate_depreciation:
        for book in doc.finance_books:
            policy_changed = policy_changed or (book.depreciation_method != v['method'] or
                cint(book.total_number_of_depreciations) != v['months'] or ar.money(book.expected_value_after_useful_life) != v['salvage_value'])
            book.depreciation_method = v['method']
            book.total_number_of_depreciations = v['months']
            book.expected_value_after_useful_life = v['salvage_value']
            if policy_changed:
                book.rate_of_depreciation = 0
    doc.flags.ignore_permissions = True
    doc.flags.ignore_validate_update_after_submit = True
    doc.save()
    if policy_changed:
        from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import reschedule_depreciation
        reschedule_depreciation(doc, 'Đổi chính sách được duyệt trong Lotus: '+op.name)


def _settle_additional_cost(op, doc, documents):
    # This ERPNext version disposes net_purchase_amount and derives accumulated depreciation from it,
    # although Asset Repair capitalizes into total_asset_cost. Clear that balance in a linked JE.
    native = next((r for r in documents if r['doctype'] == 'Sales Invoice' or r.get('native_scrap')), None)
    if not native:
        frappe.throw('Thiếu chứng từ ghi giảm gốc để đối chiếu giá trị vốn hóa.')
    _, accounts = _category(doc.asset_category)
    disposed_cost = flt(frappe.db.sql("""select sum(credit-debit) from `tabGL Entry`
        where voucher_type=%s and voucher_no=%s and account=%s and is_cancelled=0""",
        (native['doctype'], native['name'], accounts.fixed_asset_account))[0][0])
    additional = ar.money(doc.total_asset_cost) - ar.money(disposed_cost)
    if not additional:
        return
    center = doc.cost_center or frappe.get_cached_value('Company', doc.company, 'cost_center')
    dims = {k: doc.get(k) for k in ar.DIMENSIONS}
    journal = a._journal(op.posting_date, [
        dict(account=accounts.accumulated_depreciation_account, debit_in_account_currency=additional, cost_center=center, **dims),
        dict(account=accounts.fixed_asset_account, credit_in_account_currency=additional, cost_center=center, **dims)],
        'Ghi giảm giá trị vốn hóa bổ sung khi giảm tài sản '+doc.name, operation=op.name)
    documents.append(dict(doctype='Journal Entry', name=journal.name))


def apply(name, fingerprint):
    op = frappe.get_doc(a.OP, name, for_update=True)
    if op.state != 'Pending':
        frappe.throw('Nghiệp vụ đã được xử lý.')
    if op.asset:
        a._lock('Asset', op.asset)
    result = preview(name)
    if result['errors']:
        frappe.throw('<br>'.join(result['errors']))
    if result['fingerprint'] != fingerprint:
        frappe.throw('Nghiệp vụ hoặc dữ liệu nguồn đã thay đổi. Xem trước lại trước khi duyệt.')
    v = result['summary']['values']
    documents = []
    doc = a.asset_doc(op.asset) if op.asset else None
    previous = doc.as_dict() if doc else None
    if op.kind == 'Create':
        doc = _create(op, v, documents)
    elif op.kind == 'Profile':
        _profile(op, doc, v)
    elif op.kind == 'Move':
        movement = frappe.get_doc(dict(doctype='Asset Movement', company=doc.company, purpose='Transfer',
                                       transaction_date=str(op.posting_date)+' 00:00:00', assets=[dict(asset=doc.name,
                                       source_location=doc.location, target_location=v['location'], from_employee=doc.custodian,
                                       to_employee=v.get('custodian'))]))
        movement.flags.ignore_permissions = True
        movement.insert()
        movement.submit()
        documents.append(dict(doctype=movement.doctype, name=movement.name))
        frappe.db.set_value('Asset', doc.name, a._dimensions(v))
    elif op.kind in ('Repair', 'Upgrade'):
        _repair(op, doc, v, documents)
    elif op.kind in ('Suspend', 'Resume'):
        doc.db_set(dict(lotus_usage_suspended=int(op.kind == 'Suspend'), lotus_usage_reason=op.reason))
        doc.add_comment('Info', ('Tạm ngừng' if op.kind == 'Suspend' else 'Sử dụng lại')+'; giữ lịch khấu hao: '+op.reason)
    elif op.kind == 'Sell':
        _sell(op, doc, v, documents)
    elif op.kind == 'Scrap':
        from erpnext.assets.doctype.asset.depreciation import scrap_asset
        scrap_asset(doc.name, str(op.posting_date))
        doc.reload()
        documents.append(dict(doctype='Journal Entry', name=doc.journal_entry_for_scrap, native_scrap=True))
    elif op.kind == 'Restore':
        from erpnext.assets.doctype.asset.depreciation import restore_asset
        restore_asset(doc.name)
    # Disposal may create a prorated final depreciation. Allocate each native entry exactly once.
    if op.kind in ('Sell', 'Scrap'):
        _settle_additional_cost(op, doc, documents)
        allocation, _ = a.allocation_for(doc.name, str(op.posting_date)[:7])
        for name in frappe.get_all('Journal Entry', filters={'lotus_asset_operation': op.name, 'voucher_type': 'Depreciation Entry', 'docstatus': 1}, pluck='name'):
            journal = frappe.get_doc('Journal Entry', name)
            reclass = a.allocate_journal(journal, allocation, operation=op.name)
            documents.insert(0, dict(doctype='Journal Entry', name=name, depreciation=True))
            if reclass:
                documents.append(dict(doctype='Journal Entry', name=reclass.name))
    stored = a._json(op.payload, {})
    stored['_previous'] = previous
    stored['_preview'] = result['summary']
    op.update(dict(state='Posted', asset=doc.name, payload=a._dump(stored), documents=a._dump(documents), preview_hash=fingerprint,
                   approved_by=frappe.session.user, approved_at=now_datetime(), active_key=op.name))
    op.flags.ignore_permissions = True
    op.save()
    return dict(name=op.name, asset=doc.name, documents=documents)


def cancel(name, reason):
    op = frappe.get_doc(a.OP, name, for_update=True)
    if op.company != setup.company():
        frappe.throw('Nghiệp vụ không thuộc công ty.', frappe.PermissionError)
    if op.state == 'Cancelled':
        frappe.throw('Nghiệp vụ đã hủy.')
    if len(str(reason or '').strip()) < 5:
        frappe.throw('Ghi rõ lý do hủy (ít nhất 5 ký tự).')
    if op.state == 'Posted':
        setup.require_chief()
        a.check_period(op.posting_date)
        a._lock('Asset', op.asset)
        later = frappe.db.exists(a.OP, {'asset': op.asset, 'state': 'Posted', 'approved_at': ['>', op.approved_at]})
        if later:
            frappe.throw('Hủy các nghiệp vụ tài sản đã duyệt sau trước.')
        for run in frappe.get_all(a.RUN, filters={'company': op.company, 'state': 'Posted', 'approved_at': ['>', op.approved_at]}, fields=['results']):
            if any(r.get('asset') == op.asset for r in a._json(run.results, [])):
                frappe.throw('Đảo các bảng khấu hao đã duyệt sau nghiệp vụ này trước.')
        if op.kind == 'Create':
            booked = frappe.db.sql("""select j.name from `tabJournal Entry` j join `tabJournal Entry Account` r on r.parent=j.name
                where j.docstatus=1 and j.voucher_type='Depreciation Entry' and r.reference_type='Asset'
                and r.reference_name=%s limit 1""", op.asset)
            if booked:
                frappe.throw('Đảo các bảng khấu hao của tài sản trước khi hủy ghi tăng.')
        if op.kind == 'Restore':
            frappe.throw('Phục hồi đã duyệt được xử lý bằng nghiệp vụ thanh lý mới, giữ lịch sử phục hồi.')
        documents = a._json(op.documents, [])
        if op.kind == 'Scrap':
            # Reclassifications must be removed before the native restore cancels the scrap/final depreciation.
            for row in reversed(documents):
                if not row.get('native_scrap') and not row.get('depreciation'):
                    a._cancel_voucher(row['doctype'], row['name'])
            from erpnext.assets.doctype.asset.depreciation import restore_asset
            restore_asset(op.asset)
        else:
            for row in reversed(documents):
                if op.kind == 'Sell' and row.get('depreciation'):
                    # Sales Invoice.restore_asset creates the native reversal and resets the schedule.
                    continue
                current = frappe.get_doc(row['doctype'], row['name'])
                if current.docstatus == 1:
                    a._cancel_voucher(row['doctype'], row['name'])
        previous = a._json(op.payload, {}).get('_previous')
        if previous and op.kind in ('Suspend', 'Resume', 'Move', 'Profile'):
            doc = a.asset_doc(op.asset)
            changes = {k: previous.get(k) for k in ('lotus_usage_suspended', 'lotus_usage_reason', *ar.DIMENSIONS)}
            if op.kind == 'Profile':
                changes.update({k: previous.get(k) for k in ('asset_name','custodian','department','lotus_asset_code','lotus_serial_no')})
            doc.db_set(changes)
            if op.kind == 'Profile' and doc.calculate_depreciation:
                doc.reload()
                doc.set('finance_books', previous['finance_books'])
                doc.flags.ignore_permissions = True
                doc.flags.ignore_validate_update_after_submit = True
                doc.save()
                from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import reschedule_depreciation
                reschedule_depreciation(doc, 'Đảo thay đổi chính sách tài sản: '+op.name)
    op.update(dict(state='Cancelled', active_key=None, reason=reason))
    op.flags.ignore_permissions = True
    op.save()
    op.add_comment('Info', 'Hủy nghiệp vụ: '+reason)
    return dict(name=name, state='Cancelled')
