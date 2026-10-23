"""Tài chính – Kế toán: who may do what, the settings, the accounting dimensions, and applying the TT133
chart of accounts (preview first; the chief accountant applies it, it never runs on migrate).
"""
import json
from pathlib import Path

import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

from lotus_farm.finance import rules

SETTINGS = 'Lotus Finance Settings'
COA_DIR = Path(__file__).resolve().parents[1] / 'data'
ACCOUNTANT = 'Lotus Accountant'
CHIEF = 'Lotus Chief Accountant'
ACCOUNTANTS = (ACCOUNTANT, CHIEF, 'Accounts User', 'Accounts Manager', 'System Manager')
CHIEFS = (CHIEF, 'Accounts Manager', 'System Manager')
VIEWERS = ACCOUNTANTS + ('Lotus Auditor',)
# ERPNext documents the accounting roles open from Lotus (read in Desk; Lotus writes through its own API).
READ_DOCTYPES = ('Account', 'GL Entry', 'Journal Entry', 'Purchase Invoice', 'Payment Entry', 'Accounting Period',
                 'Supplier', 'Purchase Receipt', 'Stock Entry', 'Cost Center', 'Accounting Dimension',
                 # masters ERPNext reads while building an invoice or payment for the current user
                 'Item', 'Item Group', 'UOM', 'Warehouse', 'Company', 'Supplier Group', 'Currency', 'Price List',
                 'Mode of Payment', 'Fiscal Year', 'Payment Term', 'Payment Terms Template', 'Bank Account',
                 'Customer', 'Customer Group', 'Territory', 'Sales Order', 'Delivery Note', 'Sales Invoice',
                 'Sales Taxes and Charges Template', 'Purchase Taxes and Charges Template', 'Item Tax Template', 'Employee')
# The vouchers accountants make (Lotus checks its own rules first; ERPNext's mapper checks these permissions).
WRITE_DOCTYPES = ('Journal Entry', 'Purchase Invoice', 'Payment Entry', 'Sales Invoice', 'Delivery Note', 'Customer')
# Journal Entry kinds made by Lotus: signed payment vouchers (Salary, Advance, Statutory) and month-end entries (Closing, Result).
JE_KINDS = ('Salary', 'Closing', 'Advance', 'Statutory', 'Result', 'PurchaseFunding', 'PurchaseReimbursement')
SIGNED_JE_KINDS = ('Salary', 'Advance', 'Statutory', 'PurchaseFunding', 'PurchaseReimbursement')
VAT_OPTIONS = '\nKCT\n0\n5\n8\n10'


def _has(roles):
    return frappe.session.user == 'Administrator' or bool(set(roles) & set(frappe.get_roles()))


def can_view():
    return _has(VIEWERS)


def can_post():
    return _has(ACCOUNTANTS)


def is_chief():
    return _has(CHIEFS)


def _login():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)


def require_view():
    _login()
    if not can_view():
        frappe.throw('Bạn chưa có quyền xem sổ kế toán.', frappe.PermissionError)


def require_post():
    _login()
    if not can_post():
        frappe.throw('Chỉ Kế toán, Kế toán trưởng hoặc Quản trị được ghi sổ.', frappe.PermissionError)


def require_chief():
    _login()
    if not is_chief():
        frappe.throw('Chỉ Kế toán trưởng hoặc Quản trị được làm thao tác này.', frappe.PermissionError)


def settings():
    return frappe.get_single(SETTINGS)


def company():
    return settings().company or frappe.defaults.get_global_default('company') or frappe.get_all('Company', pluck='name', limit_page_length=1)[0]


def mapping(doc=None):
    doc = doc or settings()
    return {key: doc.get('acct_' + key) for key in rules.KEYS}


def require_enabled():
    """Posting from Lotus works only when the chief accountant has switched it on and every account is valid."""
    doc = settings()
    if not doc.finance_enabled:
        frappe.throw('Ghi sổ kế toán từ Lotus đang tắt. Kế toán trưởng bật ở Tài chính – Kế toán › Thiết lập.')
    errors = mapping_errors(doc)
    if errors:
        frappe.throw('Cấu hình tài khoản chưa đủ:<br>' + '<br>'.join(errors))
    return doc


