from frappe.model.document import Document


class LotusFinancialPlan(Document):
    def validate(self):
        from lotus_farm.finance.planning import validate_document
        validate_document(self)

    def on_trash(self):
        if self.state == 'Approved':
            import frappe
            frappe.throw('Không được xóa kế hoạch đã duyệt. Nhân bản để lập phương án mới.')
