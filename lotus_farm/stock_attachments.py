"""Chứng từ đính kèm phiếu kho và chứng từ mua hàng: ảnh chụp, PDF phiếu giao hàng / hóa đơn / báo giá làm bằng chứng.

The browser uploads a private File first (frappe upload_file); these calls then attach that file to a stock document
the user can read. Files stay private and are served only to users who can read the document.
"""
import os

import frappe

from lotus_farm.warehouse import _stock_doc

STOCK_DOCTYPES = ('Stock Entry', 'Stock Reconciliation')
# Purchasing documents only need read access to the document itself (buyers may not read stock entries).
PURCHASE_DOCTYPES = ('Purchase Receipt', 'Purchase Order', 'Supplier Quotation', 'Material Request')
DOCTYPES = STOCK_DOCTYPES + PURCHASE_DOCTYPES
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.pdf'}
MAX_FILES = 20


def _document(doctype, name):
    if doctype not in DOCTYPES:
        frappe.throw('Loại phiếu không hỗ trợ đính kèm.')
    if doctype in PURCHASE_DOCTYPES:
        if frappe.session.user == 'Guest':
            frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
        doc = frappe.get_doc(doctype, name)
        doc.check_permission('read')
        return doc
    return _stock_doc(doctype, name)


def _rows(doctype, name):
    rows = frappe.get_all('File', filters={'attached_to_doctype': doctype, 'attached_to_name': name},
                          fields=['name', 'file_name', 'file_url', 'owner', 'creation', 'file_size'], order_by='creation asc')
    me = frappe.session.user
    for row in rows:
        row.is_image = os.path.splitext(row.file_name or '')[1].lower() in EXTENSIONS - {'.pdf'}
        row.mine = row.owner == me
    return rows


@frappe.whitelist()
def files(doctype, name):
    _document(doctype, name)
    return _rows(doctype, name)


@frappe.whitelist(methods=['POST'])
def attach(doctype, name, file_url):
    doc = _document(doctype, name)
    file = frappe.get_doc('File', {'file_url': file_url})
    if file.owner != frappe.session.user:
        frappe.throw('Chỉ đính kèm được tệp do chính bạn vừa tải lên.', frappe.PermissionError)
    if file.attached_to_name and (file.attached_to_doctype, file.attached_to_name) != (doctype, name):
        frappe.throw('Tệp này đã gắn với chứng từ khác.')
    if os.path.splitext(file.file_name or '')[1].lower() not in EXTENSIONS:
        frappe.throw('Chỉ đính kèm ảnh (JPG, PNG, WEBP, HEIC) hoặc PDF.')
    if frappe.db.count('File', {'attached_to_doctype': doctype, 'attached_to_name': name}) >= MAX_FILES:
        frappe.throw(f'Mỗi phiếu đính kèm tối đa {MAX_FILES} tệp.')
    file.attached_to_doctype, file.attached_to_name, file.is_private = doctype, doc.name, 1
    file.save(ignore_permissions=True)
    return _rows(doctype, doc.name)


@frappe.whitelist(methods=['POST'])
def remove(doctype, name, file):
    doc = _document(doctype, name)
    row = frappe.get_doc('File', file)
    if (row.attached_to_doctype, row.attached_to_name) != (doctype, doc.name):
        frappe.throw('Tệp không thuộc phiếu này.')
    # Evidence of a posted document is permanent; drafts can drop files their uploader added by mistake.
    if doc.docstatus != 0:
        frappe.throw('Phiếu đã ghi sổ: không xóa được chứng từ đính kèm.')
    if row.owner != frappe.session.user and 'Stock Manager' not in frappe.get_roles():
        frappe.throw('Chỉ người tải lên hoặc quản lý kho được xóa tệp này.', frappe.PermissionError)
    frappe.delete_doc('File', row.name, ignore_permissions=True)
    return _rows(doctype, doc.name)