def check_cutover(on_date):
    """Documents dated before the cutover are already inside the opening balances; posting them would count twice."""
    cutover = settings().cutover_date
    if cutover and getdate(on_date) < getdate(cutover):
        frappe.throw('Chứng từ ngày %s trước ngày bắt đầu ghi sổ %s; số liệu trước ngày đó nằm trong số dư đầu kỳ.' % (
            getdate(on_date).strftime('%d/%m/%Y'), getdate(cutover).strftime('%d/%m/%Y')))


def _account_meta(names, company_name):
    rows = frappe.get_all('Account', filters={'name': ['in', [n for n in names if n] or ['']]},
                          fields=['name', 'company', 'root_type', 'account_type', 'is_group', 'disabled'])
    return {r.name: dict(r, company_ok=r.company == company_name) for r in rows}


def mapping_errors(doc=None):
    doc = doc or settings()
    m = mapping(doc)
    return rules.validate_mapping(m, _account_meta(m.values(), doc.company or company()))


def validate_settings(doc):
    """On save: only the chief accountant; switching on needs a cutover date and every account valid."""
    if not frappe.flags.in_install and not frappe.flags.in_migrate:
        require_chief()
    # While the chart is being switched, renames save this document midway; coa_apply validates at the end.
    if doc.finance_enabled and not frappe.flags.lotus_coa_apply:
        if not doc.company:
            frappe.throw('Chọn công ty trước khi bật ghi sổ.')
        if not doc.cutover_date:
            frappe.throw('Chọn ngày bắt đầu ghi sổ trước khi bật.')
        errors = mapping_errors(doc)
        if errors:
            frappe.throw('Chưa bật được vì:<br>' + '<br>'.join(errors))


