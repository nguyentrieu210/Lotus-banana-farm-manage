import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate
from lotus_farm.inheritance import lock_plot_cycles


class CropCycle(Document):
    def validate(self):
        from lotus_farm.controls import command_allowed
        if self.is_new() and self.status == "Closed":
            frappe.throw("Vụ mới không được bắt đầu ở trạng thái Đã đóng.")
        before=self.get_doc_before_save()
        if before and self.status != before.status and (self.status == "Closed" or before.status == "Closed") and not command_allowed(self,"cycle_close"):
            frappe.throw("Dùng báo cáo kết vụ đã kiểm tra để đóng hoặc mở lại vụ.")
        self._validate_block()
        self._validate_cycle()
        self._set_variety()
        self._validate_unique_cycle()

    def _validate_block(self):
        block = frappe.db.get_value("Farm Block", self.farm_block, ["farm", "variety"], as_dict=True)
        if not block:
            frappe.throw("Lô không tồn tại.")
        if block.farm != self.farm:
            frappe.throw("Lô phải thuộc vườn đã chọn.")

    def _validate_cycle(self):
        before = self.get_doc_before_save()
        changing_lineage = self.is_new() or not before or any(
            self.get(field) != before.get(field) for field in ('farm_plot', 'cycle_no', 'origin_basis', 'parent_cycle')
        )
        self._lotus_plot_cycles = lock_plot_cycles(self.farm_plot) if self.get('farm_plot') and changing_lineage else None
        other_cycles = [row for row in self._lotus_plot_cycles or [] if row.name != self.name]
        cycle_no = cint(self.cycle_no)
        if cycle_no < 1:
            frappe.throw("Số vụ phải từ 1 trở lên.")

        if cycle_no == 1:
            if self.get('origin_basis') == 'Handover':
                frappe.throw('Vụ kế thừa là vụ chồi từ số 2; không tạo vụ mẹ thiếu ngày trồng.')
            if any(row.origin_basis == 'Handover' for row in other_cycles):
                frappe.throw('Thửa đã mở vụ kế thừa; vụ tiếp theo phải liên kết vụ trước, không tạo lại vụ mẹ.')
            self.cycle_type = "Plant Crop"
            if not self.planting_date:
                frappe.throw("Vụ 1 phải có ngày trồng.")
            if self.parent_cycle:
                frappe.throw("Vụ 1 không được có vụ trước.")
        else:
            self.cycle_type = "Ratoon"
            if not self.parent_cycle:
                if self.get('origin_basis') == 'Handover':
                    from lotus_farm.controls import require_role
                    require_role('Lotus Farm Manager')
                    if not self.get('farm_plot'):
                        frappe.throw('Vụ kế thừa phải gắn với thửa theo dõi thực tế.')
                    if self.planting_date:
                        frappe.throw('Vụ kế thừa chưa biết ngày trồng: giữ trống ngày trồng, ghi ngày chọn chồi thực tế ở đợt chồi.')
                    if not (self.get('inheritance_note') or '').strip():
                        frappe.throw('Ghi rõ lý do không có hồ sơ vụ trước khi mở vụ kế thừa.')
                    if not self.get('coverage_start_date'):
                        frappe.throw('Vụ kế thừa cần ngày bắt đầu theo dõi thực tế theo lô.')
                    getdate(self.coverage_start_date)
                    previous = self.get_doc_before_save()
                    new_boundary = self.is_new() or not previous or previous.get('origin_basis') != 'Handover' or previous.get('farm_plot') != self.farm_plot
                    if new_boundary and other_cycles:
                        frappe.throw('Thửa đã có vụ theo dõi. Liên kết vụ trước thay vì mở thêm ranh giới bàn giao.')
                    if any(row.origin_basis == 'Handover' for row in other_cycles):
                        frappe.throw('Mỗi thửa chỉ có một vụ mở đầu kế thừa; vụ sau phải liên kết vụ trước.')
                    self.handover_zone = (previous.get('handover_zone') if previous and previous.get('origin_basis') == 'Handover' else None) or frappe.db.get_value('Farm Block', self.farm_block, 'farm_zone')
                    if not self.handover_zone:
                        frappe.throw('Lô kế thừa phải có khu đã khai báo.')
                    return
                frappe.throw("Vụ chồi (lưu gốc) phải có vụ trước.")
            if self.get('origin_basis') == 'Handover':
                frappe.throw('Đã có vụ trước liên kết: dùng nguồn vụ thực tế thay cho ranh giới bàn giao.')
            parent = frappe.db.get_value(
                "Crop Cycle",
                self.parent_cycle,
                ["farm", "farm_block", "farm_plot", "cycle_no"],
                as_dict=True,
            )
            if not parent:
                frappe.throw("Vụ trước không tồn tại.")
            if parent.farm != self.farm or parent.farm_block != self.farm_block or (parent.farm_plot or "") != (self.farm_plot or ""):
                frappe.throw("Vụ trước phải thuộc cùng lô.")
            if cint(parent.cycle_no) != cycle_no - 1:
                frappe.throw("Vụ trước phải là vụ liền kề trước đó.")

    def _set_variety(self):
        if not self.variety:
            self.variety = frappe.db.get_value("Farm Block", self.farm_block, "variety")

    def _validate_unique_cycle(self):
        if self._lotus_plot_cycles is not None:
            if any(row.name != self.name and cint(row.cycle_no) == cint(self.cycle_no) for row in self._lotus_plot_cycles):
                frappe.throw(f"Vụ {self.cycle_no} đã tồn tại ở lô {self.farm_block}.")
            return
        existing = frappe.db.get_value(
            "Crop Cycle",
            {"farm_block": self.farm_block, "farm_plot": self.farm_plot or "", "cycle_no": self.cycle_no},
            "name",
        )
        if existing and existing != self.name:
            frappe.throw(f"Vụ {self.cycle_no} đã tồn tại ở lô {self.farm_block}.")
