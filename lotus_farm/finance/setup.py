"""Tài chính – Kế toán: who may do what, the settings, the accounting dimensions, and applying the TT133
chart of accounts (preview first; the chief accountant applies it, it never runs on migrate).
"""
import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

from lotus_farm.finance import rules

SETTINGS = 'Lotus Finance Settings'
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
                 'Mode of Payment', 'Fiscal Year', 'Payment Term', 'Payment Terms Template', 'Bank Account')
# The vouchers accountants make (Lotus checks its own rules first; ERPNext's mapper checks these permissions).
WRITE_DOCTYPES = ('Journal Entry', 'Purchase Invoice', 'Payment Entry')


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
    if doc.finance_enabled:
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
                operations += ['create', 'write', 'submit'] + (['cancel'] if role == CHIEF else [])
            if not frappe.db.exists('Custom DocPerm', {'parent': doctype, 'role': role, 'permlevel': 0}):
                add_permission(doctype, role)
            current = frappe.db.get_value('Custom DocPerm', {'parent': doctype, 'role': role, 'permlevel': 0}, operations, as_dict=True) or {}
            for operation in operations:
                if not int(current.get(operation) or 0):
                    update_permission_property(doctype, role, 0, operation, 1)
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
    create_custom_fields({'Journal Entry': [dict(fieldname='lotus_payment_kind', label='Phiếu chi Lotus', fieldtype='Select', options='\nSalary',
                                                 read_only=1, no_copy=1, insert_after='voucher_type')]})
    install_dimensions()


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


# Chart of accounts (TT133) -----------------------------------------------------------------------------

def _roots(company_name):
    roots = {}
    for r in frappe.get_all('Account', filters={'company': company_name, 'is_group': 1}, fields=['name', 'root_type', 'parent_account', 'lft'], order_by='lft'):
        if not r.parent_account and r.root_type not in roots:
            roots[r.root_type] = r.name
    return roots


def _numbers(company_name):
    return {r.account_number: r.name for r in frappe.get_all('Account', filters={'company': company_name, 'account_number': ['is', 'set']},
                                                              fields=['name', 'account_number'])}


def _balances(company_name, on_date):
    rows = frappe.db.sql("""select account, sum(debit) - sum(credit) balance from `tabGL Entry`
        where company=%s and is_cancelled=0 and posting_date<=%s group by account having abs(sum(debit) - sum(credit)) > 0.5""", (company_name, on_date), as_dict=True)
    return {r.account: flt(r.balance) for r in rows}


def _plain_name(account):
    meta = frappe.db.get_value('Account', account, ['account_name', 'account_type', 'root_type'], as_dict=True) or {}
    return meta


def coa_preview(on_date=None, warehouse_accounts=None):
    """What applying TT133 would do: accounts to add, company defaults, warehouse accounts, balance transfer."""
    company_name = company()
    coa = rules.load_coa()
    errors = rules.validate_coa(coa)
    numbers = _numbers(company_name)
    plan = rules.coa_plan(coa, set(numbers))
    roots = _roots(company_name)
    for root_type in {a['root_type'] for a in coa['accounts']}:
        if root_type not in roots:
            errors.append('Công ty chưa có tài khoản gốc loại %s' % root_type)
    abbr = frappe.get_cached_value('Company', company_name, 'abbr')
    by_number = dict(numbers)
    for a in plan:
        by_number[a['number']] = '%s - %s - %s' % (a['number'], a['name'], abbr)
    defaults = {k: by_number.get(v) for k, v in coa['defaults'].items()}
    warehouses = []
    for w in frappe.get_all('Warehouse', filters={'company': company_name, 'is_group': 0}, fields=['name', 'account', 'warehouse_name'], order_by='name'):
        chosen = (warehouse_accounts or {}).get(w.name) or defaults['inventory_material']
        warehouses.append(dict(warehouse=w.name, current=w.account, account=chosen))
    on_date = str(getdate(on_date or nowdate()))
    transfer, missing = [], []
    stock_numbers = {coa['defaults']['inventory_material'], coa['defaults']['finished_goods'], coa['defaults'].get('goods'), coa['defaults'].get('inventory_tools')}
    for account, balance in sorted(_balances(company_name, on_date).items()):
        meta = _plain_name(account)
        number = frappe.db.get_value('Account', account, 'account_number')
        if number and number in {a['number'] for a in coa['accounts']}:
            continue
        target = coa['transfer'].get(meta.get('account_name'))
        if meta.get('account_type') in ('Payable', 'Receivable'):
            missing.append('%s có số dư công nợ theo đối tượng; chuyển bằng bút toán số dư đầu kỳ theo từng nhà cung cấp/khách hàng' % account)
            continue
        if not target:
            missing.append('Chưa có tài khoản TT133 để chuyển số dư của %s (%s)' % (account, format(round(balance), ',').replace(',', '.')))
            continue
        transfer.append(dict(old=account, new=by_number.get(target), number=target, balance=round(balance), stock=target in stock_numbers))
    return dict(company=company_name, version=coa['version'], name=coa['name'], note=coa['note'], add=plan, existing=len(numbers),
                defaults=defaults, warehouses=warehouses, transfer=transfer, errors=errors + missing, on_date=on_date,
                applied=settings().coa_version)


