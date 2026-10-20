import frappe


def execute():
    """Proposals sent before named signers existed have nobody assigned: hand them back to the proposer."""
    if not frappe.db.has_column('Material Request', 'lotus_proposal_state'):
        return
    waiting = ('Chờ phụ trách bộ phận', 'Chờ kế toán / mua hàng', 'Chờ giám đốc duyệt')
    for name in frappe.get_all('Material Request', filters={'docstatus': 0, 'lotus_proposal_state': ['in', waiting]}, pluck='name'):
        if frappe.db.exists('Lotus Sign Request', {'document_type': 'Material Request', 'document_name': name}):
            continue
        frappe.db.set_value('Material Request', name, dict(
            lotus_proposal_state='Trả lại',
            lotus_return_reason='Quy trình ký mới: chọn người ký cho từng bước rồi gửi lại.'), update_modified=False)
