import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from lotus_farm.controls import lock, positive, validate_item, validate_warehouse


class HarvestLot(Document):
    def validate(self):
        self.company = frappe.db.get_value("Farm", self.farm, "company")
        if not self.company or not self.sources:
            frappe.throw("Phải có vườn và nguồn gốc thu hoạch.")
        seen = set()
        total = 0
        for row in sorted(self.sources, key=lambda r: r.harvest_actual):
            if row.harvest_actual in seen:
                frappe.throw("Mỗi lần thu hoạch thực tế chỉ được xuất hiện một lần trong lô.")
            seen.add(row.harvest_actual)
            lock("Harvest Actual", row.harvest_actual)
            actual = frappe.get_doc("Harvest Actual", row.harvest_actual)
            actual.check_permission("read")
            if actual.docstatus != 1 or actual.farm != self.farm:
                frappe.throw("Nguồn thu hoạch phải đã duyệt và thuộc vườn này.")
            if self.is_new() and not (actual.farm_plot or frappe.db.get_value('Crop Cycle',actual.crop_cycle,'farm_plot')):
                frappe.throw('Liên kết vụ nguồn với một thửa trước khi nhận lô mới này.')
            if getdate(self.received_date) < getdate(actual.harvest_date):
                frappe.throw("Ngày nhận lô không được trước ngày thu hoạch.")
            amount = positive(row.contributed_kg, "Contributed kg")
            source = frappe.qb.DocType("Harvest Lot Source")
            lot = frappe.qb.DocType("Harvest Lot")
            used = (
                frappe.qb.from_(source)
                .join(lot)
                .on(source.parent == lot.name)
                .select(source.contributed_kg)
                .where(
                    (source.harvest_actual == row.harvest_actual)
                    & (lot.docstatus == 1)
                    & (lot.name != self.name)
                )
                .run()
            )
            if sum(float(r[0]) for r in used) + amount > float(actual.saleable_weight_kg) + 0.0005:
                frappe.throw("Nguồn của lô vượt khối lượng đã thu hoạch được phát hành.")
            total += amount
        self.released_raw_kg = total
        if self.raw_item:
            validate_item(self.raw_item, batched=True)
        if self.raw_warehouse:
            validate_warehouse(self.raw_warehouse, self.company)
        if self.raw_batch and frappe.db.get_value("Batch", self.raw_batch, "item") != self.raw_item:
            frappe.throw("Lô hàng nguyên liệu phải khớp vật tư nguyên liệu.")

    def before_cancel(self):
        source = frappe.qb.DocType("Packout Run Source")
        run = frappe.qb.DocType("Packout Run")
        linked = (
            frappe.qb.from_(source)
            .join(run)
            .on(source.parent == run.name)
            .select(run.name)
            .where((source.harvest_lot == self.name) & (run.docstatus == 1))
            .run()
        )
        if linked:
            frappe.throw("Hủy các đợt đóng gói phụ thuộc trước khi hủy lô này.")