def coa_apply(on_date=None, warehouse_accounts=None):
    """Apply the preview in one transaction. Order matters: link the new stock accounts to the warehouses first,
    then move the old balances, so ERPNext accepts the journal on the stock account."""
    require_chief()
    preview = coa_preview(on_date, warehouse_accounts)
    if preview['errors']:
        frappe.throw('Chưa áp dụng được:<br>' + '<br>'.join(preview['errors']))
    company_name = preview['company']
    roots = _roots(company_name)
    names = _numbers(company_name)
    for a in preview['add']:
        parent = roots[a['root_type']] if a['parent'] is None else names[a['parent']]
        doc = frappe.get_doc(dict(doctype='Account', account_name=a['name'], account_number=a['number'], parent_account=parent, company=company_name,
                                  is_group=a['is_group'], root_type=a['root_type'], account_type=a['account_type'] or None,
                                  account_currency=frappe.get_cached_value('Company', company_name, 'default_currency')))
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert()
        names[a['number']] = doc.name
    d = preview['defaults']
    frappe.db.set_value('Company', company_name, dict(
        default_inventory_account=d['inventory_material'], stock_received_but_not_billed=d['received_not_billed'],
        stock_adjustment_account=d['stock_adjustment'], default_payable_account=d['payable_supplier'],
        default_cash_account=d['cash'], default_bank_account=d['bank'], default_payroll_payable_account=d['payable_employee'],
        default_expense_account=d['admin_expense'], round_off_account=d['round_off']))
    for w in preview['warehouses']:
        frappe.db.set_value('Warehouse', w['warehouse'], 'account', w['account'])
    frappe.flags.pop('warehouse_account_map', None)
    # A retired stock account (no warehouse points to it any more) stops being typed Stock, otherwise ERPNext
    # compares it with the value of every warehouse and refuses the journal that moves its balance to 152.
    for t in preview['transfer']:
        if frappe.db.get_value('Account', t['old'], 'account_type') == 'Stock':
            frappe.db.set_value('Account', t['old'], 'account_type', '')
    doc = settings()
    for key in rules.KEYS:
        if d.get(key) and not doc.get('acct_' + key):
            doc.set('acct_' + key, d[key])
    doc.company = doc.company or company_name
    voucher = None
    if preview['transfer']:
        voucher = _transfer_journal(company_name, preview['on_date'], preview['transfer'])
    translate_old_accounts(company_name)
    doc.coa_version = preview['version']
    doc.coa_applied_at = now_datetime()
    doc.coa_applied_by = frappe.session.user
    doc.flags.ignore_permissions = True
    doc.save()
    doc.add_comment('Info', 'Áp dụng %s; thêm %d tài khoản; chuyển số dư: %s' % (preview['version'], len(preview['add']), voucher or 'không có'))
    return dict(added=len(preview['add']), transfer=voucher)


def translate_old_accounts(company_name=None):
    """Vietnamese display names for ERPNext's Standard chart (replaced by TT133). Only account_name changes (the
    record name and every voucher stay as they are); retired leaf accounts are marked (TK cũ). Safe to rerun."""
    import json
    from pathlib import Path
    company_name = company_name or company()
    names = json.loads((Path(rules.COA_FILE).parent / 'erpnext_standard_accounts_vi.json').read_text(encoding='utf-8'))
    changed = 0
    for a in frappe.get_all('Account', filters={'company': company_name, 'account_number': ['in', ['', None]]}, fields=['name', 'account_name', 'is_group']):
        vi = names['groups'].get(a.account_name) if a.is_group else names['accounts'].get(a.account_name)
        if vi:
            frappe.db.set_value('Account', a.name, 'account_name', vi if a.is_group else vi + ' (TK cũ)', update_modified=False)
            changed += 1
    return changed


def _transfer_journal(company_name, on_date, transfer):
    cost_center = frappe.get_cached_value('Company', company_name, 'cost_center')
    accounts = []
    for t in transfer:
        b = t['balance']
        accounts.append(dict(account=t['new'], debit_in_account_currency=max(b, 0), credit_in_account_currency=max(-b, 0), cost_center=cost_center))
        accounts.append(dict(account=t['old'], debit_in_account_currency=max(-b, 0), credit_in_account_currency=max(b, 0), cost_center=cost_center))
    je = frappe.get_doc(dict(doctype='Journal Entry', voucher_type='Journal Entry', company=company_name, posting_date=on_date,
                             user_remark='Chuyển số dư sang hệ thống tài khoản TT133', accounts=accounts))
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    from lotus_farm.finance.posting import record
    record('Lotus Finance Settings', SETTINGS, 'Chart Transfer', je, amount=sum(abs(t['balance']) for t in transfer), source_hash='tt133')
    return je.name
