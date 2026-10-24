"""Additive schema for the purchase workspace; never changes existing Item flags or ledgers."""
import frappe

FUNDING_KEYS = {
    'purchase_funding_liability': ('Phải hoàn tiền cá nhân chi hộ', ('Liability',)),
    'purchase_funding_equity': ('Vốn góp bằng khoản chi hộ', ('Equity',)),
}


def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    fields = {}
    for dt in ('Material Request Item', 'Supplier Quotation Item', 'Purchase Order Item', 'Purchase Receipt Item', 'Purchase Invoice Item'):
        fields[dt] = [dict(fieldname='lotus_purchase_kind', label='Loại mua', fieldtype='Select',
                           options='\nMaterial\nTool\nAsset\nService', insert_after='item_code'),
                      dict(fieldname='lotus_line_vat', label='VAT dòng mua', fieldtype='Select',
                           options='\nKCT\n0\n5\n8\n10', insert_after='lotus_purchase_kind'),
                      dict(fieldname='lotus_line_freight', label='Vận chuyển dòng mua', fieldtype='Currency',
                           insert_after='lotus_line_vat'),
                      dict(fieldname='lotus_quote_reason', label='Lý do chọn báo giá', fieldtype='Small Text',
                           insert_after='lotus_line_freight')]
        if not frappe.get_meta(dt).has_field('lotus_farm'):
            fields[dt].append(dict(fieldname='lotus_farm',label='Vườn mua hàng',fieldtype='Link',options='Farm'))
    for dt in ('Supplier', 'Item', 'Supplier Quotation', 'Purchase Order', 'Material Request', 'Purchase Invoice', 'Payment Entry', 'Journal Entry'):
        fields.setdefault(dt, []).extend([
            dict(fieldname='lotus_procurement_key', label='Purchase request key', fieldtype='Data', unique=1, hidden=1, read_only=1, no_copy=1),
            dict(fieldname='lotus_procurement_hash', label='Purchase request hash', fieldtype='Data', hidden=1, read_only=1, no_copy=1),
        ])
    fields['Supplier Quotation'].append(dict(fieldname='lotus_delivery_date', label='Ngày có thể giao', fieldtype='Date'))
    fields['Item'].append(dict(fieldname='lotus_default_purchase_kind',label='Loại mua gợi ý',fieldtype='Select',options='\nMaterial\nTool\nAsset\nService',insert_after='item_group'))
    fields['Journal Entry'].extend([
        dict(fieldname='lotus_purchase_funding', label='Khoản chi hộ', fieldtype='Link', options='Lotus Purchase Funding', read_only=1, no_copy=1),
        dict(fieldname='lotus_funding_hash', label='Nội dung khoản chi hộ', fieldtype='Data', hidden=1, read_only=1, no_copy=1),
    ])
    fields['Lotus Finance Settings'] = [dict(fieldname='acct_'+key, label=label, fieldtype='Link', options='Account')
                                       for key, (label, _) in FUNDING_KEYS.items()]
    create_custom_fields(fields, update=True)
    # A minimal site may not have completed ERPNext's address setup yet.
    # Use Frappe's own template only when no default exists; preserve custom templates.
    if not frappe.db.exists('Address Template', {'is_default':1}):
        country=frappe.defaults.get_global_default('country') or 'Vietnam'
        if frappe.db.exists('Country',country) and not frappe.db.exists('Address Template',country):
            frappe.get_doc(dict(doctype='Address Template',country=country,is_default=1)).insert(ignore_permissions=True)
    # ERPNext's supported setting permits one row per physical asset while keeping
    # every row tied to its original PO/receipt line. Quantities remain guarded below.
    if not frappe.db.get_single_value('Buying Settings','allow_multiple_items'):
        frappe.db.set_single_value('Buying Settings','allow_multiple_items',1)
    # Standard permissions remain the boundary for every ERPNext document.
    from frappe.permissions import add_permission, update_permission_property
    for role in ('Lotus Purchasing Buyer','Lotus Purchase Requester','Lotus Purchase Approver','Lotus Warehouse Receiver','Lotus Warehouse Manager'):
        if not frappe.db.exists('Custom DocPerm',{'parent':'Account','role':role,'permlevel':0}):
            add_permission('Account',role)
            update_permission_property('Account',role,0,'read',0)
        update_permission_property('Account',role,0,'select',1)
    for role in ('Lotus Purchasing Buyer', 'Lotus Warehouse Manager', 'Lotus Accountant', 'Lotus Chief Accountant', 'Accounts User', 'Accounts Manager'):
        if not frappe.db.exists('Role', role):
            continue
        for dt in ('Supplier Quotation',):
            add_permission(dt, role)
            for permission in ('read', 'create', 'write', 'submit'):
                update_permission_property(dt, role, 0, permission, 1)
    for role in ('Lotus Accountant','Lotus Chief Accountant','Accounts User','Accounts Manager'):
        for dt in ('Purchase Order','Material Request','Supplier Quotation'):
            add_permission(dt,role)
            update_permission_property(dt,role,0,'read',1)
        add_permission('Shareholder',role)
        update_permission_property('Shareholder',role,0,'read',1)
        if role in ('Lotus Chief Accountant','Accounts Manager'):
            for permission in ('create','write'):
                update_permission_property('Shareholder',role,0,permission,1)
    for role in ('Lotus Purchasing Buyer', 'Lotus Warehouse Manager', 'Lotus Accountant', 'Lotus Chief Accountant', 'Accounts User', 'Accounts Manager'):
        if not frappe.db.exists('Role', role):
            continue
        for dt in ('Supplier', 'Item', 'Address', 'Contact'):
            add_permission(dt, role)
            for permission in ('read', 'create', 'write'):
                update_permission_property(dt, role, 0, permission, 1)
        for dt in ('Supplier Group', 'Item Group', 'UOM', 'Country', 'Payment Terms Template', 'Asset Category', 'Bank'):
            add_permission(dt, role)
            update_permission_property(dt, role, 0, 'read', 1)
        if role in ('Lotus Accountant', 'Lotus Chief Accountant', 'Accounts User', 'Accounts Manager'):
            add_permission('Bank Account', role)
            for permission in ('read', 'create', 'write'):
                update_permission_property('Bank Account', role, 0, permission, 1)


def funding_accounts(cfg=None):
    from lotus_farm.finance import setup
    cfg = cfg or setup.settings()
    return {key: cfg.get('acct_'+key) for key in FUNDING_KEYS}


def check_funding_account(key, company):
    name = funding_accounts().get(key)
    row = frappe.db.get_value('Account', name, ['company', 'is_group', 'disabled', 'root_type', 'account_type'], as_dict=True) if name else None
    if not row or row.company != company or row.is_group or row.disabled or row.root_type not in FUNDING_KEYS[key][1] or row.account_type in ('Payable', 'Receivable'):
        frappe.throw('Thiết lập tài khoản “%s” tại Mua hàng › Thanh toán › Tài khoản chi hộ trước khi trình ký.' % FUNDING_KEYS[key][0])
    return name
