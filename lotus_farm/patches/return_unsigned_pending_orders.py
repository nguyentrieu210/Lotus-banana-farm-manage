import frappe


def execute():
    """Spec 003: every purchase order is approved only by the signature of the approver named when it was sent.
    Orders still waiting without a signing round (sent before named approvers existed) go back to draft so the
    preparer sends them to a named approver. Running again changes nothing."""
    if not frappe.db.has_column('Purchase Order', 'lotus_approval_status'):
        return
    returned = []
    for name in frappe.get_all('Purchase Order', filters={'docstatus': 0, 'lotus_approval_status': 'Chờ duyệt'}, pluck='name'):
        if frappe.db.exists('Lotus Sign Request', {'document_type': 'Purchase Order', 'document_name': name}):
            continue
        values = dict(lotus_approval_status='Nháp')
        if frappe.db.has_column('Purchase Order', 'lotus_reject_reason'):
            values['lotus_reject_reason'] = 'Quy trình duyệt mới: chọn người duyệt rồi gửi lại.'
        frappe.db.set_value('Purchase Order', name, values, update_modified=False)
        returned.append(name)
    if returned:
        print('Đơn mua trả về nháp để gửi người duyệt được chỉ định:', ', '.join(returned))