def install():
    """Roles, read permissions and the four accounting dimensions (additive; finance stays switched off)."""
    from frappe.permissions import add_permission, update_permission_property
    for role in (ACCOUNTANT, CHIEF):
        if not frappe.db.exists('Role', role):
            frappe.get_doc(dict(doctype='Role', role_name=role, desk_access=1)).insert(ignore_permissions=True)
    for doctype in READ_DOCTYPES:
        if not frappe.db.exists('DocType', doctype):
            continue
        for role in (ACCOUNTANT, CHIEF):
            operations = ['read', 'report', 'print', 'export']
            if doctype in WRITE_DOCTYPES:
                operations += ['create', 'write'] + (['cancel'] if role == CHIEF else [])
                # Server checks every payment signature, even when using native ERPNext API.
                if role == CHIEF or doctype not in ('Payment Entry', 'Journal Entry'):
                    operations.append('submit')
            if not frappe.db.exists('Custom DocPerm', {'parent': doctype, 'role': role, 'permlevel': 0}):
                add_permission(doctype, role)
            current = frappe.db.get_value('Custom DocPerm', {'parent': doctype, 'role': role, 'permlevel': 0}, operations, as_dict=True) or {}
            for operation in operations:
                if not int(current.get(operation) or 0):
                    update_permission_property(doctype, role, 0, operation, 1)
            if role == ACCOUNTANT and doctype in ('Payment Entry', 'Journal Entry'):
                if frappe.db.get_value('Custom DocPerm', {'parent': doctype, 'role': role, 'permlevel': 0}, 'submit'):
                    update_permission_property(doctype, role, 0, 'submit', 0)
    # The director signs the last step of a payment voucher, which submits it: ERPNext/HRMS then read the paid
    # invoices and accounts as that person, so approvers may read (not change) what they approve.
    from lotus_farm.signing_rules import DIRECTORS
    for role in DIRECTORS:
        if not frappe.db.exists('Role', role):
            continue
        for doctype in ('Purchase Invoice', 'Payment Entry', 'Journal Entry', 'Account', 'Supplier', 'Company', 'Currency', 'Mode of Payment'):
            if not frappe.db.exists('Custom DocPerm', {'parent': doctype, 'role': role, 'permlevel': 0}):
                add_permission(doctype, role)
                update_permission_property(doctype, role, 0, 'read', 1)
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'Journal Entry': [dict(fieldname='lotus_payment_kind', label='Phiếu chi Lotus', fieldtype='Select', options='\n' + '\n'.join(JE_KINDS),
                               read_only=1, no_copy=1, insert_after='voucher_type'),
                          dict(fieldname='lotus_employee', label='Nhân viên (tạm ứng)', fieldtype='Link', options='Employee', read_only=1, no_copy=1,
                               insert_after='lotus_payment_kind'),
                          dict(fieldname='lotus_pay_month', label='Tháng lương', fieldtype='Data', read_only=1, no_copy=1,
                               insert_after='lotus_employee')],
        'Stock Entry': [
            dict(fieldname='lotus_receipt_reason', label='Lý do nhập kho', fieldtype='Select', options='\nPurchase\nRecovery\nSurplus\nHarvest',
                 insert_after='stock_entry_type', depends_on="eval:doc.stock_entry_type=='Material Receipt'"),
            dict(fieldname='lotus_supplier', label='Nhà cung cấp (nhập mua ngoài)', fieldtype='Link', options='Supplier', insert_after='lotus_receipt_reason',
                 depends_on="eval:doc.lotus_receipt_reason=='Purchase'"),
            dict(fieldname='lotus_purchase_invoice', label='Hóa đơn mua', fieldtype='Link', options='Purchase Invoice', read_only=1, no_copy=1,
                 insert_after='lotus_supplier'),
            dict(fieldname='lotus_harvest_lot', label='Lô thu hoạch nhập kho', fieldtype='Link', options='Harvest Lot', read_only=1, no_copy=1,
                 insert_after='lotus_purchase_invoice'),
            dict(fieldname='lotus_issue_purpose', label='Mục đích xuất kho', fieldtype='Select', options='\nProduction\nSale\nDisposal\nShortage\nPacking',
                 insert_after='lotus_purchase_invoice', depends_on="eval:doc.stock_entry_type=='Material Issue'"),
        ],
        'Purchase Invoice': [dict(fieldname='lotus_vat_code', label='Thuế suất GTGT', fieldtype='Select', options=VAT_OPTIONS, insert_after='bill_date')],
        'Sales Invoice': [
            dict(fieldname='lotus_vat_code', label='Thuế suất GTGT', fieldtype='Select', options=VAT_OPTIONS, insert_after='due_date'),
            dict(fieldname='lotus_einvoice_series', label='Ký hiệu hóa đơn điện tử', fieldtype='Data', insert_after='lotus_vat_code'),
            dict(fieldname='lotus_einvoice_no', label='Số hóa đơn điện tử', fieldtype='Data', insert_after='lotus_einvoice_series'),
        ],
        'Customer': [dict(fieldname='lotus_credit_days', label='Hạn thanh toán (ngày)', fieldtype='Int', insert_after='tax_id')],
    })
    install_dimensions()
    add_missing_accounts()
    fill_mapping()
    if settings().coa_version:
        fix_references(company())


def add_missing_accounts():
    """Accounts added to the chart in a later release (911) are created on a company that already applied it; nothing
    else of the chart is touched (re-applying would reset the mapping and the warehouse accounts)."""
    doc = settings()
    if not doc.coa_version:
        return []
    company_name = doc.company or company()
    coa = rules.load_coa()
    names, roots = _numbers(company_name), _roots(company_name)
    groups = {a['parent'] for a in coa['accounts'] if a.get('parent')}
    currency = frappe.get_cached_value('Company', company_name, 'default_currency')
    added = []
    for a in coa['accounts']:
        if a['number'] in names:
            continue
        parent = roots.get(a['root_type']) if a['parent'] is None else names.get(a['parent'])
        if not parent:
            continue
        acc = frappe.get_doc(dict(doctype='Account', account_name=a['name'], account_number=a['number'], parent_account=parent, company=company_name,
                                  is_group=1 if a['number'] in groups else 0, root_type=a['root_type'], account_type=a['account_type'] or None,
                                  account_currency=currency))
        acc.flags.ignore_permissions = True
        acc.insert()
        names[a['number']] = acc.name
        added.append(acc.name)
    return added


