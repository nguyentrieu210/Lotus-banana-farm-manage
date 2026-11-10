import frappe
from frappe.model.document import Document

from lotus_farm.controls import check_farm


class WorkTeam(Document):
    def validate(self):
        check_farm(self)
        if frappe.db.exists("Work Team", {"farm": self.farm, "team_code": self.team_code, "name": ["!=", self.name]}):
            frappe.throw("Mã đội không được trùng trong cùng vườn.")
