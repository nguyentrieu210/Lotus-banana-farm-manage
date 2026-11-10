import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from lotus_farm import lot_ledger_rules as rules
from lotus_farm.field_report import validate_document

# Once confirmed a line never changes: a correction voids it (with a reason) and writes a new line.
FROZEN = ("farm", "farm_block", "work_team", "work_type", "stage", "cycle_no", "posting_date", "qty", "area_ha", "bunch_tag",
          "reject_stage", "reason", "weight_kg", "disease", "severity", "done", "source_key", "entered_by", "daily_report")


class LotusWorkEntry(Document):
    def validate(self):
        validate_document(self)
        before = self.get_doc_before_save()
        if before and before.state in (rules.CONFIRMED, rules.VOIDED):
            if before.state == rules.VOIDED or self.state in (rules.DRAFT, rules.SENT) or any(self.get(f) != before.get(f) for f in FROZEN):
                frappe.throw("Dòng đã xác nhận không được sửa; hủy dòng có lý do rồi ghi dòng mới.")
        if self.state == rules.VOIDED and not (self.void_reason or "").strip():
            frappe.throw("Hủy dòng phải ghi lý do.")
        if self.stage == rules.HARVEST and self.state != rules.VOIDED and not frappe.flags.lotus_ledger_migrating:
            from lotus_farm.lot_ledger import harvest_hold
            held = harvest_hold(self.farm_block, getdate(self.posting_date))
            if held:
                frappe.throw(f"Lô đang cách ly thuốc BVTV từ {held[0].strftime('%d/%m/%Y')} đến hết {held[1].strftime('%d/%m/%Y')}; "
                             "chưa được thu hoạch.")

    def on_update(self):
        before = self.get_doc_before_save()
        if (before.state if before else None) == self.state or self.state not in (rules.CONFIRMED, rules.VOIDED):
            return
        if any(int(m.phi_days or 0) for m in self.get("materials")):
            from lotus_farm.lot_ledger import refresh_quarantine
            refresh_quarantine(self.farm_block)

    def on_trash(self):
        if self.state != rules.DRAFT:
            frappe.throw("Không xóa dòng sổ lô đã gửi; hủy dòng có lý do.")