def fill_mapping():
    """Keys added in later releases get the chart's default account when the company already has it."""
    doc = settings()
    if not doc.coa_version:
        return
    coa = rules.load_coa()
    names = _numbers(doc.company or company())
    for key in rules.KEYS:
        number = coa['defaults'].get(key)
        if number and not doc.get('acct_' + key) and names.get(number):
            frappe.db.set_single_value(SETTINGS, 'acct_' + key, names[number])


def fix_references(company_name):
    """Defaults kept outside the company record (items, item groups, modes of payment, salary components) that still point at
    retired accounts move to the chart's accounts, or are cleared so the company defaults apply."""
    names = _numbers(company_name)
    retired = set(frappe.get_all('Account', filters={'company': company_name, 'disabled': 1}, pluck='name'))
    if not retired:
        return 0
    changed = 0
    by_field = {'expense_account': names.get('632'), 'income_account': names.get('511'), 'default_account': None}
    for doctype, field in (('Item Default', 'expense_account'), ('Item Default', 'income_account'), ('Mode of Payment Account', 'default_account'),
                           ('Salary Component Account', 'account')):
        if not frappe.db.exists('DocType', doctype) or not frappe.get_meta(doctype).has_field(field):
            continue
        for row in frappe.get_all(doctype, filters={field: ['in', list(retired)]}, fields=['name', 'parent', field]):
            value = by_field.get(field)
            if doctype == 'Mode of Payment Account':
                value = names.get('111') if 'cash' in (row.parent or '').lower() or 'tiền mặt' in (row.parent or '').lower() else names.get('112')
            frappe.db.set_value(doctype, row.name, field, value)
            changed += 1
    return changed


def install_dimensions():
    if not frappe.db.exists('DocType', 'Accounting Dimension'):
        return
    from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import make_dimension_in_accounting_doctypes
    for fieldname, doctype, label in rules.DIMENSIONS:
        if not frappe.db.exists('DocType', doctype):
            continue
        name = frappe.db.get_value('Accounting Dimension', {'document_type': doctype})
        if not name:
            doc = frappe.get_doc(dict(doctype='Accounting Dimension', document_type=doctype, label=label, fieldname=fieldname))
            doc.flags.ignore_permissions = True
            doc.insert()
        else:
            doc = frappe.get_doc('Accounting Dimension', name)
        # Create the columns now (on_update only queues the job) so stock and journal rows can carry them.
        if not frappe.get_meta('GL Entry').has_field(doc.fieldname):
            make_dimension_in_accounting_doctypes(doc=doc)


# Chart of accounts (Thông tư 99) -----------------------------------------------------------------------
# Applying the chart reconciles whatever the company has with lotus_farm/data/coa_tt99.json: missing accounts are
# added, accounts with the same number get the official name, parent and type, the company / warehouse / Lotus
# defaults move to the new accounts, balances on retired accounts are moved by one journal, and every account the
# chart does not have is deleted (or disabled when it has ledger history or is still referenced).

def _roots(company_name):
    roots = {}
    for r in frappe.get_all('Account', filters={'company': company_name, 'is_group': 1}, fields=['name', 'root_type', 'parent_account', 'lft'], order_by='lft'):
        if not r.parent_account and r.root_type not in roots:
            roots[r.root_type] = r.name
    return roots


def _accounts(company_name):
    return frappe.get_all('Account', filters={'company': company_name}, fields=['name', 'account_number', 'account_name', 'parent_account', 'is_group',
                                                                                'root_type', 'account_type', 'disabled', 'lft', 'rgt'], order_by='lft')


def _numbers(company_name):
    return {r.account_number: r.name for r in frappe.get_all('Account', filters={'company': company_name, 'account_number': ['is', 'set']},
                                                              fields=['name', 'account_number'])}


def _balances(company_name, on_date):
    rows = frappe.db.sql("""select account, sum(debit) - sum(credit) balance from `tabGL Entry`
        where company=%s and is_cancelled=0 and posting_date<=%s group by account having abs(sum(debit) - sum(credit)) > 0.5""", (company_name, on_date), as_dict=True)
    return {r.account: flt(r.balance) for r in rows}


