"""Limited Warehouse business roles, separate from global ERP administrator roles."""
import frappe

ROLE_OPERATIONS={
 'Lotus Warehouse Operator': {
  'Stock Entry':('read','create','write','submit','print'),
  'Stock Ledger Entry':('read',),
  'Material Request':('read','create','write','submit'),
 },
 'Lotus Warehouse Requester': {
  'Material Request':('read','create','write','submit'),
 },
 'Lotus Purchasing Buyer': {
  'Supplier':('read','create','write'),
  'Purchase Order':('read','create','write','print'),
  'Material Request':('read',),
  'File':('read','create','write'),
 },
 'Lotus Purchase Requester': {
  'Material Request':('read',),
  'Supplier':('read','create','write'),
  'Purchase Order':('read','create','write','print'),
  'File':('read','create','write'),
 },
 'Lotus Warehouse Receiver': {
  'Purchase Receipt':('read','create','write','submit','print'),
  'File':('read','create','write'),
 },
 'Lotus Warehouse Manager': {
  'Item':('read','create','write'),
  'Item Group':('read','create','write'),
  'Warehouse':('read','create','write'),
  'Stock Reconciliation':('read','create','write','submit','print'),
  'Purchase Receipt':('read','cancel'),
  'UOM':('read','create'),
 },
 'Lotus Purchase Approver': {
  'Purchase Order':('read','write','submit','print'),
 }
}

REFERENCE_DOCTYPES=(
 'Company','Warehouse','Item','Item Group','UOM','Bin',
 'Supplier','Supplier Group','Material Request','Purchase Order',
 'Purchase Receipt','Stock Entry','Stock Reconciliation','Stock Ledger Entry'
)

def install_roles():
    """Idempotent role and document-permission installation; no cancellation or delete privilege."""
    from frappe.permissions import add_permission, update_permission_property
    def ensure(doctype, role, actions, operations):
        # Re-applying every unchanged flag clears Frappe metadata on each call.
        # Migrations should only write the permission flags that actually differ.
        filters={'parent':doctype,'role':role,'permlevel':0}
        current=frappe.db.get_value('Custom DocPerm',filters,operations,as_dict=True)
        if current is None:
            add_permission(doctype,role)
            current=frappe.db.get_value('Custom DocPerm',filters,operations,as_dict=True) or {}
        for operation in operations:
            expected=1 if operation in actions else 0
            if int(current.get(operation) or 0)!=expected:
                update_permission_property(doctype,role,0,operation,expected)
    for role, operations in ROLE_OPERATIONS.items():
        if not frappe.db.exists('Role',role):
            frappe.get_doc(dict(doctype='Role',role_name=role,desk_access=1)).insert(ignore_permissions=True)
        for doctype in REFERENCE_DOCTYPES:
            actions=set(operations.get(doctype,('read',)))
            # Purchaser/receiver must not edit another document without the explicit role.
            ensure(doctype,role,actions,('read','select','create','write','submit','cancel','delete',
                              'amend','report','export','import','share','print','email'))
            if doctype=='File' or 'File' in operations:
                pass
        if 'File' in operations:
            ensure('File',role,operations['File'],('read','create','write','delete'))

def provision_operator(email, company):
    """Provision a System User without committing or emailing credentials.

    Call only from an administrator-controlled console after reviewing the email address.
    Operational permissions include transactions and setup but NOT Purchase Order approval.
    """
    if frappe.session.user!='Administrator':
        frappe.throw('Cần quyền quản trị (Administrator).',frappe.PermissionError)
    if not frappe.db.exists('Company',company):
        frappe.throw('Không tìm thấy công ty.')
    if not frappe.utils.validate_email_address(email,throw=False):
        frappe.throw('Email không hợp lệ.')
    install_roles()
    roles=('Lotus Warehouse Operator','Lotus Warehouse Requester',
           'Lotus Warehouse Receiver','Lotus Warehouse Manager')
    if frappe.db.exists('User',email):
        user=frappe.get_doc('User',email)
        if user.user_type!='System User':
            frappe.throw('Tài khoản đã có không phải người dùng hệ thống; hãy kiểm tra trước khi thay đổi.')
    else:
        user=frappe.get_doc(dict(doctype='User',email=email,
            first_name=email.split('@')[0],user_type='System User',
            enabled=1,send_welcome_email=0))
        user.insert(ignore_permissions=True)
    user.add_roles(*roles)
    user.enabled=1
    user.save(ignore_permissions=True)
    if not frappe.db.exists('User Permission',dict(user=user.name,allow='Company',for_value=company)):
        frappe.get_doc(dict(doctype='User Permission',user=user.name,allow='Company',
            for_value=company,apply_to_all_doctypes=1)).insert(ignore_permissions=True)
    return dict(user=user.name,enabled=user.enabled,roles=roles,
                company=company,send_welcome_email=False)