def _with_history(company_name):
    return set(frappe.db.sql_list("select distinct account from `tabGL Entry` where company=%s", company_name))


def _docname(number, name, abbr):
    return '%s - %s - %s' % (number, name, abbr)


def coa_preview(on_date=None, warehouse_accounts=None):
    """What applying the chart would do: add, rename, retire (delete / disable), defaults, warehouses, balance moves."""
    company_name = company()
    coa = rules.load_coa()
    errors = rules.validate_coa(coa)
    abbr = frappe.get_cached_value('Company', company_name, 'abbr')
    roots = _roots(company_name)
    for root_type in {a['root_type'] for a in coa['accounts']}:
        if root_type not in roots:
            errors.append('Công ty chưa có tài khoản gốc loại %s' % root_type)
    target = {a['number']: a for a in coa['accounts']}
    groups = {a['parent'] for a in coa['accounts'] if a.get('parent')}
    current = _accounts(company_name)
    by_number = {a.account_number: a for a in current if a.account_number}
    history = _with_history(company_name)
    on_date = str(getdate(on_date or nowdate()))
    balances = _balances(company_name, on_date)
    add, update = [], []
    for number, a in target.items():
        is_group = 1 if number in groups else 0
        have = by_number.get(number)
        if not have:
            add.append(dict(a, is_group=is_group))
            continue
        if have.root_type != a['root_type']:
            errors.append('TK %s hiện là loại %s, danh mục mới là %s' % (number, have.root_type, a['root_type']))
        if is_group and not have.is_group and have.name in history:
            errors.append('TK %s đã có bút toán nên không chuyển thành tài khoản tổng hợp được' % number)
        if have.account_name != a['name'] or bool(have.is_group) != bool(is_group) or (have.account_type or '') != (a['account_type'] or '') \
                or have.disabled:
            update.append(dict(a, is_group=is_group, account=have.name, old_name=have.account_name, new_account=_docname(number, a['name'], abbr)))
    names = {n: _docname(n, a['name'], abbr) for n, a in target.items()}
    retire = []
    for acc in current:
        if not acc.parent_account or (acc.account_number and acc.account_number in target):
            continue
        keep = acc.name in history
        if keep and abs(balances.get(acc.name, 0)) > 0.5 and not acc.is_group:
            continue  # moved by the transfer journal below, then disabled
        retire.append(dict(account=acc.name, label=(acc.account_number + ' - ' if acc.account_number else '') + acc.account_name,
                           action='disable' if keep else 'delete', is_group=acc.is_group, lft=acc.lft))
    transfer = []
    for account, balance in sorted(balances.items()):
        acc = next((a for a in current if a.name == account), None)
        if not acc or (acc.account_number and acc.account_number in target):
            continue
        number = coa['transfer'].get(acc.account_name.replace(' (TK cũ)', '')) or (acc.account_number if acc.account_number in target else None)
        if not number:
            # a retired TT133 account keeps its number when TT99 has it; otherwise the Standard name map decides
            from_vi = {v + ' (TK cũ)': k for k, v in json.loads((COA_DIR / 'erpnext_standard_accounts_vi.json').read_text(encoding='utf-8'))['accounts'].items()}
            number = coa['transfer'].get(from_vi.get(acc.account_name, ''))
        if acc.account_type in ('Payable', 'Receivable'):
            errors.append('%s còn số dư công nợ theo đối tượng; chuyển bằng số dư đầu kỳ theo từng nhà cung cấp/khách hàng' % account)
        elif not number:
            errors.append('Chưa có tài khoản để chuyển số dư của %s (%s)' % (account, format(round(balance), ',').replace(',', '.')))
        else:
            transfer.append(dict(old=account, new=names[number], number=number, balance=round(balance)))
            retire.append(dict(account=account, label=acc.account_name, action='disable', is_group=0, lft=acc.lft))
    defaults = {k: names.get(v) for k, v in coa['defaults'].items()}
    warehouses = [dict(warehouse=w.name, current=w.account, account=(warehouse_accounts or {}).get(w.name) or defaults['inventory_material'])
                  for w in frappe.get_all('Warehouse', filters={'company': company_name, 'is_group': 0}, fields=['name', 'account'], order_by='name')]
    company_defaults = {f: names.get(n) for f, n in coa.get('company_defaults', {}).items() if frappe.get_meta('Company').has_field(f)}
    return dict(company=company_name, version=coa['version'], name=coa['name'], note=coa['note'], add=add, update=update,
                retire=sorted(retire, key=lambda r: -r['lft']), existing=len(by_number), defaults=defaults, company_defaults=company_defaults,
                warehouses=warehouses, transfer=transfer, errors=errors, on_date=on_date, applied=settings().coa_version)


def coa_apply(on_date=None, warehouse_accounts=None):
    """Apply the preview in one transaction. Order matters: new accounts first, then every default (company,
    warehouses, Lotus) moves to them, then balances move, then retired accounts go."""
    require_chief()
    preview = coa_preview(on_date, warehouse_accounts)
    if preview['errors']:
        frappe.throw('Chưa áp dụng được:<br>' + '<br>'.join(preview['errors']))
    frappe.flags.lotus_coa_apply = True
    company_name = preview['company']
    roots = _roots(company_name)
    names = _numbers(company_name)
    currency = frappe.get_cached_value('Company', company_name, 'default_currency')
    # Leaves that become groups (no history, checked in the preview) must be groups before children are added.
    for u in preview['update']:
        if u['is_group'] and not frappe.db.get_value('Account', u['account'], 'is_group'):
            frappe.db.set_value('Account', u['account'], 'is_group', 1)
    for a in preview['add']:
        parent = roots[a['root_type']] if a['parent'] is None else names[a['parent']]
        doc = frappe.get_doc(dict(doctype='Account', account_name=a['name'], account_number=a['number'], parent_account=parent, company=company_name,
                                  is_group=a['is_group'], root_type=a['root_type'], account_type=a['account_type'] or None, account_currency=currency))
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert()
        names[a['number']] = doc.name
    # Defaults first, on today's record names: renaming an account below carries every link to its new name.
    coa = rules.load_coa()
    current = lambda number: names.get(number)
    frappe.db.set_value('Company', company_name, {f: current(n) for f, n in coa.get('company_defaults', {}).items()
                                                  if frappe.get_meta('Company').has_field(f) and current(n)})
    for w in preview['warehouses']:
        number = next((n for n, a in names.items() if a == w['account']), None) or coa['defaults']['inventory_material']
        frappe.db.set_value('Warehouse', w['warehouse'], 'account', current(number))
    frappe.flags.pop('warehouse_account_map', None)
    for key in rules.KEYS:
        if coa['defaults'].get(key) and current(coa['defaults'][key]):
            frappe.db.set_single_value(SETTINGS, 'acct_' + key, current(coa['defaults'][key]))
    if not frappe.db.get_single_value(SETTINGS, 'company'):
        frappe.db.set_single_value(SETTINGS, 'company', company_name)
    renamed = {}
    for u in preview['update']:
        name = u['account']
        if u['old_name'] != u['name']:
            name = _rename_account(name, u['name'], u['number'], company_name)
            renamed[u['account']] = name
        names[u['number']] = name
        frappe.db.set_value('Account', name, dict(account_type=u['account_type'] or '', disabled=0))
    resolve = lambda acc: renamed.get(acc, acc) if acc else acc
    frappe.flags.pop('warehouse_account_map', None)
    doc = settings()
    # A retired stock account stops being typed Stock, otherwise ERPNext compares it with the value of every
    # warehouse and refuses the journal that moves its balance.
    for t in preview['transfer']:
        if frappe.db.get_value('Account', t['old'], 'account_type') == 'Stock':
            frappe.db.set_value('Account', t['old'], 'account_type', '')
    voucher = _transfer_journal(company_name, preview['on_date'], [dict(t, new=resolve(t['new'])) for t in preview['transfer']], preview['version']) \
        if preview['transfer'] else None
    deleted, disabled, kept = [], [], []
    for r in preview['retire']:
        if not frappe.db.exists('Account', r['account']):
            continue
        if r['action'] == 'delete' and not frappe.db.exists('Account', {'parent_account': r['account']}):
            frappe.db.savepoint('lotus_coa_delete')
            try:
                frappe.delete_doc('Account', r['account'], ignore_permissions=True, force=False)
                deleted.append(r['account'])
                continue
            except Exception as exc:
                # still referenced (mode of payment, item defaults…): undo the attempt and keep it disabled
                frappe.db.rollback(save_point='lotus_coa_delete')
                kept.append((r['account'], str(exc)[:200]))
        frappe.db.set_value('Account', r['account'], 'disabled', 1)
        disabled.append(r['account'])
    for u in preview['update']:
        name = names[u['number']]
        if not u['is_group'] and frappe.db.get_value('Account', name, 'is_group') and not frappe.db.exists('Account', {'parent_account': name, 'disabled': 0}):
            if not frappe.db.exists('Account', {'parent_account': name}):
                frappe.db.set_value('Account', name, 'is_group', 0)
    translate_old_accounts(company_name)
    fix_references(company_name)
    frappe.clear_cache()
    frappe.flags.lotus_coa_apply = False
    doc = settings()
    doc.coa_version = preview['version']
    doc.coa_applied_at = now_datetime()
    doc.coa_applied_by = frappe.session.user
    doc.flags.ignore_permissions = True
    doc.save()
    doc.add_comment('Info', 'Áp dụng %s; thêm %d, sửa %d, xóa %d, ngừng dùng %d tài khoản; chuyển số dư: %s' % (
        preview['version'], len(preview['add']), len(preview['update']), len(deleted), len(disabled), voucher or 'không có'))
    return dict(added=len(preview['add']), updated=len(preview['update']), deleted=len(deleted), disabled=len(disabled), transfer=voucher,
                kept=[k for k in kept][:20])


def translate_old_accounts(company_name=None):
    """Vietnamese display names for ERPNext's Standard chart (replaced by the Vietnamese chart). Only account_name changes (the
    record name and every voucher stay as they are); retired leaf accounts are marked (TK cũ). Safe to rerun."""
    company_name = company_name or company()
    names = json.loads((COA_DIR / 'erpnext_standard_accounts_vi.json').read_text(encoding='utf-8'))
    changed = 0
    for a in frappe.get_all('Account', filters={'company': company_name, 'account_number': ['in', ['', None]]}, fields=['name', 'account_name', 'is_group']):
        vi = names['groups'].get(a.account_name) if a.is_group else names['accounts'].get(a.account_name)
        if vi:
            frappe.db.set_value('Account', a.name, 'account_name', vi if a.is_group else vi + ' (TK cũ)', update_modified=False)
            changed += 1
    return changed


def _rename_account(name, account_name, number, company_name):
    """ERPNext's update_account_number refuses a rename within 5 minutes of a ledger change, and every rename touches
    the ledger rows of the account; switching a whole chart renames many accounts in one go, so rename directly."""
    from erpnext.accounts.doctype.account.account import get_account_autoname
    frappe.db.set_value('Account', name, dict(account_name=account_name, account_number=number))
    new = get_account_autoname(number, account_name, company_name)
    if new != name:
        frappe.rename_doc('Account', name, new, force=True, merge=False, show_alert=False)
    return new


def _transfer_journal(company_name, on_date, transfer, version):
    cost_center = frappe.get_cached_value('Company', company_name, 'cost_center')
    accounts = []
    for t in transfer:
        b = t['balance']
        accounts.append(dict(account=t['new'], debit_in_account_currency=max(b, 0), credit_in_account_currency=max(-b, 0), cost_center=cost_center))
        accounts.append(dict(account=t['old'], debit_in_account_currency=max(-b, 0), credit_in_account_currency=max(b, 0), cost_center=cost_center))
    je = frappe.get_doc(dict(doctype='Journal Entry', voucher_type='Journal Entry', company=company_name, posting_date=on_date,
                             user_remark='Chuyển số dư sang hệ thống tài khoản ' + version, accounts=accounts))
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    from lotus_farm.finance.posting import record
    record('Lotus Finance Settings', SETTINGS, 'Chart Transfer', je, amount=sum(abs(t['balance']) for t in transfer), source_hash=version, key_suffix=version)
    return je.name
